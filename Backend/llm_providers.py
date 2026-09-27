"""
CLIPPER Multi-LLM Provider Support

Provider-agnostic completion API for the CLIPPER pipeline. Providers:
- "g4f"            : legacy free path (g4f Gemini web, existing gpt.py logic,
  needs fresh browser cookies)
- "openai"         : any OpenAI-compatible endpoint (OpenAI, SiliconFlow, LM Studio, vLLM, ...)
- "ollama"         : Ollama local server (OpenAI-compatible /v1 endpoint)
- "gemini"         : official Google AI SDK (GOOGLE_API_KEY)
- "qwen"           : Alibaba DashScope (OpenAI-compatible)

Settings are stored in Backend/static/clipper/llm_settings.json and editable
via the Settings UI (GET/POST /api/clipper/llm/settings) or env vars:
- CLIPPER_LLM_PROVIDER, CLIPPER_LLM_BASE_URL, CLIPPER_LLM_API_KEY,
  CLIPPER_LLM_MODEL (env always takes precedence over the file), plus
  GOOGLE_API_KEY as the api_key fallback when provider is "gemini".
"""
import os
import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional

from termcolor import colored

_SETTINGS_PATH = Path(__file__).resolve().parent / "static" / "clipper" / "llm_settings.json"
_LOCK = threading.Lock()

DEFAULT_SETTINGS: Dict[str, Any] = {
    "provider": "gemini",  # g4f | openai | ollama | gemini | qwen
    "base_url": "",           # e.g. http://localhost:11434/v1 (ollama)
    "api_key": "",            # provider API key (empty for ollama)
    "model": "",              # e.g. gemini-2.5-flash, gpt-4o-mini, qwen2.5:7b (empty = provider default)
    "outline_enabled": True,  # topic-timeline extraction on process
    "g4f_use_cookies": True,  # g4f Gemini path uses browser cookies; off = cookie-free g4f chain
}

PROVIDERS = ["gemini", "g4f", "openai", "ollama", "qwen"]


def get_llm_settings() -> Dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    if _SETTINGS_PATH.exists():
        try:
            with open(_SETTINGS_PATH) as f:
                settings.update(json.load(f))
        except Exception:
            pass
    # Env vars always take precedence over the file, so containers / .env
    # keep working even after the Settings UI has written the file once.
    env_provider = os.getenv("CLIPPER_LLM_PROVIDER")
    if env_provider:
        settings["provider"] = env_provider
    env_base = os.getenv("CLIPPER_LLM_BASE_URL")
    if env_base:
        settings["base_url"] = env_base
    env_key = os.getenv("CLIPPER_LLM_API_KEY")
    if env_key:
        settings["api_key"] = env_key
    elif settings.get("provider") == "gemini" and not settings.get("api_key"):
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            settings["api_key"] = google_key
    env_model = os.getenv("CLIPPER_LLM_MODEL")
    if env_model:
        settings["model"] = env_model
    env_cookies = os.getenv("G4F_USE_COOKIES")
    if env_cookies is not None:
        settings["g4f_use_cookies"] = env_cookies.strip().lower() not in ("0", "false", "no", "off")
    if settings.get("provider") not in PROVIDERS:
        settings["provider"] = DEFAULT_SETTINGS["provider"]
    return settings


def update_llm_settings(new_settings: Dict[str, Any]) -> Dict[str, Any]:
    current = get_llm_settings()
    for key in ("provider", "base_url", "api_key", "model"):
        if key in new_settings:
            current[key] = str(new_settings[key]).strip()
    if "outline_enabled" in new_settings:
        current["outline_enabled"] = bool(new_settings["outline_enabled"])
    if "g4f_use_cookies" in new_settings:
        current["g4f_use_cookies"] = bool(new_settings["g4f_use_cookies"])
    if current["provider"] not in PROVIDERS:
        current["provider"] = DEFAULT_SETTINGS["provider"]
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with open(_SETTINGS_PATH, "w") as f:
            json.dump(current, f, indent=2)
    return current


