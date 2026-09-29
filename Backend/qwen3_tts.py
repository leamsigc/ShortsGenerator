"""Qwen3-TTS engine (https://github.com/QwenLM/Qwen3-TTS).

Three modes, one compatible ``tts()`` entry point (mirrors supertonic_tts.py):

- ``custom`` — 9 premium timbres + free-form ``instruct`` steering
  (timbre / emotion / prosody control, e.g. "Speak cheerfully, fast-paced").
- ``design`` — free-form voice design from a natural-language description
  (``design_prompt``), no fixed speaker.
- ``clone`` — 3-second rapid voice clone from a reference clip
  (``ref_audio`` + ``ref_text``).

Models are lazy-loaded and cached per model id. The 1.7B CustomVoice model
is the default; the 0.6B variant fits smaller GPUs. Device/dtype default to
CUDA bfloat16 when available, CPU float32 otherwise (flash_attention_2 is
used opportunistically, with a safe fallback).
"""

import hashlib
import os
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf
from termcolor import colored

# ---------------------------------------------------------------------------
# Catalogs
# ---------------------------------------------------------------------------

# Premium timbres of Qwen3-TTS-*-CustomVoice (from the official README).
# Keep keys stable — they are persisted in ttsSettings.qwen_speaker.
QWEN_SPEAKERS: Dict[str, dict] = {
    "Vivian": {"name": "Vivian", "description": "Bright, slightly edgy young female voice.", "native_language": "Chinese", "gender": "female"},
    "Serena": {"name": "Serena", "description": "Warm, gentle young female voice.", "native_language": "Chinese", "gender": "female"},
    "Uncle_Fu": {"name": "Uncle Fu", "description": "Seasoned male voice with a low, mellow timbre.", "native_language": "Chinese", "gender": "male"},
    "Dylan": {"name": "Dylan", "description": "Youthful Beijing male voice, clear and natural (Beijing dialect).", "native_language": "Chinese", "gender": "male"},
    "Eric": {"name": "Eric", "description": "Lively Chengdu male voice, slightly husky brightness (Sichuan dialect).", "native_language": "Chinese", "gender": "male"},
    "Ryan": {"name": "Ryan", "description": "Dynamic male voice with strong rhythmic drive. Great for Shorts narration.", "native_language": "English", "gender": "male"},
    "Aiden": {"name": "Aiden", "description": "Sunny American male voice with a clear midrange.", "native_language": "English", "gender": "male"},
    "Ono_Anna": {"name": "Ono Anna", "description": "Playful Japanese female voice, light and nimble.", "native_language": "Japanese", "gender": "female"},
    "Sohee": {"name": "Sohee", "description": "Warm Korean female voice with rich emotion.", "native_language": "Korean", "gender": "female"},
}

QWEN_LANGUAGES = [
    {"code": "Auto", "label": "Auto-detect"},
    {"code": "Chinese", "label": "Chinese"},
    {"code": "English", "label": "English"},
    {"code": "Japanese", "label": "Japanese"},
    {"code": "Korean", "label": "Korean"},
    {"code": "German", "label": "German"},
    {"code": "French", "label": "French"},
    {"code": "Russian", "label": "Russian"},
    {"code": "Portuguese", "label": "Portuguese"},
    {"code": "Spanish", "label": "Spanish"},
    {"code": "Italian", "label": "Italian"},
]
SUPPORTED_LANGUAGE_CODES = {lang["code"] for lang in QWEN_LANGUAGES}

QWEN_MODES = [
    {"value": "custom", "label": "Preset Voice + Instruct", "description": "Pick one of the 9 premium timbres and steer it with an instruction (emotion, pace, tone)."},
    {"value": "design", "label": "Voice Design", "description": "Describe any voice in plain language — no fixed speaker, the model invents it."},
    {"value": "clone", "label": "Voice Clone", "description": "Clone a voice from a ~3s+ reference clip + its transcript."},
]

QWEN_MODELS = {
    "custom-1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "custom-0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    "design-1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    "base-1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "base-0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
}

