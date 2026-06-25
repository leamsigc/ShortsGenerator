# ShortsGenerator

![ShortGenerator](/logo.jpeg)

Automate YouTube Shorts creation locally — script generation, stock video search, TTS voiceover, subtitles, background music, and social media scheduling.

## Features

- **AI Script Generation** — uses g4f (free) or Gemini to generate video scripts
- **Stock Video Search** — auto-downloads matching clips from Pexels
- **TwelveLabs Clip Selection** *(optional)* — reranks the Pexels candidates with the Pegasus video-understanding model so the most relevant B-roll is used first; enabled by setting `TWELVELABS_API_KEY` ([free tier](https://twelvelabs.io))
- **Multi-Voice TTS** — Supertonic (local, 10 voices, 33 languages), TikTok TTS (fallback), KittenTTS
- **Subtitle Templates** — 10 presets (classic, modern_glow, bold_outline, minimal, cinematic, neon, social_viral, floating, news_ticker, karaoke_highlight)
- **Background Music** — auto-mix from your music library or extract from a video
- **Image Stitching** — upload multiple images to stitch at the start of the video with configurable duration per image (default 5s)
- **Frame Extraction** — extract a frame from any generated video for thumbnails
- **Aspect Ratios** — 9:16, 16:9, 1:1, 4:5, 21:9
- **Multi-Business MagicSync** — configure multiple API keys for different businesses; select which one to use when scheduling
- **Social Media Scheduling** — schedule posts to Instagram, TikTok, Facebook, LinkedIn, YouTube via MagicSync
- **Hardware Acceleration** — auto-detects GPU for faster ffmpeg encoding



[YouTube](https://youtu.be/s7wZ7OxjMxA) or click on the image.
[![Short Generator](/logo.jpeg)](https://youtu.be/s7wZ7OxjMxA "Short generator, video generator")

![Generate](/static/assets/images/Screen1.png)
![Generate 2](/static/assets/images/Screenshot2.png?raw=true)
![Generate 3](/static/assets/images/Screenshot3.png?raw=true)



## Quick Start (Docker)

```bash
git clone https://github.com/leamsigc/ShortsGenerator.git
cd ShortsGenerator
cp .env.example .env
# Edit .env — at minimum set PEXELS_API_KEY and IMAGEMAGICK_BINARY
docker compose up -d
```

Open **http://localhost:5000** or **http://localhost:3000** for the frontend.

## Manual Setup

### Backend (Python Flask on :8080)

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in PEXELS_API_KEY, IMAGEMAGICK_BINARY, etc.
cd Backend
python main.py
```

### Frontend (Nuxt 3 on :3000)

```bash
cd UI
npm install
npm run dev
```

The frontend depends on the backend running on port 8080.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PEXELS_API_KEY` | Yes | Stock video search |
| `IMAGEMAGICK_BINARY` | Yes | Path to ImageMagick convert (e.g. `/usr/bin/convert`) |
| `TIKTOK_SESSION_ID` | No | TikTok TTS fallback |
| `GOOGLE_API_KEY` | No | Gemini AI model |
| `ASSEMBLY_AI_API_KEY` | No | Cloud subtitle generation |
| `OPENAI_API_KEY` | No | OpenAI models |
| `MAGICSYNC_BASE_URL` | No | Default MagicSync server URL |
| `MAGICSYNC_API_TOKEN` | No | Default MagicSync API token |

See [EnvironmentVariables.md](EnvironmentVariables.md) for the full list.

## Usage

1. **Generate a script** — enter a video subject, select a script template, click Generate
2. **Review & edit** — modify the script, add search keywords, select subtitle template
3. **Upload images (optional)** — upload images that will be stitched at the start of the video; set duration per image
4. **Select voice** — choose TTS engine and voice style
5. **Set aspect ratio** — 9:16 (default), 16:9, 1:1, or 4:5
6. **Generate video** — downloads stock clips, generates TTS, combines everything with subtitles
7. **Add music** — pick from your music library or extract audio from a video
8. **Schedule** — in the Videos page, click "Schedule Upload", select a business and platforms, set date/time, and post via MagicSync

### Image Stitching

In the **Generate** page, click the **Images** section and upload one or more images. Each image becomes a video segment at the start of the final video. Adjust the global duration (default 5s) or set per-image duration. Images are scaled and cropped to match the selected aspect ratio.

### Multi-Business MagicSync

In **Settings → MagicSync Integration**, add API keys for each business. Each business has its own MagicSync URL, API token, and video base URL. When scheduling a video, select which business to use — the correct credentials are sent automatically.

### Thumbnail Extraction

`POST /api/extract-frame` extracts a frame from any generated video at a given timestamp. Use this to generate custom thumbnails.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate` | Full video generation pipeline |
| POST | `/api/script` | Generate script only |
| POST | `/api/search-and-download` | Search + download + TTS + combine |
| POST | `/api/cancel` | Cancel generation |
| POST | `/api/addAudio` | Add background music to video |
| POST | `/api/upload-music` | Upload music file |
| POST | `/api/download-music-url` | Download & extract audio from URL |
| POST | `/api/upload-video` | Upload video files |
| POST | `/api/upload-image` | Upload images for video stitching |
| POST | `/api/extract-frame` | Extract a frame from a video |
| GET | `/api/getVideos` | List generated videos |
| GET | `/api/getSongs` | List available music |
| GET | `/api/models` | List TTS voices |
| GET | `/api/settings` | Get global settings |
| POST | `/api/settings` | Update global settings |
| POST | `/api/magicsync/accounts` | List MagicSync accounts |
| POST | `/api/schedule-to-magicsync` | Schedule a post |
| GET | `/api/video/<filename>` | Serve generated video |
| GET | `/static/generated_videos/<file>` | Static video files |

## Directory Structure

```
Backend/
├── main.py              # Flask app, all API routes
├── video.py             # Video processing, ffmpeg, subtitles, images
├── settings.py          # Global defaults
├── gpt.py               # AI script generation
├── search.py            # Pexels stock video search
├── twelvelabs_select.py # Optional Pegasus clip reranking
├── tiktokvoice.py       # TikTok TTS
├── classes/
│   └── Shorts.py        # Core pipeline orchestrator
UI/
├── pages/
│   ├── generate/index.vue  # Video generation workspace
│   ├── videos/index.vue    # Gallery + scheduling
│   └── settings.vue        # Global settings + MagicSync
├── composables/
│   ├── useVideoSettings.ts # Video generation state
│   └── useGlobalSettings.ts # App-wide settings
└── stores/
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

## License

See [`LICENSE`](LICENSE) for details.
