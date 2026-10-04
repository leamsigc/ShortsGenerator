import re
import json
import time
import threading
import g4f
from g4f.models import Model, ModelUtils
from typing import Tuple, List, Optional, Dict, Any
from termcolor import colored
from dotenv import load_dotenv
import os
from google import genai

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv("../.env")

# Set environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

# Configure g4f - enable auto update and logging
g4f.version_checking = False
g4f.debug.logging = True


def _patch_g4f_copilot_shim() -> None:
    """Work around a broken g4f release: 8.6.0's needs_auth/MicrosoftDesigner
    does `from ..Copilot import get_headers, get_har_files`, but those helpers
    no longer exist in Provider/Copilot.py — so the whole needs_auth package
    (including the Gemini provider this backend uses) becomes unimportable.
    Inject harmless stand-ins when they're missing; a fixed g4f release that
    defines them again makes this a no-op. (MicrosoftDesigner itself is never
    used here; only its import-time names matter. Note: `import
    g4f.Provider.Copilot` binds the provider *class* via g4f's lazy loader —
    the real module must be patched through sys.modules.)
    """
    try:
        import importlib
        import sys as _sys
        import types as _types
        importlib.import_module("g4f.Provider.Copilot")
        module = _sys.modules.get("g4f.Provider.Copilot")
        if not isinstance(module, _types.ModuleType):
            return
        if not hasattr(module, "get_headers"):
            module.get_headers = lambda *args, **kwargs: {}
        if not hasattr(module, "get_har_files"):
            module.get_har_files = lambda *args, **kwargs: []
    except Exception as e:
        print(colored(f"[-] g4f compat shim failed: {e}", "yellow"))


_patch_g4f_copilot_shim()

G4F_GEMINI_MAX_ATTEMPTS = 2

def _configured_provider() -> str:
    """Provider selected in Settings → AI Model Provider ('g4f' = legacy cookie path)."""
    try:
        from llm_providers import get_llm_settings
        provider = str(get_llm_settings().get("provider") or "").strip()
        return provider or "g4f"
    except Exception:
        return "g4f"


def _is_transient_error(e: Exception) -> bool:
    """Provider errors worth retrying (rate limits / overload / network)."""
    message = str(e).lower()
    return any(marker in message for marker in (
        '503', '429', '502', '504', 'unavailable', 'overloaded', 'quota',
        'rate limit', 'timeout', 'timed out', 'temporarily', 'try again',
        'connection', 'resource exhausted',
    ))


def _resolve_gemini_sdk_credentials() -> Tuple[Optional[str], str]:
    """API key + model for the official Google SDK path.

    Prefers the Settings → AI Model Provider config (gemini + custom key/model)
    and falls back to GOOGLE_API_KEY / GEMINI_SDK_MODEL from the environment.
    """
    api_key = GOOGLE_API_KEY or os.getenv('GOOGLE_API_KEY')
    model = os.getenv('GEMINI_SDK_MODEL', 'gemini-3.6-flash')
    try:
        from llm_providers import get_llm_settings
        settings = get_llm_settings()
        if str(settings.get("provider") or "").strip() == "gemini":
            api_key = str(settings.get("api_key") or "").strip() or api_key
            model = str(settings.get("model") or "").strip() or model
    except Exception:
        pass
    return api_key, model


_SDK_CLIENTS: Dict[str, Any] = {}


def _generate_via_google_sdk(prompt: str) -> str:
    api_key, model = _resolve_gemini_sdk_credentials()
    if not api_key:
        raise ValueError(
            "No Gemini API key configured — paste one in Settings → AI Model "
            "Provider or set GOOGLE_API_KEY in .env"
        )
    print(colored(f"[*] Using Google AI SDK, model={model}", "cyan"))
    # NOTE: 'gemini-3.5-flash' is a g4f-only alias and does not exist in the
    # official API. Use a real official model (override with GEMINI_SDK_MODEL
    # or the model picked in Settings).
    # The client MUST stay referenced for the whole call: a temporary
    # genai.Client(...) gets finalized mid-request and its httpx transport is
    # closed -> "Cannot send a request, as the client has been closed."
    client = _SDK_CLIENTS.get(api_key)
    if client is None:
        client = genai.Client(api_key=api_key)
        _SDK_CLIENTS[api_key] = client
    return client.models.generate_content(
        model=model,
        contents=prompt
    ).text

# Cookies g4f needs for the Gemini browser session. SAPISID /
# __Secure-1PAPISID / __Secure-3PAPISID build the SAPISIDHASH Authorization
# header — dropping them guarantees a 400 xsrf failure on batchexecute.
# Only cookie NAMES are ever logged; values are secrets, never printed.
_GEMINI_ESSENTIAL_COOKIES = (
    '__Secure-1PSID', '__Secure-3PSID',
    '__Secure-1PSIDTS', '__Secure-3PSIDTS',
    'SAPISID', '__Secure-1PAPISID', '__Secure-3PAPISID',
    'HSID', 'SSID', 'APISID', 'SID',
)
# Without these the Google session is dead on arrival (logged out / expired).
_GEMINI_AUTH_COOKIES = ('__Secure-1PSID', 'SAPISID', '__Secure-1PAPISID')