DEFAULT_MODEL_FOR_MODE = {
    "custom": QWEN_MODELS["custom-1.7B"],
    "design": QWEN_MODELS["design-1.7B"],
    "clone": QWEN_MODELS["base-1.7B"],
}

# Predefined steering instructions (blog-style presets). Empty string = neutral.
# Shown as one-click chips in /settings so users can steer timbres without
# writing prompts from scratch.
QWEN_INSTRUCT_PRESETS = [
    {"value": "", "label": "Neutral (no steering)"},
    {"value": "Speak cheerfully and energetically, fast-paced like a viral Shorts narrator.", "label": "Viral Shorts energy"},
    {"value": "Speak in a calm, warm storytelling tone, slow and soothing.", "label": "Calm storytelling"},
    {"value": "Speak with a deep, authoritative documentary voice.", "label": "Documentary"},
    {"value": "Whisper softly, intimate and close to the microphone.", "label": "Whisper"},
    {"value": "Speak with excitement and urgency, like breaking news.", "label": "Breaking news"},
    {"value": "Speak angrily and intensely, with strong emphasis.", "label": "Angry / intense"},
    {"value": "Speak in a playful, youthful tone with lots of expression.", "label": "Playful"},
    {"value": "Narra con emoción desbordante como comentarista deportivo de radio: voz potente, ritmo frenético, gritos de ¡GOOL! y pura adrenalina.", "label": "EL-PERRO style (deportes)"},
    {"value": "Start with explosive shock energy on the very first sentence, then keep a fast, punchy rhythm with rising excitement — never let the energy drop for a second.", "label": "Viral hook delivery"},
    {"value": "Speak with ever-growing intensity, each sentence more urgent than the last, like a countdown nobody can look away from.", "label": "Rising retention"},
    {"value": "Speak like a coach before the final match: intense, loud, unstoppable belief in every single word.", "label": "Motivational fire"},
    {"value": "Speak like sharing the juiciest gossip on earth: fast, dramatic pauses, scandalized tone jumps between revelations.", "label": "Gossip heat"},
    {"value": "Deep, thunderous movie-trailer voice: slow, heavy, every word lands like an earthquake.", "label": "Epic trailer"},
]

# Pre-built character voices: one-click personas (voice id -> full config).
# Selecting a character forces its mode/language; a caller-provided
# design_prompt/instruct still wins when non-empty (audition tweaks).
QWEN_CHARACTER_VOICES: Dict[str, dict] = {
    "EL-PERRO": {
        "name": "EL-PERRO",
        "label": "EL-PERRO · Comentarista deportivo viral",
        "kind": "character",
        "gender": "male",
        "mode": "design",
        "language": "Spanish",
        "design_prompt": (
            "Comentarista deportivo de radio latino, voz masculina grave y potente "
            "con acento mexicano, energía explosiva y ritmo vertiginoso, gritos "
            "alargados de ¡GOOOOL!, emoción desbordante como en la final de un "
            "mundial, dicción clara a toda velocidad, estilo viral para Shorts."
        ),
        "instruct": "",
        "description": (
            "Viral Latino sports-radio commentator: explosive excitement, "
            "rapid-fire delivery, long ¡GOOOL! shouts. Built for Spanish Shorts."
        ),
    },
    "EL-GANCHO": {
        "name": "EL-GANCHO",
        "label": "EL-GANCHO · Narrador viral de Shorts",
        "kind": "character",
        "gender": "male",
        "mode": "design",
        "language": "Spanish",
        "design_prompt": (
            "Narrador viral de Shorts, voz masculina joven electrizante, primera "
            "frase explosiva que detiene el scroll, ritmo frenético sin pausas "
            "muertas, emoción siempre subiendo, dicción clarísima a toda velocidad, "
            "carisma arrollador que atrapa desde el segundo uno y no suelta."
        ),
        "instruct": "",
        "description": (
            "Ultimate viral Shorts narrator: shocking hook-first energy, "
            "relentless pace, maximum retention. Spanish."
        ),
    },
    "LA-FIERA": {
        "name": "LA-FIERA",
        "label": "LA-FIERA · Drama y chisme viral",
        "kind": "character",
        "gender": "female",
        "mode": "design",
        "language": "Spanish",
        "design_prompt": (
            "Narradora viral latina, voz femenina feroz y dramática con acento "
            "mexicano, cuenta el chisme más jugoso del mundo, pausas teatrales, "
            "subidas de tono escandalizadas, risa cómplice, emoción desbordante, "
            "imposible dejar de escuchar hasta el final."
        ),
        "instruct": "",
        "description": (
            "Fierce Latina drama storyteller: theatrical pauses, scandalized "
            "peaks, gossip energy that holds watch time. Spanish."
        ),
    },
    "SOMBRA": {
        "name": "SOMBRA",
        "label": "SOMBRA · Misterio y suspenso",
        "kind": "character",
        "gender": "female",
        "mode": "design",
        "language": "Spanish",
        "design_prompt": (
            "Narradora de misterio, voz femenina grave susurrada muy cerca del "
            "micrófono, pausada y tensa, cada frase esconde un secreto, "
            "escalofríos garantizados, tensión que crece sin parar, perfecta "
            "para historias que se escuchan hasta el final."
        ),
        "instruct": "",
        "description": (
            "Dark mystery whisper narrator: close-mic, slow-burn tension that "
            "keeps viewers through long stories. Spanish."
        ),
    },
}

