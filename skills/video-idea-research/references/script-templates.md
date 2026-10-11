# Script Templates — extracted from the ShortsGenerator Backend

Source of truth: `Backend/settings.py` (`scriptTemplates`, `scriptSettings`)
and `Backend/classes/Shorts.py` (`GenerateScript`, `SCRIPT_LENGTHS`).
Do not duplicate these prompts in skills by hand except as reference — when the
backend runs, drive it through `/api/script`.

## Generating through the backend

```bash
curl -s -X POST http://localhost:8080/api/script \
  -H "Content-Type: application/json" \
  -d '{
    "videoSubject": "<idea title / topic>",
    "extraPrompt": "<angle + outline context + audience>",
    "aiModel": "g4f",
    "scriptTemplate": "viral_shorts",
    "scriptLength": "standard"
  }'
```

Response: `data.script` (clean spoken text) + `data.search` (search terms for
stock/social clips). If the backend is down, write the script by hand using the
templates below.

## scriptLength presets (Backend/classes/Shorts.py)

| Value | ~Words | ~Seconds | Use for |
|-------|--------|----------|---------|
| `short` | 80 | 30 | quick Short |
| `standard` | 120 | 60 | default Short |
| `long` | 220 | 110 | deep Short / mini long-form |
| `extended` | 350 | 180 | long-form YouTube video |
| `epic` | 500 | 260 | documentary / pillar video |

The length requirement **overrides** any template word-count hints. For
long-form ideas use `extended`/`epic` and keep the same viral/conversational
style for the whole run time.

## Template 1 — `viral_shorts` (THE VIRAL script)

```
# Role: Viral YouTube Shorts Script Generator
## GOAL: Create a HIGHLY ENGAGING, VIRAL-WORTHY 60-second video script that
keeps viewers hooked from the FIRST SECOND until the end.

### 1. THE HOOK (0-3 seconds)
- Start with a SHOCKING statement, controversial take, or unexpected fact
- Use words like "Nobody tells you", "The truth about", "I wish I knew", "Stop doing"
- Create immediate curiosity gap - make them NEED to know more

### 2. THE CONTENT (3-45 seconds)
- Deliver VALUABLE, ACTIONABLE content
- Use SHORT, PUNCHY sentences (5-10 words max per segment)
- Include 2-3 "pattern interrupts" - unexpected shifts in content or tone
- Build TENSION - create questions in viewer's mind that you WILL answer

### 3. THE PAYOFF (45-60 seconds)
- Deliver the ANSWER or SOLUTION they came for
- End with a CALL TO ACTION: "Follow for more", "Save this", "Share with a friend"
- Leave them wanting MORE - create curiosity for next video

## STRICT RULES:
1. NO markdown, NO titles, NO formatting - pure raw script
2. NO introductions like "In this video" or "Welcome back"
3. NO "voiceover" or "narrator" labels
4. Write in CONVERSATIONAL, COLLOQUIAL tone - like talking to a friend
5. Use POWER WORDS: Secret, Truth, Hack, Trick, Mistake, Never, Always, Everyone, Nobody
6. Include EMOTIONAL TRIGGERS: surprise, curiosity, FOMO, amusement
7. Respond in the SAME LANGUAGE as the video subject
8. Keep TOTAL script length around 80-120 words for 60-second video
9. Format for AI VOICEOVER - natural spoken flow, no paragraph breaks
10. The HOOK is the single most important part - make it scroll-stopping
```

## Template 2 — `educational`

```
### 1. THE QUESTION (0-5 seconds) - relatable question/problem
### 2. THE EXPLANATION (5-45 seconds) - simple terms, analogies, one insight per sentence
### 3. THE TAKEAWAY (45-60 seconds) - key lesson + practical tip + "Follow for more"
Rules: no markdown, no intros, conversational, simple language, 1-2 surprising
facts, ~100-130 words, same language as subject, hook = instant question.
```

## Template 3 — `storytelling` (THE STORY script)

```
# Role: Storytelling Shorts Script Generator
### 1. THE SETUP (0-5 seconds)
- Start IN THE MIDDLE of action or a dilemma
- "I'll never forget when..."
- Create instant intrigue
### 2. THE CONFLICT (5-40 seconds)
- Build tension with specific details
- Describe emotions and stakes
- Use vivid, sensory language
- Make the viewer FEEL the moment
### 3. THE RESOLUTION (40-60 seconds)
- Deliver the twist, lesson, or outcome
- End with a reflective line or call to action
- Leave an emotional impact
Rules: no markdown, first person, SPECIFIC details (numbers, names, places),
~120-150 words, every sentence advances the story, hook starts mid-action.
```

## Template 4 — `listicle`

```
### 1. THE HOOK (0-5s) - "Top [N] ways to..." / "[N] things nobody tells you"
### 2. THE LIST (5-50s) - "Number one...", each item ONE punchy sentence, best last
### 3. THE CLOSE (50-60s) - recap best tip + "Which one will you try? Comment"
Rules: 3-5 items, ~80-100 words, BOLD claims with specific numbers.
```

## Template 5 — `controversial` (hot take)

```
### 1. THE HOT TAKE (0-5 seconds) - most controversial statement possible
### 2. THE REASONING (5-45 seconds) - 2-3 specific reasons, call out counter-arguments
### 3. THE CHALLENGE (45-60 seconds) - "Change my mind" / provocative question
Rules: confident but not offensive, ~90-120 words, engagement hook ending.
```

## Template 6 — `motivational` (THE INSPIRATION script)

```
# Role: Motivational Shorts Script Generator
### 1. THE STRUGGLE (0-8 seconds) - acknowledge a common pain point, instant empathy
### 2. THE SHIFT (8-45 seconds) - mindset shift, POWERFUL emotional language,
short impactful sentences building momentum
### 3. THE CALL TO ACTION (45-60 seconds) - "Start today" / "You have what it
takes" / a line that STICKS
Rules: SECOND PERSON ("you"), emphatic language (must, will, can, never),
under 100 words for maximum impact, every sentence HITS, memorable one-liner.
```

## Global prompt appended to EVERY script (`scriptSettings.defaultPromptEnd`)

```
## FINAL REMINDERS:
- NO markdown, NO formatting, NO titles — pure raw script text ready for AI voiceover
- Write in NATURAL, CONVERSATIONAL spoken language
- Use SHORT, PUNCHY sentences (5-10 words per segment)
- The FIRST 3 SECONDS must be the most hooking, attention-grabbing opener possible
- The hook is the SINGLE MOST IMPORTANT element — invest creative effort here
- Every sentence must ADD VALUE or CREATE CURIOSITY
- Use pattern interrupts and emotional triggers (surprise, curiosity, FOMO)
- End with engagement hook
- Write like you're telling a SECRET to a friend
- Optimized for SOCIAL MEDIA SHORTS — high retention, punchy delivery
```

## Cleanup applied by the backend

`Shorts.GenerateScript` strips `*`, `#`, and any `[...]` / `(...)` markup from
the model output — so write the final script as pure spoken text and keep
`[HOOK]` / `[CTA]` labels only in the research markdown, never in the string
handed to the backend (they would be stripped or read aloud depending on path).

## Metadata generation (`Backend/gpt.py generate_metadata`)

The backend can also produce title + description + keywords + a social post for
a finished script (title <60 chars, description with hashtags, 6 keywords via
`get_search_terms`, post <280 chars). Use it as a first draft, then apply the
`youtube-title` scoring rules for the final title and hand-write the
description/tags block per the playbook (Step 5).
