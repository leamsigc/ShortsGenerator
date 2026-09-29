# CLIPPER — AI Video Clip Generator

## 1. Concept & Vision

CLIPPER is an AI-powered video clipping tool that transforms long-form videos (podcasts, streams, talks) into viral-ready vertical clips. Unlike the existing generator that creates videos from scratch using stock footage, CLIPPER clips *from provided source videos* with face-centered framing, word-synced captions, and virality scoring. The philosophy: **minimal AI, maximum signal** — use transcription + heuristic scoring over expensive LLM analysis where possible.

The workflow:
1. User provides source video URL(s) and defines a **Project** (content theme, target audience, style guidelines)
2. CLIPPER downloads, transcribes with word-level timestamps, and indexes the content
3. User selects target videos/clips to create OR CLIPPER auto-selects top 3-7 segments based on scoring
4. CLIPPER renders final clips: face-cropped, captioned, with hook titles
5. User trims/splits/merges in the built-in editor
6. Export to TikTok/Reels/Shorts presets

---

## 2. Architecture Overview

### Stack
- **Backend**: Python Flask (existing), extended with new endpoints
- **Frontend**: Nuxt 3 SPA (existing), new `/clipper` route
- **MCP Server**: Python `mcp` package, exposes CLIPPER tools via Model Context Protocol
- **Real-time**: Flask SSE (Server-Sent Events) for progress streaming
- **Transcription**: Local faster-whisper (word-level timestamps) — auto-detects the video's language by default, user-overridable per run
- **Face Detection**: `face-detection` (MediaPipe) or `opencv-python` — sampled across each clip into a smoothed face track that pans the crop
- **Video Processing**: ffmpeg (existing) + moviepy (existing)

### Directory Structure
```
Backend/
  classes/
    Clipper.py           # Core pipeline orchestrator
    ClipperProject.py    # Project management + ClipSegment dataclass (URLs, training data, templates)
    FaceDetector.py      # Face detection for smart cropping
    ViralityScorer.py    # Scoring engine (minimal AI)
  mcp/
    clipper_mcp.py       # MCP server implementation
  transcription.py       # Local faster-whisper transcription (word-level) + SRT import
  llm_providers.py      # Multi-LLM provider config + dispatch + outline extraction
  clipper_routes.py      # Flask API routes
  clipper_editor.py      # Trim/split/merge operations
  clipper_cli.py         # CLI (create/process/select/export/doctor)

UI/
  pages/
    clipper/
      index.vue          # Main clipper workspace
      project.vue        # Project management
      editor.vue         # Built-in editor
  components/
    clipper/
      VideoUploader.vue
      ProjectManager.vue
      ClipCard.vue
      ClipEditor.vue
      ViralityScore.vue
      TranscriptTimeline.vue
  stores/
    ClipperStore.ts      # Pinia store
  composables/
    useClipper.ts
    useViralityScore.ts
```

---

## 3. Project System

A **Project** defines the content context for clip generation. Multiple source videos can belong to one project.

### Project Schema
```python
@dataclass
class ClipperProject:
    id: str                          # UUID
    name: str                        # "Jürgen Klopp Analysis"
    description: str                 # Content theme description
    source_urls: List[str]          # Video URLs to clip from
    training_data: str              # Custom guidelines (viral patterns, audience, style)
    template: ClipTemplate          # Caption style, font, B-roll rules
    target_platform: str            # "tiktok" | "reels" | "shorts"
    created_at: datetime
    updated_at: datetime
```

### Project Features
- **Source URL Management**: Add/remove source videos (YouTube, direct MP4, Instagram)
- **Local File Import**: Upload local video files (mp4/mkv/webm/mov/avi) via `POST /api/clipper/projects/{id}/upload` — registered as `local://` pseudo-URLs, no download needed
- **SRT Subtitle Import**: Attach a `.srt` alongside the upload (or drop `sources/{source_id}.srt` in manually) — skips Whisper transcription entirely; word timings are approximated by even split across cues
- **Training Data**: Freeform text defining viral patterns, target audience, content style
- **Templates**: Caption templates, font choices, B-roll rules per project
- **Auto-Transcription Storage**: All transcriptions saved per project for template generation, **reused on reprocess** (cache hit skips download + transcription)

