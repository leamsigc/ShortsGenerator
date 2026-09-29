import os
import re
import uuid
import json
import subprocess
import requests
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any, Callable
from dataclasses import asdict

from settings import get_settings
from video import get_aspect_ratio_dimensions, _ffprobe_duration
from .ClipperProject import (
    ClipperProject, ClipSegment, ClipTemplate, Transcript,
    WordTimestamp, SentenceTimestamp, ViralityScores,
    project_store
)
from .ViralityScorer import (
    calculate_virality_scores, score_all_segments,
    extract_keywords_from_training_data
)
from .FaceDetector import FaceDetector, smart_crop_coordinates, get_video_dimensions
from transcription import transcribe_video_local, TranscriptionError, NoSpeechDetected

from termcolor import colored


CLIPPER_STATE = {"generating": False, "progress": {}, "progress_callbacks": [], "cancel_requested": set()}


class ClipperCancelled(Exception):
    """Raised when the user cancels a running CLIPPER pipeline."""


def request_clipper_cancel(project_id: str = "*") -> None:
    """Request cancellation for a project ("*" cancels any running pipeline)."""
    CLIPPER_STATE["cancel_requested"].add(project_id)


def clear_clipper_cancel(project_id: str = "*") -> None:
    CLIPPER_STATE["cancel_requested"].discard(project_id)
    CLIPPER_STATE["cancel_requested"].discard("*")


def _check_cancelled(project_id: str) -> None:
    if project_id in CLIPPER_STATE["cancel_requested"] or "*" in CLIPPER_STATE["cancel_requested"]:
        set_clipper_progress(project_id, stage="cancelled", progress=0.0, message="Cancelled by user")
        raise ClipperCancelled(f"Pipeline cancelled for project {project_id}")


# Export presets: per-platform target dimensions + quality knobs.
# "aspect" selects the crop target; high/medium/low map to CRF values.
EXPORT_PRESETS: Dict[str, Dict[str, Any]] = {
    "tiktok":      {"aspect": "9:16", "label": "TikTok (9:16)"},
    "reels":       {"aspect": "9:16", "label": "Instagram Reels (9:16)"},
    "shorts":      {"aspect": "9:16", "label": "YouTube Shorts (9:16)"},
    "douyin":      {"aspect": "9:16", "label": "Douyin (9:16)"},
    "xiaohongshu": {"aspect": "3:4",  "label": "Xiaohongshu (3:4)"},
    "bilibili":    {"aspect": "16:9", "label": "Bilibili (16:9)"},
    "youtube":     {"aspect": "16:9", "label": "YouTube (16:9)"},
}

QUALITY_PRESETS: Dict[str, Dict[str, Any]] = {
    "high":   {"crf": 18, "preset": "fast"},
    "medium": {"crf": 23, "preset": "ultrafast"},
    "low":    {"crf": 28, "preset": "ultrafast"},
}


def resolve_export_preset(format_type: str, quality: str = "medium") -> Dict[str, Any]:
    """Resolve a format name + quality into render parameters."""
    preset = EXPORT_PRESETS.get(format_type, EXPORT_PRESETS["tiktok"])
    quality_cfg = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["medium"])
    return {
        "format": format_type,
        "aspect": preset["aspect"],
        "crf": quality_cfg["crf"],
        "preset": quality_cfg["preset"],
    }


def set_clipper_progress(
    project_id: str,
    stage: str,
    progress: float,
    message: str,
    current_clip: int = 0,
    total_clips: int = 0,
    preview_url: str = ""
):
    CLIPPER_STATE["progress"][project_id] = {
        "stage": stage,
        "progress": progress,
        "message": message,
        "current_clip": current_clip,
        "total_clips": total_clips,
        "preview_url": preview_url,
        "updated_at": datetime.utcnow().isoformat(),
    }
    for callback in CLIPPER_STATE["progress_callbacks"]:
        try:
            callback(project_id, CLIPPER_STATE["progress"][project_id])
        except Exception:
            pass


def subscribe_clipper_progress(callback: Callable):
    CLIPPER_STATE["progress_callbacks"].append(callback)


def unsubscribe_clipper_progress(callback: Callable):
    if callback in CLIPPER_STATE["progress_callbacks"]:
        CLIPPER_STATE["progress_callbacks"].remove(callback)


