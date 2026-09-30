---
name: twitter-research-topics
version: 1.0.0
description: |
  Topics Mode — auto-detects the top trending topics in a broad category or
  region (e.g. "futbol mexico europa usa"), researches each one via X search
  + WebSearch, and creates a standalone [topic-research].md file per topic
  with: viral title, news context, media/video links, 2 TTS-ready short
  video scripts (virality + shock), source post + engagement stats, and a
  data-calibrated SEO YouTube title (via the youtube-title subskill).
  Optionally hands each topic to the short-generator skill to produce a
  finished Short from the collected video links + approved script.

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

# Twitter/X Research — Topics Mode (v1)

Detects the top trending topics in a category, creates `[topic-research].md`
files, and optionally generates Shorts.

## Command

```
/twitter-research topics:<category> audience:<target audience> [limit:<n>] [shorts:<on|off>]
```

Examples:
- `/twitter-research topics:futbol mexico audience:aficionados liga mx shorts:on limit:10`
- `/twitter-research topics:champions league audience:fans europeos limit:5`

## Preconditions

- Chrome is running with `--remote-debugging-port=9222`
- User is logged into X/Twitter in Chrome
- Backend running for short generation (only if `shorts:on`):
  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/models
  ```

## Workflow

### Step 1 — Discover Trending Topics

Find what is actually trending right now in the target category/region.

1. **X trending data** (country-specific):
   ```bash
   chrome-devtools navigate_page --url "https://getdaytrends.com/es/mexico/"
   ```
   Extract the current trend list via evaluate_script. Filter to topics relevant
   to the category (for futbol: team names, player names, tournament names,
   transfers, results, goals, referees).
2. **X Explore** for global/sports trends:
   ```bash
   chrome-devtools navigate_page --url "https://x.com/explore"
   ```
   Read the Sports / Entertainment / News trend tabs.
3. **WebSearch** the category + region for today's news:
   - `WebSearch("<category> <region> noticias hoy")`
   - `WebSearch("<category> trending <region> hoy")`
   - For futbol: `WebSearch("futbol liga mx hoy"), WebSearch("champions league hoy"), WebSearch("mls noticias hoy")`
4. **Curate the top N topics** (default 5, max 10). Choose topics that are:
   - Currently hot (trending in the last 24-48h)
   - Category-relevant
   - Distinct (no duplicates)
   - Video-friendly (visual content available)

### Step 2 — Research Each Topic

For each of the top N topics:

1. **Get news context** via WebSearch: `WebSearch("<topic> noticias")` and read
   the top 2-3 results. Capture: what happened, why it matters, key numbers,
   reactions, official statements.
2. **Search X for engagement data**:
   ```bash
   chrome-devtools navigate_page --url "https://x.com/search?q=<URL_ENCODED_TOPIC>&src=typed_query&f=top"
   ```
   Wait 5s, then extract the top 5 posts with real metrics using the scrape
   extractor (handle, tweet text, status URL, and the numeric bar = replies /
   retweets / likes / views). Record the single best-performing post URL + its
   exact stats.
3. **Collect media/video links**: from the tweet media, news articles, or a
   quick platform search (`WebSearch("site:youtube.com <topic>")`,
   `WebSearch("site:tiktok.com <topic>")`). Gather 3-5 usable links.

### Step 3 — Create `[topic-research].md` Files

For each topic, create a file named ````
.twitter-research/<YYYY-MM-DD_HHMMSS>/
  ├── topic-research-<slug>.md        # one per trending topic (per-session)
  └── topics-report.md
```` in
`.twitter-research/` (or the configured output dir). The file MUST contain
these 6 sections (in this order; section 6 is filled in Step 5):

```markdown
# Topic Research: <Topic Name>
**Fecha de investigación:** <YYYY-MM-DD>
**Nivel de calor (hotness):** 🔥-🔥🔥🔥🔥🔥

## 1. Título del tema y título viral
**Tema:** <short summary of the topic>
**Títulos virales para video:**
- <viral title 1>
- <viral title 2>

