---
name: youtube-title
version: 1.0.0
description: |
  Generates the best SEO-targeted, attention-grabbing YouTube video title.
  Calibrated on the channel's own Shorts performance data (CTR, views,
  impressions, avg view duration). Use whenever a YouTube title must be
  chosen or improved: called as a step by twitter-research-topics,
  twitter-research (Topics Mode), short-generator, or standalone when the
  user asks for "the best title", "SEO title", "title for my YouTube
  video/Short".

allowed-tools:
  - Read
  - Write
  - Edit
  - Question
  - WebSearch
---

# YouTube SEO Title Generator (calibrated on channel data)

Produces ONE recommended title + 2 A/B alternates for a video idea, scored
against an evidence-based rubric. Titles are in Spanish (channel language)
unless the user requests otherwise.

## Channel benchmark (empirical — source of truth for these rules)

Channel totals (last period): **3,582 thumbnail impressions · 5.1% CTR ·
10,394 views · 0:37 avg view duration · 69.4 watch hours.**

| Title | Impr | CTR | Views | AVD |
|---|---|---|---|---|
| Mohamed EXPLOTA contra Katia Itzel tras el Cruz Azul 3-3 Toluca | 200 | 0% | 1,835 | 0:50 |
| Buscan obligar el regreso del Ascenso por ley | 32 | 3.1% | 1,541 | 0:36 |
| ¡HUMILLADOS! Querétaro le gana 0-2 a Chivas en su casa | 270 | 3.7% | 1,339 | 0:33 |
| El gobierno forzará el descenso en la Liga MX | 81 | 4.9% | 1,320 | 0:39 |
| mediocridad en la Liga MX | 26 | 7.7% | 1,223 | 0:39 |
| Mohamed EXPLOTÓ contra la árbitra y el video es brutal | 120 | 1.7% | 1,220 | 0:38 |
| El dato que nadie vio del empate de México ante Colombia | 3 | 66.7% | 1,188 | 0:25 |
| Ditta EMPUJÓ al árbitro y se puede ir suspendido | 2,057 | 6.4% | 529 | 0:23 |
| ¡Cantó el GALLO! / Cantó el GALLO: Querétaro humilla a Chivas | 267 | 4.9% | 103 | 0:43 |
| El debut de Rafa Márquez con el Tri casi fue un desastre | 153 | 5.2% | 45 | 0:44 |
| 🔴 Así quedó el debut de Rafa Márquez al frente de México | 153 | 2.6% | 18 | 0:28 |
| Los aficionados ABANDONARON el estadio al medio tiempo | 101 | 0% | 16 | 0:31 |
| Mexico vs Colombia El niño que salvó el debut de Rafa Márquez | 45 | 8.9% | 7 | 0:34 |
| La Hormiga falló lo IMPOSIBLE y los memes no perdonan | 60 | 0% | 6 | 1:07 |
| El partido se le complicaba a México frente a Colombia | 14 | 0% | 4 | 0:36 |

### What the data proves

1. **Conflict + specificity wins views.** Top-7 titles (1,188–1,835 views)
   all contain drama (EXPLOTA, EMPUJÓ, obligar, humillar), a score/number
   (3-3, 0-2), or a bold stake (descenso por ley, dato que nadie vio).
2. **Same event, better title = 13× views:** "¡HUMILLADOS! Querétaro le
   gana 0-2 a Chivas en su casa" (1,339 views) beat "Cantó el GALLO:
   Querétaro humilla a Chivas en su casa" (103 views). Score + caps
   exclamation outperformed the softer phrasing.
3. **Passive/descriptive titles die:** "El partido se le complicaba a
   México frente a Colombia" → 4 views, 0% CTR. "El niño que salvó..." →
   7 views. No stake, no conflict, no caps.
4. **Emoji prefixes hurt:** "🔴 Así quedó el debut..." → 18 views, 2.6%
   CTR (the 🟣/🔴 convention reads like clickbait spam).
5. **ALL-CAPS power word works only with substance:** EXPLOTA, HUMILLADOS,
   EMPUJÓ, GALLO (in caps with score) succeeded; "ABANDONARON" flopped
   (16 views) because the claim had no names/score attached.
6. **CTR peaks on curiosity gaps:** "El dato que nadie vio..." got 66.7%
   CTR (3 impressions — directional only). "Ditta EMPUJÓ..." combined
   curiosity + stake and delivered the best volume CTR (6.4% over 2,057
   impressions).
7. **Search still needs the entity front-loaded:** highest-impression
   titles carried searchable nouns (Ditta, árbitro, Liga MX, Rafa
   Márquez, México, Chivas). Feed-driven views hide this, but impressions
   come from search/discovery.

## Title rules (apply in order)

1. **Keyword first (chars 0–40):** start with the primary search entity —
   matchup ("México vs Perú"), player ("Gilberto Mora"), competition
   ("Liga MX Jornada 10"), or event. Never bury it mid-title.
2. **One power word in ALL CAPS:** a single verb/noun of conflict or
   emotion (ABUCHEADO, EXPLOTA, HUMILLÓ, RECHAZÓ, RENUNCIAR, TRIPLUTE,
   DEBE GANAR). Max 1–2 words; never the whole title.
3. **Attach a concrete detail:** final score, money figure, date, club, or
   role ("1-1", "12 millones", "3 de octubre", "Real Madrid").
4. **Create the stake/curiosity gap:** what it costs, what nobody saw,
   what happens next ("puede PERDER EL PUESTO", "el dato que nadie vio").
5. **Length:** 45–70 characters (YouTube cuts search display ~70; aim ≤ 60
   so the full title survives mobile). Absolute max 100.
6. **No emoji prefix, no hashtags** in the title (hashtags go in the
   description). No ALL-CAPS sentences, no deception — the title must match
   the video (channel AVD is 0:37; broken promises kill retention).
7. **Honest clickability:** if two candidates score equal, prefer the one
   whose promise the script actually delivers.

## Process

1. Read the topic/video idea: script hook, key facts, keywords.
2. Generate **5 candidate titles** covering different angles (conflict,
   score+result, curiosity gap, stake/pressure, SEO-plain).
3. Score each 0–2 on five axes (max 10):
   - **SEO** — primary keyword in first 40 chars, entity people search
   - **Power** — ALL-CAPS conflict word with substance
   - **Specificity** — score/number/names/date present
   - **Stake** — curiosity gap or consequence
   - **Format** — 45–70 chars, no emoji/hashtag spam
4. Pick the highest scorer; make sure 2nd/3rd differ in angle so they are
   usable as A/B thumbnail-test variants.
5. Output the block below (in Spanish) and, when inside a research
   session, append it as **section 6** of the topic file.

## Output format

```markdown
## 6. Título SEO para YouTube
**Título recomendado:** <best title> (<n>/10)
**Alternativo A:** <angle> — <title> (<n>/10)
**Alternativo B:** <angle> — <title> (<n>/10)
**Keywords para descripción:** <3-5 search phrases, comma separated>
**Por qué funciona:** <1-2 lines citing the data rules it hits>
```

## Quick examples (before → after, using channel evidence)

- "🔴 Así quedó el debut de Rafa Márquez al frente de México" (18 views)
  → "El debut de Rafa Márquez CASI FUE UN DESASTRE con México" (stakes + caps)
- "Cantó el GALLO: Querétaro humilla a Chivas en su casa" (103 views)
  → "¡HUMILLADOS! Querétaro le gana 0-2 a Chivas en su casa" (1,339 views)
- "El partido se le complicaba a México frente a Colombia" (4 views)
  → "México vs Colombia: el empate que CASI se vuelve desastre del Tri"
