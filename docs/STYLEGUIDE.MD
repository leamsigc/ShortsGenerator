# CLIPPER — UI/UX Design System

> **AI Video Clip Generator**
>
> **Design philosophy:** Minimal AI. Maximum signal.
>
> **Visual direction:** Stripe-inspired SaaS interface + Nuxt-inspired green + Poppins typography + professional video-editor UX.
>
> **Brand colors:** Maximum 2.
>
> **Navigation:** No sidebar.

---

# 1. Design Principles

CLIPPER transforms long-form videos into short-form vertical clips.

The interface must make this workflow immediately understandable:

```text
SOURCE
  ↓
TRANSCRIBE
  ↓
ANALYZE
  ↓
SELECT
  ↓
EDIT
  ↓
EXPORT
```

The UI should feel:

* Professional
* Extremely clean
* Fast
* Technical
* Creator-focused
* Trustworthy
* Minimal
* Information-dense without feeling crowded

The interface should **not** feel like:

* A generic AI dashboard
* A social-media toy
* A gaming interface
* A colorful analytics dashboard
* A traditional video editor with dozens of controls

### Core UX rule

At every moment the user should know:

> **What am I looking at?**
>
> **What is CLIPPER doing?**
>
> **What should I do next?**
>
> **Why was this clip selected?**

---

# 2. Visual Direction

The visual language is inspired by the principles used by modern Stripe-style product interfaces:

* White/light application surfaces
* Large amounts of whitespace
* Strong typography
* Very subtle borders
* Minimal shadows
* Restrained use of color
* Clear information hierarchy
* Compact but generous controls
* Consistent spacing
* Professional data presentation
* Content-first layouts

Do **not** copy Stripe branding or components literally.

Use the same general UX principles while maintaining CLIPPER's own identity.

---

# 3. Brand Color System

CLIPPER uses **two brand colors only**.

## Primary — Nuxt Green

```text
#00DC82
```

Usage:

* Primary buttons
* Active navigation
* Selected clips
* Progress indicators
* Focus indicators
* Active timeline regions
* Score indicators
* Links
* Important interactive states
* Brand mark

The green should be used sparingly.

It should immediately communicate:

> **Action / active / selected / important**

---

## Secondary — Ink

```text
#0F172A
```

Usage:

* Primary text
* Headings
* Icons
* Borders where stronger contrast is required
* Video/editor surfaces
* Primary dark controls

Ink is the main structural color.

---

## Neutral surfaces

The interface uses white and transparency-based neutral surfaces rather than introducing additional brand colors.

```text
Background: #FFFFFF
Surface: rgba(15, 23, 42, 0.02)
Border: rgba(15, 23, 42, 0.10)
Muted text: rgba(15, 23, 42, 0.60)
Disabled: rgba(15, 23, 42, 0.35)
```

These are **opacity treatments of Ink**, not additional brand colors.

### Important

Do not introduce:

```text
Blue
Purple
Orange
Red
Yellow
Pink
```

as UI colors.

Status should primarily be communicated using:

* Icon
* Label
* Typography
* Border
* Opacity
* Progress state

---

# 4. Color Usage Ratio

Recommended visual balance:

```text
White / neutral surfaces: ~85–90%
Ink: ~8–12%
Nuxt Green: ~2–5%
```

Green should never dominate the interface.

A good rule:

> If everything is green, nothing is important.

---

# 5. Typography

## Primary Typeface

# Poppins

Poppins is the **only application typeface**.

Import:

```css
font-family: 'Poppins', sans-serif;
```

Recommended weights:

```text
400 — Regular
500 — Medium
600 — SemiBold
700 — Bold
```

Avoid:

* 800
* 900
* Condensed variants
* Decorative fonts

---

# 6. Typography Scale

| Token       |    Size | Weight | Line Height | Usage               |
| ----------- | ------: | -----: | ----------: | ------------------- |
| Display     |    36px |    700 |         1.1 | Major project title |
| H1          |    30px |    700 |        1.15 | Page heading        |
| H2          |    24px |    600 |         1.2 | Section heading     |
| H3          |    18px |    600 |         1.3 | Card heading        |
| H4          |    16px |    600 |         1.3 | Component heading   |
| Body        |    14px |    400 |         1.5 | Standard text       |
| Body Medium |    14px |    500 |         1.5 | Controls            |
| Small       |    12px |    500 |         1.4 | Metadata            |
| Micro       |    11px |    500 |         1.3 | Labels              |
| Score       | 32–40px |    700 |           1 | Virality score      |