### Training Data Generation (Minimal AI)
1. User provides source URLs + content theme
2. CLIPPER downloads and transcribes each video (faster-whisper, word-level)
3. Transcription + user training_data → generates **Viral Patterns Template**:
   - Key phrases that indicate viral potential
   - Emotional trigger patterns
   - Engagement indicators from transcription
4. This template guides the ViralityScorer without requiring LLM per-segment analysis

---

## 4. Transcription Pipeline

### Local Transcription (faster-whisper) — the only path
CLIPPER transcribes **entirely locally** using `faster-whisper` (CTranslate2-backed, fast on CPU, low memory). No cloud transcription service is used.

```python
# Backend/transcription.py
model = WhisperModel(
    model_size,              # WHISPER_MODEL env var, default "base"
    device="cpu",            # or "cuda" via WHISPER_DEVICE env var
    compute_type="int8",     # float16 on CUDA
)

segments, info = model.transcribe(
    video_path,
    language=None,           # None = auto-detect (default); ISO code forces one
    word_timestamps=True,    # word-level timing for synced captions
)
```

**Language handling:**
- Default is **auto-detect (`"auto"`)** — Whisper transcribes in the video's own spoken language so subtitles match the audio instead of forcing English.
- The user can override per run via the **"Transcription Language"** selector in the CLIPPER workspace (UI, `Auto-detect` default) or by passing `language` in the `POST /api/clipper/process` body (`"auto"` or an ISO 639-1 code, e.g. `es`, `de`, `fr`).
- Language is passed through: UI (`ClipperStore.processProject(id, language)`) → `POST /api/clipper/process` → `Clipper.process_sources(language=...)` → `transcribe_video_local(video_path, language=...)` (`normalize_transcription_language` maps `"auto"`/`""`/`None` → `None`).
- The detected language is stored on the transcript (`language` + `language_probability`, also mirrored in `engagement_signals`) and returned in process results.
- Model size is configurable via the `WHISPER_MODEL` env var (`tiny`, `base`, `small`, `medium`, `large-v3`); device via `WHISPER_DEVICE` (`cpu` default, `cuda` supported).

### Transcript Schema
```python
@dataclass
class Transcript:
    video_url: str
    duration: float
    words: List[WordTimestamp]  # [{word, start_time, end_time, confidence}]
    sentences: List[SentenceTimestamp]  # [{text, start_time, end_time}]
    topics: List[str]  # detected topics
    i_words: int  # "viral" indicator words count
    engagement_signals: Dict  # {pause_count, long_pauses, excitement_markers}
    outline: List[Dict]  # [{topic, start, end, summary}] — topic timeline (LLM w/ heuristic fallback)
```

### Transcript Caching
Transcripts are saved locally per project and reused on reprocessing — no re-transcription cost:
- Saved to `Backend/static/clipper/projects/{project_id}/transcripts/{source_id}.json`
- JSON format with word-level timestamps

---

## 5. AI Clip Selection (Minimal AI)

### Approach
Instead of sending entire transcripts to LLM, use a **two-phase scoring system**:

**Phase 1: Heuristic Scoring (No AI)**
- Pause detection (engagement signals)
- Volume/energy analysis (if audio available)
- Keyword matching against project training_data
- Sentence boundary detection
- Duration filtering (30s–90s optimal range)

**Phase 2: Light LLM Scoring (Only for Top Segments)**
- Run Phase 1 scoring on all segments
- Take top 15-20 segments by heuristic score
- Send ONLY those segments to LLM for final ranking
- LLM picks top 3-7, outputs structured JSON

### Prompt Strategy
```python
CLIP_SELECTION_PROMPT = """
You are a viral clip selector. Given {n} video segments with transcripts,
select the {k} most clip-worthy moments for {platform} shorts.

Rules:
- Prioritize: hook strength, emotional impact, standalone clarity, shareability
- Reject: requires context, slow pacing, niche jargon
- Each segment: {start}-{end}s - "{transcript_excerpt}"

Output JSON:
{{"selected": [{{"index": int, "start": float, "end": float, "reason": str}}]}}
"""
```

