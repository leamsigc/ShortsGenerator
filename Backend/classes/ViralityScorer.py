import re
from typing import List, Dict, Any
from .ClipperProject import WordTimestamp, SentenceTimestamp, ViralityScores


# Multilingual signal words — transcripts follow the video's spoken language
# (Whisper auto-detect), so scoring must fire in more than English.
# Languages covered: en, es, de, fr, pt, it, nl.
EXCITEMENT_MARKERS = {
    # en
    "amazing", "incredible", "unbelievable", "wow", "omg", "shocking",
    "insane", "crazy", "nuts", "wild", "epic", "legendary", "perfect",
    "best", "worst", "never", "always", "must", "secret", "truth",
    "revealed", "actually", "literally", "seriously", "totally", "absolutely",
    # es
    "increíble", "increible", "impresionante", "wow", "impactante", "locura",
    "épico", "epico", "legendario", "perfecto", "mejor", "peor", "nunca",
    "siempre", "secreto", "verdad", "revelado", "literalmente", "totalmente",
    "absolutamente", "brutal", "alucinante", "demencial",
    # de
    "unglaublich", "wahnsinn", "krass", "episch", "legendär", "perfekt",
    "beste", "schlimmste", "niemals", "immer", "geheimnis", "wahrheit",
    "gelüftet", "wirklich", "absolut", "irre", "heftig",
    # fr
    "incroyable", "impressionnant", "choquant", "fou", "folle", "épique",
    "légendaire", "parfait", "meilleur", "pire", "jamais", "toujours",
    "secret", "vérité", "révélé", "littéralement", "absolument", "dingue",
    # pt
    "incrível", "incrivel", "impressionante", "chocante", "loucura", "épico",
    "epico", "lendário", "perfeito", "melhor", "pior", "nunca", "sempre",
    "segredo", "verdade", "revelado", "literalmente", "totalmente",
    # it
    "incredibile", "pazzesco", "scioccante", "epico", "leggendario",
    "perfetto", "migliore", "peggiore", "mai", "sempre", "segreto",
    "verità", "rivelato", "assolutamente",
    # nl
    "ongelooflijk", "bizar", "episch", "legendarisch", "perfect", "beste",
    "slechtste", "nooit", "altijd", "geheim", "waarheid", "onthuld",
}

CURIOUSITY_WORDS = {
    # en
    "why", "how", "what", "who", "when", "where", "imagine", "think",
    "believe", "know", "realize", "understand", "discover", "learn",
    "find out", "guess", "wonder", "suppose", "consider",
    # es
    "por qué", "porque", "cómo", "como", "qué", "que", "quién", "quien",
    "cuándo", "cuando", "dónde", "donde", "imagina", "piensa", "cree",
    "sabes", "descubre", "aprende", "adivina", "pregúntate",
    # de
    "warum", "wie", "was", "wer", "wann", "wo", "stell dir vor", "denk",
    "glaub", "weißt", "verstehe", "entdecke", "lerne", "rate",
    # fr
    "pourquoi", "comment", "quoi", "qui", "quand", "où", "imagine",
    "pense", "crois", "sais", "découvre", "apprends", "devine",
    # pt
    "por que", "porque", "como", "o que", "quem", "quando", "onde",
    "imagina", "pensa", "acredita", "sabe", "descobre", "aprende", "adivinha",
    # it
    "perché", "come", "cosa", "chi", "quando", "dove", "immagina",
    "pensa", "credici", "sai", "scopri", "impara", "indovina",
    # nl
    "waarom", "hoe", "wat", "wie", "wanneer", "waar", "stel je voor",
    "denk", "geloof", "weet", "ontdek", "leer", "raad",
}

CTA_PATTERNS = {
    "follow", "subscribe", "like", "share", "comment", "save",
    "don't forget", "let me know", "tell me", "what do you think",
    "drop a", "hit that", "check out", "link in bio", "pin it",
    # es
    "sígueme", "sigueme", "suscríbete", "suscribete", "dale like",
    "comparte", "comenta", "guarda", "no olvides", "qué opinas",
    "te cuento", "link en bio", "comentarios",
    # de
    "folg mir", "abonnier", "lass ein like da", "teilen", "kommentier",
    "speichern", "vergiss nicht", "was denkst du", "link in bio",
    # fr
    "suis-moi", "abonne-toi", "like", "partage", "commente",
    "sauvegarde", "n'oublie pas", "qu'en penses-tu", "lien en bio",
    # pt
    "me segue", "inscreva-se", "deixa o like", "compartilha", "comenta",
    "salva", "não esquece", "o que acha", "link na bio",
    # it
    "seguimi", "iscriviti", "lascia like", "condividi", "commenta",
    "salva", "non dimenticare", "cosa ne pensi", "link in bio",
    # nl
    "volg me", "abonneer", "like", "deel", "reageer", "bewaar",
    "vergeet niet", "wat denk je", "link in bio",
}

