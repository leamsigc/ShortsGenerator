---
name: twitter-research-report
version: 4.0.0
description: |
  Report state — generates the final HTML report (REPORT.html) from
  raw-posts.json, audience-scores.json, content-drafts.json, and
  engagement-responses.json. Includes audience scoring matrix, top post
  analysis, content drafts, and pre-defined engagement responses for every
  topic post. In Video Ideas Mode it also renders the top-10 videos by views
  (with outlines) and the 5 video ideas with 3 scripts each
  (viral/storytelling/inspiration) plus YouTube metadata (title, description,
  tags, keywords) via the shared video-idea-research report script.

allowed-tools:
  - Bash
  - Read
  - Write
  - ChromeDevTools
---

# Twitter/X Research — Report State (v4)

Generates the final HTML report with audience scoring, post links, and engagement responses.

## Video Ideas Mode report

When the session contains `video-ideas.json` (from the analyze state / the
`video-idea-research` playbook), render the dedicated ideas report:

```bash
node "$CLAUDE_SKILL_ROOT/scripts/build-ideas-report.js" <path-to-video-ideas.json>
# fallback: node ./skills/video-idea-research/scripts/build-ideas-report.js <path>
```

Writes `ideas-report.md` + `REPORT.html` next to the input with the two
mandatory sections: **1) the top 10 videos** (rank, title, views, window,
velocity, link, outline) and **2) the 5 video ideas** (titles, viral +
storytelling + inspiration scripts, audiences, view estimate, media links,
YouTube metadata). If the main `REPORT.html` also exists, append a link to it
so both are reachable from one index.

## Preconditions

- Config exists: `.twitter-research/<timestamp>/config.json`
- Raw posts exist: `.twitter-research/<timestamp>/raw-posts.json` (10+ topic posts)
- Analysis exists: `.twitter-research/<timestamp>/audience-scores.json`
- Content drafts exist: `.twitter-research/<timestamp>/content-drafts.json`

## Steps

### 1. Generate engagement responses (per topic post)

For **EVERY post** in `raw-posts.json` `posts[]`, craft 3 response types the user can post
as replies to build presence on the topic:

| Type | Strategy | Limit | Tone |
|------|----------|-------|------|
| **Value add** | Build on the tweet's point with an expert insight | 1-3 sentences | Helpful, authoritative |
| **Discussion starter** | Ask a thoughtful question that sparks replies | 1-2 sentences | Curious |
| **Agree + amplify** | Agree strongly and add a personal take | 1-2 sentences | Enthusiastic |

Rules: never pitch the product, stay on-topic, reference specifics, end with a hook, keep it short.

Save to `.twitter-research/<timestamp>/engagement-responses.json` (schema:
`responses[]` with `targetPostUrl`, `targetHandle`, `postPreview`, `targetSegment`,
`responses[{type, text, whyThisWorks}]`, `tracking`).

### 2. Generate REPORT.html

```bash
node "$CLAUDE_SKILL_ROOT/scripts/report-html.js" <timestamp>
# fallback: node ./skills/twitter-research/scripts/report-html.js <timestamp>
```

The script renders a self-contained dark-themed report from all JSON files:
- Audience scoring matrix
- Top posts with direct X links + engagement stats
- Content drafts (social posts + video scripts)
- Engagement responses (copyable, with Reply-on-X links)

## Report Completion

```
✅ Twitter/X Research Report Complete!

Session: .twitter-research/<timestamp>/
📊 REPORT.html — open in browser
📁 audience-scores.json · content-drafts.json · engagement-responses.json
```
