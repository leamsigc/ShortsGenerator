---
name: twitter-research-analyze
version: 4.0.0
description: |
  Analyze state — reads the scraped topic posts from raw-posts.json (10+
  posts across many accounts), scores target audience segments 1-10 based on
  engagement signals, generates social media post drafts and video script
  drafts from top-performing posts, identifies content patterns, and — in
  Video Ideas Mode — produces the top-10 video ranking (views inside the
  window), their outlines, 5 video ideas with 3 scripts each
  (viral / storytelling / inspiration) and YouTube metadata
  (title, description, tags, keywords) into video-ideas.json.

allowed-tools:
  - Bash
  - Read
  - Write
  - ChromeDevTools
  - Skill
---

# Twitter/X Research — Analyze State (v4)

Scores audiences, generates content drafts, identifies winning patterns, and
runs the **Video Ideas Mode** pipeline. Outputs are consumed by
`twitter-research-report` (`node "$CLAUDE_SKILL_ROOT/scripts/report-html.js" <timestamp>`)
and, for ideas, by the shared
`node "$CLAUDE_SKILL_ROOT/scripts/build-ideas-report.js" <video-ideas.json>`
(script ships with the `video-idea-research` skill).

## Video Ideas Mode (when the user asks for video ideas)

Follow `skill video-idea-research` — the shared playbook. X-specifics:

1. **Top-10 by views in the window**: open each video post's status page for
   the real view count; window via `since:`/`until:`. Rank by views, tie-break
   by `velocityPerDay`. Never invent numbers (`views: null` if unreadable).
2. **Outlines**: hook = first line of the caption (verbatim when possible);
   beats from the clip/replies; CTA = closing ask. Record format/duration.
3. **5 ideas**, each grounded in ≥2 top videos with their real view counts.
4. **3 scripts per idea** — viral (`viral_shorts`), storytelling
   (`storytelling`), inspiration (`motivational`) — TTS-ready, `[HOOK]`/
   `[CTA]` labels in markdown only. Optionally seed via the backend:
   ```bash
   curl -s -X POST http://localhost:8080/api/script \
     -H "Content-Type: application/json" \
     -d '{"videoSubject":"<idea title>","extraPrompt":"<angle + outline context>","aiModel":"g4f","scriptTemplate":"viral_shorts","scriptLength":"standard"}'
   ```
5. **YouTube metadata per idea** via the `youtube-title` rubric (keyword
   front-loaded, one ALL-CAPS power word, concrete detail, stake, 45-70 chars)
   + description + 8-15 tags/keywords.
6. Save `video-ideas.json` in the session folder, then build the report:
   `node "$CLAUDE_SKILL_ROOT/scripts/build-ideas-report.js" .twitter-research/<timestamp>/video-ideas.json`
   (script ships with the `video-idea-research` skill; fallback:
   `node ./skills/video-idea-research/scripts/build-ideas-report.js <path>`)

## Preconditions

- Scrape completed: `.twitter-research/<YYYY-MM-DD_HHMMSS>/raw-posts.json`
- Config exists: `.twitter-research/<timestamp>/config.json`

## Steps

### 1. Load data

```bash
node -e "const d=require('./.twitter-research/<YYYY-MM-DD_HHMMSS>/raw-posts.json'); console.log(JSON.stringify({topic:d.topic, distinctAccounts:d.distinctAccounts, posts:d.posts.map(p=>({handle:p.handle, likes:p.likes, retweets:p.retweets, url:p.url, text:p.text.substring(0,120)}))},null,2))"
```

### 2. Audience segmentation & scoring

For each `targetAudienceKeyword` in config, score 1-10 using: relevance, engagement
rate, content affinity, monetization potential, competition level (lower = better).
Find matching posts per segment and note pain points + content angles.

Save to `audience-scores.json`:
```json
{
  "analysisTimestamp": "<YYYY-MM-DD HH:MM:SS>",
  "segments": [
    {
      "segment": "social media manager",
      "finalScore": 9,
      "breakdown": {"relevance": 10, "engagementRate": 9, "contentAffinity": 8, "monetization": 9, "competitionLevel": 7},
      "verdict": "✅ Best Prospect",
      "painPoints": ["..."],
      "contentAngles": ["..."],
      "whyScore": "...",
      "matchingTweetsCount": 8
    }
  ],
  "contentPatterns": {"topHookTypes": [], "bestFormats": [], "contentCalendar": {}},
  "totalPostsAnalyzed": 10,
  "distinctAccountsAnalyzed": 7,
  "topic": "<topic>"
}
```

### 3. Generate social media post drafts

For the top topic posts, adapt each winning angle to the user's brand voice
(headline, body, CTA, hashtags, best time). Generate via the backend API if available:

```bash
curl -s -X POST http://localhost:8080/api/script \
  -H "Content-Type: application/json" \
  -d '{"videoSubject":"<topic>","extraPrompt":"<build a viral social post adapting the top tweet>","aiModel":"g4f","scriptTemplate":"viral_shorts"}'
```

If the API is unavailable, write drafts manually based on each tweet's structure and angle.

### 4. Generate video script drafts

If `contentFormat` includes video, generate 30-60s scripts: hook → problem → solution → social proof → CTA.

### 5. Save to content-drafts.json

```json
{
  "generatedAt": "<YYYY-MM-DD HH:MM:SS>",
  "postDrafts": [{"rank": 1, "sourceHandle": "@h", "sourceUrl": "...", "targetSegment": "...", "headline": "...", "body": "...", "cta": "...", "hashtags": ["#a"], "format": "social_post"}],
  "videoScripts": [{"rank": 1, "sourceHandle": "@h", "sourceUrl": "...", "targetSegment": "...", "hook": "...", "body": "...", "cta": "...", "format": "video_script"}]
}
```

## Report Completion

```
✅ Twitter/X Research Analysis Complete!
Session: .twitter-research/<timestamp>/
Audience segments scored: <N> (top: <segment> <score>/10)
Content drafts: <N> posts · <N> scripts
Next step: skill twitter-research-report
```