def download_video(url: str, output_dir: str, base_name: str = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Download video using yt-dlp or direct download.
    Files are named by base_name (the source_id) so clips can be mapped
    back to their source video.
    "local://<source_id>/<filename>" pseudo-URLs reference an already-uploaded
    file in the sources dir (no download happens).
    Returns (video_path, error_message).
    """
    import glob as _glob

    os.makedirs(output_dir, exist_ok=True)
    video_id = base_name or str(uuid.uuid4())

    # Local upload: file already sits in sources/<source_id>.<ext>
    if url.startswith("local://"):
        local_candidates = [
            p for p in _glob.glob(os.path.join(output_dir, f"{video_id}.*"))
            if os.path.splitext(p)[1] in (".mp4", ".mkv", ".webm", ".mov", ".avi")
        ]
        if local_candidates:
            return local_candidates[0], None
        return None, f"Local source file for {video_id} not found in sources directory"

    # Reuse an existing download for this source_id
    existing = [p for p in _glob.glob(os.path.join(output_dir, f"{video_id}.*"))
                if os.path.splitext(p)[1] in (".mp4", ".mkv", ".webm")]
    if existing:
        return existing[0], None

    outtmpl = os.path.join(output_dir, f"{video_id}.%(ext)s")

    try:
        # Bypass YouTube's bot-gate: `android` client is the primary bypass,
        # `tv`/`tv_embedded` also pass without cookies/PO tokens. Override with
        # YTDLP_PLAYER_CLIENT env var (comma-separated) if needed.
        # Format: prefer H.264 (avc1) — AV1 downloads fail to decode on this
        # platform ("Your platform doesn't support hardware accelerated AV1
        # decoding") and are re-encoded to H.264 anyway.
        ydl_opts = {
            "format": (
                "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[vcodec^=avc1]+bestaudio/"
                "best[vcodec^=avc1]/"
                "bestvideo[ext=mp4][vcodec!^=av01]+bestaudio[ext=m4a]/"
                "best[ext=mp4][vcodec!^=av01]/"
                "best"
            ),
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 60,
            "retries": 5,
            "fragment_retries": 5,
            "noplaylist": True,
            "player_client": [c.strip() for c in os.getenv(
                "YTDLP_PLAYER_CLIENT", "android,tv,tv_embedded,ios,mweb,android_vr"
            ).split(",") if c.strip()],
        }

        # Use cookies if provided via env (file or browser profile)
        cookie_file = os.getenv("YTDLP_COOKIES")
        if cookie_file and os.path.exists(cookie_file):
            ydl_opts["cookiefile"] = cookie_file
        cookie_browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER")
        if cookie_browser:
            ydl_opts["cookiesfrombrowser"] = (cookie_browser,)

        import yt_dlp
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return None, "Failed to extract video info"
        except Exception as first_err:
            # Retry without the mp4/format constraints (more permissive),
            # but still avoid AV1 which this platform cannot decode.
            print(colored(f"[-] yt-dlp preferred formats failed: {first_err}. Retrying with non-AV1 'best'.", "yellow"))
            fallback_opts = dict(ydl_opts)
            fallback_opts["format"] = "best[vcodec!^=av01]/bestvideo[vcodec!^=av01]+bestaudio/best"
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return None, str(first_err)

        downloaded = [p for p in _glob.glob(os.path.join(output_dir, f"{video_id}.*"))
                      if os.path.splitext(p)[1] in (".mp4", ".mkv", ".webm")]
        if downloaded:
            return downloaded[0], None

        return None, "Video file not found after download"

    except Exception as e:
        return None, str(e)


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def get_subtitle_template_options() -> List[Dict[str, Any]]:
    """Return the system-wide subtitle template options (settings.py) — the
    single source of truth shared by the main generator and CLIPPER."""
    try:
        from settings import get_settings
        options = get_settings().get("subtitleTemplates", {}).get("options", [])
        if options:
            return options
    except Exception:
        pass
    return [{
        "value": "classic", "label": "Classic Yellow",
        "color": "#FFFF00", "stroke_color": "black", "stroke_width": 5,
        "fontsize": 100, "position": "center,bottom",
    }]


def resolve_clipper_subtitle_template(template_name: str) -> Dict[str, Any]:
    """Resolve a subtitle template from the SYSTEM templates (settings.py).

    CLIPPER reuses the same subtitle styles the user already configured for
    the main generator — no separate clipper styling. Falls back to the
    globally selected template when the requested name is unknown.
    """
    from video import _resolve_subtitle_template
    resolved = _resolve_subtitle_template(template_name)
    if not resolved:
        # Fall back to the system's current template
        try:
            from settings import get_settings
            current = get_settings().get("subtitleTemplates", {}).get("current", "classic")
            resolved = _resolve_subtitle_template(current)
        except Exception:
            pass
    if not resolved:
        resolved = get_subtitle_template_options()[0]

    return {
        "color": resolved.get("color", "#FFFF00"),
        "stroke_color": resolved.get("stroke_color", "black"),
        "stroke_width": resolved.get("stroke_width", 5),
        "fontsize": resolved.get("fontsize", 100),
        "position": resolved.get("position", "center,bottom"),
    }


def generate_word_synced_srt(
    words: List[WordTimestamp],
    output_path: str,
    start_offset: float = 0.0,
    max_words_per_line: int = 8,
    max_chars_per_line: int = 42,
) -> str:
    """Generate SRT with per-word timing for karaoke-style highlighting.

    Chunking mirrors the main generator (`srt_equalizer`, max ~42 chars):
    words accumulate until the char budget (or the word cap) is hit, so
    clip captions wrap exactly like generate-pipeline subtitles instead of
    fixed 8-word blocks that overflow narrow 9:16 frames.
    """
    if not words:
        return output_path

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    chunks: List[List[WordTimestamp]] = []
    current: List[WordTimestamp] = []
    current_len = 0
    for w in words:
        token_len = len(w.word) + (1 if current else 0)
        if current and (len(current) >= max_words_per_line or current_len + token_len > max_chars_per_line):
            chunks.append(current)
            current = []
            current_len = 0
        current.append(w)
        current_len += token_len
    if current:
        chunks.append(current)

    entries: List[str] = []
    for counter, chunk in enumerate(chunks, start=1):
        chunk_start = chunk[0].start_time + start_offset
        chunk_end = chunk[-1].end_time + start_offset
        text = " ".join(w.word for w in chunk)

        entries.append(
            f"{counter}\n"
            f"{_format_srt_time(chunk_start)} --> {_format_srt_time(chunk_end)}\n"
            f"{text}\n"
                )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(entries) + "\n")

    return output_path


def _clipper_font_family(font_path: str) -> str:
    """Resolve a font file to its family name (same as generate pipeline).

    libass matches `FontName` against the family, not the filename — using
    fc-scan keeps clipper captions on the exact same font as /api/generate.
    """
    try:
        from video import _get_font_family
        return _get_font_family(font_path)
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["fc-scan", "--format", "%{family}", font_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split(",")[0]
    except Exception:
        pass
    return os.path.splitext(os.path.basename(font_path))[0]


def burn_subtitles_and_hook(
    clip_video_path: str,
    output_path: str,
    subtitle_srt_path: str,
    hook_title: str,
    template: ClipTemplate,
    face_x: float = 0.5,
    face_y: float = 0.35,
    target_w: int = 1080,
    target_h: int = 1920,
) -> bool:
    """Burn word-synced subtitles and hook title into a clip using ffmpeg.

    Uses the SAME subtitle rendering as the main generator
    (`video._ffmpeg_render_with_subtitles`): same system templates
    (settings.py), same ASS PlayRes scaling, same font-family resolution,
    same filter escaping with `original_size`. target_w/h must match the
    already-cropped clip dimensions so caption size/position is identical.
    """
    sub_template = resolve_clipper_subtitle_template(template.subtitle_template)

    color = sub_template["color"]
    stroke_color = sub_template["stroke_color"]
    stroke_width = sub_template["stroke_width"]
    fontsize = sub_template["fontsize"]
    position = sub_template["position"]

    def _hex_to_ass(hex_color: str) -> str:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) != 6:
            return "&H00000000"
        try:
            int(h, 16)
        except ValueError:
            return "&H00000000"
        return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}"

    primary = _hex_to_ass(color)
    outline = _hex_to_ass(stroke_color)

    pos_map = {
        "center,bottom": 2, "center,center": 5, "center,top": 8,
        "left,bottom": 1, "right,bottom": 3, "left,center": 4,
        "right,center": 6, "left,top": 7, "right,top": 9,
    }
    alignment = pos_map.get(position, 2)

    font_path = os.path.join(
        os.path.dirname(__file__), "..", "static", "assets", "fonts",
        template.font or "bold_font.ttf",
    )
    font_path = os.path.abspath(font_path)
    if not os.path.exists(font_path):
        font_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "static", "assets", "fonts", "bold_font.ttf"))
    font_dir = os.path.dirname(font_path)
    font_family = _clipper_font_family(font_path)

    # ASS PlayRes defaults to 384x288 for SRT — identical scaling to generate.
    ass_playres_y = 288
    fontsize_ass = max(12, round(fontsize * ass_playres_y / target_h))
    stroke_width_ass = max(0, round(stroke_width * ass_playres_y / target_h))

    ass_style = (
        f"FontName={font_family},"
        f"FontSize={fontsize_ass},"
        f"PrimaryColour={primary},"
        f"OutlineColour={outline},"
        f"Outline={stroke_width_ass},"
        f"BorderStyle=1,"
        f"Alignment={alignment}"
    )

    # Same escaping as the generate pipeline: ffmpeg splits filters on ","
    # and options on ":", so both must be escaped inside force_style/paths.
    escaped_style = ass_style.replace(",", "\\,").replace(":", "\\:")
    safe_subs = subtitle_srt_path.replace(":", "\\:")
    safe_fontdir = font_dir.replace(":", "\\:")
    filters = [
        f"subtitles={safe_subs}:fontsdir={safe_fontdir}"
        f":original_size={target_w}x{target_h}:force_style={escaped_style}"
    ]

    if hook_title:
        safe_title = hook_title.replace(":", "\\:").replace(",", "\\,")
        hook_y = int(target_h * 0.15)
        drawtext = (
            f"drawtext="
            f"fontfile='{font_path}':"
            f"text='{safe_title}':"
            f"fontsize={int(fontsize * 0.6)}:"
            f"fontcolor=white@0.95:"
            f"box=1:boxcolor=black@0.7:boxborderw=10:"
            f"x=(w-text_w)/2:y={hook_y}:"
            f"enable='between(t,0,3)'"
        )
        filters.append(drawtext)

    filter_chain = ",".join(filters)

    cmd = [
        # No -hwaccel: force software decoding — hardware AV1 decode fails on
        # this platform and breaks the whole transcode ("Failed to get pixel
        # format"). Software decode (libdav1d/libvpx/h264) always works.
        "ffmpeg", "-y",
        "-i", clip_video_path,
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(colored(f"[+] Rendered clip with captions + hook title: {output_path}", "green"))
            return True
        else:
            print(colored(f"[-] Subtitle/hook burn failed: {result.stderr[-300:]}", "red"))
            return False
    except Exception as e:
        print(colored(f"[-] Burn error: {e}", "red"))
        return False


def generate_thumbnail(
    video_path: str,
    output_path: str,
    timestamp: float = 0.5,
) -> Optional[str]:
    """Extract a thumbnail frame from a video at ``timestamp`` fraction."""
    if not os.path.exists(video_path):
        return None

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    duration = _ffprobe_duration(video_path)
    ts = duration * timestamp if duration > 0 else 0.0

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(ts),
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
    except Exception:
        pass

    return None


def fetch_broll_video(keyword: str, cache_dir: str, pexels_key: str = None) -> Optional[str]:
    """
    Fetch a short B-roll clip from Pexels for the given keyword.
    Downloads to cache_dir and returns local path or None if unavailable.
    Minimal Pexels usage — 1 video per clip, cached by keyword.
    """
    if not keyword or not keyword.strip():
        return None
    pexels_key = pexels_key or os.getenv("PEXELS_API_KEY")
    if not pexels_key:
        print(colored("[*] B-roll skipped: PEXELS_API_KEY not set", "yellow"))
        return None
    keyword = keyword.strip()
    safe_kw = re.sub(r'[^a-zA-Z0-9_-]', '_', keyword)[:40]
    os.makedirs(cache_dir, exist_ok=True)
    # Cache hit — reuse existing B-roll for same keyword
    cached = [p for p in os.listdir(cache_dir) if p.startswith(f"broll_{safe_kw}")]
    if cached:
        hit = os.path.join(cache_dir, cached[0])
        if os.path.exists(hit) and os.path.getsize(hit) > 0:
            print(colored(f"[+] B-roll cache hit for '{keyword}': {hit}", "green"))
            return hit
    try:
        from search import search_for_stock_videos
        urls = search_for_stock_videos(keyword, pexels_key, 1, 5)
        if not urls:
            print(colored(f"[-] No B-roll found for '{keyword}'", "yellow"))
            return None
        broll_url = urls[0]
        print(colored(f"[+] B-roll found for '{keyword}': {broll_url[:80]}...", "cyan"))
        # Download via save_video helper
        from video import save_video
        broll_path = save_video(broll_url, directory=cache_dir)
        if broll_path and os.path.exists(broll_path):
            # Rename to cache key for future hits
            ext = os.path.splitext(broll_path)[1] or ".mp4"
            cached_path = os.path.join(cache_dir, f"broll_{safe_kw}{ext}")
            try:
                if broll_path != cached_path:
                    os.rename(broll_path, cached_path)
                    return cached_path
            except Exception:
                pass
            return broll_path
    except Exception as e:
        print(colored(f"[-] B-roll fetch failed for '{keyword}': {e}", "yellow"))
    return None


def overlay_broll_on_clip(
    main_clip_path: str,
    broll_path: str,
    output_path: str,
    broll_start: float = 5.0,
    broll_duration: float = 4.0,
    scale_factor: float = 0.35,
    position: str = "bottom_right",
    transition: str = "cut",
) -> bool:
    """
    Overlay B-roll picture-in-picture onto main clip.
    Uses ffmpeg overlay filter with optional fade transition.
    Returns True on success.
    """
    if not os.path.exists(main_clip_path) or not os.path.exists(broll_path):
        return False

    # Determine main duration to clamp B-roll timing
    main_dur = _ffprobe_duration(main_clip_path)
    if main_dur <= 0:
        main_dur = broll_duration + broll_start + 1
    # Clamp B-roll window inside main clip
    broll_start = max(0.5, min(broll_start, max(0, main_dur - broll_duration - 0.5)))
    broll_end = broll_start + broll_duration

    # Scale B-roll to 35% of main width, keep aspect, position bottom-right with 20px margin
    # Transition support: cut (default), fade (in/out), zoom (slow Ken-Burns style)
    broll_chain = f"scale=w=iw*{scale_factor}:h=-1:eval=frame,format=yuv420p"
    if transition == "zoom":
        # Slow zoom-in on the B-roll clip (d=1 frame per output frame, capped at 1.15x)
        broll_chain += ",zoompan=z='min(zoom+0.0015,1.15)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=iw*ih:fps=30"
    overlay_filter = (
        f"[1:v]{broll_chain}[br];"
        f"[0:v][br]overlay=W-w-20:H-h-120:enable='between(t,{broll_start},{broll_end})':eof_action=pass[ov]"
    )
    # Add fade if requested (anything except cut/zoom fades in and out)
    if transition and transition not in ("cut", "zoom"):
        fade_dur = 0.5
        overlay_filter = (
            f"[1:v]scale=w=iw*{scale_factor}:h=-1:eval=frame,format=yuv420p,"
            f"fade=t=in:st={broll_start}:d={fade_dur}:alpha=1,"
            f"fade=t=out:st={broll_end - fade_dur}:d={fade_dur}:alpha=1[br];"
            f"[0:v][br]overlay=W-w-20:H-h-120:enable='between(t,{broll_start},{broll_end})':eof_action=pass[ov]"
        )

    cmd = [
        "ffmpeg", "-y",  # software decode (hwaccel breaks on AV1)
        "-i", main_clip_path,
        "-i", broll_path,
        "-filter_complex", overlay_filter,
        "-map", "[ov]",
        "-map", "0:a:0?",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(colored(f"[+] B-roll overlay success: {output_path}", "green"))
            return True
        print(colored(f"[-] B-roll overlay failed: {result.stderr[-400:]}", "red"))
        return False
    except Exception as e:
        print(colored(f"[-] B-roll overlay exception: {e}", "red"))
        return False


def generate_hook_title_llm(
    transcript_segment: str,
    duration: float,
    ai_model: str = "llm"
) -> str:
    """
    Generate hook title for a clip segment using light LLM call.
    """
    from gpt import generate_response

    prompt = f"""You are a viral video hook writer. Create a catchy, attention-grabbing title for a short video clip.

Clip transcript excerpt:
\"{transcript_segment[:300]}...\"

Duration: {duration:.0f} seconds
Platform: TikTok/Reels style
Format: Single line, max 10 words, no quotes

The title should:
- Create curiosity or shock
- Hint at valuable content
- Be easy to read at a glance
- Match the energy of the content

Return ONLY the title text, nothing else."""

    try:
        title = generate_response(prompt, ai_model)
        title = title.strip().strip('"').strip("'").replace("\n", " ")
        return title if title else "Must watch this!"
    except Exception:
        return "Must watch this!"


def generate_clip_metadata_llm(
    transcript_segment: str,
    hook_title: str,
    duration: float,
    target_platform: str = "tiktok",
    training_data: str = "",
    ai_model: str = "llm"
) -> Dict[str, Any]:
    """
    Generate YouTube + social metadata for a single clip.
    Returns dict with title, description, tags, post_content, suggested_schedule.
    Minimal AI usage — single call.
    """
    from gpt import generate_response
    import json as _json

    prompt = f"""You are a viral social media copywriter for {target_platform}. Given a short video clip, create metadata.

Hook title: "{hook_title}"
Transcript excerpt: "{transcript_segment[:500]}..."
Duration: {duration:.0f}s
Training context: {training_data[:300] if training_data else 'General'}

Return JSON only:
{{
  "title": "YouTube title, max 70 chars, hook-driven",
  "description": "YouTube description, 2-3 sentences, SEO-friendly",
  "tags": ["tag1","tag2","tag3","tag4","tag5"],
  "post_content": "Short social post, 1-2 sentences + 1-2 hashtags, platform-native",
  "suggested_schedule": "ISO 8601 UTC suggestion for best posting time within next 48h"
}}

Be concise, no markdown, JSON only."""

    try:
        resp = generate_response(prompt, ai_model)
        resp = resp.strip()
        if resp.startswith("```json"): resp = resp[7:]
        if resp.startswith("```"): resp = resp[3:]
        if resp.endswith("```"): resp = resp[:-3]
        data = _json.loads(resp)
        # Ensure required keys
        return {
            "title": data.get("title", hook_title)[:80],
            "description": data.get("description", transcript_segment[:150])[:500],
            "tags": data.get("tags", [])[:8],
            "post_content": data.get("post_content", hook_title)[:300],
            "suggested_schedule": data.get("suggested_schedule", ""),
        }
    except Exception as e:
        print(colored(f"[-] Metadata LLM failed: {e}", "yellow"))
        return {
            "title": hook_title[:70],
            "description": transcript_segment[:200],
            "tags": ["viral", "shorts"],
            "post_content": hook_title,
            "suggested_schedule": "",
        }


def select_top_clips_llm(
    scored_segments: List[Dict[str, Any]],
    training_data: str,
    target_platform: str,
    max_clips: int = 7,
    ai_model: str = "llm"
) -> List[Dict[str, Any]]:
    """
    Use LLM to select top N clips from scored segments.
    Only sends top 20 segments to minimize AI usage.
    """
    from gpt import generate_response

    top_segments = scored_segments[:20]

    segments_text = "\n".join([
        f"[{i}] {s['start_time']:.1f}s-{s['end_time']:.1f}s ({s['duration']:.0f}s): \"{s['transcript'][:150]}...\" | hook={s['scores']['hook_score']:.0f}, eng={s['scores']['engagement_score']:.0f}, overall={s['scores']['overall_score']:.0f}"
        for i, s in enumerate(top_segments)
    ])

    prompt = f"""You are a viral clip selector for {target_platform}. From the {len(top_segments)} segments below, select the {max_clips} most clip-worthy.

Selection criteria:
- Hook strength (curiosity, shock, contrast)
- Engagement potential (emotional triggers)
- Standalone clarity (understandable without context)
- Shareability (universal appeal, CTA presence)
- Duration: 30-90 seconds optimal

Training context: {training_data[:500] if training_data else 'General content'}

Segments:
{segments_text}

Output JSON format:
{{"selected_indices": [list of segment indices from the input]}}

Select ONLY from the provided segments. Return valid JSON only."""

    try:
        response = generate_response(prompt, ai_model)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        result = json.loads(response)
        selected_indices = result.get("selected_indices", [])

        selected = [s for s in top_segments if s["index"] in selected_indices]
        if len(selected) < max_clips:
            fallback = [s for i, s in enumerate(top_segments) if i not in selected_indices][:max_clips - len(selected)]
            selected.extend(fallback)

        return selected[:max_clips]

    except Exception as e:
        print(colored(f"[-] LLM selection failed, using heuristic: {e}", "yellow"))
        return scored_segments[:max_clips]


def dedup_segments(
    scored_segments: List[Dict[str, Any]],
    min_score: float = 30.0,
    separation: float = 45.0,
    keep_at_least: int = 3,
) -> List[Dict[str, Any]]:
    """Filter out weak and near-duplicate segments (sorted best-first).

    Two passes:
    1. Virality gate: drop segments below ``min_score`` (if that leaves
       fewer than ``keep_at_least`` clips, the top ones are kept anyway).
    2. Dedup: drop segments that overlap or start within ``separation``
       seconds of an already-kept segment from the same source — clips
       like 9:04 / 9:19 are the same moment, so only the best survives.

    Input must be sorted by overall_score descending (generate_clips sorts).
    """
    qualified = [s for s in scored_segments if s["scores"]["overall_score"] >= min_score]
    if len(qualified) < keep_at_least:
        qualified = scored_segments[:keep_at_least]

    kept: List[Dict[str, Any]] = []
    kept_windows: List[Tuple[str, float, float]] = []  # (source_id, start, end)

    for seg in qualified:
        start, end = seg["start_time"], seg["end_time"]
        duplicate = False
        for k_src, k_start, k_end in kept_windows:
            if k_src != seg.get("source_id"):
                continue
            overlaps = start < k_end and end > k_start
            too_close = abs(start - k_start) < separation
            if overlaps or too_close:
                duplicate = True
                break
        if not duplicate:
            kept.append(seg)
            kept_windows.append((seg.get("source_id", ""), start, end))

    return kept


class Clipper:
    """
    Core pipeline orchestrator for CLIPPER.
    """

    def __init__(self, project: ClipperProject):
        self.project = project
        self.base_dir = os.path.join(
            os.path.dirname(__file__), "..", "static", "clipper", "projects", project.id
        )
        os.makedirs(self.base_dir, exist_ok=True)
        self.face_detector = FaceDetector()

    def process_sources(
        self,
        language: str = "auto",
        model_size: str = None,
        ai_model: str = None
    ) -> List[Dict[str, Any]]:
        """
        Download and transcribe all source videos using local faster-whisper.
        Defaults to "auto" (Whisper auto-detects the video's language so
        subtitles match the spoken audio); pass an ISO language code to force
        one (e.g. "es", "de"). Reuses cached transcripts when the source is
        already downloaded and transcribed. User-provided SRT files
        (sources/<source_id>.srt) skip Whisper transcription entirely.
        Returns list of source results.
        """
        from transcription import parse_srt_file
        from llm_providers import get_llm_settings, build_transcript_outline

        results = []

        total = max(1, len(self.project.source_urls))
        # "auto"/"" /None → Whisper auto-detect (subtitles follow the video's
        # spoken language instead of forcing English).
        from transcription import normalize_transcription_language
        whisper_lang = normalize_transcription_language(language)
        display_lang = whisper_lang or "auto"
        if ai_model is None:
            from llm_providers import get_clipper_ai_model
            ai_model = get_clipper_ai_model()
        llm_settings = get_llm_settings()

        for i, url in enumerate(self.project.source_urls):
            _check_cancelled(self.project.id)

            set_clipper_progress(
                self.project.id,
                stage="downloading",
                progress=(i / total) * 0.5,
                message=f"Downloading source {i + 1}/{len(self.project.source_urls)}",
            )

            source_id = self.project.source_ids[i] if i < len(self.project.source_ids) else str(uuid.uuid4())
            download_dir = os.path.join(self.base_dir, "sources")
            video_path, error = download_video(url, download_dir, base_name=source_id)

            if error:
                results.append({
                    "source_id": source_id,
                    "url": url,
                    "status": "error",
                    "error": error,
                })
                continue

            # Transcript cache reuse: skip transcription if a cached transcript
            # already exists for this source (reprocessing is then instant).
            cached_transcript = project_store.get_transcript(self.project.id, source_id)
            if cached_transcript is not None and cached_transcript.words:
                print(colored(f"[+] Transcript cache hit for source {source_id}, skipping transcription", "green"))
                results.append({
                    "source_id": source_id,
                    "url": url,
                    "video_path": video_path,
                    "status": "success",
                    "duration": cached_transcript.duration,
                    "cached": True,
                })
                continue

            set_clipper_progress(
                self.project.id,
                stage="transcribing",
                progress=0.5 + (i / total) * 0.5,
                message=f"Transcribing source {i + 1}/{len(self.project.source_urls)}",
            )

            # User-provided SRT wins over Whisper (faster + more accurate)
            srt_candidates = [
                p for p in (os.path.join(download_dir, f"{source_id}.srt"),)
                if os.path.exists(p)
            ]
            try:
                if srt_candidates:
                    print(colored(f"[+] Using provided SRT subtitles for source {source_id}", "green"))
                    transcript = parse_srt_file(srt_candidates[0], video_path=video_path, language=whisper_lang)
                else:
                    transcript = transcribe_video_local(video_path, language=whisper_lang, model_size=model_size)
                    print(colored(f"[+] Transcribed source {source_id} in '{transcript.language}' (requested: {display_lang})", "green"))
            except NoSpeechDetected as e:
                results.append({
                    "source_id": source_id,
                    "url": url,
                    "video_path": video_path,
                    "status": "error",
                    "error": str(e),
                })
                continue
            except TranscriptionError as e:
                print(colored(f"[-] Transcription error for {url}: {e}", "red"))
                results.append({
                    "source_id": source_id,
                    "url": url,
                    "video_path": video_path,
                    "status": "error",
                    "error": f"Transcription failed: {e}",
                })
                continue

            # Topic timeline / outline extraction (one LLM call per source,
            # heuristic fallback; toggleable via llm settings)
            if llm_settings.get("outline_enabled", True) and transcript.sentences:
                try:
                    _check_cancelled(self.project.id)
                    transcript.outline = build_transcript_outline(transcript.sentences, ai_model)
                except ClipperCancelled:
                    raise
                except Exception as e:
                    print(colored(f"[-] Outline extraction failed: {e}", "yellow"))

            project_store.save_transcript(self.project.id, source_id, transcript)

            results.append({
                "source_id": source_id,
                "url": url,
                "video_path": video_path,
                "status": "success",
                "duration": transcript.duration,
                "language": transcript.language,
            })

        _check_cancelled(self.project.id)

        self.project.status = "ready"
        self.project.source_ids = [r["source_id"] for r in results if r.get("source_id")]
        project_store.update_project(self.project)

        set_clipper_progress(
            self.project.id,
            stage="ready",
            progress=1.0,
            message="Processing complete",
        )

        return results

    def generate_clips(
        self,
        max_clips: int = 7,
        ai_model: str = "llm",
        min_duration: float = 30.0,
        max_duration: float = 90.0,
        min_score: float = 30.0,
    ) -> List[ClipSegment]:
        """
        Score all segments and generate top clips.

        min_score + dedup run before selection: weak segments and
        near-duplicates (overlapping or <45s apart, e.g. 9:04 vs 9:19)
        are dropped, keeping only the strongest moment of each.
        """
        if not self.project.source_ids:
            return []

        all_segments = []
        training_keywords = extract_keywords_from_training_data(self.project.training_data)

        source_ids = [sid for sid in self.project.source_ids
                      if project_store.get_transcript(self.project.id, sid) is not None]
        total = max(1, len(source_ids))

        for pos, source_id in enumerate(source_ids):
            _check_cancelled(self.project.id)
            transcript = project_store.get_transcript(self.project.id, source_id)

            set_clipper_progress(
                self.project.id,
                stage="scoring",
                progress=0.1 + (pos / total) * 0.4,
                message=f"Scoring segments in source {pos + 1}/{total}",
            )

            scored = score_all_segments(
                transcript.words,
                transcript.sentences,
                segment_duration=60.0,
                min_duration=min_duration,
                max_duration=max_duration,
                training_data=self.project.training_data,
            )

            for seg in scored:
                seg["source_id"] = source_id

            all_segments.extend(scored)

        all_segments.sort(key=lambda x: x["scores"]["overall_score"], reverse=True)

        # Drop weak + near-duplicate segments before selection
        pre_count = len(all_segments)
        all_segments = dedup_segments(all_segments, min_score=min_score)
        print(colored(
            f"[*] Clip filter: {pre_count} scored -> {len(all_segments)} qualified "
            f"(min_score={min_score}, dedup separation=45s)", "cyan"))

        _check_cancelled(self.project.id)

        set_clipper_progress(
            self.project.id,
            stage="selecting",
            progress=0.6,
            message=f"Selecting top {max_clips} clips",
        )

        if training_keywords:
            selected = select_top_clips_llm(
                all_segments,
                self.project.training_data,
                self.project.target_platform,
                max_clips,
                ai_model
            )
        else:
            selected = all_segments[:max_clips]

        clips = []
        for i, seg in enumerate(selected):
            _check_cancelled(self.project.id)
            set_clipper_progress(
                self.project.id,
                stage="selecting",
                progress=0.7 + (i / max(1, len(selected))) * 0.3,
                message=f"Writing hook titles for clip {i + 1}/{len(selected)}",
                current_clip=i + 1,
                total_clips=len(selected),
            )

            scores = ViralityScores.from_dict(seg["scores"])

            hook_title = generate_hook_title_llm(
                seg["transcript"],
                seg["duration"],
                ai_model
            ) if ai_model else f"Clip {i + 1}"

            face_x, face_y = self.face_detector.get_face_for_segment(
                self._resolve_source_video(seg["source_id"]) or "",
                seg["start_time"],
                seg["end_time"],
            )

            clip = ClipSegment(
                id=str(uuid.uuid4()),
                project_id=self.project.id,
                source_id=seg["source_id"],
                index=i,
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                duration=seg["duration"],
                transcript=seg["transcript"],
                scores=scores,
                hook_title=hook_title,
                status="selected",
                face_x=face_x,
                face_y=face_y,
            )

            transcript = project_store.get_transcript(self.project.id, seg["source_id"])
            if transcript and transcript.words:
                clip_words = [
                    w for w in transcript.words
                    if w.start_time >= seg["start_time"] and w.end_time <= seg["end_time"]
                ]
                thumbnail_dir = os.path.join(
                    os.path.dirname(__file__), "..",
                    "static", "clipper", "projects", self.project.id, "thumbnails"
                )
                thumbnail_path = os.path.join(thumbnail_dir, f"{clip.id}.jpg")
                video_path = self._resolve_source_video(seg["source_id"])
                if video_path and os.path.exists(video_path):
                    generate_thumbnail(video_path, thumbnail_path, timestamp=0.1)
                    clip.thumbnail_url = f"/static/clipper/projects/{self.project.id}/thumbnails/{clip.id}.jpg"

            clips.append(clip)

        for clip in clips:
            project_store.save_clip(clip)

        set_clipper_progress(
            self.project.id,
            stage="done",
            progress=1.0,
            message=f"Selected {len(clips)} clips",
            total_clips=len(clips),
        )

        return clips

    def _resolve_source_video(self, source_id: str) -> Optional[str]:
        """Find the downloaded source video file for a source_id."""
        import glob as _glob

        sources_dir = os.path.join(self.base_dir, "sources")
        candidates = [p for p in _glob.glob(os.path.join(sources_dir, f"{source_id}.*"))
                      if os.path.splitext(p)[1] in (".mp4", ".mkv", ".webm")]
        if candidates:
            return candidates[0]

        # Fallback: the transcript stores the video path used at transcription time
        transcript = project_store.get_transcript(self.project.id, source_id)
        if transcript and transcript.video_url and os.path.exists(transcript.video_url):
            return transcript.video_url

        return None

    def render_clip(
        self,
        clip: ClipSegment,
        output_dir: str,
        face_x: float = None,
        face_y: float = None,
        aspect: str = "9:16",
        crf: int = 23,
        encode_preset: str = "ultrafast",
        burn_subtitles: bool = True,
    ) -> Optional[str]:
        """Render a single clip with face-centered crop, original audio,
        word-synced captions, and hook title burn-in.

        aspect/crf/encode_preset come from the export preset
        (see resolve_export_preset); burn_subtitles toggles caption burn-in.
        Compilation clips (is_compilation=True) render via concat instead.
        """
        if clip.is_compilation:
            return self.render_compilation(clip, output_dir)

        _check_cancelled(self.project.id)

        video_path = self._resolve_source_video(clip.source_id)

        if video_path is None or not os.path.exists(video_path):
            print(colored(f"[-] Source video not found for clip {clip.id} (source {clip.source_id})", "red"))
            return None

        target_w, target_h = get_aspect_ratio_dimensions(aspect)
        final_path = os.path.join(output_dir, f"{clip.id}.mp4")

        if face_x is None:
            face_x = clip.face_x if clip.face_x is not None else 0.5
        if face_y is None:
            face_y = clip.face_y if clip.face_y is not None else 0.35

        source_w, source_h = get_video_dimensions(video_path)
        # Face TRACKING crop: sample faces across the clip and pan the 9:16
        # window to follow the speaker. Falls back to the static face-centered
        # crop when no face is found (or detection is unavailable).
        from .FaceDetector import build_tracking_crop_filter
        try:
            face_track = self.face_detector.get_face_track(
                video_path, clip.start_time, clip.end_time, n_samples=6,
            )
        except Exception as e:
            print(colored(f"[*] Face tracking failed, using static crop: {e}", "yellow"))
            face_track = [(0.0, face_x, face_y, False)]
        tracked_any = any(f for (_, _, _, f) in face_track)
        if tracked_any:
            crop_expr, crop_w, crop_h, crop_x, crop_y = build_tracking_crop_filter(
                face_track, source_w, source_h, target_w, target_h, clip.duration,
            )
            # Persist the track average for preview/thumbnail positioning.
            clip.face_x = sum(fx for (_, fx, _, f) in face_track if f) / max(1, sum(1 for (_, _, _, f) in face_track if f))
            clip.face_y = sum(fy for (_, _, fy, f) in face_track if f) / max(1, sum(1 for (_, _, _, f) in face_track if f))
            print(colored(f"[+] Face tracking crop for clip {clip.id} ({len(face_track)} samples)", "green"))
        else:
            crop_x, crop_y, crop_w, crop_h = smart_crop_coordinates(
                face_x, face_y, source_w, source_h, target_w, target_h
            )
            crop_expr = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"

        raw_clip_path = os.path.join(output_dir, f"{clip.id}_raw.mp4")
        if os.path.exists(raw_clip_path):
            os.remove(raw_clip_path)

        crop_filter = (
            f"{crop_expr},"
            f"scale={target_w}:{target_h},"
            f"setsar=1,format=yuv420p"
        )

        crop_cmd = [
            "ffmpeg", "-y",  # software decode (hwaccel breaks on AV1)
            "-ss", str(clip.start_time),
            "-i", video_path,
            "-t", str(clip.duration),
            "-vf", crop_filter,
            "-map", "0:v:0",
            "-map", "0:a:0?",
            "-c:v", "libx264",
            "-preset", encode_preset,
            "-crf", str(crf),
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            raw_clip_path,
        ]

        def _run_crop(cmd: List[str]) -> bool:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0 and os.path.exists(raw_clip_path) and os.path.getsize(raw_clip_path) > 0:
                    return True
                print(colored(f"[-] FFmpeg crop failed: {result.stderr[-200:]}", "red"))
            except Exception as e:
                print(colored(f"[-] Crop error: {e}", "red"))
            if os.path.exists(raw_clip_path):
                try:
                    os.remove(raw_clip_path)
                except Exception:
                    pass
            return False

        if not _run_crop(crop_cmd):
            # Animated tracking expressions are rejected by some ffmpeg builds
            # (quoted if() syntax) — retry once with the static fallback crop
            # so a render never fails purely because of tracking.
            if tracked_any:
                print(colored("[*] Retrying crop with static fallback (tracking expression rejected)", "yellow"))
                fb_x, fb_y, fb_w, fb_h = smart_crop_coordinates(
                    face_x, face_y, source_w, source_h, target_w, target_h
                )
                fb_filter = (
                    f"crop={fb_w}:{fb_h}:{fb_x}:{fb_y},"
                    f"scale={target_w}:{target_h},"
                    f"setsar=1,format=yuv420p"
                )
                fb_cmd = list(crop_cmd)
                try:
                    vf_idx = fb_cmd.index("-vf") + 1
                    fb_cmd[vf_idx] = fb_filter
                except ValueError:
                    pass
                if not _run_crop(fb_cmd):
                    return None
            else:
                return None

        # Optional B-roll overlay (Pexels) — before captions so captions stay on top
        if getattr(self.project.template, "broll_enabled", False) and getattr(self.project.template, "broll_keyword", ""):
            broll_cache = os.path.join(os.path.dirname(__file__), "..", "static", "clipper", "broll_cache")
            broll_path = fetch_broll_video(self.project.template.broll_keyword, broll_cache)
            if broll_path:
                broll_output = os.path.join(output_dir, f"{clip.id}_broll.mp4")
                broll_success = overlay_broll_on_clip(
                    raw_clip_path,
                    broll_path,
                    broll_output,
                    broll_start=min(5.0, max(1.0, clip.duration * 0.25)),
                    broll_duration=min(4.0, max(2.0, clip.duration * 0.3)),
                    scale_factor=0.32,
                    transition=self.project.template.transition_type,
                )
                if broll_success and os.path.exists(broll_output):
                    try:
                        os.remove(raw_clip_path)
                    except Exception:
                        pass
                    os.rename(broll_output, raw_clip_path)
                    print(colored(f"[+] B-roll applied for clip {clip.id} (keyword='{self.project.template.broll_keyword}')", "green"))
                else:
                    print(colored(f"[*] B-roll skipped for clip {clip.id}, continuing without", "yellow"))
                    if os.path.exists(broll_output):
                        try:
                            os.remove(broll_output)
                        except Exception:
                            pass

        transcript = project_store.get_transcript(self.project.id, clip.source_id)
        if transcript and transcript.words and burn_subtitles:
            clip_words = [
                WordTimestamp(
                    word=w.word,
                    start_time=w.start_time - clip.start_time,
                    end_time=w.end_time - clip.start_time,
                    confidence=w.confidence,
                )
                for w in transcript.words
                if w.start_time >= clip.start_time and w.end_time <= clip.end_time
            ]

            subtitle_dir = os.path.join(
                os.path.dirname(__file__), "..",
                "static", "clipper", "projects", self.project.id, "subtitles"
            )
            srt_path = os.path.join(subtitle_dir, f"{clip.id}.srt")
            generate_word_synced_srt(clip_words, srt_path)

            success = burn_subtitles_and_hook(
                clip_video_path=raw_clip_path,
                output_path=final_path,
                subtitle_srt_path=srt_path,
                hook_title=clip.hook_title or "",
                template=self.project.template,
                face_x=face_x,
                face_y=face_y,
                target_w=target_w,
                target_h=target_h,
            )

            if os.path.exists(raw_clip_path):
                os.remove(raw_clip_path)

            if not success:
                print(colored(f"[-] Burn step failed for clip {clip.id}", "red"))
                if os.path.exists(final_path):
                    os.remove(final_path)
                return None
        else:
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(raw_clip_path, final_path)

        if os.path.exists(final_path):
            clip.status = "rendered"
            project_store.save_clip(clip)
            return final_path

        return None

    def render_compilation(
        self,
        compilation: ClipSegment,
        output_dir: str,
    ) -> Optional[str]:
        """Render a compilation clip by concatenating its source clips.

        Each source clip is rendered first (reusing existing renders when
        possible), then joined with the ffmpeg concat demuxer.
        """
        if not compilation.source_clip_ids:
            print(colored(f"[-] Compilation {compilation.id} has no source clips", "red"))
            return None

        clips = []
        for cid in compilation.source_clip_ids:
            for c in project_store.get_clips(compilation.project_id):
                if c.id == cid:
                    clips.append(c)
                    break

        if len(clips) < 2:
            print(colored("[-] Compilation needs at least 2 source clips", "red"))
            return None

        renders_dir = os.path.join(self.base_dir, "renders")
        os.makedirs(renders_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        segment_paths: List[str] = []
        for i, c in enumerate(clips):
            _check_cancelled(self.project.id)
            set_clipper_progress(
                self.project.id,
                stage="rendering",
                progress=i / len(clips),
                message=f"Rendering compilation segment {i + 1}/{len(clips)}",
                current_clip=i + 1,
                total_clips=len(clips),
                preview_url=c.thumbnail_url or "",
            )

            rendered = os.path.join(renders_dir, f"{c.id}.mp4")
            if not (os.path.exists(rendered) and c.status == "rendered"):
                rendered = self.render_clip(c, renders_dir)
            if not rendered or not os.path.exists(rendered):
                print(colored(f"[-] Skipping unrenderable clip {c.id} in compilation", "yellow"))
                continue
            segment_paths.append(rendered)

        if len(segment_paths) < 2:
            print(colored("[-] Compilation needs at least 2 rendered segments", "red"))
            return None

        # Normalize segments to a uniform format so the concat demuxer works
        target_w, target_h = get_aspect_ratio_dimensions("9:16")
        norm_dir = os.path.join(output_dir, f"{compilation.id}_segments")
        os.makedirs(norm_dir, exist_ok=True)
        norm_paths: List[str] = []
        for i, seg in enumerate(segment_paths):
            norm_path = os.path.join(norm_dir, f"{i:03d}.mp4")
            cmd = [
                "ffmpeg", "-y", "-i", seg,
                "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                       f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                "-movflags", "+faststart",
                norm_path,
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    print(colored(f"[-] Segment normalize failed: {result.stderr[-200:]}", "red"))
                    return None
                norm_paths.append(norm_path)
            except Exception as e:
                print(colored(f"[-] Segment normalize error: {e}", "red"))
                return None

        concat_list_path = os.path.join(norm_dir, "concat.txt")
        with open(concat_list_path, "w") as f:
            for p in norm_paths:
                f.write(f"file '{p}'\n")

        final_path = os.path.join(output_dir, f"{compilation.id}.mp4")
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            "-movflags", "+faststart",
            final_path,
        ]
        try:
            result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0 or not os.path.exists(final_path):
                print(colored(f"[-] Concat failed: {result.stderr[-300:]}", "red"))
                return None
        except Exception as e:
            print(colored(f"[-] Concat error: {e}", "red"))
            return None

        try:
            import shutil
            shutil.rmtree(norm_dir, ignore_errors=True)
        except Exception:
            pass

        compilation.status = "rendered"
        project_store.save_clip(compilation)
        print(colored(f"[+] Compilation rendered: {final_path}", "green"))
        return final_path

    def generate_cover(
        self,
        clip: ClipSegment,
        video_path: str = None,
    ) -> Optional[str]:
        """Generate a cover image: frame grab + hook title text overlay."""
        if video_path is None:
            video_path = self._resolve_source_video(clip.source_id)
        if not video_path or not os.path.exists(video_path):
            return None

        covers_dir = os.path.join(self.base_dir, "covers")
        os.makedirs(covers_dir, exist_ok=True)
        cover_path = os.path.join(covers_dir, f"{clip.id}.jpg")

        duration = _ffprobe_duration(video_path)
        ts = duration * 0.15 if duration > 0 else 0.0

        font_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "static", "assets", "fonts",
            self.project.template.font or "bold_font.ttf",
        ))
        if not os.path.exists(font_path):
            font_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "static", "assets", "fonts", "bold_font.ttf",
            ))
            if not os.path.exists(font_path):
                font_path = None

        title = (clip.hook_title or clip.title or "").strip()
        safe_title = title.replace(":", "\\:").replace(",", "\\,").replace("'", "\\'") if title else ""

        cmd = ["ffmpeg", "-y", "-ss", str(ts), "-i", video_path, "-frames:v", "1"]
        if safe_title and font_path:
            cmd += [
                "-vf",
                f"scale=1080:-2,"
                f"drawtext=fontfile='{font_path}':text='{safe_title}'"
                f":fontsize=64:fontcolor=white:borderw=4:bordercolor=black"
                f":x=(w-text_w)/2:y=h*0.72",
            ]
        cmd += ["-q:v", "2", cover_path]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and os.path.exists(cover_path):
                return cover_path
            print(colored(f"[-] Cover generation failed: {result.stderr[-200:]}", "red"))
        except Exception as e:
            print(colored(f"[-] Cover error: {e}", "red"))
        return None

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress for this project."""
        return CLIPPER_STATE["progress"].get(self.project.id, {})