def _masked(settings: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(settings)
    if out.get("api_key"):
        out["api_key"] = out["api_key"][:4] + "****" if len(out["api_key"]) > 4 else "****"
    return out


def use_g4f_cookies(settings: Optional[Dict[str, Any]] = None) -> bool:
    """Whether the g4f path may touch browser cookies (Settings toggle)."""
    settings = settings if settings is not None else get_llm_settings()
    return bool(settings.get("g4f_use_cookies", DEFAULT_SETTINGS["g4f_use_cookies"]))


def get_clipper_ai_model() -> str:
    """Return the ai_model key clipper code should pass to gpt.generate_response.

    "llm" routes through the configured provider (default: official Gemini
    API); "g4f" keeps the legacy free path (needs fresh browser cookies).
    """
    settings = get_llm_settings()
    if settings.get("provider") and settings["provider"] != "g4f":
        return "llm"
    return "g4f"


def llm_complete(prompt: str) -> str:
    """Generate a completion using the configured provider. Raises on failure."""
    settings = get_llm_settings()
    provider = settings.get("provider") or DEFAULT_SETTINGS["provider"]

    if provider == "g4f":
        from gpt import generate_response
        return generate_response(prompt, "g4f")

    if provider == "gemini":
        api_key = settings.get("api_key") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini provider requires an API key: paste a (free) key into "
                "Settings → AI Model Provider, or set GOOGLE_API_KEY / "
                "CLIPPER_LLM_API_KEY in .env (get one at https://makersuite.google.com/app/apikey)"
            )
        from google import genai
        client = genai.Client(api_key=api_key)
        model = settings.get("model") or "gemini-2.5-flash"
        return client.models.generate_content(model=model, contents=prompt).text

    # OpenAI-compatible: openai, ollama, qwen, LM Studio, vLLM, SiliconFlow...
    if provider == "ollama":
        base_url = (settings.get("base_url") or "http://localhost:11434/v1").rstrip("/")
        api_key = settings.get("api_key") or "ollama"
        model = settings.get("model") or "qwen2.5:7b"
    elif provider == "qwen":
        base_url = (settings.get("base_url") or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
        api_key = settings.get("api_key")
        model = settings.get("model") or "qwen-plus"
    else:  # openai / any OpenAI-compatible
        base_url = (settings.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        api_key = settings.get("api_key")
        model = settings.get("model") or "gpt-4o-mini"

    if not api_key and provider != "ollama":
        raise ValueError(f"{provider} provider requires an API key")

    import requests
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def test_llm_connection(settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send a tiny prompt to validate provider config. Returns {ok, detail}."""
    try:
        if settings:
            saved = get_llm_settings()
            update_llm_settings(settings)
            try:
                reply = llm_complete("Reply with exactly: OK")
                return {"ok": True, "detail": str(reply)[:200], "provider": get_llm_settings()["provider"]}
            finally:
                update_llm_settings(saved)
        reply = llm_complete("Reply with exactly: OK")
        return {"ok": True, "detail": str(reply)[:200], "provider": get_llm_settings()["provider"]}
    except Exception as e:
        return {"ok": False, "detail": str(e)[:300], "provider": (settings or get_llm_settings()).get("provider")}


def masked_llm_settings() -> Dict[str, Any]:
    return _masked(get_llm_settings())


def build_transcript_outline(sentences, ai_model: str = "llm") -> list:
    """Extract an outline / topic timeline from transcript sentences.

    Uses a single LLM call over the sentence timeline; falls back to a
    heuristic (60s blocks labeled by their first sentence) on any failure.
    Returns list of {topic, start, end, summary}.
    """
    if not sentences:
        return []

    timeline = "\n".join(f"{s.start_time:.0f}s-{s.end_time:.0f}s: {s.text}" for s in sentences)
    prompt = f"""You are a video content analyst. Given a sentence timeline with timestamps, extract the main topics discussed.

Timeline:
{timeline[:15000]}

Output JSON only, no markdown:
[{{"topic": "short topic name (3-6 words)", "start": <start seconds>, "end": <end seconds>, "summary": "one sentence about what is discussed"}}]

Rules:
- 3-10 topics depending on video length
- topics must cover the video chronologically, non-overlapping
- start/end are seconds from the timeline
"""

    try:
        from gpt import generate_response
        resp = generate_response(prompt, ai_model).strip()
        if resp.startswith("```json"):
            resp = resp[7:]
        if resp.startswith("```"):
            resp = resp[3:]
        if resp.endswith("```"):
            resp = resp[:-3]
        data = json.loads(resp)
        outline = []
        for item in data:
            outline.append({
                "topic": str(item.get("topic", ""))[:80],
                "start": float(item.get("start", 0)),
                "end": float(item.get("end", 0)),
                "summary": str(item.get("summary", ""))[:300],
            })
        if outline:
            return outline
    except Exception as e:
        print(colored(f"[-] Outline LLM failed, using heuristic: {e}", "yellow"))

    # Heuristic fallback: ~60s topic blocks labeled by first sentence
    outline = []
    block_start = None
    block_label = ""
    block_end = 0.0
    for s in sentences:
        if block_start is None or s.start_time - block_start >= 60.0:
            if block_start is not None:
                outline.append({
                    "topic": block_label[:60],
                    "start": block_start,
                    "end": block_end,
                    "summary": block_label[:200],
                })
            block_start = s.start_time
            block_label = s.text[:60]
        block_end = s.end_time
    if block_start is not None:
        outline.append({
            "topic": block_label[:60],
            "start": block_start,
            "end": block_end,
            "summary": block_label[:200],
        })
    return outline
