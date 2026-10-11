---
name: facebook-research
version: 4.0.0
description: |
  Facebook page analytics tool with history tracking, competitor analysis,
  HTML report generation, viral engagement opportunity engine, and video
  template extraction.
  Scrape top-performing content, analyze engagement patterns, deconstruct
  viral videos, track performance trends over time (better/worse), research
  competitors (up to 5), generate replication scripts adapted to other
  topics, find unlimited engagement opportunities with high-like hooks
  and direct post links, download top 5 reels, transcribe with Whisper,
  analyze transcripts for patterns, and generate a reusable video template
  based on the best-performing video structure.
  Video Ideas Mode (shared video-idea-research playbook): the 10 videos with
  the most views in a week/month/year window → outlines → 5 video ideas × 3
  scripts (viral / storytelling / inspiration) + YouTube metadata (title,
  description, tags, keywords) → REPORT.html.
  Output: self-contained HTML report with embedded charts.
  Uses Chrome DevTools CLI for all Facebook interactions.

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

states:
  - facebook-research-setup      — Prerequisites, config (up to 5 competitors), Chrome setup
  - facebook-research-scrape     — Scrape page analytics + competitors + top 10 videos
  - facebook-research-analyze    — Deep deconstruction of top 5 videos + 5 competitors + video ideas pipeline
  - facebook-research-report     — REPORT.html (self-contained, charts, competitor links, engagement opps)
  - facebook-research-engage     — Generate engagement opportunities with viral hooks
  - facebook-research-grow       — Follower growth engine ("page audience stealer", goal-driven campaigns)
  - facebook-research-template   — Download → transcribe → analyze → generate reusable video template
  - video-idea-research          — shared playbook: top-10 videos by views → outlines → 5 ideas → 3 scripts + YouTube metadata
---

# Facebook Research — Main Skill (v2.3)

Full workflow: Setup → Scrape → Analyze → Report → Engage → Template

## Quick Start

```
skill facebook-research-setup       # Step 1: Setup (prerequisites + config + competitors)
skill facebook-research-scrape      # Step 2: Scrape page + competitors analytics
skill facebook-research-analyze     # Step 3: Deep deconstruct top 5 + competitor videos
skill facebook-research-report      # Step 4: REPORT.html with history trends + competitor analysis
skill facebook-research-engage      # Step 5: Generate engagement opportunities (10+ at a time)
skill facebook-research-grow        # Step 5b: Grow followers — goal-driven "audience stealer" campaigns (e.g. +200 in 24h)
skill facebook-research-template    # Step 6: Download reels + transcribe + analyze + generate template
```

## Video Ideas Mode

