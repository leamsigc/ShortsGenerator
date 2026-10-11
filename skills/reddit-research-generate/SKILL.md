---
name: reddit-research-generate
version: 3.0.0
description: |
  Generate state — reads scraped Reddit posts from .reddit-research/,
  searches DuckDuckGo for videos related to the SPECIFIC post topic
  (e.g., for a Klopp post: "Jürgen Klopp German national team new era
  video"), appends video URLs to each post's markdown file, then calls
  the short-generator skill to produce a YouTube Short. Also generates
  Shorts from the video-ideas pipeline (video-idea-research): each idea's
  viral script + its media links feed short-generator.

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

# Reddit Research — Generate State (v3)

Takes scraped Reddit posts (with viral scripts already embedded), finds CONTEXT-RELEVANT videos, and generates Shorts.

> **CSV for MagicSync**: after generating Shorts (ask the user), build the bulk-scheduling CSV with
> `node "$CLAUDE_SKILL_ROOT/scripts/build-csv.js" <timestamp>` (see the main `reddit-research` skill, Phase 3).

## Key Improvement over v1

Video search queries must be **specific to the post topic**, not generic. Example:
- Post about Klopp → search `"Jürgen Klopp German national team new era coach 2026"`
- Post about Mbappé Paraguay → search `"Mbappé Paraguay penalty controversy dark arts 2026"`
- Post about referee → search `"Ilgiz Tantashev referee Paraguay France no cards 2026"`

## Before Running

1. Ensure `.reddit-research/<timestamp>/` exists with scraped posts (from Phase 1)
2. Ensure Flask backend is running on port 8080
3. Chrome DevTools available

## Steps

### 1. Select Research Session

```bash
ls -d .reddit-research/*/
```

Read the `index.json` to get the post list and select the most recent session.

### 2. For Each Post, Search for Context-Relevant Videos

For each post, construct a targeted search query based on the post title and content:

| Post Topic | Search Query |
|------------|-------------|
| Klopp Germany | `"Jürgen Klopp German national team new era coach 2026 video"` |
| Mbappé Paraguay | `"Mbappé Paraguay penalty controversy dark arts dirty game 2026 video"` |
| Olise card | `"Michael Olise yellow card Galarza simulation dive 2026 video"` |
| Ancelotti Ferguson | `"Carlo Ancelotti Alex Ferguson only coach more experienced video 2026"` |
| Referee 1/10 | `"Ilgiz Tantashev referee Paraguay France no yellow cards 2026 video"` |
| Mbappé insult | `"Mbappé insult Paraguay player Spanish mother 2026 video"` |
| Galarza elbow | `"Galarza elbow Kounde no foul VAR controversy 2026 video"` |
| Galarza punches | `"Galarza punch Mbappe 38th minute Paraguay France 2026 video"` |

#### Use Chrome DevTools on DuckDuckGo Videos

```bash
chrome-devtools navigate_page --url "https://duckduckgo.com/"
chrome-devtools fill "<search_input_uid>" "<specific_search_query>"
chrome-devtools press_key "Enter"
```

Wait for results. Click the "Videos" tab:

```bash
chrome-devtools take_snapshot
# Find the Videos tab/link and click it
chrome-devtools click "<videos_tab_uid>"
```

Then extract video URLs (YouTube, TikTok, Instagram, etc.):

```javascript
() => {
  const links = document.querySelectorAll('a[href*="youtube.com/watch"], a[href*="youtu.be"], a[href*="tiktok.com"], a[href*="instagram.com/reel"], a[href*="vimeo.com"], a[href*="dailymotion.com"]');
  const results = [];
  const seen = new Set();
  links.forEach(a => {
    const href = a.getAttribute('href');
    let actualUrl = href;
    try {
      const u = new URL(href);
      if (u.hostname.includes('duckduckgo') && u.searchParams.get('uddg')) {
        actualUrl = decodeURIComponent(u.searchParams.get('uddg'));
      }
    } catch(e) {}
    if (actualUrl && !seen.has(actualUrl)) {
      seen.add(actualUrl);
      results.push({ title: a.innerText?.trim() || a.getAttribute('title') || '', url: actualUrl });
    }
  });
  return JSON.stringify(results.slice(0, 8));
}
```

#### Fallback: WebSearch

If Chrome DevTools yields fewer than 3 video URLs:

```
websearch "<specific_search_query> video"
```

Extract video URLs from results. Prefer YouTube, TikTok, Instagram Reel URLs.

### 3. Append Sourced Videos to Post Markdown File

Read the post's markdown file. Find the `## Sourced Videos` section (or add it). Append the discovered video URLs:

```markdown
## Sourced Videos

1. [Video Title](<video_url>)
2. [Video Title](<video_url>)
...
```

### 4. Call short-generator for Each Post

The markdown file already contains:
- Title
- Post content
- Top comments  
- Viral video script (in Spanish)
- Sourced video URLs

To generate the Short, call the short-generator:
```
/short-generator <post_title> voice:M5 hashtags:<keyword1,keyword2> sources:youtube,tiktok,instagram ratio:9:16 music:off subtitle_position:center,bottom
```

When the short-generator asks for:
- **Script**: Use the script already saved in the `## Viral Video Script (Spanish)` section
- **Video URLs**: Provide the URLs from `## Sourced Videos`
- **Voice**: M5 (Daniel)
- **Subtitle position**: center,bottom
- **Language**: Spanish
- **Hashtags**: Extract keywords from the post title (e.g., `Klopp, Germany, football`)

### 5. Track Generation Status

Append to each post's markdown file:

```markdown
## Short Generation

- **Status**: ✅ Generated / ❌ Failed
- **Voice**: M5
- **Language**: Spanish
- **Subtitle Position**: center,bottom
- **Generated At**: <YYYY-MM-DD HH:MM:SS>
```

### 7. Generate from the Video Ideas Pipeline (`video-ideas.json`)

When the session has `video-ideas.json` (from the `video-idea-research`
playbook), each idea is already production-ready:

1. Read `.reddit-research/<timestamp>/video-ideas.json`.
2. Ask the user which idea(s) to produce (rank order by view estimate).
3. Use the idea's **`scripts.viral`** as the script (or `storytelling` /
   `inspiration` per the user's pick) — paste-ready, pure spoken text.
4. Use the idea's **`mediaLinks`** as the sourced video URLs (Step 2 search is
   then optional — links already collected).
5. Upload title/description/tags/keywords come from the idea's
   **`youtube`** metadata block — never invent new ones.
6. Then run Step 4's short-generator call with those values.

### 8. Report Completion

```
✅ Shorts Generation Complete!

Session: .reddit-research/<timestamp>/
Posts processed: 10/10
Generated: X
Failed: Y

Video files:
- http://localhost:8080/static/generated_videos/<file1>.mp4
- http://localhost:8080/static/generated_videos/<file2>.mp4
...
```