class _AttemptWatchdog:
    """Heartbeat logs while a g4f attempt runs, so a stall shows up in the
    backend log with its current phase instead of failing silently at the
    outer timeout."""

    _HINTS = {
        "reading-cookies":
            "reading the browser cookie DB (should be instant — a stuck read means a locked browser profile)",
        "waiting-first-token":
            "Google hasn't answered yet — throttled/flagged session or rejected model; "
            "see the cookie checklist in Settings → AI Model Provider",
        "streaming":
            "response stream stalled mid-way — network or provider hiccup",
    }

    def __init__(self, label: str, interval: int = 15, max_wait: Optional[float] = None):
        self.label = label
        self.interval = interval
        # Self-deadline: the outer _call_with_timeout abandons (but cannot
        # kill) the hung worker thread, so without this the heartbeat would
        # keep logging long after the attempt already failed.
        self.max_wait = max_wait
        self._phase = "starting"
        self._t0 = time.time()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"watchdog-{label}", daemon=True)

    def set_phase(self, phase: str) -> None:
        self._phase = phase

    def __enter__(self) -> "_AttemptWatchdog":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> bool:
        self._stop.set()
        self._thread.join(timeout=2)
        return False

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            elapsed = time.time() - self._t0
            if self.max_wait is not None and elapsed >= self.max_wait:
                break
            hint = self._HINTS.get(self._phase, "")
            print(colored(
                f"[...] {self.label}: still waiting ({elapsed:.0f}s) — phase: {self._phase}. {hint}",
                "yellow"))


def _load_gemini_cookie_diagnostics() -> Dict[str, Any]:
    """Read .google.com cookies per browser and grade them for Gemini use.

    Re-reads the browser stores on every call (Google rotates __Secure-1PSIDTS;
    g4f's in-process cache would otherwise serve pre-login values forever).
    Returns {"browser", "per_browser", "total", "essential", "missing",
    "cookies", "error"}. "cookies" holds live values for internal use only —
    callers must only ever log names/counts from this dict.
    """
    diag: Dict[str, Any] = {
        "browser": None, "per_browser": {}, "total": 0, "essential": 0,
        "missing": list(_GEMINI_ESSENTIAL_COOKIES), "cookies": {}, "error": None,
    }
    try:
        from g4f.cookies import load_cookies_from_browsers, set_cookies, BROWSERS
        set_cookies('.google.com')  # drop stale cache so we read the disk
        # "all" returns per-browser {name: value} dicts (no cache write).
        # Same winner as g4f's single-browser mode: first non-empty jar in
        # BROWSERS order (g4f profile, firefox, chrome, …).
        per_browser_raw = load_cookies_from_browsers('.google.com', False, "all")
        merged: Dict[str, str] = {}
        for browser_fn in BROWSERS:
            jar = {k: v for k, v in (per_browser_raw.get(browser_fn.__name__) or {}).items()
                   if k != "config"}
            diag["per_browser"][browser_fn.__name__] = len(jar)
            if diag["browser"] is None and jar:
                diag["browser"] = browser_fn.__name__
                merged = dict(jar)
        diag["total"] = len(merged)
        diag["cookies"] = merged
        diag["essential"] = sum(1 for k in merged if k in _GEMINI_ESSENTIAL_COOKIES)
        diag["missing"] = [k for k in _GEMINI_ESSENTIAL_COOKIES if k not in merged]
        # Seed g4f's cache with this fresh read so later g4f-internal
        # cookie lookups in the same attempt reuse it instead of re-reading.
        set_cookies('.google.com', merged)
    except Exception as e:
        diag["error"] = f"{type(e).__name__}: {e}"
    return diag


def describe_gemini_cookies() -> str:
    """One-line cookie health summary, for logs and the Test-connection result."""
    diag = _load_gemini_cookie_diagnostics()
    if diag["error"]:
        return (f"cookies: unreadable ({diag['error']}) — no usable browser "
                "cookie store on this PC?")
    if not diag["browser"]:
        return ("cookies: none found for .google.com in any browser — log in at "
                "gemini.google.com in Firefox/Chrome on this PC, then re-test")
    base = (f"cookies: {diag['browser']} · {diag['total']} total → "
            f"{diag['essential']} essential")
    if diag["missing"]:
        return (base + f" · MISSING {', '.join(diag['missing'])} — session expired "
                "or logged out: log in again at gemini.google.com (same browser, "
                "no private window), then re-test")
    return base + " · missing: none"