---

# 7. Typography Rules

### Headings

Use Ink.

```text
Jürgen Klopp Analysis
```

### Supporting text

Use Ink opacity.

```text
Top clips from your processed sources
```

### Interactive text

Use Nuxt Green.

```text
View all clips →
```

### Never

Use multiple colored headings.

Avoid:

```text
Purple heading
Blue subtitle
Orange badge
Green button
```

CLIPPER should feel visually calm.

---

# 8. Application Shell

There is **no sidebar**.

The primary navigation is a compact horizontal header.

```text
┌─────────────────────────────────────────────────────────────┐
│ CLIPPER   Project ▼     Clips   Sources   Transcript  ... │
│                                      Settings   + Project  │
└─────────────────────────────────────────────────────────────┘
```

---

# 9. Global Header

Height:

```text
64px
```

Horizontal padding:

```text
24px
```

Maximum content width:

```text
1440px
```

Header layout:

```text
[CLIPPER] [Project Selector]        [Clips] [Sources] [Transcript] [Settings] [+ New Project]
```

---

# 10. CLIPPER Logo

The logo consists of:

* Simple play/clip symbol
* `CLIPPER` wordmark

Logo color:

```text
Ink
```

Play symbol:

```text
Nuxt Green
```

Keep the logo minimal.

No gradients.

No shadows.

---

# 11. Project Selector

The project selector sits immediately beside the logo.

Example:

```text
Jürgen Klopp Analysis ▾
```

Dimensions:

```text
Height: 40px
Min width: 160px
Radius: 8px
```

Interaction:

* Hover → subtle Ink border
* Focus → Green outline
* Open → project dropdown

Dropdown options:

```text
Jürgen Klopp Analysis
Joe Rogan Experience
Motivation Hub
+ Create Project
```

---

# 12. Main Navigation

Navigation is horizontal.

Items:

```text
Clips
Sources
Transcript
Settings
```

Active item:

* Ink text
* Nuxt Green underline
* Medium weight

Example:

```text
Clips
─────
```

Do not use filled navigation pills.

---

# 13. Primary CTA

The most important global action:

```text
+ New Project
```

Button:

```text
Background: #00DC82
Text: #0F172A
Height: 40px
Radius: 8px
```

Hover:

```text
Slightly darker green via opacity treatment
```

Avoid gradients.

---

# 14. Main Workspace

The main workspace is the most important screen.

Recommended structure:

```text
┌───────────────────────────────────────────────────────────────┐
│ Header                                                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│ Clips                                                         │
│ Top clips from your sources                                   │
│                                                               │
│ [Search] [Top Clips ▼] [Filters]               [9:16] [Undo] │
│                                                               │
├───────────────────────┬───────────────────────┬───────────────┤
│                       │                       │               │
│ CLIP LIST             │ TRANSCRIPT + VIDEO   │ INTELLIGENCE  │
│                       │                       │               │
│ Clip 96               │ Transcript            │ Score 96     │
│ Clip 93               │                       │               │
│ Clip 91               │       VIDEO           │ Hook 98      │
│ Clip 88               │       9:16            │ Engagement   │
│ Clip 87               │                       │ Value        │
│                       │                       │ Shareability │
│                       │                       │               │
├───────────────────────┴───────────────────────┴───────────────┤
│                                                               │
│ Timeline / Waveform                                           │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

# 15. Workspace Columns

Recommended desktop proportions:

```text
Clip list:      28%
Editor:         48%
Inspector:      24%
```

Alternative fixed sizing:

```text
Clip list:      300px
Inspector:      320px
Center:         flexible
```

---

# 16. Clip List

The clip list displays automatically selected clips.

Each item contains:

```text
[Thumbnail]

The hardest part
isn't losing...

00:00 — 00:45