### Clip Selection Output
```python
@dataclass
class ClipSegment:
    index: int
    start_time: float
    end_time: float
    transcript: str
    scores: ViralityScores
    hook_title: str  # AI-generated per clip
    thumbnail_url: str
    status: str  # "pending" | "selected" | "rejected" | "rendered"
```

---

## 6. Virality Scoring

### Score Components (No AI, multilingual)
Signal word lists cover en/es/de/fr/pt/it/nl so non-English videos score on their own language. Training-data keywords are tokenized (phrases + significant words, stopwords dropped) so freeform descriptions match. Overall scores are min-max rescaled per video (20–95) so the best moment clearly stands out instead of every clip landing in one flat band.
```python
@dataclass
class ViralityScores:
    hook_score: float      # 0-100: First 5s excitement/curiosity
    engagement_score: float  # 0-100: Pauses, excitement density, speech-rate sweet spot
    value_score: float    # 0-100: Training-keyword token overlap (or richness proxy)
    shareability_score: float  # 0-100: Universal appeal, emotions evoked
    overall_score: float  # Weighted composite, rescaled 20-95 across segments

    # Component metrics
    pause_count: int      # Silence/slow moments
    excitement_markers: int  # Energy words detected
    question_marks: int  # Curiosity gaps
    call_to_action: bool  # Engagement prompt present
```

### Scoring Algorithm
```python
def calculate_virality_score(transcript_segment: str, word_timestamps: List[WordTimestamp]) -> ViralityScores:
    # Hook: Check first 5s for question/contrast/shock patterns
    first_5s_words = get_words_in_range(word_timestamps, 0, 5)
    hook_score = analyze_hook_strength(first_5s_words)

    # Engagement: Count pauses (gaps > 1.5s between words)
    pauses = count_pauses(word_timestamps, threshold=1.5)
    engagement_score = min(100, pauses * 15 + base_engagement)

    # Value: Keyword density from training_data
    value_keywords = extract_keywords(training_data)
    value_score = keyword_density(transcript_segment, value_keywords)

    # Shareability: Emotional word detection + CTA presence
    shareability_score = analyze_shareability(transcript_segment)

    return ViralityScores(...)
```

---

## 7. Smart Vertical Cropping (Face Detection)

### Face-Tracked 9:16 Rendering
Clips follow the speaker: `FaceDetector.get_face_track(video, start, end)` samples up to 6 faces *inside the clip segment* (absolute timestamps, gap-filled + moving-average smoothed), and `build_tracking_crop_filter` turns the track into a time-interpolated ffmpeg crop (`x='if(lt(t,…),…)'`) so the 9:16 window pans with the face. Static fallback (upper-third) applies when no face is found, and the render retries once with a static crop if the ffmpeg build rejects the animated expression.
```python
def smart_crop_to_vertical(
    input_path: str,
    output_path: str,
    face_x: float,  # detected face center X (0-1 normalized)
    face_y: float,  # detected face center Y (0-1 normalized)
    target_w: int = 1080,
    target_h: int = 1920
) -> bool:
    """
    Crop and scale to 9:16, keeping face centered.
    If no face detected, use rule-of-thirds composition.
    Prefer build_tracking_crop_filter + get_face_track for clips:
    the window pans to follow the face across the segment.
    """
    # Calculate crop window centered on face
    # Scale up to fill frame
    # Apply subtle zoom effect
```

### Face Detection Implementation
```python
# Using MediaPipe (face-detection package) or OpenCV Haar Cascades
def detect_face_center(frame) -> Tuple[float, float]:
    # Returns (x, y) normalized 0-1, or None if no face
    # Prefer largest/most-central face if multiple detected
    pass

def get_best_crop_for_segment(video_path: str, start: float, end: float) -> Tuple[float, float]:
    # Sample frames at start, 1/3, 2/3, end
    # Use face with most consistent presence
    # Fallback: upper-third composition (speaker headroom)
```

### B-Roll & Transitions
```python
# Optional B-roll from Pexels (existing search integration)
# Transitions: "cut", "fade", "zoom" (all implemented in the ffmpeg filter chain)
# "zoom" applies a slow Ken-Burns style zoompan to the B-roll PiP
TRANSITION_PRESETS = {
    "viral": {"type": "cut", "duration": 0},
    "cinematic": {"type": "dissolve", "duration": 0.5},
    "dynamic": {"type": "zoom", "duration": 0.25},
}
```