def _resolve_cookie_gemini_model(explicit: Optional[str] = None) -> Tuple[str, str]:
    """Model to actually send on the cookie path, plus the picked name.

    The installed g4f maps old aliases (e.g. gemini-3.5-flash → gemini-3.6-flash);
    both names are logged so the backend log always shows what Google received.
    """
    model = (explicit or "").strip()
    if not model:
        try:
            from llm_providers import get_llm_settings, DEFAULT_SETTINGS
            settings = get_llm_settings()
            model = str(settings.get("g4f_model") or DEFAULT_SETTINGS.get("g4f_model") or "").strip()
        except Exception:
            pass
    if not model:
        model = "gemini-3.6-flash"
    sent = model
    try:
        from g4f.Provider.needs_auth.Gemini import MODEL_ALIASES, models
        sent = MODEL_ALIASES.get(model, model)
        if model not in models and model not in MODEL_ALIASES:
            print(colored(
                f"[!] g4f Gemini: model '{model}' is unknown to the installed g4f "
                f"({len(models)} known) — sending it anyway; Google may reject or "
                "ignore it. Prefer a model from the Settings dropdown.", "yellow"))
    except Exception:
        pass
    return sent, model


def _generate_via_g4f_gemini(prompt: str, attempt: int, sent_model: str, picked_model: str,
                           timeout_sec: int = 60) -> str:
    from g4f.client import Client as G4FClient
    from g4f import Provider
    from g4f.Provider.needs_auth import Gemini
    import aiohttp

    label = f"g4f Gemini attempt {attempt}"
    started = time.time()
    with _AttemptWatchdog(label, max_wait=timeout_sec) as watch:
        # Phase 1 — cookies. Values are never logged, only names/counts.
        watch.set_phase("reading-cookies")
        diag = _load_gemini_cookie_diagnostics()
        if diag["error"]:
            raise RuntimeError(f"Could not read browser cookies: {diag['error']}")
        if not diag["browser"]:
            raise RuntimeError(
                "No .google.com cookies in any browser — log in at gemini.google.com "
                "in Firefox/Chrome on this PC first (see the cookie checklist in "
                "Settings → AI Model Provider)")
        cookie_line = (f"{diag['browser']}: {diag['total']} total → "
                       f"{diag['essential']} essential"
                       + (", missing: none" if not diag["missing"]
                          else f", MISSING: {', '.join(diag['missing'])}"))
        if any(k in diag["missing"] for k in _GEMINI_AUTH_COOKIES):
            print(colored(
                f"[!] {label} cookies incomplete ({cookie_line}) — Google will reject "
                "this session; re-login needed before retrying", "red"))
        else:
            print(colored(
                f"[*] {label} cookies OK ({cookie_line}) [{time.time() - started:.1f}s]",
                "cyan"))
        Gemini._cookies = {k: v for k, v in diag["cookies"].items()
                           if k in _GEMINI_ESSENTIAL_COOKIES}
        # Drop cached session metadata so g4f rediscovers snlm0e/sid with the
        # fresh cookies instead of reusing the rejected session.
        # (g4f>=7.9 tracks _metadata_cookie_key/_metadata_auth_user too —
        # reset them so the provider's own staleness check stays consistent.)
        Gemini._snlm0e = None
        Gemini._sid = None
        Gemini._metadata_fetched_at = 0
        Gemini._metadata_cookie_key = None
        Gemini._metadata_auth_user = None
        Gemini._account_status = None
        Gemini._account_models = {}
        Gemini._account_models_fetched_at = 0

        if not getattr(aiohttp.ClientSession, "_shorts_patched", False):
            original_init = aiohttp.ClientSession.__init__
            def _patched_init(self, *args, **kwargs):
                kwargs.setdefault('max_line_size', 65536)
                kwargs.setdefault('max_field_size', 65536)
                return original_init(self, *args, **kwargs)
            aiohttp.ClientSession.__init__ = _patched_init
            aiohttp.ClientSession._shorts_patched = True

        # Phase 2 — request, streamed so the first token is timed. Everything
        # before the first chunk (snlm0e metadata GET, models POST, generation
        # POST) runs inside g4f with no per-call timeout, which is exactly the
        # black box the watchdog narrates while we wait.
        model_note = picked_model if picked_model == sent_model else f"{picked_model} → {sent_model}"
        watch.set_phase("waiting-first-token")
        req_sent_at = time.time()
        print(colored(
            f"[>] {label}: request sent (model {model_note}), waiting for first token…",
            "cyan"))
        g4f_client = G4FClient(provider=Provider.Gemini)
        try:
            stream = g4f_client.chat.completions.create(
                model=sent_model,
                messages=[{"role": "user", "content": prompt}],
                web_search=False,
                stream=True,
            )
            iterator = iter(stream)
        except TypeError:
            # g4f without stream= support: one blocking call instead. No
            # first-token timing, but the watchdog still narrates the wait.
            print(colored(f"[*] {label}: streaming unsupported, using blocking call", "cyan"))
            response = g4f_client.chat.completions.create(
                model=sent_model,
                messages=[{"role": "user", "content": prompt}],
                web_search=False,
            )
            text = response.choices[0].message.content or ""
            if not text.strip():
                raise ValueError(f"{picked_model} returned empty response")
            print(colored(f"[+] {label}: done in {time.time() - started:.1f}s, {len(text)} chars", "green"))
            return text

        parts: List[str] = []
        first_token_at: Optional[float] = None
        for chunk in iterator:
            try:
                part = chunk.choices[0].delta.content or ""
            except Exception:
                part = ""  # usage / heartbeat chunks carry no text
            if part and first_token_at is None:
                first_token_at = time.time()
                watch.set_phase("streaming")
                print(colored(
                    f"[+] {label}: first token after {first_token_at - req_sent_at:.1f}s, streaming…",
                    "green"))
            parts.append(part)
        text = "".join(parts)
        if not text.strip():
            raise ValueError(f"{picked_model} returned empty response")
        print(colored(f"[+] {label}: done in {time.time() - started:.1f}s, {len(text)} chars", "green"))
        return text