Hook    Emotional                         96
```

The clip score should be visually prominent but not oversized.

---

# 17. Clip Selection

Selected clip:

```text
Border: 1px solid #00DC82
```

Optional background:

```text
rgba(0, 220, 130, 0.04)
```

Do not use large glowing effects.

---

# 18. Clip Card

Dimensions:

```text
Min height: 96px
Radius: 8px
Padding: 12px
```

Thumbnail:

```text
72 × 72px
Radius: 6px
```

Content:

```text
Title
Time range
Tags
Score
```

Hover:

* Border becomes slightly stronger
* Play action appears

---

# 19. Clip Score

The score is a key differentiator of CLIPPER.

Example:

```text
96
Exceptional
```

The number should use:

```text
32px
700
Ink
```

The active score indicator uses Nuxt Green.

---

# 20. Virality Score

The PRD defines:

```text
Hook Score
Engagement Score
Value Score
Shareability Score
Overall Score
```

These must be visible in the inspector.

Example:

```text
CLIP SCORE

96
Exceptional

────────────────────

Hook Strength       98  ━━━━━━━━━━━
Engagement          95  ━━━━━━━━━━
Value               94  ━━━━━━━━━━
Shareability        92  ━━━━━━━━━━
```

---

# 21. Score Visualization

Use horizontal bars.

Do not use:

* Rainbow charts
* Color-coded traffic lights
* Excessive circular gauges
* Multiple accent colors

Example:

```text
Hook Strength                  98
██████████████████████████████

Engagement                     95
████████████████████████████

Value                          94
████████████████████████████

Shareability                   92
██████████████████████████
```

Inactive track:

```text
rgba(15,23,42,0.08)
```

Active track:

```text
#00DC82
```

---

# 22. Score Explanation

Scores should explain themselves.

Example:

```text
Strong hook with high emotional impact
and strong standalone context.
```

Avoid technical AI jargon.

The user needs to understand **why** a clip was selected.

---

# 23. Clip Tags

Tags communicate detected characteristics.

Examples:

```text
Hook
Emotional
Insightful
Relatable
Teamwork
Value
Motivation
```

Tags use neutral surfaces.

Example:

```text
[ Emotional ]
```

Style:

```text
Font: Poppins
Size: 11–12px
Weight: 500
Background: rgba(15,23,42,0.05)
Text: Ink
Radius: 999px
Padding: 4px 9px
```

Green is reserved for important/active states.

---

# 24. Video Preview

The video is the visual center of CLIPPER.

Aspect ratio:

```text
9:16
```

Target:

```text
1080 × 1920
```

The PRD explicitly requires face-centered vertical rendering.

---

# 25. Preview Container

Desktop preview:

```text
Width: approximately 320–400px
Aspect ratio: 9:16
Radius: 8px
```

The video itself should be visually dominant.

Do not put unnecessary controls around the video.

---

# 26. Hook Title

Hook title appears during the first three seconds.

Position:

```text
Top 15%
```

Maximum:

```text
2 lines
```

Example:

```text
The hardest part
isn't losing...
```

Typography:

```text
Poppins
32–44px
700
```

Important words may use Nuxt Green.

---

# 27. Captions

Captions are generated from word-level Whisper timestamps.

The PRD requires word-synced captions and karaoke/highlight behavior.

Caption system:

```text
Poppins
Bold
High contrast
Centered
Lower third
```

Active word:

```text
Nuxt Green
```

Inactive words:

```text
White
```

Use an Ink outline/shadow for readability.

---

# 28. Caption Templates

Initial templates:

```text
Viral Stroke
Kinetic
```

### Viral Stroke

```text
Font: Poppins
Weight: 700
Position: Center / Bottom
Animation: Typewriter
```

### Kinetic

```text
Font: Poppins
Weight: 700
Position: Center
Animation: Pop-on
```

The PRD defines these two caption styles.

---

# 29. Transcript Panel

Transcript appears next to the video.

Example:

```text
Transcript

00:00   The hardest part isn't losing a game.

00:04   It's preparing your team to bounce back.

00:08   You have to build resilience.

