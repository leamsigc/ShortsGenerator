import re
import json
import time
import g4f
from g4f.models import Model, ModelUtils
from typing import Tuple, List  
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

G4F_GEMINI_MAX_ATTEMPTS = 2

def _generate_via_google_sdk(prompt: str) -> str:
    if client is None:
        raise ValueError("GOOGLE_API_KEY not configured")
    print(colored("[*] Using Google AI SDK (GOOGLE_API_KEY)", "cyan"))
    # NOTE: 'gemini-3.5-flash' is a g4f-only alias and does not exist in the
    # official API. Use a real official model (override with GEMINI_SDK_MODEL).
    model = os.getenv('GEMINI_SDK_MODEL', 'gemini-3.6-flash')
    return client.models.generate_content(
        model=model,
        contents=prompt
    ).text

def _generate_via_g4f_gemini(prompt: str, attempt: int) -> str:
    from g4f.client import Client as G4FClient
    from g4f import Provider
    from g4f.Provider.needs_auth import Gemini
    from g4f.cookies import get_cookies, set_cookies
    import aiohttp

    # Re-read cookies on every attempt: Google rotates __Secure-1PSIDTS and a
    # stale token makes gemini.google.com reject requests (BardErrorInfo 1096).
    # NOTE: g4f caches cookies per-process (CookiesConfig.cookies), so a plain
    # get_cookies() would keep returning the pre-login values forever in a
    # long-running backend. Clear the cache first to force a fresh disk read.
    set_cookies('.google.com')
    all_cookies = get_cookies('.google.com', False, True)
    # NOTE: SAPISID / __Secure-1PAPISID / __Secure-3PAPISID are required:
    # g4f builds the SAPISIDHASH Authorization header from them. Filtering
    # them out guarantees a 400 xsrf failure on the batchexecute endpoint.
    essential_keys = {
        '__Secure-1PSID', '__Secure-1PSIDTS', '__Secure-3PSID',
        '__Secure-1PSIDTS', '__Secure-3PSIDTS',
        'SAPISID', '__Secure-1PAPISID', '__Secure-3PAPISID',
        'HSID', 'SSID', 'APISID', 'SID',
    }
    Gemini._cookies = {k: v for k, v in all_cookies.items() if k in essential_keys}
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
    print(colored(f"[*] g4f Gemini attempt {attempt}: {len(all_cookies)} cookies -> {len(Gemini._cookies)} essential cookies for Gemini", "cyan"))

    if not getattr(aiohttp.ClientSession, "_shorts_patched", False):
        original_init = aiohttp.ClientSession.__init__
        def _patched_init(self, *args, **kwargs):
            kwargs.setdefault('max_line_size', 65536)
            kwargs.setdefault('max_field_size', 65536)
            return original_init(self, *args, **kwargs)
        aiohttp.ClientSession.__init__ = _patched_init
        aiohttp.ClientSession._shorts_patched = True

    g4f_client = G4FClient(provider=Provider.Gemini)
    response = g4f_client.chat.completions.create(
        model="gemini-3.6-flash",
        messages=[{"role": "user", "content": prompt}],
        web_search=False
    )
    return response.choices[0].message.content

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
    "In Firefox, open gemini.google.com and log in with your Google account.",
    "If it already shows you logged in, log OUT and back IN — this rotates the __Secure-1PSIDTS token g4f needs.",
    "Back here, press 'Check cookies' (or 'Test connection') to confirm.",
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