# Cookie-free g4f chain, verified live against the installed g4f release.
# Free mirrors change fast, so the user's selection is tried first and the
# rest serve as fallbacks in order.
G4F_FREE_CHAIN = [
    ("DeepAI", "gemini-2.5-flash-lite"),
    ("DeepAI", "deepseek-v3.2"),
    ("Perplexity", "auto"),
    ("Yqcloud", "gpt-4"),
]

def resolve_g4f_provider(name: str):
    """Resolve a g4f provider class by name (top-level or needs_auth)."""
    import importlib
    for pkg in ("g4f.Provider", "g4f.Provider.needs_auth"):
        try:
            mod = importlib.import_module(f"{pkg}.{name}")
        except ImportError:
            continue
        provider = getattr(mod, name, None)
        if isinstance(provider, type) and hasattr(provider, "working"):
            return provider
    raise ValueError(f"Unknown g4f provider: {name!r}")


def list_g4f_providers() -> list:
    """Enumerate installed g4f providers for the settings dropdowns."""
    import pkgutil
    import inspect
    import g4f.Provider as top
    try:
        import g4f.Provider.needs_auth as auth
        packages = [(top, False), (auth, True)]
    except ImportError:
        packages = [(top, False)]
    skip_modules = {'base_provider', 'helper', 'template', 'retry', 'route',
                    'any_provider', 'audio', 'search', 'local', 'openai', 'qwen',
                    'hf_space', 'image', 'video'}
    providers = []
    for pkg, needs_auth_pkg in packages:
        try:
            modules = list(pkgutil.iter_modules(pkg.__path__))
        except Exception:
            continue
        for _, mod_name, _ in modules:
            if mod_name.startswith('_') or mod_name in skip_modules:
                continue
            try:
                mod = __import__(f"{pkg.__name__}.{mod_name}", fromlist=["*"])
            except Exception:
                continue
            for _, cls in inspect.getmembers(mod, inspect.isclass):
                if cls.__module__ != mod.__name__ or not hasattr(cls, 'working'):
                    continue
                if not getattr(cls, 'working', False):
                    continue
                models = getattr(cls, 'models', None)
                if isinstance(models, dict):
                    models = list(models.keys())
                models = [str(m) for m in (models or [])][:80]
                name = cls.__name__
                providers.append({
                    "id": name,
                    "label": getattr(cls, 'label', name),
                    "url": getattr(cls, 'url', ''),
                    "default_model": str(getattr(cls, 'default_model', '') or ''),
                    "models": models,
                    # Gemini web needs browser cookies despite needs_auth=False.
                    "needs_cookies": bool(getattr(cls, 'needs_auth', False)) or needs_auth_pkg or 'Gemini' in name,
                })
    providers.sort(key=lambda p: (p["needs_cookies"], p["id"]))
    return providers

G4F_COOKIE_RENEW_STEPS = [
    "Cookies come from the browsers on the PC running the backend — log in there, not on your phone.",
    "In Firefox (or Chrome) on that PC, open gemini.google.com and log in — no private/incognito window.",
    "Send one message on the Gemini website. If it answers, the session is alive.",
    "If it already shows you logged in, log OUT and back IN — this rotates the __Secure-1PSIDTS token g4f needs.",
    "Back here, press 'Check cookies': it must say fresh. Then 'Test connection' and watch backend.log — "
    "expect 'cookies OK (… missing: none)' followed by 'first token after …s'.",
    "Stuck on 'waiting for first token' until it times out? Google is throttling this session: wait a while, "
    "log out/in again — or switch Provider to 'gemini' + API key.",
    "No backend restart needed after re-login — cookies are re-read on every attempt.",
    "No luck? Turn OFF 'Use browser cookies' to use cookie-free providers instead.",
]

def _call_with_timeout(fn, timeout_sec: int, label: str):
    """Run fn() but give up after timeout_sec (hung providers fail fast).

    The worker thread can't be killed, so it may linger in the background —
    the caller moves on regardless instead of hanging forever.
    """
    import concurrent.futures
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        fut = ex.submit(fn)
        try:
            return fut.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError as e:
            raise TimeoutError(f"{label} timed out after {timeout_sec}s") from e
    finally:
        ex.shutdown(wait=False, cancel_futures=True)