---

## 8. Word-Synced Subtitles

### Word-Level SRT Generation (same style as /api/generate)
Clip captions reuse the system subtitle templates (`settings.py` — the single source of truth shared with the main generator) and the same ffmpeg ASS rendering (`original_size`, fc-scan font-family resolution, identical PlayRes scaling and filter escaping). `generate_word_synced_srt` chunks by ~42 chars like `srt_equalizer` (not fixed 8-word blocks) so captions wrap identically on narrow 9:16 frames, and `burn_subtitles_and_hook` takes the real `target_w/h` so exports (9:16 / 3:4 / 16:9) keep the same caption size/position.
```python
def generate_word_synced_srt(
    words: List[WordTimestamp],
    output_path: str,
    template: SubtitleTemplate
) -> str:
    """
    Generate SRT with per-word timing.
    Uses word-level timestamps from faster-whisper.
    Falls back to equal-duration allocation when timestamps unavailable.
    """
    # For each word, create mini-subtitle entry
    # Enable karaoke/highlight style rendering
```

### Caption Templates (Extend Existing)
```python
CLIPPER_SUBTITLE_TEMPLATES = {
    "viral_stroke": {
        "color": "#FFFF00",
        "stroke_color": "black",
        "stroke_width": 6,
        "fontsize": 110,
        "position": "center,bottom",
        "animation": "typewriter",  # new
    },
    "kinetic": {
        "color": "#FFFFFF",
        "stroke_color": "#000000",
        "stroke_width": 3,
        "fontsize": 90,
        "position": "center,center",
        "animation": "pop_on",  # new
    },
}
```

### Hook Title Burn-In
```python
def burn_hook_title(
    clip_path: str,
    title: str,
    output_path: str,
    style: dict  # font, color, position, animation
) -> str:
    """
    Burn AI-generated hook title into first 3s of clip.
    Position: top 15% of frame.
    Animation: slide-in from top or typewriter effect.
    """
```

---

## 9. Built-in Editor

### Editor Features
- **Timeline View**: Visual representation of clip with word-synced captions
- **Trim**: Drag start/end handles on waveform (pointer-captured, `touch-none`, 0.5s min span; click-to-seek suppressed briefly after a handle drag)
- **Seek**: Click the track to seek (clamped to the trim region); selecting a clip seeks the preview to that clip's segment start (never 0:00) and the preview loops inside the trimmed region without `#t=` fragments so timeline timestamps stay absolute
- **Split**: Click to split at cursor position
- **Merge**: Combine multiple segments into single clip
- **Preview**: Real-time preview of edits

### Editor Actions
```python
# Trim
POST /api/clipper/clip/{clip_id}/trim
{"start_time": 12.5, "end_time": 45.2}

# Split
POST /api/clipper/clip/{clip_id}/split
{"split_time": 30.0}

# Merge
POST /api/clipper/merge
{"clip_ids": ["uuid1", "uuid2"], "output_name": "merged_clip"}

# Export
POST /api/clipper/clip/{clip_id}/export
{"format": "tiktok"|"reels"|"shorts", "quality": "high"|"medium"}
```

---

## 10. Real-Time Progress (SSE)

### Server-Sent Events Stream
```python
@app.route("/api/clipper/pipeline/stream")
def clipper_pipeline_stream():
    """SSE endpoint for real-time progress"""
    def generate():
        # Subscribe to global CLIPPER_PROGRESS publisher
        for progress in iter_progress():
            yield f"data: {json.dumps(progress)}\n\n"
    return Response(generate(), mimetype='text/event-stream')
```

### Progress Events
```python
@dataclass
class PipelineProgress:
    stage: str  # "downloading"|"transcribing"|"scoring"|"rendering"|"done"
    progress: float  # 0.0-1.0
    current_clip: int  # n of total
    total_clips: int
    message: str
    preview_url: str  # thumbnail of current clip
```

### Frontend Integration
```typescript
// useClipper.ts
async function streamProgress(projectId: string) {
  const eventSource = new EventSource(`/api/clipper/pipeline/stream?project_id=${projectId}`)
  eventSource.onmessage = (event) => {
    const progress = JSON.parse(event.data)
    clipperStore.updateProgress(progress)
  }
}
```