00:12   That's leadership.
```

Clicking a sentence:

1. Moves playhead
2. Highlights sentence
3. Updates preview

---

# 30. Word-Level Transcript

Individual words can be highlighted.

Example:

```text
The [hardest] part isn't losing
```

Active word:

```text
Background: rgba(0,220,130,0.16)
Text: Ink
```

This connects the transcript directly to the caption timeline.

---

# 31. Timeline

The timeline is located underneath the preview/editor.

Required functionality:

* Trim
* Split
* Merge
* Playhead
* Waveform
* Word-synced captions
* Clip boundaries
* Optional B-roll markers

The PRD explicitly defines these editor capabilities.

---

# 32. Timeline Structure

```text
00:00                 00:15                 00:30                 00:45
│─────────────────────│─────────────────────│─────────────────────│

       waveform
░░░░░░░░░░░████████████████████░░░░░░░░░░░░

       ┌───────────────────────────┐
       │       SELECTED CLIP       │
       └───────────────────────────┘

                         │
                       PLAYHEAD
```

---

# 33. Timeline Colors

Selected region:

```text
Nuxt Green
```

Waveform:

```text
Ink with opacity
```

Playhead:

```text
Ink
```

Do not introduce another timeline color.

---

# 34. Trim Controls

Trim handles should be:

```text
8px minimum visual width
44px practical hit area
```

They must be easy to grab.

Hover:

```text
Green
```

Selected:

```text
Green
```

---

# 35. Editor Toolbar

Minimal toolbar:

```text
Split
Delete
Add Marker
```

Additional controls:

```text
Crop
Captions
B-roll
Volume
```

Use icons with labels where appropriate.

Do not create a toolbar containing dozens of icons.

---

# 36. Sources

Sources should be accessible from the horizontal navigation.

Example:

```text
Sources

[ + Add Source ]

Jürgen Klopp Press Conference
YouTube · 1:24:35
Transcribed

Joe Rogan Experience #2068
YouTube · 2:15:30
Transcribed

Motivation Hub Podcast
MP4 · 48:22
Transcribed
```

The PRD supports:

* YouTube
* Direct MP4
* Instagram

as source types.

---

# 37. Add Source

Primary interaction:

```text
+ Add Source
```

Input:

```text
Paste video URL...
```

Actions:

```text
Add Source
```

After adding:

```text
Downloading
```

Then:

```text
Transcribing
```

---

# 38. Processing Experience

Processing should be highly visible.

Pipeline:

```text
Downloading
      ↓
Transcribing
      ↓
Scoring
      ↓
Rendering
      ↓
Done
```

These are the actual pipeline stages specified in the PRD.

---

# 39. Processing Component

Example:

```text
PROCESSING

✓ Downloading
✓ Transcribing
● Scoring
○ Rendering
○ Done

Analyzing viral potential...

━━━━━━━━━━━━━━━━━━━━━━ 65%
```

Active stage:

```text
Nuxt Green
```

Completed:

```text
Ink + check icon
```

Pending:

```text
Ink opacity
```

---

# 40. Real-Time Processing

The frontend receives progress through SSE.

The UI must update:

```text
stage
progress
current clip
total clips
message
preview thumbnail
```

The interface must remain interactive while processing.

The user should be able to:

* Inspect sources
* View completed clips
* Navigate the project
* Cancel where supported

---

# 41. Project Dashboard

The project dashboard should be clean and compact.

Example:

```text
Projects

[Search projects...]                         [+ New Project]


Jürgen Klopp Analysis
12 videos · 245 clips · Updated 2h ago
━━━━━━━━━━━━━━━━━━ 68%


Joe Rogan Experience
8 videos · 156 clips · Updated 5m ago
━━━━━━━━━━ 43%


Elon Musk Talks
6 videos · 89 clips · Updated 1d ago
━━━━━━━━ 25%
```

Avoid large colorful dashboard cards.

---

# 42. Project Creation

Project creation fields:

```text
Project name
Description
Source URLs
Training data
Target platform
Transcription language
```

The PRD defines these project-level concepts.

---

# 43. Project Creation UX

Use a clean multi-step setup.

### Step 1

```text
Create Project

Project name
Description
```

### Step 2

```text
Add Sources

Paste URLs
```

### Step 3

```text
Audience & Style

Describe your audience
Describe viral patterns
```

### Step 4

```text
Output

TikTok
Reels
Shorts