def _generate_via_g4f_free(prompt: str) -> str:
    """g4f without cookies and without API keys. Raises on total failure.

    Tries the provider/model selected in Settings first, then the fallback
    chain.
    """
    from g4f.client import Client as G4FClient
    from llm_providers import get_llm_settings
    settings = get_llm_settings()
    selected = (settings.get("g4f_provider") or "").strip()
    selected_model = (settings.get("g4f_model") or "").strip()
    attempts = []
    if selected:
        attempts.append((selected, selected_model))
    for provider_name, model in G4F_FREE_CHAIN:
        if (provider_name, model) not in attempts:
            attempts.append((provider_name, model))
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
                45, f"{provider_name}/{model}",
            )
            text = response.choices[0].message.content
            if text and text.strip():
                return text
            last_error = ValueError(f"{provider_name}/{model} returned empty response")
        except Exception as e:
            last_error = e
            print(colored(f"[-] g4f cookie-free {provider_name}/{model} failed: {e}", "yellow"))
    raise last_error


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
    if ai_model in ('g4f', 'gpt4', 'gpt3.5-turbo', 'gemini-api', 'gemmini'):
        if ai_model in ('gemmini', 'gemini-api'):
            return _generate_via_google_sdk(prompt)

        from llm_providers import use_g4f_cookies, get_llm_settings
        settings = get_llm_settings()
        selected = (settings.get("g4f_provider") or "").strip()
        cookies_ok = use_g4f_cookies(settings)

        if not cookies_ok:
            # Toggle OFF: no browser cookies, no env keys — cookie-free g4f only.
            print(colored("[*] g4f cookies disabled in settings: using cookie-free providers", "cyan"))
            try:
                return _generate_via_g4f_free(prompt)
            except Exception as e:
                raise RuntimeError(
                    f"g4f cookie-free providers failed ({e}). Fix: turn ON "
                    "'Use browser cookies' in Settings → AI Model Provider (needs fresh "
                    "Firefox Google login), or switch provider to gemini/ollama/openai."
                ) from e

        # Explicit non-Gemini selection goes FIRST (each attempt capped at
        # 60s): otherwise Test/Generate burns 120s+ on the cookie path even
        # when the user picked a different provider.
        if selected and selected != "Gemini":
            try:
                print(colored(f"[*] g4f selected provider first: {selected}", "cyan"))
                return _generate_via_g4f_free(prompt)
            except Exception as e:
                print(colored(f"[-] selected g4f provider failed, trying cookie path: {e}", "yellow"))

        last_error: Exception = ValueError("No g4f Gemini attempt was made")
        for attempt in range(1, G4F_GEMINI_MAX_ATTEMPTS + 1):
            try:
                # 100s cap: g4f's own stall detector fires at 120s, and its
                # metadata calls have no timeout at all — bound the whole
                # attempt so one stuck session can't eat the 5-min UI budget.
                return _call_with_timeout(
                    lambda: _generate_via_g4f_gemini(prompt, attempt),
                    100, f"g4f Gemini attempt {attempt}",
                )
            except Exception as e:
                last_error = e
                print(colored(f"[-] g4f Gemini attempt {attempt} failed: {e}", "yellow"))
                if "idle" in str(e).lower() or "timed out" in str(e).lower():
                    # Hung stream or hung metadata = throttled/flagged session.
                    # Retrying the same session won't help — go to fallbacks now
                    # instead of burning more stalls.
                    print(colored("[*] Cookie session stalled, skipping remaining cookie attempts", "yellow"))
                    break
                if attempt < G4F_GEMINI_MAX_ATTEMPTS:
                    time.sleep(2 * attempt)

        # Cookies failed: try the cookie-free chain before giving up.
        try:
            print(colored("[*] g4f Gemini (cookies) exhausted. Trying cookie-free providers", "cyan"))
            return _generate_via_g4f_free(prompt)
        except Exception as e:
            print(colored(f"[-] g4f cookie-free fallback failed: {e}", "yellow"))

        # Last resort: official Google AI SDK if a key is configured.
        if client is not None:
            print(colored("[*] Falling back to Google AI SDK (GOOGLE_API_KEY)", "cyan"))
            return _generate_via_google_sdk(prompt)
        raise RuntimeError(
            f"g4f Gemini failed after {G4F_GEMINI_MAX_ATTEMPTS} attempts ({last_error}). "
            "Google rejected the stored .google.com cookies (400 xsrf / missing SNlM0e = "
            "logged-out landing page). Fix: 1) turn OFF 'Use browser cookies' in "
            "Settings → AI Model Provider to use cookie-free providers; 2) in Firefox, "
            "open gemini.google.com, log back in, then retry; or 3) set a valid "
            "GOOGLE_API_KEY in .env to use the official API instead."
        ) from last_error

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