---

## 11. Multi-LLM Provider Configuration

Any provider can be configured at runtime (Settings view → "AI Model Provider") or via env vars (`CLIPPER_LLM_PROVIDER`, `CLIPPER_LLM_BASE_URL`, `CLIPPER_LLM_API_KEY`, `CLIPPER_LLM_MODEL`). Stored in `Backend/static/clipper/llm_settings.json`.

| Provider | Backend | Default base URL / model |
|----------|---------|---------------------------|
| `g4f` | g4f Gemini web (free, default) | — |
| `openai` | OpenAI-compatible (OpenAI, SiliconFlow, LM Studio, vLLM…) | `https://api.openai.com/v1` / `gpt-4o-mini` |
| `ollama` | Ollama local | `http://localhost:11434/v1` / `qwen2.5:7b` |
| `gemini` | Official Google AI SDK | `gemini-2.5-flash` |
| `qwen` | Alibaba DashScope (OpenAI-compatible) | `qwen-plus` |

- `POST /api/clipper/llm/test` sends a tiny prompt to validate the config ("Test connection" button).
- All CLIPPER LLM calls (clip selection, hook titles, metadata, outline) route through the configured provider automatically.

---

## 12. Cancellation

- `POST /api/clipper/cancel` with `{project_id}` (or `*` for any run) sets a cancel flag.
- The pipeline checks the flag at stage boundaries (per-source download/transcribe, per-segment scoring, per-clip render) and raises `ClipperCancelled`.
- Routes catch it and return `{status: "cancelled"}` (HTTP 200); the UI shows "Processing cancelled" instead of an error.
- Long ffmpeg calls complete their current step before the cancel takes effect (no partial-file corruption).

---

## 13. Export Presets & Compilations

### Platform presets (real render differences, not folder names)
```python
EXPORT_PRESETS = {
    "tiktok": "9:16", "reels": "9:16", "shorts": "9:16",
    "douyin": "9:16", "xiaohongshu": "3:4", "bilibili": "16:9", "youtube": "16:9",
}
QUALITY_PRESETS = {"high": crf 18/fast, "medium": crf 23/ultrafast, "low": crf 28/ultrafast}
```
- `burn_subtitles` toggle (POST body) — render with or without caption burn-in.
- Compilations: `POST /api/clipper/merge` now renders a **real concatenated video** (each clip rendered first, normalized, joined via ffmpeg concat demuxer). Compilation clips carry `is_compilation: true` + `source_clip_ids`.

### Auto-covers
- `POST /api/clipper/clip/{id}/cover` — frame grab + hook-title text overlay (`Clipper.generate_cover`), saved to `covers/{clip_id}.jpg` and set as the clip thumbnail.

---

## 14. Publish Records

Every MagicSync schedule call persists a record to `projects/{id}/publish_records.json`:
`{id, clip_id, clip_hook_title, platforms, scheduled_at, visibility, title, video_url, status ("scheduled"|"error"), response, created_at}`

- `GET /api/clipper/projects/{id}/publish-records` — list (shown in the UI "Publish" view grouped by day)
- `DELETE /api/clipper/projects/{id}/publish-records/{record_id}` — remove a record
- The schedule payload now supports `visibility: "private" | "public"` (passed through to MagicSync)

---

## 15. CLI

```bash
cd Backend
python clipper_cli.py create --name "Podcast" --url https://youtube.com/watch?v=...
python clipper_cli.py process --project PROJECT_ID --language auto --model-size base
python clipper_cli.py select  --project PROJECT_ID --max-clips 7
python clipper_cli.py export  --project PROJECT_ID --format shorts --quality high
python clipper_cli.py list
python clipper_cli.py doctor --provider ollama   # health check: ffmpeg, whisper, yt-dlp, LLM
```

Same pipeline as the web UI and MCP server.

---

## 16. REST API Endpoints

### Project Management
```
GET    /api/clipper/projects              # List all projects
POST   /api/clipper/projects              # Create project
GET    /api/clipper/projects/{id}        # Get project details
PUT    /api/clipper/projects/{id}        # Update project
DELETE /api/clipper/projects/{id}        # Delete project
POST   /api/clipper/projects/{id}/sources  # Add source URL
POST   /api/clipper/projects/{id}/upload  # Upload local video (+ optional SRT), multipart
DELETE /api/clipper/projects/{id}/sources/{source_id}  # Remove source
```

