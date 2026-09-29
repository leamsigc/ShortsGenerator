# HOW-TO-USE-AI — ShortsGenerator for AI Assistants

> Read this first when dropped into this repo. Companion docs: `onBoard.md`
> (system map), `README.md` (features/endpoints), `.env.example` (all env vars).

## 1. What this is

Local YouTube Shorts factory. **Backend:** Python Flask on `:8080`
(`Backend/main.py`, all API routes). **Frontend:** Nuxt 3 SPA
(`UI/`, SSR off). **CLIPPER MCP server:** stdio JSON-RPC 2.0 tools for
clip-project operations (`Backend/mcp/clipper_mcp.py`). Heavy local ML:
Supertonic TTS, faster-whisper, Qwen3-TTS (torch/CUDA).

## 2. Environment setup (do this before anything)

```bash
conda env create -f environment.yml   # one-time: Python 3.11 + ffmpeg + pip deps
conda activate shortsgenerator        # EVERY new shell — the backend refuses
                                      # to start on any other interpreter
cp .env.example .env                  # then fill PEXELS_API_KEY, TIKTOK_SESSION_ID, IMAGEMAGICK_BINARY
```

Rules:

- **Python 3.11 only.** `Backend/main.py` exits(1) on anything else. Never
  install project packages into `base` (its stale torch/torchaudio pair is
  broken — that exact trap already bit once).
- **Install with the lockfile, not `requirements.txt`:**
  `pip install -r requirements.lock` (pre-resolved via
  `uv pip compile requirements.txt --python $(which python) -o requirements.lock`).
  Plain `requirements.txt` stalls pip's resolver (`resolution-too-deep`).
  After changing pins, regenerate the lock.
- **Full sync is several GB** (torch/CUDA for Qwen3-TTS). Qwen3 deps are
  optional at runtime: without them the engine reports `unavailable` and the
  TTS fallback chain (Qwen3 → Supertonic → TikTok) still works.
- `conda env update -f environment.yml --prune` to re-sync later.
- Health check: `python -c "import moviepy, PIL, flask, faster_whisper, ctranslate2; print('env OK')"`

## 3. Start the dev servers

```bash
# Terminal 1 — backend (CWD must be Backend/ for relative asset paths)
cd Backend && python main.py          # Flask on :8080
# or: conda run -n shortsgenerator python Backend/main.py   (from repo root)

# Terminal 2 — frontend
cd UI && npm install && npm run dev   # Nuxt on :3000 (reads ../.env)
```

Verify: `curl localhost:8080/api/settings` (backend),
`curl localhost:8080/api/tts/status` → want
`{"supertonic":"healthy","tiktok":"available","qwen3":"available"}`.
Frontend needs the backend on 8080 or every page shows "Backend unreachable".

Key routes: `/` script entry · `/generate` workspace · `/search` stock+IG ·
`/settings` ← TTS engine, AI provider, MagicSync · `/videos` gallery+schedule.

## 4. MCP server (CLIPPER tools for AI clients)

`Backend/mcp/clipper_mcp.py` — 13 tools over stdio (newline-delimited
JSON-RPC 2.0, no external `mcp` package needed). It shares CLIPPER project
storage with the Flask backend, so MCP and UI operate on the same projects.

| Tool | Purpose |
|------|---------|
| `list_projects` / `get_project` / `delete_project` | Project CRUD (needs `project_id`) |
| `create_project` | New project (`name`, `source_urls` required; `target_platform`: tiktok/reels/shorts) |
| `process_project` | Download + Whisper-transcribe sources (`language`: `auto` or ISO, e.g. `es`) |
| `get_clips` | Scored segments (`min_score` filter) |
| `select_clips` | AI-pick top clips (`max_clips`, `min/max_duration`, `ai_model`) |
| `render_clip` | Render one clip (`clip_id`, face-crop `face_x/face_y`) |
| `trim_clip` / `split_clip` | Adjust `start/end_time`, split at timestamp |
| `merge_clips` | ffmpeg-concat compilation (`render: true`) |
| `export_clips` | Batch export (`format`: tiktok/reels/shorts/douyin/xiaohongshu/bilibili/youtube; `quality`; `burn_subtitles`) |
| `get_transcript` | Transcript + topic outline (`project_id`, `source_id`) |

