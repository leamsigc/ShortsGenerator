import re
from typing import List, Dict, Any
from .ClipperProject import WordTimestamp, SentenceTimestamp, ViralityScores


EXCITEMENT_MARKERS = {
    "amazing", "incredible", "unbelievable", "wow", "omg", "shocking",
    "insane", "crazy", "nuts", "wild", "epic", "legendary", "perfect",
    "best", "worst", "never", "always", "must", "secret", "truth",
    "revealed", "actually", "literally", "seriously", "totally", "absolutely"
}

CURIOUSITY_WORDS = {
    "why", "how", "what", "who", "when", "where", "imagine", "think",
    "believe", "know", "realize", "understand", "discover", "learn",
    "find out", "guess", "wonder", "suppose", "consider"
}

CTA_PATTERNS = {
    "follow", "subscribe", "like", "share", "comment", "save",
    "don't forget", "let me know", "tell me", "what do you think",
    "drop a", "hit that", "check out", "link in bio", "pin it"
}


def analyze_hook_strength(words: List[WordTimestamp], threshold: float = 5.0) -> float:
    """
    Analyze the hook strength of the first N seconds.
    Returns score 0-100 based on question marks, contrast words, curiosity gaps.
    """
    if not words:
        return 30.0

    text = " ".join(w.word.lower() for w in words).strip()
    score = 50.0

    question_count = text.count("?")
    score += min(20, question_count * 10)

    for word in CURIOUSITY_WORDS:
        if re.search(rf"\b{word}\b", text, re.IGNORECASE):
            score += 5

    contrast_count = len(re.findall(r"\b(but|however|actually|yet|while)\b", text, re.IGNORECASE))
    score += min(15, contrast_count * 5)

    exclamation_count = text.count("!")
    score += min(10, exclamation_count * 5)

    if len(words) < 5 and len(text) < 30:
        score += 10

    return min(100.0, max(0.0, score))


def count_pauses(word_timestamps: List[WordTimestamp], threshold: float = 1.5) -> int:
    """
    Count significant pauses (gaps > threshold seconds between words).
    These often indicate engagement moments or emphasis.
    """
    if len(word_timestamps) < 2:
        return 0

    pauses = 0
    for i in range(1, len(word_timestamps)):
        gap = word_timestamps[i].start_time - word_timestamps[i - 1].end_time
        if gap >= threshold:
            pauses += 1
    return pauses


def count_long_pauses(word_timestamps: List[WordTimestamp], threshold: float = 3.0) -> int:
    """Count dramatic pauses (gaps > threshold seconds)."""
    if len(word_timestamps) < 2:
        return 0

    long_pauses = 0
    for i in range(1, len(word_timestamps)):
        gap = word_timestamps[i].start_time - word_timestamps[i - 1].end_time
        if gap >= threshold:
            long_pauses += 1
    return long_pauses


def detect_excitement_markers(text: str) -> int:
    """Count excitement/emotion markers in text."""
    text_lower = text.lower()
    count = 0
    for marker in EXCITEMENT_MARKERS:
        count += len(re.findall(rf"\b{marker}\b", text_lower))
    return count


def detect_cta(text: str) -> bool:
    """Check if text contains a call-to-action."""
    text_lower = text.lower()
    for pattern in CTA_PATTERNS:
        if pattern in text_lower:
            return True
    return False


def keyword_density(text: str, keywords: List[str], max_score: float = 100.0) -> float:
    """
    Calculate how well text matches project keywords.
    Used for value_score component.
    """
    if not keywords or not text:
        return 30.0

    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    density = matches / len(keywords)
    return min(max_score, density * max_score * 2 + 30)


def analyze_shareability(text: str) -> float:
    """
    Score shareability based on emotional words and CTA presence.
    Returns 0-100.
    """
    score = 50.0

    excitement_count = detect_excitement_markers(text)
    score += min(25, excitement_count * 5)

    if detect_cta(text):
        score += 15

    emotional_markers = len(re.findall(r"\b(love|hate|fear|hope|dream|believe|amazing|incredible)\b", text.lower()))
    score += min(15, emotional_markers * 5)

    question_count = text.count("?")
    score += min(10, question_count * 5)

    return min(100.0, max(0.0, score))