### Source Video Processing
```
POST   /api/clipper/process               # Start processing (download + transcribe; body: language, model_size, ai_model)
POST   /api/clipper/cancel                # Request cancellation
GET    /api/clipper/process/{project_id}/status  # Get processing status
GET    /api/clipper/transcript/{source_id}  # Get transcript for source (incl. outline)
```

### Clip Operations
```
GET    /api/clipper/projects/{id}/clips  # List clips for project (min_score filter)
POST   /api/clipper/select               # AI select top clips
POST   /api/clipper/clip/{id}/render     # Render single clip (format/quality/burn_subtitles options)
POST   /api/clipper/clip/{id}/cover      # Generate cover image (frame + title overlay)
POST   /api/clipper/export               # Batch export clips (7 platform presets, quality, burn toggle)
POST   /api/clipper/clip/{id}/trim
POST   /api/clipper/clip/{id}/split
POST   /api/clipper/merge                # Real compilation render (ffmpeg concat)
```

### LLM & Publishing
```
GET    /api/clipper/llm/settings          # Get provider config (masked key)
POST   /api/clipper/llm/settings          # Update provider config
POST   /api/clipper/llm/test              # Test connection (tiny prompt)
GET    /api/clipper/projects/{id}/publish-records    # List publish records
DELETE /api/clipper/projects/{id}/publish-records/{record_id}  # Delete record
```

### Editor & Export
```
POST   /api/clipper/clip/{id}/preview    # Generate preview frame
GET    /api/clipper/clip/{id}/download   # Download rendered clip
```

---

## 17. MCP Server

### MCP Tools Definition
```python
# clipper_mcp.py
from mcp.server import Server
from mcp.types import Tool, TextContent

clipper_server = Server("clipper")

@clipper_server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="list_projects",
            description="List all CLIPPER projects",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="create_project",
            description="Create a new CLIPPER project",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "source_urls": {"type": "array", "items": {"type": "string"}},
                    "training_data": {"type": "string"},
                },
                "required": ["name", "source_urls"]
            }
        ),
        Tool(
            name="process_project",
            description="Start processing source videos in a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_clips",
            description="Get clips for a project with scores",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "min_score": {"type": "number"}
                }
            }
        ),
        Tool(
            name="render_clip",
            description="Render a specific clip",
            inputSchema={
                "type": "object",
                "properties": {
                    "clip_id": {"type": "string"},
                    "format": {"type": "string", "enum": ["tiktok", "reels", "shorts"]}
                },
                "required": ["clip_id"]
            }
        ),
    ]

@clipper_server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    # Route to appropriate handler
    pass
```

### MCP Transport
```python
# Run with: python -m clipper_mcp
# Or integrate with existing Flask app via SSE bridge
```

---

## 18. Frontend Design

