---
name: facebook-research-analyze
version: 3.0.0
description: |
  Analyze state — reads top 5 posts from scrape phase and performs deep
  deconstruction of each: audience retention signals, engagement patterns,
  hook analysis, content structure, psychological triggers. Also analyzes
  competitor top content for benchmarking. Generates detailed "why it worked"
  analysis with actionable replication guidance and competitive comparison.
  Also runs the video-ideas pipeline (shared video-idea-research playbook):
  the 10 Facebook videos/reels with the most views in a window
  (week/month/year) → outlines → 5 video ideas × 3 scripts (viral /
  storytelling / inspiration) + YouTube metadata (title, description, tags,
  keywords) → ideas-report.md + REPORT.html.

allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - ChromeDevTools
  - WebSearch
  - Question
  - Skill
---

# Facebook Research — Analyze State (v2)

Deep deconstruction of the top 5 performing videos and competitor top content.

## Preconditions

- Scrape completed: `.fb-research/projects/<project-name>/page-analytics.json`
- Competitors scraped: `.fb-research/projects/<project-name>/competitors/`
- Config exists: `.fb-research/projects/<project-name>/config.json`

## Steps

### 1. Load Data

```bash
cat .fb-research/projects/<project-name>/<YYYY-MM-DD_HHMMSS>/page-analytics.json  # or latest: cat .fb-research/projects/<project-name>/latest.json then session
cat .fb-research/projects/<project-name>/config.json
ls .fb-research/projects/<project-name>/competitors/
```

Extract: top 5 posts, page niche, your topics, competitor names.

### 2. For Each of the Top 5 Posts, Perform Deep Analysis

Re-navigate to each post URL:

```bash
chrome-devtools navigate_page --url "<post_url>"
```

Wait for full load. Extract the complete caption/description and engagement:

```javascript
() => {
  const text = document.body.innerText;
  const result = {
    fullText: text.substring(0, 3000),
    ogTitle: (document.querySelector('meta[property="og:title"]') || {}).content || '',
    ogDescription: (document.querySelector('meta[property="og:description"]') || {}).content || '',
    visibleText: document.body.innerText?.substring(0, 200) || '',
  };
  return JSON.stringify(result, null, 2);
}
```

### 3. Deconstruction Framework — Analyze Each Post Against

For each of the top 5 posts, analyze these dimensions:

#### A. The Hook (First 3 seconds)
- **Hook type**: Question, bold statement, pattern interrupt, curiosity gap, statistic, controversy, story, prediction
- **Hook text**: The exact first line/sentence
- **Hook strength**: Strong / Medium / Weak — based on whether it creates an information gap
- **Visual hook**: What's happening on screen in the first frame (from screenshot)
- **Audio hook**: Music stinger, sound effect, voice tone shift, silence

#### B. Content Structure
- **Format**: Talking head, text overlay, montage, screen recording, story, tutorial, listicle, reaction
- **Pacing**: Fast cuts, slow build, steady, rhythmic
- **Length**: Short (<30s), Medium (30-60s), Long (60-120s), Extended (>120s)
- **Pattern**: Problem → Solution, Story → Lesson, Question → Answer, Controversy → Discussion, Tease → Reveal
- **Scene breakdown**: Number of distinct scenes/segments

#### C. Psychological Triggers Detected

| Trigger | Present? | Evidence | Intensity (1-10) |
|---------|----------|----------|------------------|
| Curiosity gap | Yes/No | Open loop in hook | /10 |
| Social proof | Yes/No | Shows popularity/numbers | /10 |
| Identity | Yes/No | "This is for people who..." | /10 |
| Loss aversion | Yes/No | "Don't miss..." | /10 |
| Authority | Yes/No | Expert positioning | /10 |
| Pattern interrupt | Yes/No | Unexpected angle | /10 |
| Controversy | Yes/No | Polarizing take | /10 |
| Emotional | Yes/No | Anger/joy/surprise/sadness | /10 |
| Relatability | Yes/No | "This is so me" factor | /10 |
| Urgency/scarcity | Yes/No | Limited time/opportunity | /10 |
| Reciprocity | Yes/No | Gives value before asking | /10 |
| Anchoring | Yes/No | Specific numbers feel researched | /10 |

#### D. Engagement Analysis
- **Like-to-View ratio**: Calculate as proxy for engagement quality
- **Comment-to-View ratio**: High ratio suggests strong opinion/discussion trigger
- **Share-to-View ratio**: High ratio suggests strong identity signaling or utility
- **Comment sentiment**: Positive, mixed, controversial, supportive, questioning — infer from visible comments and emoji reactions
- **What drives comments**: Question asked?, Controversial opinion?, Fill-in-the-blank?, Tag a friend?, Correction invitation?
- **Top comment themes**: What are people talking about in the top 3-5 visible comments?
- **Emoji reactions breakdown**: Which reactions dominate? (Like, Love, Care, HaHa, Wow, Sad, Angry)