def _run_g4f_attempts(prompt: str, attempts, timeout_sec: int = 45) -> str:
    """Try each (provider, model) pair cookie-free. Raises the last error."""
    from g4f.client import Client as G4FClient
    last_error: Exception = ValueError("No g4f cookie-free provider attempted")
    for provider_name, model in attempts:
        try:
            provider = resolve_g4f_provider(provider_name)
            if not model:
                model = str(getattr(provider, 'default_model', '') or '')
            print(colored(f"[*] g4f cookie-free: {provider_name}/{model}", "cyan"))
            g4f_client = G4FClient(provider=provider)
            # 45s each: a hung mirror must not stall generation forever.
            response = _call_with_timeout(
                lambda: g4f_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout_sec, f"{provider_name}/{model}",
            )
            text = response.choices[0].message.content
            if text and text.strip():
                return text
            last_error = ValueError(f"{provider_name}/{model} returned empty response")
        except Exception as e:
            last_error = e
            print(colored(f"[-] g4f cookie-free {provider_name}/{model} failed: {e}", "yellow"))
    raise last_error


def _g4f_selected(settings) -> Tuple[str, str]:
    """The (provider, model) picked in Settings → AI Model Provider."""
    from llm_providers import DEFAULT_SETTINGS
    provider_name = str(settings.get("g4f_provider") or DEFAULT_SETTINGS["g4f_provider"]).strip()
    model = str(settings.get("g4f_model") or DEFAULT_SETTINGS["g4f_model"]).strip()
    return provider_name, model


def _g4f_free_attempts(settings) -> list:
    """Provider/model selected in Settings first, then the built-in chain."""
    selected = _g4f_selected(settings)
    attempts = [selected] if selected[0] else []
    for entry in G4F_FREE_CHAIN:
        if entry not in attempts:
            attempts.append(entry)
    return attempts


def _generate_via_g4f_free(prompt: str) -> str:
    """g4f without cookies and without API keys. Raises on total failure."""
    from llm_providers import get_llm_settings
    return _run_g4f_attempts(prompt, _g4f_free_attempts(get_llm_settings()))


def _try_cookie_gemini(prompt: str, model: Optional[str] = None) -> str:
    """Cookie path for the g4f Gemini provider. Raises the last error.

    `model` is the g4f model picked in Settings (falls back to the saved
    g4f_model, then g4f's own default) — it is what Google actually receives,
    so the failure message names the real model.
    """
    sent_model, picked_model = _resolve_cookie_gemini_model(model)
    last_error: Exception = ValueError("No g4f Gemini attempt was made")
    # 90s cap: this session answers slowly when throttled (first token observed
    # at ~49s), but g4f/aiohttp would otherwise wait up to 5 min with zero
    # feedback. The watchdog heartbeat narrates the live phase while we wait.
    attempt_cap = 90
    for attempt in range(1, G4F_GEMINI_MAX_ATTEMPTS + 1):
        try:
            return _call_with_timeout(
                lambda: _generate_via_g4f_gemini(prompt, attempt, sent_model, picked_model,
                                                timeout_sec=attempt_cap),
                attempt_cap, f"g4f Gemini attempt {attempt}",
            )
        except Exception as e:
            last_error = e
            print(colored(f"[-] g4f Gemini attempt {attempt} failed: {e}", "yellow"))
            if "idle" in str(e).lower() or "timed out" in str(e).lower():
                # Hung stream or hung metadata = throttled/flagged session.
                # Retrying the same session won't help — stop here.
                print(colored("[*] Cookie session stalled, skipping remaining cookie attempts", "yellow"))
                break
            if attempt < G4F_GEMINI_MAX_ATTEMPTS:
                time.sleep(2 * attempt)
    raise last_error


def _model_error_head(provider_name: str, model: str, error: Exception) -> str:
    """Human-readable first half of a generation failure message."""
    message = str(error).lower()
    if any(marker in message for marker in (
        'not found', '404', 'not supported', 'unsupported', 'unknown model',
        'invalid model', 'model not', 'no such model', 'does not support',
        'not available', 'no provider',
    )):
        return f"Model '{model}' from provider '{provider_name}' is not available"
    if any(marker in message for marker in (
        'xsrf', 'sapisid', 'unauthorized', '401', '403', 'login', 'cookie',
        'logged-out', 'snlm0e',
    )):
        return f"Browser cookies for provider '{provider_name}' were rejected (Google login expired)"
    return f"Model '{model}' from provider '{provider_name}' failed"