Language
```

### Final

```text
Create Project
```

---

# 44. Training Data

Training data should be presented as a helpful content field rather than an "AI prompt."

Label:

```text
Audience & Content Guidelines
```

Placeholder:

```text
Describe your audience, tone, viral patterns,
topics and content style...
```

This maps directly to the project's `training_data` field and viral pattern generation process.

---

# 45. Platform Selector

Platforms:

```text
TikTok
Reels
Shorts
```

Use segmented controls.

Selected:

```text
Border: Nuxt Green
Text: Ink
```

Unselected:

```text
Border: Ink opacity
Text: Ink
```

No platform-specific brand colors.

---

# 46. Transcription Language

Default:

```text
English
```

Users can select:

```text
English
Spanish
German
French
...
```

The PRD specifies ISO 639-1 language selection and English as the default.

---

# 47. Export

Export should be available from:

* Workspace
* Editor
* Batch selection

Primary action:

```text
Export Clip
```

Batch:

```text
Export Selected
```

Supported presets:

```text
TikTok
Reels
Shorts
```

Quality:

```text
High
Medium
```

These correspond to the PRD export API.

---

# 48. Export Dropdown

Example:

```text
Export Clip ▾
```

Dropdown:

```text
Export as TikTok
Export as Reels
Export as Shorts
──────────────
Export Settings
```

Keep the dropdown simple.

---

# 49. Buttons

## Primary

```text
Background: #00DC82
Text: #0F172A
Height: 40px
Radius: 8px
Font: Poppins 14px 600
```

Examples:

```text
+ New Project
Add Source
Render Clip
Export Clip
```

---

## Secondary

```text
Background: white
Border: rgba(15,23,42,0.12)
Text: #0F172A
```

Examples:

```text
Cancel
Preview
Edit
Filters
```

---

## Text Button

No background.

```text
Color: #0F172A
```

Hover:

```text
Color: #00DC82
```

---

# 50. Button Dimensions

```text
Small:    32px
Default:  40px
Large:    48px
```

Horizontal padding:

```text
12–20px
```

Radius:

```text
8px
```

Do not use excessive pill-shaped buttons.

---

# 51. Inputs

Height:

```text
40px
```

Radius:

```text
8px
```

Background:

```text
white
```

Border:

```text
rgba(15,23,42,0.12)
```

Text:

```text
Ink
```

Focus:

```text
Nuxt Green
```

Example:

```text
┌──────────────────────────────────────┐
│ Search clips...                    🔍 │
└──────────────────────────────────────┘
```

---

# 52. Textareas

Minimum height:

```text
120px
```

Padding:

```text
12px
```

Radius:

```text
8px
```

Use for:

* Project description
* Audience guidelines
* Training data

---

# 53. Cards

Cards should feel like containers, not floating objects.

```text
Background: white
Border: rgba(15,23,42,0.08)
Radius: 12px
Shadow: none
```

Optional subtle shadow:

```text
0 1px 3px rgba(15,23,42,0.04)
```

Avoid:

```text
Large shadows
Glows
Gradients
Glassmorphism
```

---

# 54. Borders

Default:

```text
1px solid rgba(15,23,42,0.08)
```

Interactive:

```text
1px solid rgba(15,23,42,0.16)
```

Active:

```text
1px solid #00DC82
```

---

# 55. Border Radius

Use a restrained radius system.

```text
4px   Micro
8px   Controls
12px  Cards
16px  Large containers
```

Default application radius:

```text
8px
```

Avoid extremely rounded SaaS components.

---

# 56. Spacing System

Use an 8px grid.

```text
4
8
12
16
24
32
48
64
96
```

Recommended:

```text
Page padding:       24px
Card padding:       16–20px
Section spacing:    32px
Major spacing:      48px
Header:             64px
```

---

# 57. Iconography

Use a consistent outline icon set.

Recommended size:

```text
16px — inline
18px — controls
20px — buttons
24px — major actions
```

Icons should use:

```text
Ink
```

Active icons:

```text
Nuxt Green
```

Do not use different icon colors for different meanings.

---

# 58. Icon Examples

Required icons:

```text
Play
Pause
Search
Settings
Plus
Chevron Down
Chevron Right
Upload
Download
Link
Scissors
Crop
Captions
Audio
Trash
Undo
Redo
Filter
More
Check
```

---

# 59. Icon Rules

Never rely exclusively on icons for critical actions.

Bad:

```text
[ ✂ ]
```

Better:

```text
[ ✂ Split ]
```

Icon-only buttons are acceptable for:

* Undo
* Redo
* More
* Fullscreen
* Play
* Pause
* Close

Use tooltips.

---

# 60. Modals

Modal width:

```text
480–640px
```

Radius:

```text
16px
```

Structure:

```text
Title

