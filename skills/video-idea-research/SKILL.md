---
name: video-idea-research
version: 1.0.0
description: |
  Universal "top videos → video ideas → scripts → YouTube metadata" research
  protocol shared by every platform research skill (youtube-research,
  twitter-research, ig-research, facebook-research, reddit-research).
  Given a TOPIC (e.g. "futbol mexicano"), research the specified platform for
  the videos/posts getting the most views inside a time window (week / month /
  year), extract each top performer's OUTLINE (hook, beats, CTA, format,
  duration), then draw 5 video ideas from the top 10 and write 3 full
  TTS-ready scripts per idea — VIRAL, STORYTELLING and INSPIRATION — plus the
  YouTube metadata block (title, description, tags, keywords) for each idea.
  Final output: video-ideas.json (canonical) + ideas-report.md + REPORT.html
  ranking the top 10 videos and the 5 fully-scripted ideas.
  Script templates are extracted from the ShortsGenerator Backend
  (Backend/settings.py scriptTemplates) and hook/title craft from public
  Claude skill repos (see references/hook-library.md).
  Load this skill whenever a platform research skill enters "video ideas"
  mode, or the user asks for video ideas, outlines of top videos, viral /
  storytelling / inspiration scripts, or titles + descriptions + tags for a
  topic.

allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Question
  - ChromeDevTools
  - WebSearch
  - Skill
---

# Video Idea Research — Shared Playbook (v1)

The pipeline every platform research skill runs when the goal is **video ideas
that gain views over time**. Platform skills own the *scraping*; this playbook
owns the *research → ideas → scripts → metadata → report* steps.

> Platform entry points: `youtube-research-topic`, `twitter-research-topics`,
> `ig-research`, `facebook-research-analyze`, `reddit-research`. Each of them
> calls into this skill with a topic + platform + window.

## Command shape

```
video-idea-research topic:<topic> platform:<youtube|x|instagram|facebook|reddit|tiktok>
                    [window:week|month|6months|year] [limit:10] [ideas:5]
                    [length:short|standard|long|extended|epic] [lang:es] [audience:<text>]
```

| Param | Meaning | Default |
|-------|---------|---------|
| `topic:` | Research topic (e.g. `futbol mexicano`) | required |
| `platform:` | Where to research | `youtube` |
| `window:` | Freshness window for the "most viewed" ranking | `month` |
| `limit:` | Top videos to research (their outlines feed the ideas) | `10` |
| `ideas:` | Video ideas to draw from the top 10 | `5` |
| `length:` | Script length preset (see `references/script-templates.md`) | `standard` |
| `lang:` | Script/metadata language | `es` |
| `audience:` | Target audience hint (auto-derived if absent) | auto |

Window presets: `week`, `month`, `6months` (use for "last 6 months" research),
`year`. On the YouTube path any window is also expressible in hours
(`maxage:4320` = 6 months). Long-form videos: `length:extended` (180s) or
`length:epic` (260s).

## Pipeline

```
scrape (platform skill)          -> raw-videos.json / raw-posts.json
   |
1. TOP-10 RANK                   -> most viewed inside window, keep top `limit`
2. OUTLINE EXTRACTION            -> hook / beats / CTA / format / duration per video
3. IDEA GENERATION               -> `ideas` ideas, each grounded in >=2 top videos
                                    + investigation dossier per idea
4. SCRIPTS x3 per idea           -> viral_shorts + storytelling + motivational
5. YOUTUBE METADATA per idea     -> title, description, tags, keywords
6. REPORT                        -> video-ideas.json + ideas-report.md + REPORT.html
```

---

## Step 1 — Top-10 ranking (most viewed inside the window)

The default sort is **raw views inside `window`** — the "most viewed videos of
the last N" list. Sort `views` descending; keep `velocityPerDay` as a column so
breakouts stay visible, and note it in the reasoning when a lower-view but
high-velocity video is chosen as an idea base. Keep the top `limit` (default 10).

| Platform | Primary metric | Views source | Window filter |
|----------|---------------|--------------|---------------|
| YouTube | views | card / watch page | search filters `sp=EgQIAhAB` (today), `CAM` (view count) + `&t=` week/month; or parse "X days ago" |
| X / Twitter | views on video posts | status page (`/status/<id>` shows Views) | `since:`/`until:` operators, or Latest tab |
| Instagram | reel plays (fallback likes×est.) | reel page play count when visible | hashtag/reels page, newest first |
| Facebook | video views | watch page view count | page videos sorted by views |
| Reddit | upvotes + comments (proxy) | JSON API `score`, `num_comments` | `t=week` / `t=month` / `t=year`, sort `top` |
| TikTok | views | video card / video page | search + upload-date filter |

