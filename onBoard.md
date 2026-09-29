# ShortsGenerator — LLM Onboard

YouTube Shorts video generation system. Backend: Python Flask (port 8080). Frontend: Nuxt 3 SPA (port 3000).

## Quick Start

### Recommended: Anaconda/Miniconda environment (isolated, pinned versions)

The project needs Python 3.11 with pinned package versions (see `environment.yml` / `requirements.txt`).
Do **not** install into `base` — conflicting versions in base cause runtime errors (e.g. transcription failures).

```bash
# 1. Create the environment (one-time, ~5 min: Python 3.11 + ffmpeg + all pip deps)
conda env create -f environment.yml

# 2. Activate it
conda activate shortsgenerator

# 3. Configure and run
cp .env.example .env
# Fill .env: PEXELS_API_KEY, TIKTOK_SESSION_ID, IMAGEMAGICK_BINARY
cd Backend && python main.py           # Flask on :8080
cd UI && npm install && npm run dev     # Nuxt on :3000
```

Useful commands:

```bash
conda activate shortsgenerator          # switch into the env (do this in every new shell)
conda env update -f environment.yml --prune   # re-sync after requirements.txt changes
conda env remove -n shortsgenerator           # delete and recreate if broken
conda run -n shortsgenerator python Backend/main.py   # run without activating
```

> `pip install -r requirements.txt` resolves versions from scratch and pip's
> backtracker can stall on it (`resolution-too-deep`). Prefer the pre-resolved
> lockfile instead — same packages, instant resolution:
> ```bash
> conda activate shortsgenerator
> pip install -r requirements.lock
> ```
> After changing pins in `requirements.txt`, regenerate the lock:
> `uv pip compile requirements.txt --python $(which python) -o requirements.lock`
> (torch/CUDA wheels for Qwen3-TTS make the full sync several GB).

Verify the env is healthy:

```bash
conda activate shortsgenerator
python -c "import moviepy, PIL, flask, faster_whisper, ctranslate2; print('env OK')"
```

### Alternative A: Anaconda/Miniconda venv (no conda env needed)

If `conda env create` is slow or unavailable, create a plain Python 3.11 venv in the repo:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # Fill: PEXELS_API_KEY, TIKTOK_SESSION_ID, IMAGEMAGICK_BINARY