Description

Fields

──────────────

Cancel          Create Project
```

No excessive decoration.

---

# 61. Dropdowns

Dropdown:

```text
Background: white
Border: rgba(15,23,42,0.10)
Radius: 8px
```

Item:

```text
Height: 40px
Padding: 8px 12px
```

Hover:

```text
rgba(15,23,42,0.04)
```

Selected:

```text
Nuxt Green indicator
```

---

# 62. Loading States

Avoid generic spinning loaders whenever possible.

Prefer:

```text
Progress
Skeleton
Stage indicator
```

Example:

```text
Transcribing

██████████████░░░░░░ 68%

Processing words...
```

---

# 63. Empty States

## No Projects

```text
Create your first project

Turn long-form videos into short clips
automatically.

[ + New Project ]
```

## No Sources

```text
Add a source video

Paste a YouTube or direct video URL
to begin.

[ + Add Source ]
```

## No Clips

```text
No clips generated yet

Process your sources to discover
high-potential moments.

[ Process Sources ]
```

---

# 64. Error States

Do not expose technical errors by default.

Bad:

```text
HTTP 500
Pipeline exception
```

Better:

```text
Processing stopped

We couldn't process this source.
Check the URL and try again.

[ Retry ] [ Remove Source ]
```

Technical details:

```text
View details
```

---

# 65. Success States

Keep success understated.

Example:

```text
✓ Clip exported
```

Use:

```text
Ink + icon
```

Do not introduce a new green/blue success palette.

Nuxt Green is already the active brand color.

---

# 66. Motion

Motion should be subtle.

```text
Fast:   100–150ms
Normal: 150–200ms
Modal:  200ms
```

Use:

* Fade
* Small translation
* Scale 0.98 → 1
* Progress interpolation

Avoid:

* Bounce
* Elastic animations
* Large transitions
* Decorative movement

---

# 67. Accessibility

Target:

```text
WCAG 2.2 AA
```

Requirements:

* Keyboard navigation
* Visible focus state
* Minimum 44px touch targets where practical
* Accessible labels
* Screen-reader friendly controls
* Caption readability
* No color-only status communication
* Focus trapping in dialogs
* Escape closes temporary dialogs
* Accessible timeline controls

---

# 68. Responsive Design

## Desktop

```text
≥ 1280px
```

Use the complete three-column workspace.

---

## Tablet

```text
768–1279px
```

Collapse:

```text
Clip list → drawer
Inspector → drawer
```

Keep:

```text
Video preview
Timeline
Primary actions
```

---

## Mobile

```text
< 768px
```

Do not attempt to replicate the complete desktop editor.

Prioritize:

```text
Video
Score
Transcript
Basic editing
Export
```

The mobile experience should be a **review and publishing interface**, not a full professional timeline editor.

---

# 69. Dashboard Metrics

Project-level metrics can be shown at the bottom of the project overview.

Example:

```text
128                  802                24.5h              12.4M
Total Videos         Total Clips       Transcribed        Potential Views
```

Keep metrics monochromatic.

Only the most important value may use Nuxt Green.

---

# 70. Information Hierarchy

Every screen follows:

```text
1. Page / Project
2. Current task
3. Primary content
4. Supporting intelligence
5. Secondary actions
```

For the editor:

```text
Video
↓
Transcript
↓
Timeline
↓
Virality score
↓
Editing controls
↓
Export
```

---

# 71. Workspace Header Example

```text
CLIPPER

Jürgen Klopp Analysis ▾

Clips    Sources    Transcript    Settings

                                      + New Project
```

Under it:

```text
Clips