def _raise_or_backup(prompt: str, provider_name: str, model: str,
                     error: Exception, settings=None, include_sdk: bool = True,
                     include_cookie_backup: bool = True) -> str:
    """Primary model failed: raise a clear error, or run the backup if enabled.

    Backup (Settings → "Use backup if the selected model fails") tries, in order:
    the configured backup g4f provider/model, the built-in cookie-free chain,
    the Gemini browser-cookie session (only when cookies are ON and the primary
    was a g4f provider), and finally the official Google SDK when a key is
    configured.
    """
    from llm_providers import get_llm_settings, use_g4f_cookies
    settings = get_llm_settings() if settings is None else settings
    head = _model_error_head(provider_name, model, error)

    if not settings.get("fallback_enabled"):
        raise RuntimeError(
            f"{head}: {error}. Backup is OFF — turn ON 'Use backup if the "
            "selected model fails' in Settings → AI Model Provider, or pick "
            "another model."
        ) from error

    fallback_provider = str(settings.get("fallback_provider") or "").strip()
    fallback_model = str(settings.get("fallback_model") or "").strip()
    if fallback_provider:
        backup_attempts = [(fallback_provider, fallback_model)]
        backup_label = f"{fallback_provider}/{fallback_model or 'default'}"
    else:
        backup_attempts = list(G4F_FREE_CHAIN)
        backup_label = "built-in backup chain"
    backup_attempts = [
        entry for entry in backup_attempts
        if not (entry[0] == provider_name and (entry[1] or "") == (model or ""))
    ]
    print(colored(f"[!] {head} — using backup ({backup_label}), enabled in Settings", "yellow"))

    backup_error: Optional[Exception] = None
    if backup_attempts:
        try:
            return _run_g4f_attempts(prompt, backup_attempts)
        except Exception as e:
            backup_error = e
            print(colored(f"[-] backup ({backup_label}) failed: {e}", "yellow"))

    if include_cookie_backup and use_g4f_cookies(settings) and provider_name != "Gemini":
        try:
            print(colored("[*] backup: Gemini browser-cookie session", "cyan"))
            return _try_cookie_gemini(prompt)
        except Exception as e:
            backup_error = e

    if include_sdk:
        sdk_key, _ = _resolve_gemini_sdk_credentials()
        if sdk_key:
            try:
                print(colored("[*] backup: official Google AI SDK", "cyan"))
                return _generate_via_google_sdk(prompt)
            except Exception as e:
                backup_error = e

    raise RuntimeError(
        f"{head}: {error}. Backup also failed ({backup_error}). Fix the model in "
        "Settings → AI Model Provider (use 'Test connection') or pick another model."
    ) from error


def check_g4f_cookie_status() -> dict:
    """Fast health check for the stored .google.com cookies (no generation).

    Returns {"ok": bool, "reason": str, "detail": str, "renew_steps": [...]}.
    ok=True means gemini.google.com served an authenticated page (SNlM0e
    token present). ok=False means the cookies are missing/expired and the
    g4f Gemini path will fail with the 400 xsrf error.
    """
    from g4f.cookies import get_cookies, set_cookies
    try:
        # Same cache caveat as above: force a fresh disk read so a re-login
        # in Firefox is picked up without restarting the backend.
        set_cookies('.google.com')
        all_cookies = get_cookies('.google.com', False, True)
    except Exception as e:
        return {"ok": False, "reason": "unreadable",
                "detail": f"Could not read browser cookies: {e}",
                "renew_steps": G4F_COOKIE_RENEW_STEPS}
    required = ['__Secure-1PSID', '__Secure-1PSIDTS']
    missing = [k for k in required if k not in all_cookies]
    if ('SAPISID' not in all_cookies and '__Secure-1PAPISID' not in all_cookies
            and '__Secure-3PAPISID' not in all_cookies):
        # g4f builds the SAPISIDHASH Authorization header from these; without
        # one of them every call fails with 'Response 400 ... xsrf'.
        missing.append('SAPISID (or __Secure-1PAPISID)')
    if missing:
        return {"ok": False, "reason": "missing",
                "detail": f"Google login cookies not found in browser ({', '.join(missing)} missing). "
                          f"Found {len(all_cookies)} .google.com cookies, none usable for Gemini.",
                "renew_steps": G4F_COOKIE_RENEW_STEPS}
    try:
        import requests
        from g4f.Provider.needs_auth.Gemini import XSRF_PATTERN
        resp = requests.get(
            "https://gemini.google.com/app",
            cookies={k: v for k, v in all_cookies.items()},
            headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                                   "Chrome/150.0.0.0 Safari/537.36"},
            timeout=25,
        )
        page = resp.text
    except Exception as e:
        return {"ok": False, "reason": "network",
                "detail": f"Could not reach gemini.google.com to verify cookies: {e}",
                "renew_steps": G4F_COOKIE_RENEW_STEPS}
    if XSRF_PATTERN.search(page):
        return {"ok": True, "reason": "fresh",
                "detail": f"Cookies valid ({len(all_cookies)} .google.com cookies, authenticated session).",
                "renew_steps": []}
    return {"ok": False, "reason": "expired",
            "detail": "Cookies are outdated: Google served a logged-out page "
                      "(no session token). g4f Gemini calls will fail with 'Response 400 ... xsrf'.",
            "renew_steps": G4F_COOKIE_RENEW_STEPS}