### Main Clipper Page (`/clipper`)
```
┌─────────────────────────────────────────────────────────┐
│ Header: CLIPPER  [New Project] [Projects] [Settings]    │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────────────────────────────┐ │
│ │             │ │                                     │ │
│ │  Project    │ │   Video Preview / Editor            │ │
│ │  Sources    │ │   (9:16 vertical preview)          │ │
│ │  Panel      │ │                                     │ │
│ │             │ │                                     │ │
│ │  - URL 1 ✓ │ │   [Hook Title]                      │ │
│ │  - URL 2 ◌ │ │                                     │ │
│ │  + Add URL  │ │   Word-synced captions              │ │
│ │             │ │                                     │ │
│ └─────────────┘ │   Face-centered crop                 │ │
│ ┌─────────────┐ │                                     │ │
│ │             │ │                                     │ │
│ │  Clips      │ └─────────────────────────────────────┘ │
│ │  List       │ ┌─────────────────────────────────────┐ │
│ │             │ │  Virality Scores                    │ │
│ │  [Clip 1]   │ │  Hook: ████████░░ 80               │ │
│ │  Hook: 85   │ │  Engagement: ██████░░░░ 60         │ │
│ │  Score: 78  │ │  Value: ███████░░░ 70               │ │
│ │             │ │  Shareability: ████░░░░░░ 40       │ │
│ │  [Clip 2]  │ └─────────────────────────────────────┘ │
│ │  Hook: 72   │                                        │
│ │  Score: 65  │  [Render Selected] [Export All]        │
│ └─────────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

### Project Setup Modal
- Name, description fields
- Source URL input (YouTube, direct MP4)
- Training data textarea (viral patterns, audience description)
- Target platform selector (TikTok/Reels/Shorts)

### Editor View (`/clipper/editor/:clipId`)
- Full-width timeline with waveform visualization
- Word-synced caption track
- Trim handles (drag to adjust start/end)
- Split button (splits at playhead)
- B-roll insertion points
- Real-time preview

---

## 19. Key Technical Decisions

### Minimize AI Usage
- Phase 1 scoring: Pure heuristics, zero AI calls
- Phase 2: LLM only for top 15-20 segments (not entire transcript)
- Hook titles: One AI call per selected clip (not per potential clip)
- Template generation: One AI call per project (not per clip)

### Transcription Storage
- Save all transcripts to `Backend/static/clipper/projects/{project_id}/transcripts/`
- Reuse cached transcripts when reprocessing
- JSON format with word-level timestamps

### Face Detection Strategy
- Use MediaPipe face detection (CPU, fast), OpenCV Haar fallback
- Sample up to 6 frames *inside each clip segment* (absolute timestamps via `detect_faces_at_times`), gap-fill + smooth into a face track
- Render pans the crop window along the track (`build_tracking_crop_filter`); static retry fallback if the ffmpeg build rejects animated expressions
- Fallback: upper-third composition when no face detected
- Store face coordinates per segment for consistent cropping

### yt-dlp Bot-Gate Strategy
- `player_client` defaults to `["android", "tv", "tv_embedded", "ios", "mweb", "android_vr"]` in all yt-dlp call sites (`classes/Clipper.py`, `main.py`) — `android` is the primary bot-gate bypass; `tv`/`tv_embedded` also pass without cookies/PO tokens. Override the chain with `YTDLP_PLAYER_CLIENT` (comma-separated); if YouTube still flags the IP, set `YTDLP_COOKIES` (Netscape cookies.txt file) or `YTDLP_COOKIES_FROM_BROWSER` (e.g. `chrome`).
- If the IP is still flagged ("Sign in to confirm you're not a bot"), cookies are required since no player client alone will pass:
  - `YTDLP_COOKIES=/path/to/cookies.txt` — Netscape-format cookies file
  - `YTDLP_COOKIES_FROM_BROWSER=chrome` — export cookies from a local browser profile (`chrome` | `firefox` | `edge` | `chromium` | `brave`)
- Both vars are optional and read at download time.

### Video Rendering Pipeline
```
1. Download source (yt-dlp)
2. Transcribe (faster-whisper, local, auto-detect language / user-overridable)
3. Score segments (multilingual heuristics, rescaled 20-95)
4. Select top clips (light LLM)
5. Generate hook titles (AI)
6. For each clip:
   a. Track face positions across the segment
   b. Crop to 9:16 (face-tracking pan, static fallback)
   c. Burn captions (ffmpeg ASS filter, same style as /api/generate)
   d. Burn hook title (first 3s)
   e. Optional: Add B-roll overlays
   f. Add transitions
