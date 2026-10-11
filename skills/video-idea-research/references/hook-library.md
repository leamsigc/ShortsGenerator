# Hook, Title & Attention Library

Synthesized from public Claude skill repositories (researched for this
playbook) plus the channel-calibrated `youtube-title` skill. Cite these when
explaining why a hook/title was chosen.

## The 10 psychology triggers (hook categories)

From `rediumvex/viral-hooks-skill` (100 hook formulas / 10 triggers) and
`artemnovitckii/content-skills`:

| Trigger | Feel | Example pattern |
|---------|------|-----------------|
| **Curiosity** | open loop must close | "Nadie te cuenta qué pasó después de…" |
| **Contrarian** | expectation broken | "Todos dicen que X… y están EQUIVOCADOS" |
| **Authority** | insider proof | "Lo que vio el técnico desde la banca…" |
| **Emotional** | feeling before fact | "Se rompió en el vestidor cuando supo que…" |
| **Listicle** | countable promise | "3 cosas que nadie vio del…" |
| **Question** | brain must answer | "Por qué el árbitro NO marcó el penal?" |
| **Story** | mid-action entry | "Minuto 90, todavía no lo puedo creer…" |
| **Negation** | stop-scroll denial | "Nunca vuelvas a decir que…" |
| **Specificity** | real number/name | "12 millones de euros. Un solo jugador." |
| **Confession** | honest admission | "Me equivoqué con este jugador y acepto que…" |

**Mixing rule (rediumvex):** the two best hooks per video come from different
categories — one *stop-scroll* (negation / specificity / question) + one
*retention* (story / confession / emotional). First stops the thumb, second
keeps them past 3 seconds. Return 3 candidates, label each, recommend a leader.

## Anti-patterns (what kills retention)

From `social-media-skills/skills` (hook-writer) + `viral-hooks`:
- Welcome intros, logo animations, "hey guys", subscribe-before-value.
- Vague teases: "You won't believe what happened" — no noun, no stake.
- **Bait-and-switch**: hook oversells the payoff → mid-video retention cliff.
- Hooks with no specific noun (a name, score, club, number).
- Emoji prefixes / hashtag walls (channel data: 🔴 titles underperform).

## The WATCH framework (short-form retention)

From `social-media-skills/skills/short-form-video-script`:
- **W — Win the first 3 seconds.** ~50-60% of drop-off happens here; layered
  hook (visual + on-screen text + verbal ≈3× the hold); 5 variants to test.
- **A — Arc with open loops.** Hook → Body → Payoff → CTA/loop; open a loop
  early, change the visual every ~2-4s, cut lines that don't earn the next.
- **T — Two tracks.** ~80% watch muted — on-screen text must carry the story;
  captions from word one.
- **C — Cash the promise.** Payoff delivers exactly what the hook sold.
- **H — Hold the loop.** Ending flows back to frame 1 (replays compound);
  one ~2s CTA tied to the value, never a rote "like & subscribe".

## The 5-part script skeleton (short-form)

From `criscatalyst/script-writer-skill` (Hook → Build-Up → Value → Payoff →
CTA) with duration guides:

| Duration | Hook | Build-Up | Value | Payoff | CTA |
|----------|------|----------|-------|--------|-----|
| 15s | 1 sentence | 1 sentence | 1-2 points | built-in | 1 sentence |
| 30s | 1 sentence | 1-2 sentences | 2-3 points | 1 sentence | 1 sentence |
| 60s | 1 sentence | 2-3 sentences | 3-5 points / mini-story | 1-2 sentences | 1-2 sentences |
| 90s | 1 sentence | 3-4 sentences | full story | 2-3 sentences | 1-2 sentences |

Psychology tricks to weave invisibly: Dream Outcome, Subtle Authority (show,
don't brag), Mind Read (clear the objection), Risk Reversal, Extreme Value
(paid-level info free), Burning Question, Reciprocity CTA (keep giving).

## 50+ title formulas (by category)

From `aaaronmiller/create-viral-content` (`references/title-formulas.md`),
adapted to Spanish + sports/news:

**Curiosity gap**
- `What [group] won't tell you about [topic]` → "Lo que nadie te cuenta del vestidor"
- `The [adj] secret to [outcome]` → "El secreto de la remontada"
- `I discovered [thing] that [unexpected result]`
- `The [surprising] truth about [topic]`

**Contrarian**
- `[Common practice] is dead. [New paradigm] is next.`
- `Stop [X]. Start [Y].`
- `[Popular opinion] is wrong — here's why`
- `[Common advice] is bad advice — do this instead`

**Listicle**
- `[N] ways to [achieve X] without [sacrifice]`
- `[N] [topic] mistakes destroying your [metric]`
- `[N] things I wish I knew before [X]`
- `[N] lessons from [notable experience]`

**How-to**
- `How to [achieve X] in [timeframe] (step-by-step)`
- `How to [achieve X] even if [common objection]`
- `How I [achieved X] (and how you can too)`
- `How [authority] [achieved X] — broken down`

**Question**
- `Is [common belief] actually [myth/true]?`
- `Can [ordinary thing] really [impressive claim]?`
- `What happens when you [action] for [time]?`

**Comparison / prediction / loss aversion**
- `[A] vs [B]: Which [outcome] better?` / `I tried [A] and [B] — here's the winner`
- `[Concept] is the [year] [category] that [outcome]` / `[N] [topic] trends for [year]`
- `Warning: [Thing] is [damaging your thing]` / `The hidden danger of [X]`

**YouTube adaptation (50-60 chars):** front-load the keyword entity, add a
number when possible, include one emotional trigger word, no emoji prefix.

## Channel-calibrated overlay (youtube-title skill)

On this channel (futbol mexicano Shorts, Spanish):
- Conflict + specificity wins: EXPLOTA, HUMILLADOS, EMPUJÓ + score (3-3, 0-2).
- Same event, better title = 13× views ("¡HUMILLADOS! Querétaro le gana 0-2 a
  Chivas" 1,339 vs "Cantó el GALLO..." 103).
- Passive/descriptive titles die (4 views). All-caps works only with substance.
- Curiosity gaps peak CTR; searchable nouns (Ditta, árbitro, Liga MX) front-loaded.
- Length 45-70 chars; ≤60 so mobile doesn't cut. AVD 0:37 — never promise what
  the script can't deliver.

## Sources

- https://github.com/rediumvex/viral-hooks-skill — 100 hooks / 10 triggers
- https://github.com/criscatalyst/script-writer-skill — 5-part skeleton, psychology tricks, duration guides
- https://github.com/aaaronmiller/create-viral-content — 50+ title formulas
- https://github.com/social-media-skills/skills — hook-writer + short-form-video-script (WATCH)
- https://github.com/artemnovitckii/content-skills — storytelling (tension/turn/payoff) + viral-hooks