## 2. Contexto de la noticia
<2-4 paragraphs: what happened, why it's hot, key facts, reactions>

## 3. Enlaces de video e imágenes
- <link with description>
- <link with description>

## 4. Guiones de video corto

### Guion A — VIRALIDAD
> [HOOK 0-3s] <hook sentence>
> <4-8 more short TTS-read sentences, one per line>
> [CTA] <call to action>

### Guion B — SHOCK VALUE
> [HOOK] <hook>
> <short punchy lines for TTS>
> <closing line>

## 5. Publicación de referencia + interacción
**Post principal:** <url>
- Respuestas: X | Reposts: X | Me gusta: X | Reproducciones: X
**¿Qué tan caliente está?** <hotness rating + note>

## 6. Título SEO para YouTube
**Título recomendado:** <title> (<score>/10)
**Alternativo A:** <angle> — <title> (<score>/10)
**Alternativo B:** <angle> — <title> (<score>/10)
**Keywords para descripción:** <3-5 search phrases>
**Por qué funciona:** <rules hit from youtube-title>
```

**Script writing rules (for TTS / short vertical video):**
- Spanish (or the user's language), spoken-style, no complex punctuation
- Short sentences (6-12 words), one idea per line
- Hook in first 3 seconds (question, bold claim, or shock stat)
- Rhythmic pacing; numbers written out naturally
- End with a CTA (comment / save / follow)
- NO stage directions inside the read text — use `[HOOK]`, `[CTA]` markers
  only as labels; the text after them is what the TTS reads

### Step 4 — Write `topics-report.md`

Create an index file listing all topics, their hotness, and file links:

```markdown
# Topics Report — <category>
**Fecha:** <date>
**Audiencia objetivo:** <audience>

| # | Tema | Calor | Archivo |
|---|------|-------|---------|
| 1 | ... | 🔥🔥🔥 | ```
.twitter-research/<YYYY-MM-DD_HHMMSS>/
  ├── topic-research-<slug>.md        # one per trending topic (per-session)
  └── topics-report.md
``` |
```

### Step 5 — Generate SEO YouTube Title (subskill: `youtube-title`)

For each topic file, load the subskill and produce the best SEO-targeted,
attention-grabbing YouTube title:

1. Load it: `skill youtube-title`
2. Generate 5 candidates from the topic's script hook + key facts, scored
   on SEO keyword, ALL-CAPS power word, specificity (score/names), stake,
   and length (45–70 chars) against the channel's own CTR/views data.
3. Keep the best title + 2 A/B alternates and **write them into section 6**
   of the topic file (see template), plus 3-5 description keywords.
4. These titles are the ones used later for the Shorts/YouTube upload.

**Why this step exists:** titles are the #1 lever on the channel's own
data (same video, different title = 13× views). Never skip it.

### Step 6 — Optional: Generate Shorts (`shorts:on`)

For each topic, hand off to the short-generator skill:

1. Load it: `skill short-generator`
2. Subject = the topic; script = the **Virality** guion from the topic file
3. Provide `hashtags:` from the topic keywords and `sources:` (default
   instagram,facebook,tiktok,youtube)
4. Collect the video links from section 3 of the topic file and use them in
   short-generator Step 4/5 (fallback sources if search finds <5 URLs)
5. **Show the generated script for user approval before generating** the video
6. On approval, generate the Short and download the videos from the links
7. Use the **section 6 recommended YouTube title** as the video/upload title

**Important**: Always show the script and get explicit user approval before
calling the final video generation endpoint.

### Step 7 — Report Completion

```
✅ Twitter/X Research Topics Mode Complete!

Category: <category>
Audience: <audience>
Topics researched: <N>
  - <topic 1> (🔥hotness) → .twitter-research/```
.twitter-research/<YYYY-MM-DD_HHMMSS>/
  ├── topic-research-<slug>.md        # one per trending topic (per-session)
  └── topics-report.md
```
  - ...
Shorts generated: <M/N>

Next step (optional): skill twitter-research-report for a full HTML report
```