Top clips from your sources
```

Then:

```text
[ Search clips... ] [ Top Clips ▾ ] [ Filters ]      [ 9:16 ]
```

---

# 72. Recommended Workspace

```text
┌──────────────────────────────────────────────────────────────────┐
│ CLIPPER   Project ▾   Clips  Sources  Transcript  Settings       │
│                                               + New Project       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Clips                                                            │
│ Top clips from your sources                                      │
│                                                                  │
│ [Search]       [Top Clips ▼] [Filters]              [9:16]       │
│                                                                  │
├────────────────────┬──────────────────────────┬──────────────────┤
│ TOP CLIPS          │ TRANSCRIPT               │ CLIP SCORE       │
│                    │                          │                  │
│ ┌───────────────┐  │ 00:00                    │       96         │
│ │ thumbnail     │  │ The hardest part         │   Exceptional    │
│ │ The hardest   │  │ isn't losing a game.     │                  │
│ │ part...     96│  │                          │ Hook       98    │
│ └───────────────┘  │ 00:04                    │ Engagement 95    │
│                    │ It's preparing your      │ Value      94    │
│ ┌───────────────┐  │ team to bounce back.     │ Shareability 92 │
│ │ thumbnail     │  │                          │                  │
│ │ We don't... 93│  │                          │ Strong hook with │
│ └───────────────┘  │                          │ high emotional   │
│                    │       ┌─────────┐        │ impact.          │
│ ┌───────────────┐  │       │         │        │                  │
│ │ thumbnail     │  │       │  VIDEO  │        │                  │
│ │ What makes 91 │  │       │  9:16   │        │                  │
│ └───────────────┘  │       │         │        │                  │
│                    │       └─────────┘        │                  │
├────────────────────┴──────────────────────────┴──────────────────┤
│                                                                  │
│ 00:00              00:15                00:30              00:45│
│ ──────── waveform ────────████████████████───────              │
│                          │                                       │
│                        PLAYHEAD                                  │
│                                                                  │
│ Split     Delete     Add Marker                  Export Clip     │
└──────────────────────────────────────────────────────────────────┘
```

---

# 73. Project Workflow

The intended UX is:

```text
Create Project
      ↓
Add Sources
      ↓
Download
      ↓
Transcribe
      ↓
Analyze
      ↓
Select Top Clips
      ↓
Review
      ↓
Edit
      ↓
Render
      ↓
Export
```

---

# 74. AI Visibility

CLIPPER should not constantly advertise AI.

Instead of:

```text
✨ AI MAGIC
```

Use:

```text
Analyze clips
```

Instead of:

```text
🤖 AI GENERATED
```

Use:

```text
Auto-selected
```

Instead of:

```text
AI POWERED VIRAL SCORE
```

Use:

```text
Virality Score
```

The product's intelligence should be visible through useful results, not marketing language.

---

# 75. Minimal-AI Philosophy

The product architecture intentionally minimizes expensive AI usage.

The UX should reflect this.

The user primarily interacts with:

```text
Transcription
Heuristics
Scores
Patterns
Selected clips
```

The PRD specifies heuristic scoring for all segments and LLM ranking only for the top 15–20 candidates.

Therefore the UI should avoid making every interaction look like an LLM operation.

---

# 76. Component Naming

Recommended Vue/Nuxt component architecture:

```text
components/
└── clipper/
    ├── ClipperHeader.vue
    ├── ProjectSelector.vue
    ├── ProjectManager.vue
    ├── ProjectSetup.vue
    ├── SourceList.vue
    ├── SourceCard.vue
    ├── ProcessingProgress.vue
    ├── ClipList.vue
    ├── ClipCard.vue
    ├── ClipPreview.vue
    ├── ViralityScore.vue
    ├── ScoreMetric.vue
    ├── TranscriptPanel.vue
    ├── TranscriptTimeline.vue
    ├── ClipEditor.vue
    ├── EditorToolbar.vue
    ├── CaptionTrack.vue
    ├── CropControls.vue
    ├── ExportPanel.vue
    ├── PlatformSelector.vue
    └── EmptyState.vue