def refresh_g4f_cookies() -> dict:
    """Nuke everything cached and re-import cookies fresh from the browser.

    Drops the in-process cookie cache, deletes the on-disk rotation cache
    (auth_Gemini.json), resets the Gemini provider session, then re-reads
    Firefox's cookie store and reports the live status.
    """
    import os
    from g4f.cookies import get_cookies, set_cookies, get_cookies_dir
    from g4f.Provider.needs_auth import Gemini
    cleared = []
    set_cookies('.google.com')
    cleared.append('memory cache')
    try:
        auth_file = os.path.join(get_cookies_dir(), 'auth_Gemini.json')
        if os.path.exists(auth_file):
            os.remove(auth_file)
            cleared.append('auth_Gemini.json')
    except Exception as e:
        print(colored(f"[-] Could not delete cookie rotation cache: {e}", "yellow"))
    for attr in ('_snlm0e', '_sid', '_metadata_cookie_key', '_metadata_auth_user',
                 '_account_status'):
        try:
            setattr(Gemini, attr, None)
        except Exception:
            pass
    for attr in ('_account_models',):
        try:
            setattr(Gemini, attr, {})
        except Exception:
            pass
    for attr in ('_metadata_fetched_at', '_account_models_fetched_at'):
        try:
            setattr(Gemini, attr, 0)
        except Exception:
            pass
    fresh = get_cookies('.google.com', False, True)
    status = check_g4f_cookie_status()
    print(colored(f"[+] Cookies refreshed: cleared {', '.join(cleared)}, re-imported {len(fresh)} from browser", "green"))
    return {"cleared": cleared, "cookies_found": len(fresh), "status": status}


def generate_response(prompt: str, ai_model: str) -> str:
    """
    Generate a script for a video, depending on the subject of the video.

    Args:
        prompt (str): The prompt to send to the AI model.
        ai_model (str): The AI model to use for generation.

    Returns:
        str: The response from the AI model.
    """

    print(colored(f"[*] ai_model received: '{ai_model}'", "cyan"))
    ai_model = ai_model.split(':')[0] if ':' in ai_model else ai_model
    if ai_model == "llm":
        # CLIPPER multi-provider path (OpenAI-compatible / Ollama / Gemini / Qwen)
        from llm_providers import llm_complete
        return llm_complete(prompt)
    if ai_model in ('g4f', 'gpt4', 'gpt3.5-turbo'):
        # The generate UI always sends one of these legacy keys, but Settings →
        # AI Model Provider may select an API-backed provider (gemini + custom
        # key, openai, ollama, qwen). Honour that selection so generation
        # matches what 'Test connection' validated.
        #
        # Deliberately NO fallback to the browser-cookie g4f path here: an
        # API failure must surface as an error (or the explicitly enabled
        # backup), never a silent switch to cookies. Cookies are only used
        # when the provider in Settings is literally 'g4f'.
        from llm_providers import get_llm_settings, llm_complete
        settings = get_llm_settings()
        provider = str(settings.get("provider") or "g4f").strip() or "g4f"
        if provider != 'g4f':
            model = str(settings.get("model") or "").strip() or f"{provider} default"
            print(colored(f"[*] ai_model '{ai_model}' routed to configured provider '{provider}' (Settings)", "cyan"))
            last_error: Optional[Exception] = None
            # Transient provider failures (503 high demand, 429 quota, dropped
            # connections) are retried here — retrying is safe and keeps the
            # call on the API path instead of leaking into the cookie path.
            for attempt in range(1, 4):
                try:
                    return llm_complete(prompt)
                except Exception as e:
                    last_error = e
                    if attempt < 3 and _is_transient_error(e):
                        print(colored(f"[-] provider '{provider}' transient error "
                                      f"(attempt {attempt}/3): {e}", "yellow"))
                        time.sleep(3 * attempt)
                        continue
                    break
            # Raises a clear "not available" error, or runs the backup when
            # Settings → "Use backup if the selected model fails" is ON.
            return _raise_or_backup(
                prompt, provider, model,
                last_error or ValueError("provider returned no response"),
                settings, include_sdk=False, include_cookie_backup=False,
            )
    if ai_model in ('g4f', 'gpt4', 'gpt3.5-turbo', 'gemini-api', 'gemmini'):
        from llm_providers import use_g4f_cookies, get_llm_settings
        settings = get_llm_settings()

        if ai_model in ('gemmini', 'gemini-api'):
            sdk_model = str(settings.get("model") or "").strip() or "gemini (Google AI SDK)"
            try:
                return _generate_via_google_sdk(prompt)
            except Exception as e:
                return _raise_or_backup(
                    prompt, "gemini (Google AI SDK)", sdk_model, e, settings,
                    include_sdk=False, include_cookie_backup=False,
                )

        selected_provider, selected_model = _g4f_selected(settings)
        cookies_ok = use_g4f_cookies(settings)

        # PRIMARY: exactly the provider/model selected in Settings. Nothing
        # else is tried before this, so an unavailable model fails loudly.
        try:
            if cookies_ok and selected_provider == "Gemini":
                print(colored(f"[*] g4f selected (browser cookies): "
                              f"{selected_provider}/{selected_model}", "cyan"))
                return _try_cookie_gemini(prompt, selected_model)
            print(colored(f"[*] g4f selected: {selected_provider}/{selected_model}", "cyan"))
            return _run_g4f_attempts(prompt, [(selected_provider, selected_model)])
        except Exception as e:
            # Clear "model not available" error when the backup option is OFF,
            # otherwise the configured/built-in backup runs (loudly logged).
            return _raise_or_backup(prompt, selected_provider, selected_model, e, settings)

    else:
        raise ValueError("Invalid AI model selected.")