7. Render final clips
```

---

## 20. Dependencies

```txt
# New dependencies for CLIPPER (already in requirements.txt)
faster-whisper>=1.0.0          # Local transcription (word-level timestamps, English default)
opencv-python>=4.9.0.0         # Fallback face detection + video tools
mcp>=0.9.0                     # MCP server SDK
```

> Note: no cloud transcription dependency is required — CLIPPER is local-only.

---

## 21. Implementation Phases

### Phase 1: Core Infrastructure ✅
- [x] ClipperProject dataclass and storage (`Backend/classes/ClipperProject.py`, JSON-backed `project_store` incl. publish records)
- [x] Transcription pipeline — **local-only faster-whisper**, English default, user-selectable language + model size (`Backend/transcription.py`)
- [x] Basic REST API endpoints (`Backend/clipper_routes.py`, 30+ routes registered under `/api/clipper`)
- [x] ClipSegment dataclass with scoring + compilation fields (`Backend/classes/ClipperProject.py`)

### Phase 2: Virality Scoring ✅
- [x] ViralityScorer implementation (pure heuristics, zero AI calls) (`Backend/classes/ViralityScorer.py`)
- [x] Score visualization in API response (hook / engagement / value / shareability / overall)
- [x] Segment filtering by score threshold (`GET /api/clipper/projects/{id}/clips?min_score=` + UI Filters popover)

### Phase 3: AI Clip Selection ✅
- [x] Light LLM integration for top-N selection (two-phase: heuristic shortlist → LLM ranking, `Backend/classes/Clipper.py`)
- [x] Hook title generation (one AI call per selected clip)
- [x] Project training data integration (feeds keyword matching + value score)
- [x] **Multi-LLM provider config** (`Backend/llm_providers.py`: g4f/OpenAI-compatible/Ollama/Gemini/Qwen + Test Connection UI)
- [x] **Topic timeline / outline extraction** (`build_transcript_outline`, LLM with heuristic fallback, shown in UI transcript view)

### Phase 4: Rendering Pipeline ✅
- [x] Face detection integration (`Backend/classes/FaceDetector.py`, MediaPipe with OpenCV fallback)
- [x] Smart vertical cropping (face-TRACKED pan via `get_face_track` + `build_tracking_crop_filter`, per-preset aspect: 9:16 / 3:4 / 16:9, static + upper-third fallback)
- [x] Word-synced subtitle generation (faster-whisper word timestamps → ASS burn-in with generate-pipeline parity, **toggleable**)
- [x] Hook title burn-in (first 3s of clip)
- [x] B-roll overlay support (Pexels fetch + PiP overlay with cut/fade/**zoom** transitions)
- [x] **Auto-covers** (frame + hook-title text overlay, `POST /clip/{id}/cover`)
- [x] **Real export presets** (7 platforms × 3 quality levels, actual render differences)

### Phase 5: Editor ✅
- [x] Trim/split/merge operations (`Backend/clipper_editor.py`, REST: `/clip/{id}/trim`, `/clip/{id}/split`, `/merge`)
- [x] Timeline visualization (word-synced blocks + draggable trim handles, `UI/components/clipper/TranscriptTimeline.vue`)
- [x] Real-time preview (in-editor 9:16 video streaming with Range support via `GET /api/clipper/clip/{id}/video`, frame previews via `POST /api/clipper/clip/{id}/preview`)
- [x] **Merge renders a real compilation video** (ffmpeg concat of rendered segments)

### Phase 6: MCP Server ✅
- [x] MCP server (`Backend/mcp/clipper_mcp.py`) — JSON-RPC 2.0 stdio with initialize handshake
- [x] 13 tools: list/create/get/delete_project, process, get_clips, select, render, trim, **split, merge, get_transcript, export** (with presets)
- [x] Path resolution fixed (static dirs resolve from `Backend/` root)

### Phase 7: Frontend ✅
- [x] `/clipper` page (`UI/pages/clipper/index.vue` — projects / workspace / editor / transcript / publish / settings views, SSE progress)
- [x] Project management UI (`ProjectManager.vue`, `VideoUploader.vue` — URLs **and local file upload + SRT**)
- [x] Clip list with scores (`ClipCard.vue`, `ViralityScore.vue`)
- [x] Editor view (`editor/[clipId].vue` + `ClipEditor.vue` — playback sync, trim/split, export with presets, cover generation)
- [x] **Publish view** — records grouped by day, status badges, visibility, delete
- [x] **LLM provider settings card** with Test Connection
- [x] **Cancel button** during processing

### Phase 8: Import & Automation ✅
- [x] Local video file upload (`POST /projects/{id}/upload`, `local://` pseudo-URLs)
- [x] SRT subtitle import (skips Whisper; word timings approximated from cues)
- [x] Transcript cache reuse on reprocess (no re-transcription)
- [x] Pipeline cancellation (`POST /cancel`, stage-boundary checks)
- [x] CLI (`Backend/clipper_cli.py` — create/process/select/render/export/list/delete/doctor)

**Status: feature parity with AutoClip's core workflow (import → transcribe/SRT → outline → score → clip → render → export → publish). Remaining optional work: none blocking.**