# Contrast / turn markers across languages ("but ..." moments hook attention).
CONTRAST_WORDS = {
    "but", "however", "actually", "yet", "while",
    "pero", "sin embargo", "aunque", "mientras",
    "aber", "jedoch", "eigentlich", "während",
    "mais", "cependant", "pourtant", "alors que",
    "mas", "porém", "no entanto", "enquanto",
    "ma", "però", "tuttavia", "mentre",
    "maar", "echter", "terwijl",
}

# Emotional charge words (shareability) across languages.
EMOTIONAL_WORDS = {
    "love", "hate", "fear", "hope", "dream", "believe", "amazing", "incredible",
    "amor", "odio", "miedo", "esperanza", "sueño", "increíble",
    "liebe", "hass", "angst", "hoffnung", "traum",
    "amour", "haine", "peur", "espoir", "rêve",
    "amor", "ódio", "medo", "esperança", "sonho",
    "amore", "odio", "paura", "speranza", "sogno",
    "liefde", "haat", "angst", "hoop", "droom",
}

# Tokens too generic to count as training keywords in any language.
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "more",
    "el", "la", "los", "las", "una", "unos", "unas", "para", "con", "por",
    "der", "die", "das", "und", "mit", "für", "von",
    "les", "des", "une", "pour", "avec", "dans",
    "que", "como", "para", "isso", "este", "esta",
    "che", "come", "della", "nella",
    "een", "het", "van", "voor", "met",
}


def analyze_hook_strength(words: List[WordTimestamp], threshold: float = 5.0) -> float:
    """Hook strength of the first seconds (0-100, multilingual).

    Starts low (35) so weak opens score low and strong hooks stand out —
    the old 50-point base flattened every clip into the same band.
    """
    if not words:
        return 25.0

    text = " ".join(w.word for w in words).strip()
    text_lower = text.lower()
    score = 35.0

    # Questions / exclamations in the open (multilingual ¿ ? ¡ !).
    score += min(20, (text.count("?") + text.count("¿")) * 10)
    score += min(10, (text.count("!") + text.count("¡")) * 5)

    curiosity_hits = sum(
        1 for word in CURIOUSITY_WORDS
        if re.search(rf"\b{re.escape(word)}\b", text_lower)
    )
    score += min(20, curiosity_hits * 6)

    contrast_hits = sum(
        1 for word in CONTRAST_WORDS
        if re.search(rf"\b{re.escape(word)}\b", text_lower)
    )
    score += min(15, contrast_hits * 7)

    # Numbers + superlatives stop thumbs ("3 mistakes", "mejor", "beste").
    score += min(10, len(re.findall(r"\b\d+[%x]?\b", text)) * 5)
    score += min(8, sum(
        len(re.findall(rf"\b{re.escape(m)}\b", text_lower))
        for m in EXCITEMENT_MARKERS
    ) * 2)

    # Punchy opens (few words, fast to read) hook better than rambling ones.
    if 4 <= len(words) <= 14:
        score += 6
    elif len(words) > 30:
        score -= 6

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
    """Count excitement/emotion markers in text (multilingual)."""
    text_lower = text.lower()
    count = 0
    for marker in EXCITEMENT_MARKERS:
        count += len(re.findall(rf"\b{re.escape(marker)}\b", text_lower))
    return count


def detect_cta(text: str) -> bool:
    """Check if text contains a call-to-action."""
    text_lower = text.lower()
    for pattern in CTA_PATTERNS:
        if pattern in text_lower:
            return True
    return False


def keyword_density(text: str, keywords: List[str], max_score: float = 100.0) -> float:
    """How well text matches project keywords (token overlap, 0-100).

    Matches whole tokens (not substrings) so "ai" doesn't match "said".
    Scales with the fraction of keywords hit — 0 hits scores low instead of
    the old flat 30, so on-topic clips separate from off-topic ones.
    """
    if not keywords or not text:
        return 25.0

    tokens = set(re.findall(r"[a-zà-ÿäöüßçñ0-9]+", text.lower()))
    if not tokens:
        return 25.0
    hits = 0
    for kw in keywords:
        kw_l = kw.lower().strip()
        if not kw_l:
            continue
        if " " in kw_l:
            if kw_l in text.lower():
                hits += 1
        elif kw_l in tokens:
            hits += 1
    recall = hits / max(1, len(keywords))
    return min(max_score, max(0.0, 15.0 + recall * 85.0))