Rules:
- **Real numbers only** — never invent views. If a view count can't be read,
  record `views: null` and rank by the platform proxy metric instead.
- Compute `velocityPerDay = views / ageDays` — a breakout beats a giant channel.
- Prefer videos whose **language matches `lang:`**; note language per video.
- Saved as `topVideos[]` inside `video-ideas.json` (schema below).

## Step 2 — Outline extraction (per top video)

For each top video, capture the **outline** — the skeleton that makes it work:

```json
"outline": {
  "hook": "first 3 seconds / first line, verbatim when possible",
  "beats": ["beat 1", "beat 2", "beat 3"],
  "cta": "closing call to action",
  "format": "clips+voiceover | talking-head | text-on-screen | listicle",
  "durationSec": 47,
  "language": "es"
}
```

How to get the outline:
1. **Transcript first** when available: run Whisper on the downloaded clip
   (`skills/ig-research/scripts/transcribe.sh`,
   `skills/facebook-research/scripts/transcribe.sh`) or the backend
   transcription module. Hook = first 2-3 sentences verbatim.
2. **Caption/description fallback**: title + description + first comments
   reveal the promise, the beats and the CTA.
3. Read the outline against `references/hook-library.md` — name the hook type
   (curiosity gap, contrarian, specificity…) and the structure
   (Hook → Build-Up → Value → Payoff → CTA).

## Step 3 — Idea generation (from the top 10)

Draw `ideas` (default **5**) ideas from the top-10 outlines. Each idea ships as
a **topic dossier + titles + 3 scripts + YouTube metadata**:

- **Investigación (dossier)** — WebSearch the story (`<keywords> hoy/today`),
  read the top 2-3 results, capture: what happened, why it's hot, key numbers,
  reactions, official statements, and the source URLs. This is the research
  base the scripts are written from — never script facts the dossier lacks.
- Each idea must be backed by **≥2 top videos** (`sourceVideos` ranks) whose
  outlines share a winning skeleton — that is the "drawn from the top 10" rule.
- **Distinct angles only**: resultado vs controversia vs dato insólito vs
  historia de jugador vs previa — never two ideas about the same
  match/player unless the angle differs.
- Prefer (a) highest views in window, (b) repeatable skeletons (a formula that
  appeared in 2+ top videos), (c) evergreen re-packaging — the goal is views
  that keep accruing, so favor angles that stay searchable.
