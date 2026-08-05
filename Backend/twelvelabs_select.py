# TwelveLabs Pegasus clip selection.
#
# Optional, opt-in provider. When TWELVELABS_API_KEY is set, the candidate
# stock clips gathered for a Short are scored by the Pegasus video-understanding
# model for how well each one matches the video subject/script, and the best
# matches are kept. When the key is absent (or the SDK/network is unavailable),
# every function is a graceful no-op and the original Pexels ordering is used,
# so existing behaviour is unchanged.
#
# Get a free API key at https://twelvelabs.io (generous free tier).

import os
import re
import json

from termcolor import colored

# Pegasus reads the public Pexels URLs server-side, so no upload/index step.
MODEL_NAME = os.getenv("TWELVELABS_MODEL", "pegasus1.5")


def is_enabled() -> bool:
    """True only when a key is configured. This is what makes the feature opt-in."""
    return bool(os.getenv("TWELVELABS_API_KEY"))


def _client():
    """Build a TwelveLabs client, or return None if the SDK/key is unavailable."""
    api_key = os.getenv("TWELVELABS_API_KEY")
    if not api_key:
        return None
    try:
        from twelvelabs import TwelveLabs
        return TwelveLabs(api_key=api_key)
    except Exception as e:  # SDK not installed
        print(colored(f"[-] TwelveLabs SDK unavailable: {e}", "yellow"))
        return None


def _score_clip(client, video_url: str, subject: str, script: str) -> float:
    """Ask Pegasus how well one clip matches the Short. Returns 0-100 (0 on failure)."""
    from twelvelabs.types.video_context import VideoContext_Url

    prompt = (
        "You are selecting B-roll for a short-form video.\n"
        f"Video subject: {subject}\n"
        f"Script excerpt: {script[:500]}\n\n"
        "Rate from 0 to 100 how well THIS clip visually matches the subject and "
        "script. Reply with ONLY a JSON object like {\"score\": 73}."
    )
    try:
        resp = client.analyze(
            model_name=MODEL_NAME,
            video=VideoContext_Url(url=video_url),
            prompt=prompt,
            max_tokens=512,  # Pegasus requires max_tokens >= 512
        )
        text = (resp.data or "").strip()
        match = re.search(r"\{[^{}]*\}", text)
        score = float(json.loads(match.group())["score"]) if match else 0.0
        return max(0.0, min(100.0, score))
    except Exception as e:
        print(colored(f"[-] Pegasus scoring failed for {video_url}: {e}", "yellow"))
        return 0.0


def rerank_clips(video_urls, subject: str, script: str, keep: int = None):
    """
    Reorder candidate clip URLs by Pegasus relevance, best first.

    No-op (returns the list unchanged) when the feature is disabled or the
    client cannot be built, so callers never need to branch on availability.

    Args:
        video_urls: candidate stock-video URLs (publicly reachable).
        subject: the video subject.
        script: the generated script (used as matching context).
        keep: if set, return at most this many top-ranked URLs.
    """
    urls = list(video_urls)
    if not is_enabled() or len(urls) <= 1:
        return urls[:keep] if keep else urls

    client = _client()
    if client is None:
        return urls[:keep] if keep else urls

    print(colored(f"[X] TwelveLabs: ranking {len(urls)} clips with {MODEL_NAME}...", "blue"))
    scored = [(u, _score_clip(client, u, subject, script)) for u in urls]
    # Pegasus may rate every clip 0 (e.g. all calls failed) — keep original order then.
    if not any(s > 0 for _, s in scored):
        print(colored("[-] TwelveLabs returned no usable scores; keeping original order.", "yellow"))
        return urls[:keep] if keep else urls

    scored.sort(key=lambda x: x[1], reverse=True)
    ranked = [u for u, _ in scored]
    print(colored(f"[+] TwelveLabs ranked clips; top score {scored[0][1]:.0f}", "green"))
    return ranked[:keep] if keep else ranked