def analyze_shareability(text: str) -> float:
    """Shareability from emotional words + CTA presence (0-100, multilingual)."""
    score = 35.0

    excitement_count = detect_excitement_markers(text)
    score += min(25, excitement_count * 6)

    if detect_cta(text):
        score += 15

    text_lower = text.lower()
    emotional_markers = sum(
        len(re.findall(rf"\b{re.escape(w)}\b", text_lower))
        for w in EMOTIONAL_WORDS
    )
    score += min(20, emotional_markers * 6)

    score += min(10, (text.count("?") + text.count("¿")) * 5)

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

    # Engagement (0-100, from a low base so delivery differences show).
    pause_count = count_pauses(word_timestamps, threshold=1.5)
    long_pause_count = count_long_pauses(word_timestamps, threshold=3.0)

    engagement_score = 32.0
    # Dramatic pauses help, but continuous speech shouldn't score 0 either.
    engagement_score += min(18, pause_count * 9 + long_pause_count * 6)

    excitement_markers = detect_excitement_markers(transcript_segment)
    engagement_score += min(20, excitement_markers * 4)

    # Speech-rate sweet spot: ~2-3.5 words/sec is engaging narration;
    # mumbling (<1 wps) or machine-gun delivery (>5 wps) scores lower.
    duration = segment_end - segment_start
    word_density = len(word_timestamps) / max(1.0, duration)
    if 2.0 <= word_density <= 3.5:
        engagement_score += 10
    elif 1.2 <= word_density < 2.0 or 3.5 < word_density <= 4.5:
        engagement_score += 5
    elif word_density < 0.7 or word_density > 6.0:
        engagement_score -= 8

    # Question density keeps viewers watching for the answer.
    engagement_score += min(10, transcript_segment.count("?") * 4 + transcript_segment.count("¿") * 4)

    # Duration sweet-spot: 45-60s optimal for virality
    if 45 <= duration <= 60:
        engagement_score += 6
        hook_score += 4
    elif 30 <= duration < 45 or 60 < duration <= 75:
        engagement_score += 3
    elif duration > 85:
        engagement_score -= 4
        hook_score -= 2

    value_score = keyword_density(transcript_segment, training_data_keywords)
    # Without training keywords, content richness is the value proxy:
    # unique-vocabulary ratio + numbers/entities signal information density.
    if not training_data_keywords:
        tokens = re.findall(r"[a-zà-ÿäöüßçñ0-9]+", transcript_segment.lower())
        unique_ratio = (len(set(tokens)) / max(1, len(tokens))) if tokens else 0.0
        numbers = len(re.findall(r"\b\d+[%x]?\b", transcript_segment))
        value_score = min(90.0, 20.0 + unique_ratio * 45.0 + min(15, len(tokens) * 0.12) + min(10, numbers * 3))

    shareability_score = analyze_shareability(transcript_segment)

    question_marks = transcript_segment.count("?")
    has_cta = detect_cta(transcript_segment)

    hook_score = min(100.0, max(0.0, hook_score))
    engagement_score = min(100.0, max(0.0, engagement_score))
    hook_contribution = hook_score * 0.35
    engagement_contribution = engagement_score * 0.25
    value_contribution = value_score * 0.20
    shareability_contribution = shareability_score * 0.20
    overall_score = hook_contribution + engagement_contribution + value_contribution + shareability_contribution
    overall_score = min(99.5, max(5.0, overall_score))

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
    """Extract matchable keywords from freeform training data.

    The old version split only on commas, so a sentence like "funny football
    moments" became one giant keyword that never matched anything (and every
    clip fell back to the flat default score). Now: split on delimiters into
    phrases (kept for multi-word matching) AND tokenize into significant
    words (stopwords + <3 chars dropped), so both "tiki-taka" style phrases
    and plain descriptions produce hits.
    """
    if not training_data:
        return []

    keywords: List[str] = []
    phrases = re.split(r'[,;\n|]', training_data)
    for phrase in phrases:
        phrase = phrase.strip().lower()
        if len(phrase) >= 3:
            # Keep short multi-word phrases for exact matching (max 3 words).
            words_in_phrase = re.findall(r"[a-zà-ÿäöüßçñ0-9]+", phrase)
            if 2 <= len(words_in_phrase) <= 3:
                keywords.append(phrase)
            # Always index the individual tokens.
            for tok in words_in_phrase:
                if len(tok) >= 3 and tok not in STOPWORDS:
                    keywords.append(tok)

    return sorted(set(keywords))


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

    if not scored_segments:
        return scored_segments

    # Min-max rescale overall scores to 20-95 so the ranking has real spread:
    # raw heuristics cluster (everything lands 45-65), which made every clip
    # look equally "good". Rescaling keeps the order but makes the best clip
    # clearly the best and weak moments clearly weak.
    raw_scores = [s["scores"]["overall_score"] for s in scored_segments]
    raw_min, raw_max = min(raw_scores), max(raw_scores)
    span = raw_max - raw_min
    if span >= 1.0:
        for seg in scored_segments:
            raw = seg["scores"]["overall_score"]
            seg["scores"]["overall_score"] = round(20.0 + (raw - raw_min) / span * 75.0, 1)
    elif scored_segments:
        # All identical — center them instead of pretending they're great.
        for seg in scored_segments:
            seg["scores"]["overall_score"] = round(min(99.5, max(5.0, seg["scores"]["overall_score"])), 1)

    scored_segments.sort(key=lambda x: x["scores"]["overall_score"], reverse=True)
    return scored_segments