# Starter voice-design prompts (persona descriptions) for Design mode.
QWEN_DESIGN_PRESETS = [
    {"value": "A dynamic young male narrator with strong rhythmic drive, clear midrange, energetic Shorts-style delivery.", "label": "Shorts narrator (EN)"},
    {"value": "A warm, gentle young female voice, soft and soothing, slow natural pace.", "label": "Warm female"},
    {"value": "A deep, seasoned male voice with a low mellow timbre, confident documentary tone.", "label": "Deep documentary"},
    {"value": "A playful, bright young female voice, high pitch with lively variation, cheerful and engaging.", "label": "Playful bright"},
    {"value": "An explosive young male hype narrator, first sentence hits like a thunderclap, relentless high energy, perfect viral Shorts delivery.", "label": "Viral hype beast (EN)"},
    {"value": "A low female whisper storyteller, slow and tense, every sentence hides a secret, chilling true-crime retention voice.", "label": "Mystery whisper (EN)"},
]

MAX_CHUNK_CHARS = 400
CHUNK_SILENCE_SEC = 0.3

_SENT_SPLIT_RE = re.compile(r"(?<=[.?!\n;:—])\s+")

_model_cache: Dict[str, object] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _force_split(text: str, max_chars: int) -> List[str]:
    words = text.split()
    pieces, current = [], ""
    for word in words:
        while len(word) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:max_chars])
            word = word[max_chars:]
        candidate = f"{current} {word}".strip() if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return [p for p in pieces if p]


