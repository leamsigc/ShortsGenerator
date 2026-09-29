"""
CLIPPER Transcription Pipeline

Local-only transcription using faster-whisper (word-level timestamps).
Defaults to English; pass an ISO language code to transcribe other languages.
Transcriptions are cached to disk per project.
"""
import os
import re
from typing import List, Optional

from classes.ClipperProject import Transcript, WordTimestamp, SentenceTimestamp


_WHISPER_MODEL_CACHE = {}


def _get_whisper_model(model_size: str = "base"):
    """Load (and cache) a faster-whisper model.

    CTranslate2-backed => fast on CPU, low memory, word-level timestamps.
    """
    if model_size not in _WHISPER_MODEL_CACHE:
        from faster_whisper import WhisperModel

        device = "cuda" if os.getenv("WHISPER_DEVICE", "cpu").lower() == "cuda" else "cpu"
        compute_type = "int8" if device == "cpu" else "float16"

        _WHISPER_MODEL_CACHE[model_size] = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    return _WHISPER_MODEL_CACHE[model_size]


class TranscriptionError(Exception):
    """Raised when the transcription pipeline fails."""


class NoSpeechDetected(TranscriptionError):
    """Raised when the audio contains no detectable speech."""


def _parse_srt_time(time_str: str) -> float:
    """Parse an SRT timestamp (HH:MM:SS,mmm) into seconds."""
    time_str = time_str.strip().replace(",", ".")
    parts = time_str.split(":")
    try:
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        if len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        return float(parts[0])
    except ValueError:
        return 0.0


def parse_srt_file(srt_path: str, video_path: str = "", language: Optional[str] = None) -> Transcript:
    """Parse a user-provided .srt file into a Transcript.

    Sentence timings come directly from the SRT cues; word-level timings
    are approximated by splitting each cue's text evenly across its duration
    (good enough for word-synced caption rendering and scoring).
    """
    if not os.path.exists(srt_path):
        raise TranscriptionError(f"SRT file not found: {srt_path}")

    with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    sentences: List[SentenceTimestamp] = []
    words: List[WordTimestamp] = []

    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        # Skip a leading index line ("1", "2", ...)
        if lines[0].isdigit() and len(lines) >= 3:
            lines = lines[1:]
        if "-->" not in lines[0]:
            continue
        try:
            start_str, end_str = lines[0].split("-->")
        except ValueError:
            continue
        start = _parse_srt_time(start_str)
        end = _parse_srt_time(end_str.split()[0] if end_str.split() else end_str)
        text = " ".join(lines[1:]).strip()
        if not text:
            continue

        sentences.append(SentenceTimestamp(text=text, start_time=start, end_time=end))

        # Approximate word timings: even split across the cue duration
        cue_words = text.split()
        if cue_words and end > start:
            per_word = (end - start) / len(cue_words)
            for i, w in enumerate(cue_words):
                words.append(WordTimestamp(
                    word=w,
                    start_time=start + i * per_word,
                    end_time=start + (i + 1) * per_word,
                    confidence=1.0,
                ))

    if not sentences:
        raise NoSpeechDetected("SRT file contains no usable subtitle cues")

    duration = max(sentences[-1].end_time, words[-1].end_time if words else 0.0)

    i_words = sum(
        1 for w in words
        if any(m in w.word.lower() for m in [
            "viral", "amazing", "incredible", "wow", "shocking", "insane"
        ])
    )

    srt_lang = normalize_transcription_language(language) or "en"
    return Transcript(
        video_url=video_path,
        duration=duration,
        words=words,
        sentences=sentences,
        topics=[],
        i_words=i_words,
        engagement_signals={"pause_count": 0, "source": "srt", "language": srt_lang},
        language=srt_lang,
    )


def normalize_transcription_language(language: Optional[str]) -> Optional[str]:
    """Normalize a UI/API language value to a faster-whisper `language` arg.

    "auto" (the UI default), "" and None all mean auto-detect → None, so
    Whisper transcribes in the video's own language instead of forcing
    English. Anything else is lower-cased and passed through (e.g. "es").
    """
    if language is None:
        return None
    lang = str(language).strip().lower()
    if lang in ("", "auto", "detect", "automatic"):
        return None
    return lang


def transcribe_video_local(
    video_path: str,
    language: Optional[str] = None,
    model_size: Optional[str] = None,
) -> Transcript:
    """Local transcription using faster-whisper (default and recommended).

    Produces word-level timestamps and sentences with accurate timing.
    `language=None` (or "auto") auto-detects the video's language so
    subtitles match the spoken audio; pass an ISO 639-1 code to force one.
    Raises NoSpeechDetected when the audio has no speech, and
    TranscriptionError when the pipeline itself fails.
    """
    if not os.path.exists(video_path):
        raise TranscriptionError(f"Video file not found: {video_path}")

    model_size = model_size or os.getenv("WHISPER_MODEL", "base")
    whisper_lang = normalize_transcription_language(language)

    try:
        model = _get_whisper_model(model_size)
    except Exception as e:
        raise TranscriptionError(f"Failed to load whisper model '{model_size}': {e}")

    try:
        segments, info = model.transcribe(
            video_path,
            language=whisper_lang,
            word_timestamps=True,
            vad_filter=True,
            beam_size=5,
        )
    except Exception as e:
        raise TranscriptionError(f"Whisper transcription failed: {e}")

    detected_language = getattr(info, "language", None) or whisper_lang or "en"
    language_probability = float(getattr(info, "language_probability", 0.0) or 0.0)

    words: List[WordTimestamp] = []
    sentences: List[SentenceTimestamp] = []

    for segment in segments:
        if segment.text and segment.text.strip():
            sentences.append(SentenceTimestamp(
                text=segment.text.strip(),
                start_time=float(segment.start),
                end_time=float(segment.end),
            ))

        for w in getattr(segment, "words", None) or []:
            words.append(WordTimestamp(
                word=w.word,
                start_time=float(w.start),
                end_time=float(w.end),
                confidence=float(getattr(w, "probability", 0.9) or 0.9),
            ))

    if not sentences and not words:
        raise NoSpeechDetected(
            "No speech detected in the audio (silent track or unsupported language)"
        )

    duration = max(
        sentences[-1].end_time if sentences else 0.0,
        words[-1].end_time if words else 0.0,
    )

    i_words = sum(
        1 for w in words
        if any(m in w.word.lower() for m in [
            "viral", "amazing", "incredible", "wow", "shocking", "insane"
        ])
    )

    return Transcript(
        video_url=video_path,
        duration=duration,
        words=words,
        sentences=sentences,
        topics=[],
        i_words=i_words,
        engagement_signals={"pause_count": 0, "language": detected_language, "language_probability": language_probability},
        language=detected_language,
        language_probability=language_probability,
    )