# Run
cd Backend && ../.venv/bin/python main.py    # Flask on :8080
cd UI && npm install && npm run dev          # Nuxt on :3000
```

This is the fastest path — `pip check` verified clean with the pinned versions
(Pillow 12.3.0 + moviepy 1.0.3 + yt-dlp 2026.08.19).

### Alternative B: plain pip (into an activated venv/conda env)

```bash
pip install -r requirements.txt && cp .env.example .env
# Fill .env: PEXELS_API_KEY, TIKTOK_SESSION_ID, IMAGEMAGICK_BINARY
cd Backend && python main.py           # Flask on :8080
cd UI && npm install && npm run dev     # Nuxt on :3000
# Or: docker-compose up -d
```

## Key Files

| File | Purpose |
|------|---------|
| `Backend/main.py` | Flask app, all API routes |
| `Backend/settings.py` | Global defaults (fonts, TTS, aspect ratios, subtitle templates) |
| `Backend/gpt.py` | AI script generation (g4f/Gemini) |
| `Backend/search.py` | Pexels stock video search |
| `Backend/video.py` | Video processing (download, combine, subtitles, render) |
| `Backend/classes/Shorts.py` | Core pipeline orchestrator |
| `Backend/tiktokvoice.py` | TikTok TTS |
| `Backend/supertonic_tts.py` | Local ML TTS |
| `Backend/qwen3_tts.py` | Qwen3 TTS (preset timbres + Voice Design + Voice Clone) |
| `Backend/youtube.py` | YouTube OAuth2 upload |
| `requirements.txt` | Python deps |
| `.env.example` | All env vars documented |
| `UI/nuxt.config.ts` | Nuxt config (14 modules, SSR off) |
| `UI/pages/generate/index.vue` | Main video generation page |
| `UI/pages/settings.vue` | Global settings page |
| `UI/pages/videos/index.vue` | Generated videos gallery |
| `UI/pages/search.vue` | Stock video search page |
| `UI/stores/` | Pinia stores (AppStore, TabsStore) |
| `UI/composables/` | useGlobalSettings, useVideoSettings (localStorage-backed) |
| `UI/content/docs/` | Markdown docs (index, how-to-use, road-map) |

## API Endpoints

**Generation:** `POST /api/generate` (full pipeline), `POST /api/script` (script only), `POST /api/search-and-download` (from existing script), `POST /api/cancel`

**Audio:** `POST /api/addAudio`, `POST /api/upload-music`, `POST /api/download-music-url`, `GET /api/getSongs`

**Video:** `GET /api/getVideos`, `GET /api/video/<filename>`, `GET /api/getSubtitles`, `GET /api/assets`

**TTS:** `GET /api/models`, `GET /api/tts/status`, `GET /api/tts/voices?engine=`

**Settings:** `GET/POST /api/settings`

**Social:** `POST /api/instagram/download`, `POST /api/magicsync/accounts`, `POST /api/schedule-to-magicsync`

**Static:** `GET /static/generated_videos/<file>`, `GET /static/assets/music/<file>`

## Generation Pipeline (POST /api/generate)

1. Validate input → 2. Generate script (AI) → 3. Generate search terms → 4. Search & download Pexels videos → 5. TTS (Supertonic→TikTok fallback) + subtitles → 6. Combine videos (ffmpeg concat/scale/crop) → 7. Render final video (composite + audio) → 8. Generate metadata (title/desc/keywords) → 9. Optional: YouTube upload + background music → 10. Cleanup

## Key Config

- **Env required:** `PEXELS_API_KEY`, `TIKTOK_SESSION_ID`, `IMAGEMAGICK_BINARY`
- **Env optional:** `GOOGLE_API_KEY` (Gemini), `ASSEMBLY_AI_API_KEY` (cloud subtitles), `MAGICSYNC_BASE_URL`, `MAGICSYNC_API_TOKEN`
- **Aspect ratios:** 9:16 (default), 16:9, 1:1, 4:5, 21:9
- **TTS engines:** Supertonic (local, 10 voices, 33 langs), TikTok (44 voices, fallback), KittenTTS (8 voices), Qwen3-TTS (local, 9 preset timbres + characters EL-PERRO/EL-GANCHO/LA-FIERA/SOMBRA + My Voices saved in browser IndexedDB + Voice Design + Voice Clone, 10 langs + Auto, hook/retention steering)
- **Subtitle templates:** 10 presets (classic, modern_glow, bold_outline, minimal, cinematic, neon, social_viral, floating, news_ticker, karaoke_highlight)
- **Static dirs:** `Backend/static/generated_videos/` (output), `Backend/static/assets/temp/` (working), `Backend/static/assets/music/` (library), `Backend/static/assets/subtitles/`
- **Cancellation:** Global `GENERATING` flag, checked mid-pipeline

## MagicSync Integration

- Schedule posts to social platforms via `POST /api/schedule-to-magicsync`
- Video base URL must be publicly accessible (needs reverse proxy/tunnel like tunnl.gg, ngrok)
- Configured in Settings page or via `MAGICSYNC_BASE_URL`/`MAGICSYNC_API_TOKEN` env vars
- Endpoints: `POST /api/magicsync/accounts` (list connected platforms), `POST /api/schedule-to-magicsync` (schedule post)

## Frontend Routes

| Route | Page | Purpose |
|-------|------|---------|
| `/` | `pages/index.vue` | Generate script entry |
| `/generate` | `pages/generate/index.vue` | Full generation workspace |
| `/search` | `pages/search.vue` | Stock video search + Instagram download |
| `/settings` | `pages/settings.vue` | Global settings + MagicSync config |
| `/videos` | `pages/videos/index.vue` | Gallery + schedule upload |
| `/docs/*` | `pages/docs/[...slug].vue` | Documentation (Nuxt Content) |

## Notable Patterns

- **Imports:** standard → third-party → local; grouped by category
- **Error handling:** try/except with `termcolor.colored()` for console output
- **Types:** Python type hints required; Vue `<script setup lang="ts">`
- **Styling:** Tailwind CSS + UnoCSS + Naive UI components
- **i18n:** Single English locale in `UI/locales/en-US.json`
- **State:** Pinia stores + localStorage composables (useVideoSettings, useGlobalSettings)
- **Video processing:** ffmpeg preferred (fast), MoviePy fallback