Research a topic (or the page's niche) for the Facebook videos/reels getting
the most views inside a window and build publishable ideas from them:

```
facebook-research ideas:<topic> [window:week|month|year] [limit:10] [ideas:5] [length:standard] [lang:es]
```

Runs the shared `video-idea-research` playbook: top-10 by views (watch pages
show the count; window from the video dates) → outline extraction (hook /
beats / CTA / format / duration — Whisper transcripts when needed) → 5 ideas
drawn from the top 10 → 3 scripts per idea (viral `viral_shorts`,
storytelling, inspiration `motivational`) → YouTube metadata (title via the
`youtube-title` rubric, description, tags, keywords) → `video-ideas.json` and
`REPORT.html` / `ideas-report.md` via
`node "$CLAUDE_SKILL_ROOT/scripts/build-ideas-report.js" <path>`
(script ships with the `video-idea-research` skill).

## Architecture

```
skills/facebook-research/          # Skill (bundled, global-installable via ~/.claude/skills/)
├── SKILL.md
└── scripts/                       # Bundled — no external .fb-research/scripts needed
    ├── package.json               # Node deps (chrome-remote-interface)
    ├── scrape.js                  # Page + competitor scraper via Chrome DevTools
    ├── report-html.js             # HTML report generator
    ├── download-reels.js          # Top-5 reel downloader via Chrome DevTools
    └── transcribe.sh              # Whisper transcription of downloaded reels

.fb-research/                      # Tool data directory (project root, auto-resolved via CWD walk-up)
└── projects/<page-name>/
    ├── config.json                       # Project config (page + competitors with URLs)
    ├── page-analytics-history.json       # All historical snapshots (global, appended each run)
    ├── report-history.json               # Historical report snapshots (global)
    ├── replication-history.json          # History of all replication scripts (global)
    ├── latest.json                       # Pointer to latest sessionId
    ├── competitors/                      # Legacy mirror of last run (for back-compat)
    │   ├── <competitor-1>/raw-posts.json
    │   └── <competitor-2>/raw-posts.json
    └── <YYYY-MM-DD_HHMMSS>/             # One folder per run (dated)
        ├── page-analytics.json           # This run's page stats
        ├── raw-posts.json                # This run's raw posts
        ├── competitors/<name>/raw-posts.json
        ├── discovered-competitors.json
        ├── top5-analysis.md
        ├── REPORT.html                   # Self-contained report for this run
        ├── report.md
        ├── replication-scripts/
        ├── screenshots/                  # Hook screenshots
        ├── screenshots-competitors/
        ├── screenshots-engagement/       # Screenshots of target posts + top comments
        ├── screenshots-growth/           # Screenshots of target posts + our visitor comments
        ├── growth-campaign.json
        ├── growth-targets.json
        ├── growth-log.json
        ├── growth-progress.json
        ├── growth-strategy.md
        ├── video-template/
        │   ├── downloads/                # Downloaded reels for this run
        │   ├── transcripts/
        │   ├── transcript-analysis.json
        │   ├── VIDEO-TEMPLATE.md
        │   └── best-performer-breakdown.md
        └── engagement-opportunities.json
```

**Execution model (hybrid):** scraping, reporting, reel download, and transcription run as
bundled scripts in `skills/facebook-research/scripts/` (Chrome DevTools Protocol).
Skills resolve the data dir via CWD walk-up (`./.fb-research`), `FB_RESEARCH_ROOT` env, or
`--data-root`. Dated runs live in `projects/<name>/<YYYY-MM-DD_HHMMSS>/`. Use the Chrome DevTools
CLI directly for quick DOM reads, comment posting, and screenshots. Global-install safe (Muse `~/.claude/skills/` — Opencode also reads it).

## Video Template Pipeline

This pipeline deconstructs the page's top 5 performing reels down to their DNA and builds a reusable template.

### How It Works

1. **Download**: Chrome DevTools navigates to each of the top 5 post insight pages, extracts the video source URL from the `<video>` element, and downloads the MP4 file.
2. **Transcribe**: Whisper (local) processes each downloaded video and generates transcriptions (.txt) with timestamps.
3. **Analyze**: All 5 transcripts are analyzed for:
   - **Hook pattern**: First 5 seconds — what's the exact phrasing, tone, and pacing?
   - **Content structure**: How is the narrative organized? (Tease → Context → Drama → CTA)
   - **Pacing**: Sentence length, pause points, question frequency, emphasis words
   - **Vocabulary**: Key phrases, power words, repetition patterns
   - **CTA structure**: How is the call-to-action framed? Question format?
   - **Emotional arc**: How does the video progress emotionally scene by scene
   - **Length & timing**: Exact timing of each section
4. **Template**: The #1 performing video (by views/engagement) is used as the reference. A reusable fill-in-the-blank template is generated.

### Video Template Format (VIDEO-TEMPLATE.md)

The template is a structured, fillable document with:

```markdown
## Template: [PATTERN NAME]
**Source**: [original post title] — [views] views

### Hook (0:00-0:03)
Text overlay: "[FORMULA]"
Audio: "[EXACT WORDING PATTERN]"

### Context (0:03-0:10)
Structure: [pattern of how context is established]
Vocabulary: [power words used]
Pacing: [sentence rhythm]

### Drama/Body (0:10-0:40)
Narrative flow: [story structure]
Emotional arc: [how emotions shift]
Key phrases: [repeatable phrases]

### CTA (0:40-0:50)
Format: [question formula]
Hook type: [debate / opinion / prediction]
Length: [seconds]

### Production Specs
- Duration: [seconds]
- Text overlay style: [font/color/position]
- Audio style: [music type + commentary]
- Transition speed: [fast/medium/slow]
- Caption style: [styled / auto]
```

### Mapping New Content to the Template

```
Your Topic: [fill in]
Hook:    ¡[STAR] [VERB] [TEAM]! [EMOJI]
Context: [match situation] + [stakes]
Drama:   [key moment 1] → [reaction] → [key moment 2] → [climax]
CTA:     [controversial question] + ¡Te leo en los comentarios!
```

### Commands

| Action | Description |
|--------|-------------|
| `skill facebook-research-template` | Run full pipeline: download → transcribe → analyze → template |
| "regenerate the template" | Re-run template analysis without re-downloading |
| "apply template to [topic]" | Generate a new script using the saved template |

## Engagement Opportunity Engine (v3)

The engagement system visits competitor pages, scrapes their top posts and comments, and generates snarky/rage-bait comments that match the audience's real voice.

### How It Works

1. Visits each **competitor page** via Chrome DevTools
2. Finds their **most recent popular posts** (sorted by engagement)
3. Navigates into each post to get the **real permalink URL**
4. Extracts the **top 10 most-liked comments** from the post
5. Analyzes comment patterns: tone, slang (Mexican for Spanish pages), inside jokes
6. Generates **3 comment variants per post**:
   - **Hot take**: Strong controversial opinion
   - **Sarcastic zinger**: Short, meme-like jab
   - **Analysis + jab**: Shows knowledge then takes a shot
7. Takes **screenshots** of the post and comments section
8. Saves everything with **real post URLs** for one-click action

### Key Rules

- **Match the audience's tone** — if they're sarcastic, be sarcastic. Don't sound like a bot.
- **Use Mexican slang** for Spanish pages: "no mames", "wey", "qué pedo", "chingón", "neta", "carnal"
- **Don't promote yourself** — comments should look like they're from a passionate fan
- **Rage-bait triggers**: bad reffing, overrated players, controversial takes, hypocrisy
- **1-3 sentences max** — short comments get more likes than long rants

### Engagement Hook Formula

```
[SPECIFIC REFERENCE to post] + [OPINIONATED TAKE] + [MEXICAN SLANG / INSIDER JOKE] + [JAB or RHETORICAL QUESTION]
```

### Comment Templates (Spanish with Mexican Slang)

| Type | Template |
|------|----------|
| Hot take | "No mames, [player] está bien sobrevalorado wey. [specific play] fue pura suerte. Neta que [team] merecía más." |
| Sarcastic zinger | "Claro, y el árbitro no vio nada... como siempre. Qué pedo con este nivel, estamos en un mundial o qué?" |
| Analysis + jab | "Estadísticamente [team] tuvo [X] oportunidades claras pero [player] las falló todas. Para eso mejor me quedo en mi casa carnal. Ándale." |
| Rage bait | "A poco esto es fútbol? [ref/player/team] debería darle las gracias al árbitro. Valió madre el partido desde el minuto [X]." |

### JSON Schema (engagement-opportunities.json)

```json
{
  "id": 1,
  "batch": 1,
  "createdAt": "YYYY-MM-DD HH:MM:SS",
  "competitorName": "...",
  "competitorUrl": "https://www.facebook.com/...",
  "postUrl": "https://www.facebook.com/...",
  "postPreview": "...",
  "screenshot": "screenshots-engagement/...png",
  "commentsScreenshot": "screenshots-engagement/...comments.png",
  "topComments": [
    {"commenter": "...", "text": "...", "likes": "5K"}
  ],
  "commentPatterns": {
    "tone": "sarcastic",
    "slangUsed": ["wey", "no mames"],
    "commonThemes": ["bad reffing", "player x is overrated"]
  },
  "generatedComments": [
    {"variant": 1, "type": "hot_take", "text": "...", "whyItGetsLikes": "..."},
    {"variant": 2, "type": "sarcastic_zinger", "text": "...", "whyItGetsLikes": "..."},
    {"variant": 3, "type": "analysis_jab", "text": "...", "whyItGetsLikes": "..."}
  ],
  "value": "high",
  "used": false
}
```

## Notes

- Requires Chrome logged into Facebook (Cookies imported via `/setup-browser-cookies` or manual login)
- Video download requires being logged into Facebook (videos are gated behind authentication)
- Whisper is required: `pip install openai-whisper`
- ffmpeg is required for audio extraction if video download fails
- All output paths are relative to `dataRoot` (resolved from CWD's `.fb-research`, or `FB_RESEARCH_ROOT`)
- Each run creates `projects/<name>/<YYYY-MM-DD_HHMMSS>/` and appends a snapshot to `page-analytics-history.json` (global) for trend tracking
- User can ask for engagement opportunities ANY time, not just in the engage state
