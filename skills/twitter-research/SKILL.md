---
name: twitter-research
version: 3.0.0
description: |
  Twitter/X content research tool with two modes:
  1. SINGLE-TOPIC MODE — explore 10+ posts across the platform based on a
     TOPIC the user chooses, generate scripts + audience scores + HTML report.
  2. TOPICS MODE — given a broad category (e.g. "futbol mexico europa usa")
     and a TARGET AUDIENCE, auto-detect the top 5-10 currently-trending
     topics, and for each one create a standalone [topic-research].md file
     with: viral title, news context, media/video links, 2 TTS-ready short
     video scripts (virality + shock), source post + engagement stats, and
     an SEO-optimized YouTube title (youtube-title subskill, calibrated on
     the channel's own CTR/view data).
     Optionally hands each topic to the short-generator skill to produce a
     finished Short video from the collected video links + script.

  Uses X search + trending content via Chrome DevTools CLI (no API key
  required).

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
  - twitter-research-setup    — Gather topic, audience params, optional seed accounts
  - twitter-research-scrape   — Search X by topic, collect 10+ posts across accounts
  - twitter-research-analyze  — Score audiences, generate content drafts
  - twitter-research-report   — Generate HTML report + engagement responses
  - twitter-research-topics   — TOPICS MODE: auto-detect trending topics in a category, create [topic-research].md files, optionally generate Shorts via short-generator
---

# Twitter/X Research — Main Skill (v3)

Two modes: Single-Topic Mode and Topics Mode.

## Architecture

```
skills/twitter-research/         # Skill (bundled, global-installable via ~/.claude/skills/)
├── SKILL.md
└── scripts/                     # Bundled — no external .twitter-research/scripts needed
    ├── package.json
    ├── scrape.js
    ├── report-html.js
    └── report-topics-html.js

.twitter-research/               # Tool data directory (project root, auto-resolved via CWD walk-up)
└── <YYYY-MM-DD_HHMMSS>/         # One folder per research session (dated)
    ├── config.json
    ├── raw-posts.json
    ├── audience-scores.json
    ├── content-drafts.json
    ├── engagement-responses.json
    ├── REPORT.html
    ├── topic-research-<slug>.md # Topics mode: one per trending topic (per-session, not root)
    ├── topics-report.md         # Topics mode index
    └── screenshots/
```

**Execution model (hybrid):** heavy lifting runs as bundled scripts in `skills/twitter-research/scripts/`.
Skills resolve dataRoot via CWD walk-up (`./.twitter-research`), `TWITTER_RESEARCH_ROOT`, or `--data-root`.
Global-install safe (`~/.claude/skills/`).

## Quick Start

```
# Single-Topic Mode (original)
/twitter-research <topic> [limit:<number>] [accounts:<account1,account2>]

# Topics Mode (NEW — research trending topics + optional Short generation)
/twitter-research topics:<category> audience:<target audience> [limit:<number>] [shorts:<on|off>]
```

Examples:
- `/twitter-research social media scheduling tools limit:15`
- `/twitter-research topics:futbol mexico audience:aficionados liga mx shorts:on limit:10`
- `/twitter-research topics:champions league audience:fans de futbol europeo`

## Topics Mode (NEW)

Runs the full pipeline: research → topic files → optional Short videos.

### Command Parameters

| Param | Meaning | Example |
|-------|---------|---------|
| `topics:<category>` | Broad category/region to detect trending topics in | `topics:futbol mexico europa usa` |
| `audience:<text>` | Target audience description | `audience:aficionados de la liga mx` |
| `limit:<n>` | Max topics to research (default `5`, max `10`) | `limit:8` |
| `shorts:<on|off>` | Auto-call short-generator after research (default `off`) | `shorts:on` |

### Workflow (state: `skill twitter-research-topics`)

1. **Discover trending topics** — use X trending (getdaytrends.com/es/mexico or
   x.com/explore) + WebSearch for the category/region. Pick the top N football
   (or category-relevant) topics currently hot.
2. **Research each topic** — for each, pull news context, media/video links,
   and real engagement stats from X search (10+ posts, real numbers).
3. **Create `[topic-research].md` files** — one per topic in `.twitter-research/`,
   containing the 6 required sections (see below).
4. **SEO YouTube titles** — for each topic, load `skill youtube-title` and
   generate the best SEO-targeted, attention-grabbing title (5 candidates
   scored on keyword, ALL-CAPS power word, specificity, stake, length —
   calibrated on the channel's own CTR/views data). Save as section 6.
5. **Optional Short generation** — if `shorts:on`, for each topic hand off to
   `skill short-generator` with: the viral script + the collected video links +
   context. Script is shown for user approval, then the video is generated and
   downloaded from the provided links. Uses the section 6 title for upload.

### Required sections in each `[topic-research].md` file

1. **Title of the topic + viral title for a video**
2. **Context of the topic / news** (what happened, why it's hot)
3. **Video or image links** related to the news
4. **2 short video scripts** — one for virality, one for shock value.
   Format specifically for short vertical content, readable by a TTS (short
   punchy sentences, hooks, CTA).
5. **Link to the source post + engagement stats** + how hot the topic is.
6. **SEO YouTube title** — recommended title + 2 A/B alternates + description
   keywords (via `youtube-title` subskill).

### Output Structure (Topics Mode)

```
.twitter-research/<YYYY-MM-DD_HHMMSS>/
  ├── topic-research-<slug>.md        # one per trending topic (per-session)
  └── topics-report.md                # summary index (per-session)
  # legacy: loose topic-research-*.md at .twitter-research/ root (migrated on next run)
```

## Single-Topic Mode (original v2 workflow)

### Workflow

### Phase 1: Setup (`skill twitter-research-setup`)

1. Ask user for the **research topic** (e.g., "social media scheduling tools", "Liga MX")
2. Ask for **minimum posts to collect** (default: `10`, recommend `10-15`)
3. Ask for optional seed accounts to bootstrap the search (can be empty)
4. Define target audience keywords and niche
5. Set up output directory structure
6. Ensure Chrome is configured for X/Twitter access

### Phase 2: Scrape (`skill twitter-research-scrape`)

1. Run the scraper: `node "$CLAUDE_SKILL_ROOT/scripts/scrape.js" <timestamp>  # fallback: node ./skills/twitter-research/scripts/scrape.js <timestamp>`
   - Searches X by topic (Top + Latest tabs), scrolls, extracts 10+ posts from **different accounts**
   - Optionally visits seed accounts from config and keeps topic-relevant posts
   - Deduplicates by URL, ranks by engagement, saves `raw-posts.json`
2. If search fails or returns too few results, the skill falls back to Chrome DevTools CLI for manual extraction, or broaden the query via topic keywords.

### Phase 3: Analyze (`skill twitter-research-analyze`)

1. Score audience segments 1-10 based on engagement data
2. Generate social media post drafts from top content
3. Generate video script drafts from top content
4. Identify content patterns and angles that work on that topic

### Phase 4: Report (`skill twitter-research-report`)

1. Generate pre-defined engagement responses (3 per topic post)
2. Run `node "$CLAUDE_SKILL_ROOT/scripts/report-html.js" <timestamp>` to generate a self-contained HTML report
3. Include direct links to all source posts + content playbook

## Output Structure

```
.twitter-research/
  └── <YYYY-MM-DD_HHMMSS>/
      ├── config.json                   # Research parameters (topic, limits)
      ├── raw-posts.json                # 10+ topic posts with metrics (across accounts)
      ├── audience-scores.json          # Audience segment scores
      ├── content-drafts.json           # Generated post & script drafts
      ├── engagement-responses.json     # Pre-defined responses per topic post
      └── REPORT.html                   # Self-contained final report
```

## Key Features

| Feature | Description |
|---------|-------------|
| Topic-based research | Searches X for a user-chosen topic, collects 10+ posts across accounts |
| No API key | Uses Chrome DevTools CLI — works with X's web interface |
| Engagement responses | 3 pre-written responses per topic post (value add / discussion / agree) |
| Audience scoring | Scores audience segments 1-10 by engagement potential |
| Content generation | Social media posts + video scripts from top content |
| HTML report | Self-contained, styled, with clickable post links |