Run standalone (env activated — `conda run` swallows stdin, so it cannot be
used for stdio transports; call the env python directly or activate first):

```bash
conda activate shortsgenerator
python -m Backend.mcp.clipper_mcp
```

Smoke test (same shell, env activated):

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m Backend.mcp.clipper_mcp
```

Register in an MCP client (adapt absolute paths). opencode `opencode.json`:

```json
{
  "mcp": {
    "clipper": {
      "type": "local",
      "command": ["/home/leamsigc/miniconda3/envs/shortsgenerator/bin/python", "-m", "Backend.mcp.clipper_mcp"],
      "enabled": true
    }
  }
}
```

Claude Code: `claude mcp add clipper -- /home/leamsigc/miniconda3/envs/shortsgenerator/bin/python -m Backend.mcp.clipper_mcp`
(run from the repo root, or add `--cwd /path/to/ShortsGenerator`).

Typical flow: `create_project` → `process_project` → `get_clips` →
`select_clips` → `render_clip` → `export_clips`. Same `.env` as the backend
applies (Pexels key for downloads, Whisper via `WHISPER_MODEL`/`WHISPER_DEVICE`).

## 5. What's available (for planning work)

- **Generation pipeline** (`POST /api/generate`, `/api/search-and-download`,
  `/api/regenerate-video` = re-render without AI calls): script → Pexels →
  TTS+subtitles → combine → render → metadata → optional music/YouTube.
- **TTS engines** (`GET /api/tts/voices?engine=`, `POST /api/settings`
  `type: TTS`): `supertonic` (10 voices, 33 langs, quality/speed),
  `tiktok` (cloud fallback), `qwen3` (9 preset timbres + Voice Design +
  Voice Clone + 🐶 EL-PERRO Spanish commentator character; `instruct`
  steering; audition via `POST /api/tts/qwen/preview`; clone refs via
  `POST /api/tts/qwen/clone-reference`). `ttsSettings.qwen_*` keys in
  `Backend/settings.py`; engine code in `Backend/qwen3_tts.py`.
- **AI providers** (`Backend/llm_providers.py`, `Backend/gpt.py`): `gemini`
  (official API, default — needs `GOOGLE_API_KEY`), `g4f` free chain
  (cookie-free providers, or browser cookies via `browser-cookie3` —
  toggle in Settings → AI Model Provider; "0 cookies found" = package
  missing or backend not restarted, never a login problem on its own).
- **Repo skills** (`.claude/skills/`): `short-generator` (Shorts from
  multi-platform clips), `onboard`, `workflow-conventions` (read before
  touching workflows), research skills (`reddit`/`twitter`/`youtube`/`ig`/
  `facebook-research` + `-setup/-scrape/-analyze/-report` states),
  `list-workflows`, `new-workflow`.

## 6. Working rules (learned the hard way)

1. **Verify by execution.** `python3 -m py_compile` for backend edits;
   `npx vue-tsc --noEmit -p tsconfig.json` for UI (ignore pre-existing
   errors in untouched files); live-test new endpoints with `curl`/python
   before claiming done.
2. **Backend CWD matters.** Asset paths are CWD-relative; start from
   `Backend/` (or use absolute paths in new code). New path resolution must
   handle both — see `_resolve_ref_audio()` in `qwen3_tts.py`.
3. **Settings are in-memory.** `ttsSettings`/LLM settings reset on backend
   restart (only uploaded *files* persist). Don't promise persistence.
4. **Lazy-load heavy models.** Never import torch/transformers at module
   top-level; follow the `_get_model()` cache pattern. Status checks must
   not download weights.
5. **Keep the pipeline compatible.** New TTS/LLM options must flow through
   `tts_with_fallback()` / `GenerateVoice()` so `/generate` works
   unchanged; sanitize foreign voice names in fallback branches.
6. **Frontend:** Vue `<script setup lang="ts">`, Tailwind+Naive UI, Pinia +
   localStorage composables. No `as` casts in templates; use template refs,
   not `$refs`.
7. **Don't commit secrets.** Check `git status`/`git diff` before commits;
   `.env` is never committed. Docs live in `README.md`/`onBoard.md` —
   update them when behavior changes.