def split_for_tts(text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    """Split text into pieces capped at max_chars, merging short sentences
    greedily so callers get a few large chunks (fewer model calls = faster
    and more consistent) instead of one call per sentence."""
    chunks: List[str] = []
    for paragraph in re.split(r"\n\s*\n+", text.strip()):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        for sentence in _SENT_SPLIT_RE.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= max_chars:
                chunks.append(sentence)
            else:
                chunks.extend(_force_split(sentence, max_chars))
    merged: List[str] = []
    current = ""
    for ch in chunks:
        candidate = f"{current} {ch}".strip() if current else ch
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                merged.append(current)
            current = ch
    if current:
        merged.append(current)
    return merged


def _resolve_device_and_dtype() -> Tuple[str, object]:
    """CUDA bfloat16 when available, else CPU float32. Never raises."""
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda:0", torch.bfloat16
    except Exception:
        pass
    try:
        import torch

        return "cpu", torch.float32
    except Exception:
        return "cpu", None


def _resolve_model_id(mode: str, model: Optional[str]) -> str:
    if model and model.strip():
        model = model.strip()
        # Accept short keys ("custom-0.6B") as well as full HF ids.
        if model in QWEN_MODELS:
            return QWEN_MODELS[model]
        return model
    env_default = os.getenv("QWEN_TTS_MODEL", "").strip()
    if env_default:
        return env_default
    return DEFAULT_MODEL_FOR_MODE.get(mode, QWEN_MODELS["custom-1.7B"])


def _evict_model(model_id: str, reason: str = "evicted") -> None:
    """Drop one cached model and free its VRAM. Never raises."""
    import gc
    if _model_cache.pop(model_id, None) is not None:
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        print(colored(f"[*] Qwen3-TTS model '{model_id}' unloaded ({reason})", "cyan"))


def _get_model(model_id: str):
    """Lazy-load + cache a Qwen3TTSModel. Downloads weights on first use.

    The cache holds at most QWEN_TTS_MAX_CACHED_MODELS models (default 2):
    the long-running backend would otherwise accumulate custom + design +
    base models until CUDA OOMs and every request silently falls back to a
    preset voice.
    """
    global _model_cache
    if model_id in _model_cache:
        return _model_cache[model_id]
    try:
        import torch
        from qwen_tts import Qwen3TTSModel
    except ImportError as e:
        raise RuntimeError(
            "qwen-tts is not installed. Run: pip install -r requirements.txt "
            "(needs qwen-tts + torch + transformers)."
        ) from e

    device, dtype = _resolve_device_and_dtype()
    env_device = os.getenv("QWEN_TTS_DEVICE", "").strip()
    if env_device:
        device = env_device
    kwargs = {"device_map": device}
    if dtype is not None:
        kwargs["dtype"] = dtype
    # flash_attention_2 only works on CUDA fp16/bf16 — fall back silently.
    try:
        if device.startswith("cuda"):
            kwargs["attn_implementation"] = "flash_attention_2"
    except Exception:
        pass
    print(colored(f"[+] Loading Qwen3-TTS model '{model_id}' on {device} (first run downloads weights)...", "cyan"))
    try:
        model = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
    except Exception:
        # Retry without flash attention (e.g. CPU or missing flash-attn).
        kwargs.pop("attn_implementation", None)
        model = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
    _model_cache[model_id] = model
    try:
        max_cached = max(1, int(os.getenv("QWEN_TTS_MAX_CACHED_MODELS", "2")))
    except ValueError:
        max_cached = 2
    while len(_model_cache) > max_cached:
        oldest = next(k for k in _model_cache if k != model_id)
        _evict_model(oldest, reason="cache cap")
    print(colored("[+] Qwen3-TTS model loaded", "green"))
    return model


def _resolve_ref_audio(ref_audio: str) -> str:
    """Resolve a clone reference clip to a usable path.

    Uploads are stored as CWD-relative paths (e.g.
    ``static/assets/qwen_refs/<file>``), so also try them relative to the
    Backend/ dir and the repo root — the process CWD depends on how the
    server was launched. URLs / data-URIs pass through untouched.
    """
    if not ref_audio:
        return ref_audio
    s = str(ref_audio)
    if s.startswith(("http://", "https://", "data:")) or os.path.exists(s):
        return s
    here = os.path.dirname(os.path.abspath(__file__))  # Backend/
    for base in (here, os.path.dirname(here)):  # Backend/, repo root
        cand = os.path.join(base, s)
        if os.path.exists(cand):
            return cand
    return s


def _write_wavs(wavs, sample_rate: int, filename: str) -> str:
    """Concatenate chunk wavs with a short silence gap and write to file."""
    import numpy as _np

    parts = []
    for i, w in enumerate(wavs):
        chunk = _np.asarray(w).squeeze().astype(_np.float32)
        parts.append(chunk)
        if i < len(wavs) - 1:
            parts.append(_np.zeros(int(sample_rate * CHUNK_SILENCE_SEC), dtype=_np.float32))
    audio = _np.concatenate(parts) if len(parts) > 1 else _np.asarray(parts[0])
    sf.write(filename, audio, sample_rate)
    return filename


# ---------------------------------------------------------------------------
# Public API (mirrors supertonic_tts.py shape)
# ---------------------------------------------------------------------------

def tts(
    text: str,
    voice: str = "Ryan",
    filename: str = "output.wav",
    language: str = "English",
    instruct: str = "",
    mode: str = "custom",
    design_prompt: str = "",
    ref_audio: str = "",
    ref_text: str = "",
    model: Optional[str] = None,
    clone_model: Optional[str] = None,
    chunk_chars: int = 0,
    **kwargs,
) -> str:
    """Generate speech with Qwen3-TTS.

    Args:
        text: Text to synthesize.
        voice: Preset speaker for ``custom`` mode (one of QWEN_SPEAKERS), or a
            character id (e.g. "EL-PERRO") which forces its mode/language.
        filename: Output wav/mp3 path.
        language: Language name ("English", "Spanish", ...) or "Auto".
        instruct: Steering instruction for ``custom`` mode only (emotion,
            pace, tone). Ignored in clone/design — there the voice comes
            from the reference clip / persona description.
        mode: "custom" | "design" | "clone".
        design_prompt: Voice description for ``design`` mode.
        ref_audio: Reference clip path/URL for ``clone`` mode.
        ref_text: Transcript of ``ref_audio`` for ``clone`` mode.
        model: HF model id or short key from QWEN_MODELS. Defaults per mode.
        clone_model: Base-model override for the design-then-clone step
            (default QWEN_TTS_CLONE_MODEL env or 1.7B-Base).
        chunk_chars: max chars per synthesis chunk (0 = default 400).
            Previews use ~800 so a short audition renders in one call.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    mode = (mode or "custom").lower()
    if mode not in ("custom", "design", "clone"):
        raise ValueError(f"Invalid Qwen3 mode: {mode}. Use custom, design or clone.")

    # Character voices (e.g. EL-PERRO) carry their own identity: force their
    # mode/language, keep caller-provided prompt/instruct when non-empty.
    char = QWEN_CHARACTER_VOICES.get(voice or "")
    if char:
        mode = char["mode"]
        language = char["language"]
        design_prompt = design_prompt or char.get("design_prompt", "")
        instruct = instruct or char.get("instruct", "")

    if language not in SUPPORTED_LANGUAGE_CODES:
        language = "Auto"

    model_id = _resolve_model_id(mode, model)

    if mode == "design":
        prompt = design_prompt or instruct or QWEN_DESIGN_PRESETS[0]["value"]
        return _tts_design(
            text, filename, language, prompt,
            design_model_id=model_id,
            clone_model_id=clone_model or "",
            chunk_chars=chunk_chars,
            **kwargs,
        )
    if mode == "clone":
        return _tts_clone_direct(
            text, filename, language, ref_audio, ref_text,
            model_id=model_id, chunk_chars=chunk_chars, **kwargs,
        )

    # custom: sequential single calls. (Batched multi-chunk calls spike VRAM
    # and trip shape bugs in qwen-tts 0.1.1 batch prep — sequential is stable
    # and timbre stays consistent because the speaker embedding is fixed.)
    speaker = voice if voice in QWEN_SPEAKERS else "Ryan"
    tts_model = _get_model(model_id)
    pieces = split_for_tts(text, max_chars=chunk_chars or MAX_CHUNK_CHARS)
    if len(pieces) > 1:
        print(colored(f"[*] Qwen3-TTS: {len(pieces)} chunks sequentially (speaker={speaker})", "cyan"))
    all_wavs = []
    sample_rate = None
    for piece in pieces:
        wavs, sr = tts_model.generate_custom_voice(
            text=piece, language=language, speaker=speaker,
            instruct=instruct or "", **kwargs,
        )
        sample_rate = sr
        all_wavs.extend(wavs)
    return _finish(wavs, sample_rate, filename, f"custom/{speaker}")


def _finish(all_wavs, sample_rate: int, filename: str, tag: str) -> str:
    duration = sum(len(np.asarray(w).squeeze()) for w in all_wavs) / float(sample_rate)
    _write_wavs(all_wavs, sample_rate, filename)
    print(colored(f"[+] Qwen3-TTS audio saved to '{filename}' ({duration:.2f}s, {tag})", "green"))
    # Release cached activations: the allocator otherwise holds GBs per
    # process and the next load/generation OOMs on smaller GPUs.
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    return filename


def _tts_clone_direct(text: str, filename: str, language: str,
                      ref_audio: str, ref_text: str,
                      model_id: str, chunk_chars: int = 0, **kwargs) -> str:
    """Direct clone, sequential single calls sharing ONE prebuilt prompt.

    Reference encoding dominates per-call cost, so the prompt features are
    built once via create_voice_clone_prompt and reused for every chunk
    (the documented qwen-tts pattern). Batching instead spikes VRAM and
    trips shape bugs in qwen-tts 0.1.1 batch prep.

    NOTE: the Base model takes no `instruct` — emotion and pace come from
    the reference clip itself, so steering text is intentionally not
    forwarded here.
    """
    if not ref_audio:
        raise ValueError("Clone mode needs ref_audio (reference clip path/URL).")
    ref_path = _resolve_ref_audio(ref_audio)
    if (
        not os.path.exists(ref_path)
        and not str(ref_path).startswith(("http://", "https://", "data:"))
    ):
        raise ValueError(f"Clone reference clip not found: {ref_audio}")
    # A 3s reference clip holds ~10 words: a longer transcript can't align
    # with the audio and blows up batch/concat shapes — keep the head.
    if ref_text and len(ref_text.strip()) > 300:
        print(colored(f"[*] Clone transcript truncated to 300 chars ({len(ref_text.strip())} given)", "cyan"))
        ref_text = ref_text.strip()[:300]
    tts_model = _get_model(model_id)
    pieces = split_for_tts(text, max_chars=chunk_chars or MAX_CHUNK_CHARS)
    if ref_text and ref_text.strip():
        prompt_items = tts_model.create_voice_clone_prompt(
            ref_audio=ref_path, ref_text=ref_text.strip())
    else:
        prompt_items = tts_model.create_voice_clone_prompt(
            ref_audio=ref_path, x_vector_only_mode=True)
    if len(pieces) > 1:
        print(colored(f"[*] Qwen3-TTS clone: {len(pieces)} chunks, one shared prompt", "cyan"))
    all_wavs = []
    sample_rate = None
    for piece in pieces:
        wavs, sr = tts_model.generate_voice_clone(
            text=piece, language=language,
            voice_clone_prompt=prompt_items, **kwargs,
        )
        sample_rate = sr
        all_wavs.extend(wavs)
    return _finish(all_wavs, sample_rate, filename, "clone")


DESIGN_REF_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "static", "assets", "qwen_refs", "design"
)
_design_prompt_cache: Dict[str, object] = {}


def _drop_model(model_id: str) -> None:
    _evict_model(model_id, reason="no longer needed")


def _tts_design(text: str, filename: str, language: str, prompt: str,
                design_model_id: str, clone_model_id: str = "",
                chunk_chars: int = 0, **kwargs) -> str:
    """Design-then-clone: ONE stable voice for the whole script.

    A free-form design call invents a slightly different voice every time,
    so per-chunk design calls drift across a script. Instead: design a short
    reference ONCE, persist it under qwen_refs/design/, build a reusable
    clone prompt, and synthesize every chunk through it. Repeat runs reuse
    the saved reference without touching the design model at all.
    """
    pieces = split_for_tts(text, max_chars=chunk_chars or MAX_CHUNK_CHARS)
    if len(pieces) > 1:
        print(colored(f"[*] Qwen3-TTS design: {len(pieces)} chunks, one consistent voice", "cyan"))
    key = hashlib.sha1(f"{design_model_id}|{language}|{prompt}".encode()).hexdigest()[:16]
    os.makedirs(DESIGN_REF_DIR, exist_ok=True)
    ref_wav = os.path.join(DESIGN_REF_DIR, f"{key}.wav")
    ref_txt = os.path.join(DESIGN_REF_DIR, f"{key}.txt")
    clone_id = clone_model_id or os.getenv("QWEN_TTS_CLONE_MODEL", "") or QWEN_MODELS["base-1.7B"]
    clone_model = _get_model(clone_id)

    prompt_items = _design_prompt_cache.get(key)
    if prompt_items is not None:
        print(colored("[*] Reusing designed voice from this session (no re-design)", "cyan"))
    elif os.path.exists(ref_wav) and os.path.exists(ref_txt):
        with open(ref_txt, encoding="utf-8") as f:
            saved_text = f.read().strip()
        xvec_only = not saved_text
        prompt_items = clone_model.create_voice_clone_prompt(
            ref_audio=ref_wav,
            ref_text=saved_text or None,
            x_vector_only_mode=xvec_only,
        )
        _design_prompt_cache[key] = prompt_items
        print(colored("[*] Rebuilt designed voice from saved reference (no re-design)", "cyan"))
    else:
        design_model = _get_model(design_model_id)
        ref_text = pieces[0][:200]
        ref_wavs, sr = design_model.generate_voice_design(
            text=ref_text, language=language, instruct=prompt,
        )
        sf.write(ref_wav, np.asarray(ref_wavs[0]).squeeze().astype(np.float32), sr)
        with open(ref_txt, "w", encoding="utf-8") as f:
            f.write(ref_text)
        prompt_items = clone_model.create_voice_clone_prompt(
            ref_audio=(np.asarray(ref_wavs[0]).squeeze().astype(np.float32), sr),
            ref_text=ref_text,
        )
        _design_prompt_cache[key] = prompt_items
        print(colored(f"[*] Designed new voice, reference saved ({os.path.basename(ref_wav)})", "cyan"))
        _drop_model(design_model_id)

    # Sequential single calls through the shared prompt (no batching).
    all_wavs = []
    sample_rate = None
    for piece in pieces:
        wavs, sr = clone_model.generate_voice_clone(
            text=piece, language=language,
            voice_clone_prompt=prompt_items, **kwargs,
        )
        sample_rate = sr
        all_wavs.extend(wavs)
    return _finish(wavs, sample_rate, filename, "design/clone (one voice)")


def preview(
    text: str,
    filename: str,
    mode: str = "custom",
    speaker: str = "Ryan",
    language: str = "English",
    instruct: str = "",
    design_prompt: str = "",
    ref_audio: str = "",
    ref_text: str = "",
    chunk_chars: int = 800,
) -> str:
    """Short preview synthesis for the /settings audition button."""
    short = (text or "").strip()[:300] or "Hello! This is a preview of my new voice."
    return tts(
        short, voice=speaker, filename=filename, language=language,
        instruct=instruct, mode=mode, design_prompt=design_prompt,
        ref_audio=ref_audio, ref_text=ref_text, chunk_chars=chunk_chars,
    )


def available_voices() -> List[str]:
    return list(QWEN_SPEAKERS.keys()) + list(QWEN_CHARACTER_VOICES.keys())


def available_voices_detailed() -> Dict[str, dict]:
    detailed = {k: {**v, "kind": "preset"} for k, v in QWEN_SPEAKERS.items()}
    detailed.update(QWEN_CHARACTER_VOICES)
    return detailed


def available_characters() -> List[Dict]:
    """One-click character personas (EL-PERRO, ...) with their full config."""
    return [
        {"value": key, **cfg} for key, cfg in QWEN_CHARACTER_VOICES.items()
    ]


def available_languages() -> List[Dict]:
    return QWEN_LANGUAGES


def available_modes() -> List[Dict]:
    return QWEN_MODES


def available_models() -> Dict[str, str]:
    return dict(QWEN_MODELS)


def available_instruct_presets() -> List[Dict]:
    return QWEN_INSTRUCT_PRESETS


def available_design_presets() -> List[Dict]:
    return QWEN_DESIGN_PRESETS


def is_qwen_available() -> bool:
    """Lightweight check: deps importable (does NOT load model weights)."""
    try:
        import qwen_tts  # noqa: F401
        import transformers  # noqa: F401
        return True
    except Exception:
        return False


def get_status_detail() -> Dict[str, str]:
    """Richer status for /api/tts/status without downloading weights."""
    try:
        import qwen_tts  # noqa: F401
    except Exception:
        return {"state": "unavailable", "detail": "pip package 'qwen-tts' not installed"}
    try:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        device = "unknown"
    loaded = len(_model_cache) > 0
    return {
        "state": "healthy" if loaded else "available",
        "detail": f"installed, model {'loaded' if loaded else 'lazy-loads on first use'} ({device})",
    }