```

---

# 77. Design Tokens

Use the following tokens as the source of truth.

```css
:root {
  /* Brand */
  --clipper-green: #00DC82;
  --clipper-ink: #0F172A;

  /* Surface */
  --clipper-white: #FFFFFF;

  /* Ink opacity */
  --ink-04: rgba(15, 23, 42, 0.04);
  --ink-06: rgba(15, 23, 42, 0.06);
  --ink-08: rgba(15, 23, 42, 0.08);
  --ink-10: rgba(15, 23, 42, 0.10);
  --ink-12: rgba(15, 23, 42, 0.12);
  --ink-16: rgba(15, 23, 42, 0.16);
  --ink-35: rgba(15, 23, 42, 0.35);
  --ink-60: rgba(15, 23, 42, 0.60);

  /* Green opacity */
  --green-04: rgba(0, 220, 130, 0.04);
  --green-08: rgba(0, 220, 130, 0.08);
  --green-16: rgba(0, 220, 130, 0.16);

  /* Typography */
  --font-family: "Poppins", sans-serif;

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-7: 32px;
  --space-8: 48px;
  --space-9: 64px;
  --space-10: 96px;

  /* Layout */
  --header-height: 64px;
  --content-max-width: 1440px;
  --clip-list-width: 300px;
  --inspector-width: 320px;

  /* Motion */
  --transition-fast: 150ms ease;
  --transition-normal: 200ms ease;
}
```

---

# 78. Tailwind Mapping

If using Tailwind:

```js
colors: {
  clipper: {
    green: '#00DC82',
    ink: '#0F172A',
  }
}
```

Use opacity modifiers instead of introducing additional colors.

Examples:

```html
bg-clipper-green
text-clipper-ink
border-clipper-ink/10
text-clipper-ink/60
bg-clipper-green/5
bg-clipper-green/10
```

---

# 79. Global CSS

```css
html,
body {
  font-family: "Poppins", sans-serif;
  color: #0F172A;
  background: #FFFFFF;
}

button,
input,
textarea,
select {
  font-family: inherit;
}

button {
  transition:
    background-color 150ms ease,
    border-color 150ms ease,
    opacity 150ms ease;
}

:focus-visible {
  outline: 2px solid #00DC82;
  outline-offset: 2px;
}
```

---

# 80. Do Not Use

The following are explicitly prohibited from the visual system:

```text
❌ Sidebar navigation
❌ Gradients
❌ Purple
❌ Blue
❌ Orange
❌ Red status colors
❌ Rainbow charts
❌ Glassmorphism
❌ Excessive shadows
❌ Excessive rounded pills
❌ Multiple font families
❌ Decorative AI graphics
❌ Neon effects
❌ Large glowing score gauges
❌ Overly colorful badges
❌ Dense icon-only toolbars
```

---

# 81. Visual Quality Checklist

Before considering a screen complete:

### Typography

```text
□ Poppins everywhere
□ Correct font weights
□ Clear heading hierarchy
□ Comfortable line height
```

### Color

```text
□ Only Nuxt Green + Ink as brand colors
□ Green used sparingly
□ No unexpected accent colors
□ Status doesn't depend on color alone
```

### Layout

```text
□ No sidebar
□ Generous whitespace
□ Strong alignment
□ Consistent 8px spacing grid
□ Clear content hierarchy
```

### Components

```text
□ 8px default control radius
□ 12px card radius
□ Subtle borders
□ Minimal shadows
□ Consistent controls
```

### Video

```text
□ 9:16 preview
□ Face-centered composition
□ Hook title visible
□ Word-synced captions
□ Timeline accessible
```

### Intelligence

```text
□ Overall virality score visible
□ Hook score
□ Engagement score
□ Value score
□ Shareability score
```

### Workflow

```text
□ Sources accessible
□ Processing state visible
□ Clips selectable
□ Editor accessible
□ Export obvious
```

---

# 82. Final Product Personality

CLIPPER should feel like:

```text
Stripe
    +
Professional video editor
    +
Creator analytics
    +
Nuxt ecosystem
```

But with its own identity.

The final visual impression should be:

> **Clean. Intelligent. Fast. Precise. Professional.**

The interface should never compete with the video.

The video is the content.

The transcript explains it.

The score explains its potential.

The editor makes it better.

The export button gets it published.

---

# 83. Final UX Rule

If a UI element does not help the user:

```text
Find a good clip
Understand why it is good
Edit it
Export it
```

remove it.

**CLIPPER should always maximize signal and minimize interface noise.**