def calculate_virality_scores(
    transcript_segment: str,
    word_timestamps: List[WordTimestamp],
    training_data_keywords: List[str],
    segment_start: float,
    segment_end: float
) -> ViralityScores:
    """
    Calculate comprehensive virality scores for a transcript segment.
    Uses heuristic analysis - no AI calls.
    """
    first_5s_words = []
    for w in word_timestamps:
        if w.start_time >= segment_start and w.start_time < segment_start + 5.0:
            first_5s_words.append(w)
        elif w.start_time > segment_start + 5.0:
            break

    hook_score = analyze_hook_strength(first_5s_words)

    # Engagement — pauses are rare, so add density-based variance to avoid identical scores
    pause_count = count_pauses(word_timestamps, threshold=1.5)
    long_pause_count = count_long_pauses(word_timestamps, threshold=3.0)

    base_engagement = 40.0
    engagement_score = min(100.0, base_engagement + pause_count * 12 + long_pause_count * 8)

    excitement_markers = detect_excitement_markers(transcript_segment)
    engagement_score += min(15, excitement_markers * 3)

    # Add word-density variance (clips with more words in same duration are denser)
    word_density = len(word_timestamps) / max(1.0, (segment_end - segment_start))
    engagement_score += min(8, word_density * 1.5)

    # Duration sweet-spot: 45-60s optimal for virality
    duration = segment_end - segment_start
    if 45 <= duration <= 60:
        engagement_score += 6
        hook_score += 4
    elif 30 <= duration < 45 or 60 < duration <= 75:
        engagement_score += 3
    elif duration > 85:
        engagement_score -= 4
        hook_score -= 2

    value_score = keyword_density(transcript_segment, training_data_keywords)
    # If no training keywords, use content richness as proxy for value
    if not training_data_keywords:
        unique_words = len(set(w.lower() for w in transcript_segment.split()))
        value_score = min(75, 35 + unique_words * 0.4 + len(transcript_segment.split()) * 0.15)

    shareability_score = analyze_shareability(transcript_segment)

    question_marks = transcript_segment.count("?")
    has_cta = detect_cta(transcript_segment)

    hook_contribution = hook_score * 0.35
    engagement_contribution = engagement_score * 0.25
    value_contribution = value_score * 0.20
    shareability_contribution = shareability_score * 0.20
    overall_score = hook_contribution + engagement_contribution + value_contribution + shareability_contribution

    # Small deterministic jitter based on transcript hash to break exact ties and surface distinct clips
    jitter = (hash(transcript_segment) % 100) / 100.0 * 2.5  # 0-2.5
    overall_score = min(99.5, overall_score + jitter)

    return ViralityScores(
        hook_score=round(hook_score, 1),
        engagement_score=round(engagement_score, 1),
        value_score=round(value_score, 1),
        shareability_score=round(shareability_score, 1),
        overall_score=round(overall_score, 1),
        pause_count=pause_count,
        excitement_markers=excitement_markers,
        question_marks=question_marks,
        has_cta=has_cta,
    )


def extract_keywords_from_training_data(training_data: str) -> List[str]:
    """
    Extract potential keywords from training data text.
    Splits on common delimiters and filters short words.
    """
    if not training_data:
        return []

    keywords = re.split(r'[,;\n|]', training_data)
    keywords = [kw.strip().lower() for kw in keywords if len(kw.strip()) >= 3]
    return list(set(keywords))


def score_all_segments(
    word_timestamps: List[WordTimestamp],
    sentences: List[SentenceTimestamp],
    segment_duration: float = 60.0,
    min_duration: float = 30.0,
    max_duration: float = 90.0,
    training_data: str = ""
) -> List[Dict[str, Any]]:
    """
    Score all possible segments in a video transcript.
    Returns list of scored segments sorted by overall score.
    """
    if not sentences:
        return []

    training_keywords = extract_keywords_from_training_data(training_data)

    video_duration = word_timestamps[-1].end_time if word_timestamps else 0.0

    scored_segments = []

    for start_idx in range(len(sentences)):
        for end_idx in range(start_idx + 1, len(sentences) + 1):
            segment_sentences = sentences[start_idx:end_idx]
            segment_text = " ".join(s.text for s in segment_sentences)

            segment_start = segment_sentences[0].start_time
            segment_end = segment_sentences[-1].end_time
            duration = segment_end - segment_start

            if duration < min_duration or duration > max_duration:
                continue

            segment_words = [
                w for w in word_timestamps
                if w.start_time >= segment_start and w.end_time <= segment_end
            ]

            scores = calculate_virality_scores(
                segment_text,
                segment_words,
                training_keywords,
                segment_start,
                segment_end
            )

            scored_segments.append({
                "start_time": segment_start,
                "end_time": segment_end,
                "duration": duration,
                "transcript": segment_text,
                "scores": scores.to_dict(),
                "index": start_idx,
            })

    scored_segments.sort(key=lambda x: x["scores"]["overall_score"], reverse=True)
    return scored_segments
