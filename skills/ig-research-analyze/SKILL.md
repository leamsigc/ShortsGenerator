---
name: ig-research-analyze
version: 2.0.0
description: |
  Content psychology analysis state. Reads raw-posts.json and transcripts,
  analyzes top 6 posts through a psychological lens, identifies trigger
  patterns, and generates 5 tailored content angle recommendations.
  Also runs the video-ideas pipeline (shared video-idea-research playbook):
  top 10 reels/videos by views in the window → outlines → 5 video ideas × 3
  scripts (viral / storytelling / inspiration) + YouTube metadata
  (title, description, tags, keywords) → ideas-report.md + REPORT.html.

allowed-tools:
  - Bash
  - Read
  - Write
  - Skill
---

# Social Research — Analyze State

After scraping and transcription, this state reads the data and provides content psychology analysis, then the video-ideas pipeline.

## Preconditions

- Raw data exists: `.ig-research/projects/<project-name>/raw-posts.json`
- Transcripts exist in `.ig-research/projects/<project-name>/transcripts/`
- Report exists in `.ig-research/projects/<project-name>/report.html`

## Steps

### 1. Read report data

```bash
cat .ig-research/projects/<project-name>/report.html
```

### 2. Read raw posts

```bash
node -e "const d=require('./.ig-research/projects/<project-name>/raw-posts.json'); console.log(JSON.stringify(d.posts.slice(0,6),null,2))"
```

### 3. For each of the top 6 posts, identify psychological triggers

Analyze against these frameworks:

| Trigger | Description | Signal |
|---------|-------------|--------|
| Curiosity gaps / open loops | Creates info gap the brain wants to close | "Here's why...", "The one thing..." |
| Identity signaling | Makes viewer feel like "that person" | "This is for people who..." |
| Social proof / tribal belonging | Shows community validation | High engagement numbers, "join" |
| Loss aversion / FOMO | Fear of missing out | "Don't make this mistake", "before it's too late" |
| Authority / credibility | Positions creator as expert | Named frameworks, credentials |
| Pattern interrupt / contrarian | Goes against expectation | "Everything you know about X is wrong" |
| Reciprocity / value-first | Gives before asking | Free frameworks, actionable tips |
| Anchoring / specificity | Specific numbers feel researched | "3 things", "7 strategies" |

### 4. Give 5 content angle recommendations

For each angle: psychological trigger, hook example, why it works in the niche.

### 5. Summarize findings

Write a brief summary: how many posts scraped, top 3-5 performers, common patterns.

### 6. Open the report

```bash
xdg-open .ig-research/projects/<project-name>/report.html
```

(Use `open` on Mac, `start` on Windows)

### 7. Video ideas pipeline (`skill video-idea-research`)

When the user wants **video ideas for a topic**, run the shared playbook:

1. **Top 10 by views in the window** — rank the scraped reels (plus a fresh
   hashtag/explore scrape for the topic when needed). Real play counts only;
   `views: null` + the proxy metric when the count isn't visible.
2. **Outlines** — hook = first caption line or transcript opening; beats and
   CTA from the Whisper transcript (`scripts/transcribe.sh`); format/duration
   from the reel itself.
3. **5 ideas**, each grounded in ≥2 top reels with their real numbers.
4. **3 scripts per idea** — viral (`viral_shorts`), storytelling
   (`storytelling`), inspiration (`motivational`); TTS-ready, `[HOOK]`/`[CTA]`
   labels only. Optional backend seeding:
   ```bash
   curl -s -X POST http://localhost:8080/api/script \
     -H "Content-Type: application/json" \
     -d '{"videoSubject":"<idea title>","extraPrompt":"<angle + outline context>","aiModel":"g4f","scriptTemplate":"viral_shorts","scriptLength":"standard"}'
   ```
5. **YouTube metadata per idea** (title via the `youtube-title` rubric,
   description, tags, keywords).
6. Save `video-ideas.json` and render the report:
   ```bash
   node "$CLAUDE_SKILL_ROOT/scripts/build-ideas-report.js" <path-to-video-ideas.json>
   # fallback: node ./skills/video-idea-research/scripts/build-ideas-report.js <path>
   ```