- For each idea record: `title` (working topic title), `angle`, `investigation`
  (the dossier), `whyItWins` (citing the source videos' real view counts),
  `hotness` (1-5).

## Step 4 — Scripts (3 per idea: viral, storytelling, inspiration)

Write **3 complete TTS-ready scripts per idea**, one per emotional register.
Templates come from the Backend (`references/script-templates.md`):

| Variant | Backend template | Job |
|---------|------------------|-----|
| **Viral** | `viral_shorts` (+ `controversial` when the angle is a hot take) | Scroll-stop, max retention, debate |
| **Storytelling** | `storytelling` | Emotional journey: setup → conflict → resolution |
| **Inspiration** | `motivational` | Uplift, second-person, memorable one-liner |

Hard rules for every script:
- `[HOOK]` in the first 3 seconds; `[CTA]` at the end — labels only, TTS reads
  the text after them.
- Sentences 6-14 words, one idea per line, spoken rhythm, no markdown.
- Numbers spelled out naturally ("tres a tres", "un millón").
- Hook craft from `references/hook-library.md`; stop-scroll category
  (negation/specificity/question) + retention category (story/confession).
- Write in `lang` (default Spanish).
- Optionally seed via the backend, then hand-polish:
  `curl -s -X POST http://localhost:8080/api/script -H "Content-Type: application/json" -d '{"videoSubject":"<idea title>","extraPrompt":"<angle+context>","aiModel":"g4f","scriptTemplate":"viral_shorts","scriptLength":"standard"}'`
- Scripts must be **paste-ready into the short-generator / long-form generator**
  — no annotations inside the spoken text.

## Step 5 — YouTube metadata (per idea)

Every idea gets a full metadata block (the upload package):

```json
"youtube": {
  "title": "<45-70 chars, keyword front-loaded, ONE ALL-CAPS power word>",
  "description": "<2-4 lines, hook line first, hashtags at the end>",
  "tags": ["tag1", "tag2", "..."],
  "keywords": ["search phrase 1", "search phrase 2", "..."]
}
```

Title rules (from the channel-calibrated `youtube-title` skill — apply it here):
1. Primary search entity in the first 40 chars (matchup, player, competition).
2. One ALL-CAPS power word of conflict/emotion — never the whole title.
3. A concrete detail: score, money figure, date, club.
4. Stake/curiosity gap: what it costs, what nobody saw.
5. 45-70 chars, no emoji prefix, no hashtags in the title.
6. Honest clickability — the script must deliver the promise (AVD is the metric).

`description` = hook line + 2-3 sentence summary + timestamps when long-form +
3-5 hashtags. `tags`/`keywords` = 8-15 search phrases (matchup + player +
competition + angle), Spanish + English mix for bilingual search. When the
backend is running these can be seeded with `generate_metadata()`
(Backend/gpt.py) via `/api/script` + manual polish — the hand-written package
above is the source of truth.

## Step 6 — Report

Canonical data: `video-ideas.json` in the platform session folder. Then build
the human report (see `references/report-template.md`):

```bash
node "$CLAUDE_SKILL_ROOT/scripts/build-ideas-report.js" <path-to-video-ideas.json>
# fallback: node ./skills/video-idea-research/scripts/build-ideas-report.js" <path>
```

Writes next to the input: `ideas-report.md` + `REPORT.html` —
**Section 1: the top 10 videos** (rank, title, channel/platform, views,
window, velocity, url, hook type) and **Section 2: the 5 ideas** (titles,
3 full scripts, audiences, view estimate, media links, YouTube metadata).

## video-ideas.json schema (canonical)

```json
{
  "generatedAt": "YYYY-MM-DD HH:MM:SS",
  "topic": "futbol mexicano",
  "platform": "youtube",
  "window": "month",
  "language": "es",
  "targetAudience": "aficionados de la liga mx",
  "topVideos": [
    {
      "rank": 1, "title": "...", "channel": "...", "url": "...",
      "views": 897000, "publishedAt": "...", "ageDays": 12,
      "velocityPerDay": 74750, "language": "es",
      "outline": {"hook": "...", "beats": ["..."], "cta": "...",
                  "format": "clips+voiceover", "durationSec": 47}
    }
  ],
  "ideas": [
    {
      "rank": 1, "slug": "debut-rafa-marquez-tri", "title": "...",
      "angle": "controversia del árbitro", "hotness": 5,
      "investigation": {"summary": "<what happened + why it's hot, 2-4 paragraphs>", "keyFacts": ["..."], "sources": ["url1", "url2"]},
      "whyItWins": "comparables: 11K, 74K, 897K views en el mes — mismo esqueleto",
      "sourceVideos": [1, 4, 7],
      "scripts": {"viral": "[HOOK] ...\n[CTA] ...",
                  "storytelling": "[HOOK] ...\n[CTA] ...",
                  "inspiration": "[HOOK] ...\n[CTA] ..."},
      "audiences": [{"segment": "aficionados del Tri en USA", "score": 9, "why": "..."}],
      "viewEstimate": {"min": 15000, "max": 350000, "reasoning": "comparables: ..."},
      "mediaLinks": [{"platform": "youtube", "url": "...", "description": "..."}],
      "youtube": {"title": "...", "description": "...", "tags": ["..."], "keywords": ["..."]}
    }
  ]
}
```

## Platform notes (what each entry point must supply)

| Entry point | Scraped by | Notes |
|-------------|-----------|-------|
| `youtube-research-topic` | chrome-devtools MCP on youtube.com | views + "X days ago" per card; transcripts via backend |
| `twitter-research-topics` | X search `f=video` + status pages | view counts on the status page; `since:`/`until:` for window |
| `ig-research` | hashtag/reels scrape + Whisper | reel play count when visible; transcripts via transcribe.sh |
| `facebook-research-analyze` | page/competitor videos + download-reels.js | view counts on watch pages; transcripts via transcribe.sh |
| `reddit-research` | JSON API (`t=week/month/year`, sort=top) | upvotes+comments as the views proxy; selftext + top comments are the outline |

## References

- `references/script-templates.md` — Backend templates (viral_shorts,
  educational, storytelling, listicle, controversial, motivational),
  scriptLength presets, `/api/script` usage.
- `references/hook-library.md` — hook archetypes, psychology triggers, 50+
  title formulas, anti-patterns (sourced from public Claude skill repos).
- `references/report-template.md` — final report layout + idea markdown file
  format.

## Completion block

```
✅ Video Idea Research Complete!
Topic: <topic> · Platform: <platform> · Window: <window>
Top videos: 10 (top: "<title>" — <views> views)
Ideas: 5 (each: 3 scripts + YouTube metadata)
Next step: node "$CLAUDE_SKILL_ROOT/scripts/build-ideas-report.js" <path> -> REPORT.html
```