def get_search_terms(video_subject: str, amount: int, script: str, ai_model: str) -> List[str]:
    """
    Generate a JSON-Array of search terms for stock videos,
    depending on the subject of a video.

    Args:
        video_subject (str): The subject of the video.
        amount (int): The amount of search terms to generate.
        script (str): The script of the video.
        ai_model (str): The AI model to use for generation.

    Returns:
        List[str]: The search terms for the video subject.
    """

    # Build prompt
    prompt = f"""
    # Role: Video Search Terms Generator
    ## Goals:
    Generate {amount} search terms for stock videos, depending on the subject of a video.

    ## Constrains:
    1. the search terms are to be returned as a json-array of strings.
    2. each search term should consist of 1-3 words, always add the main subject of the video.
    3. you must only return the json-array of strings. you must not return anything else. you must not return the script.
    4. the search terms must be related to the subject of the video.
    5. reply with english search terms only.

    ## Output Example:
    ["search term 1", "search term 2", "search term 3","search term 4","search term 5"]
    
    ## Context:
    ### Video Subject
    {video_subject}

    ### Video Script
    {script}

    Please note that you must use English for generating video search terms; Chinese is not accepted.
    """.strip()


    # Let user know
    print(colored(f"Generating {amount} search terms for {video_subject}...", "cyan"))

    # Generate search terms
    response = generate_response(prompt, ai_model)

    # Let user know
    print(colored(f"Response: {response}", "cyan"))
    # Parse response into a list of search terms
    search_terms = []
    
    try:
        search_terms = json.loads(response)
        if not isinstance(search_terms, list) or not all(isinstance(term, str) for term in search_terms):
            raise ValueError("Response is not a list of strings.")

    except (json.JSONDecodeError, ValueError):
        print(colored("[*] GPT returned an unformatted response. Attempting to clean...", "yellow"))

        # Attempt to extract list-like string and convert to list
        match = re.search(r'\["(?:[^"\\]|\\.)*"(?:,\s*"[^"\\]*")*\]', response)
        if match:
            try:
                search_terms = json.loads(match.group())
            except json.JSONDecodeError:
                print(colored("[-] Could not parse response.", "red"))
                return []



    # Let user know
    print(colored(f"\nGenerated {len(search_terms)} search terms: {', '.join(search_terms)}", "cyan"))

    # Return search terms
    return search_terms


def generate_metadata(video_subject: str, script: str, ai_model: str) -> Tuple[str, str, List[str], str]:  
    """  
    Generate metadata for a YouTube video, including the title, description, keywords, and social post content.  

    Args:  
        video_subject (str): The subject of the video.  
        script (str): The script of the video.  
        ai_model (str): The AI model to use for generation.  

    Returns:  
        Tuple[str, str, List[str], str]: The title, description, keywords, and post content for the video.  
    """  

    # Build prompt for title  
    title_prompt = f"""  
    You are an expert YouTube Shorts title writer. Generate a single catchy, SEO-optimized title for a video based on the following script.  
    The title must be attention-grabbing, under 60 characters, and directly reflect the content of the script.  
    Return ONLY the title text — no quotes, no explanations, no extra formatting.  

    Video Subject: {video_subject}  

    Script:  
    {script}  
    """  

    # Generate title  
    title = generate_response(title_prompt, ai_model).strip().strip('"').strip("'")  
    
    # Build prompt for description  
    description_prompt = f"""  
    You are an expert YouTube Shorts description writer. Write a brief, engaging description for a video based on the following script.  
    The description should include relevant hashtags and be optimized for discovery.  
    Return ONLY the description text — no extra formatting or explanations.  

    Video Subject: {video_subject}  

    Script:  
    {script}  
    """  

    # Generate description  
    description = generate_response(description_prompt, ai_model).strip()  

    # Generate keywords  
    keywords = get_search_terms(video_subject, 6, script, ai_model)  

    # Generate social media post content  
    post_prompt = f"""  
    You are an expert social media content writer. Write a short, engaging post to promote this video on social platforms like YouTube, TikTok, or Instagram.  
    The post should grab attention, use line breaks, and end with a call to action. Keep it under 280 characters.  
    Return ONLY the post text — no quotes, no formatting.  

    Video Title: {title}  
    Video Subject: {video_subject}  

    Script:  
    {script}  
    """  
    post_content = generate_response(post_prompt, ai_model).strip().strip('"').strip("'")  

    return title, description, keywords, post_content