#### E. Caption Analysis
- **Length**: Short (<50 chars), Medium (50-200), Long (200-500), Very Long (>500)
- **Structure**: Single line, multi-paragraph, bullet points, numbered list
- **CTA**: Explicit (comment/share/follow) or Implicit, Type (question, poll, tag, link, shop)
- **Emoji usage**: Count, placement (start/middle/end), which emojis
- **Hashtags**: Count, relevance (branded vs viral vs niche), placement (inline vs end)
- **First line**: Does it restate the hook or add new info?
- **Line breaks**: Short punchy lines vs dense paragraphs

#### F. Production Quality
- **Lighting**: Professional / Natural / Low / Dramatic
- **Audio**: Clear Voiceover / Background music / Natural sound / Mixed
- **Editing**: Minimal / Moderate / Heavy / Cinematic
- **Text overlays**: Yes/No, style (bold, animated, minimal, kinetic typography)
- **Subtitles**: Auto-generated / Styled captions / None — placement and style
- **Color grading**: Warm / Cool / Natural / High contrast / Vintage

#### G. Timing & Posting Pattern
- **Posting time**: Inferred from date text
- **Day of week**: Inferred from context
- **Post type**: Reel / Video / Live / Crosspost
- **First-hour engagement**: Estimated from available signals

### 4. Generate Analysis File

Create a markdown file with the full deconstruction for each post.

### 5. Analyze Competitor Top Content

For each competitor, read their scraped data:

```bash
cat .fb-research/projects/<project-name>/competitors/<competitor-name>/page-analytics.json
cat .fb-research/projects/<project-name>/competitors/<competitor-name>/raw-posts.json
```

Apply the same deconstruction framework (steps 2-3) to the competitor's top 3 posts. Add a comparative lens:

```markdown
## Competitor: <Name>

### Page Comparison
| Metric | Our Page | Competitor | Difference |
|--------|----------|------------|------------|
| Followers | <ours> | <theirs> | +/- |
| Top Post Views | <ours> | <theirs> | +/- |
| Avg Views | <ours> | <theirs> | +/- |

### Their Top 3 Posts
For each post, run the same deconstruction framework.

### What They Do Better Than Us
- <specific advantage>
- <specific advantage>

### What We Do Better Than Them
- <specific advantage>
- <specific advantage>

### Replicable Strategies from Competitor
- <what we can copy/adapt>
- <what we can copy/adapt>

### Gaps in Their Content
- <opportunities for us>
- <opportunities for us>
```

### 6. Identify Cross-Post and Cross-Competitor Patterns

```markdown
## Cross-Post Pattern Analysis

### Common Hook Types (Our Page)
- <hook type> — used in X/5 top posts

### Common Hook Types (Competitors)
- <hook type> — used across competitor top posts

### Shared Patterns (Across Our Page + Competitors)
- <pattern that everyone in the niche uses>
- <pattern that everyone in the niche uses>

### Unique Angles (Competitors have, we don't)
- <angle> — <competitor> does this, we should try it

### Unique Angles (We have, competitors don't)
- <angle> — our differentiator

### Winning Caption Formula (Across All)
- <common caption pattern>

### Optimal Posting Characteristics
- **Best length**: <duration range>
- **Best pacing**: <pacing type>
- **Best hook type**: <hook type>
- **Best CTA**: <cta pattern>
- **Best time**: <estimated time>

### Replication Blueprint
1. Start with <hook_type> hook
2. Use <format> format
3. Include <triggers> triggers
4. Structure caption as: <caption_pattern>
5. Call to action: <cta_pattern>
```

### 7. Save Analysis

```bash
cat > ".fb-research/projects/<project-name>/<YYYY-MM-DD_HHMMSS>/top5-analysis.md"  # also mirrored to project root for legacy << 'ANALYSIS_EOF'
<full analysis content>
ANALYSIS_EOF
```

### 8. Video Ideas Pipeline (`skill video-idea-research`)

The deep deconstruction above feeds the ideas pipeline. When the user wants
**video ideas for a topic**, run the shared playbook with `platform:facebook`:

1. **Top 10 by views in the window** — rank the page's + competitors' top
   reels/videos by view count (watch pages show real view counts; fallback to
   engagement proxies and say so). Never invent numbers.
2. **Outlines** — hook (first caption line / transcript opening), beats, CTA,
   format, duration. Use the downloaded reels + `transcribe.sh` (Whisper) when
   the skeleton matters.
3. **5 ideas**, each grounded in ≥2 top videos with their real view counts.
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
6. Save `video-ideas.json` in the session folder and render the report:
   ```bash
   node "$CLAUDE_SKILL_ROOT/scripts/build-ideas-report.js" <path-to-video-ideas.json>
   # fallback: node ./skills/video-idea-research/scripts/build-ideas-report.js <path>
   ```
   → `ideas-report.md` + `REPORT.html`: **top 10 videos** + **5 ideas** with
   scripts and metadata.

### 9. Report Completion

```
✅ Facebook Research Analysis Complete!

Project: .fb-research/projects/<project-name>/
Analysis file: top5-analysis.md

Top 5 deconstructed: ✅
Competitors analyzed: <N>
  - <competitor-1>: ✅ analyzed
  - <competitor-2>: ✅ analyzed
Cross-post patterns identified: ✅
Competitive comparison: ✅
Replication blueprint created: ✅

Key finding: <top insight about what drives success>

Next step: skill facebook-research-report
```
