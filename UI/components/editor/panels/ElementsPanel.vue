<script lang="ts" setup>
/**
 * ElementsPanel — text presets (system subtitle templates from
 * GET /api/settings) + shape presets.
 *
 * - No text selected: clicking a preset inserts a 3s clip at the playhead
 *   on the topmost elements track via `elah.addClipFree`.
 * - Text clip(s) selected: clicking a preset restyles the selection
 *   in place (one undo entry) instead of inserting.
 * - The brush button on a preset row applies that preset to every
 *   auto-generated caption clip ("Caption*") on the timeline.
 *
 * Contract (frozen by the editor shell):
 *   props:  { elah }
 *   emits: { inserted: [name: string], applied: [name: string, count: number] }
 */
import { secondsToFrames } from "@elah/core"
import type { ShapeVariant, Transform } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()
const emit = defineEmits<{
  inserted: [name: string]
  applied: [name: string, count: number]
}>()

const API = useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080"
const fps = computed(() => props.elah.project.value.fps)

// =====================================================================
// Text presets (GET /api/settings → data.subtitleTemplates.options)
// =====================================================================
interface SubtitleTemplate {
  value: string
  label: string
  description?: string
  color?: string
  stroke_color?: string
  stroke_width?: number
  fontsize?: number
  position?: string
  shadow_color?: string
  shadow_blur?: number
  shadow_offset_x?: number
  shadow_offset_y?: number
}

const templates = ref<SubtitleTemplate[]>([])

onMounted(async () => {
  try {
    const res = await $fetch<{ status?: string; data?: { subtitleTemplates?: { current?: string; options?: SubtitleTemplate[] } } }>(
      `${API}/api/settings`,
    )
    templates.value = res.data?.subtitleTemplates?.options ?? []
  } catch (e) {
    console.error("[ElementsPanel] failed to load subtitle templates", e)
  }
})

/** Resolve a subtitle template to concrete clip style fields. */
interface TemplateStyle {
  fontSize: number
  y: number
  color: string
  fontFamily: string
  fontWeight: "bold"
  textAlign: "center"
  strokeColor?: string
  strokeWidth?: number
  textShadowColor?: string
  textShadowBlur?: number
  textShadowOffsetX?: number
  textShadowOffsetY?: number
}
const templateStyle = (t: SubtitleTemplate): TemplateStyle => {
  const stage = props.elah.project.value.stage
  const fontSize = Math.min(160, Math.max(32, Math.round((t.fontsize ?? 20) * stage.height / 288 / 7)))
  const y = t.position?.includes("center,center") ? 0.5 : t.position?.includes("top") ? 0.15 : 0.85
  const strokeWidth = Number(t.stroke_width ?? 0)
  // Shadow px are authored at 1920px frame height (settings.py) — scale to
  // the stage so captions keep their proportions on any aspect ratio.
  // Missing fields fall back to a subtle stroke-colored drop shadow so the
  // applied clip matches the preset row's advertised (shadowed) look.
  const shadowScale = stage.height / 1920
  const shadowBlur = t.shadow_blur !== undefined
    ? Math.max(0, t.shadow_blur * shadowScale)
    : (strokeWidth > 0 ? 2 * shadowScale : 0)
  return {
    fontSize,
    y,
    color: t.color ?? "#ffffff",
    fontFamily: "Poppins",
    fontWeight: "bold" as const,
    textAlign: "center" as const,
    ...(strokeWidth > 0 && t.stroke_color
      ? { strokeColor: t.stroke_color, strokeWidth }
      : {}),
    ...(t.shadow_color ?? (t.stroke_color && strokeWidth > 0 ? t.stroke_color : undefined)
      ? {
          textShadowColor: t.shadow_color ?? t.stroke_color as string,
          textShadowBlur: shadowBlur,
          textShadowOffsetX: (t.shadow_offset_x ?? 0) * shadowScale,
          textShadowOffsetY: (t.shadow_offset_y ?? (y === 0.5 ? 0 : 2)) * shadowScale,
        }
      : {}),
  }
}

/** Text clips currently selected on the timeline. */
const selectedTextClips = () => {
  const out: { id: string; trackId: string }[] = []
  for (const id of props.elah.selectedClipIds.value) {
    const found = props.elah.findClip(id)
    if (found && found.clip.type === "text") out.push({ id, trackId: found.trackId })
  }
  return out
}

/** Auto-generated caption clips ("Caption*") across all tracks. */
const captionClips = computed(() => {
  const out: { id: string; trackId: string }[] = []
  const byTrack = props.elah.clipsByTrack.value as Record<string, { id: string; type: string; name: string }[]>
  for (const [trackId, clips] of Object.entries(byTrack)) {
    for (const c of clips ?? []) {
      if (c.type === "text" && c.name.startsWith("Caption")) out.push({ id: c.id, trackId })
    }
  }
  return out
})

/** Restyle existing text clips in place (single undo entry). */
const applyTemplate = (t: SubtitleTemplate, targets: { id: string; trackId: string }[]) => {
  if (!targets.length) return 0
  const style = templateStyle(t)
  let applied = 0
  props.elah.engine.batch(() => {
    for (const target of targets) {
      const found = props.elah.findClip(target.id)
      if (!found || found.clip.type !== "text") continue
      const prevTf: Transform = found.clip.transform ?? {
        x: 0.5, y: style.y, scale: 1, rotation: 0, anchor: { x: 0.5, y: 0.5 },
      }
      props.elah.updateClip(target.id, target.trackId, {
        color: style.color,
        fontSize: style.fontSize,
        fontFamily: style.fontFamily,
        fontWeight: style.fontWeight,
        textAlign: style.textAlign,
        transform: { ...prevTf, y: style.y },
        ...(style.strokeColor ? { strokeColor: style.strokeColor, strokeWidth: style.strokeWidth } : {}),
        ...(style.textShadowColor
          ? {
              textShadowColor: style.textShadowColor,
              textShadowBlur: style.textShadowBlur ?? 0,
              textShadowOffsetX: style.textShadowOffsetX ?? 0,
              textShadowOffsetY: style.textShadowOffsetY ?? 0,
            }
          : {}),
      })
      applied += 1
    }
  }, `Apply preset ${t.label}`)
  return applied
}

const hasTextSelection = computed(() => selectedTextClips().length > 0)
const selectedTextHint = (t: SubtitleTemplate) =>
  `${t.description ?? t.label}${hasTextSelection.value ? " — click to restyle the selected text" : " — click to insert"}`

/** Preset click: restyle the text selection, or insert when nothing is selected. */
const onPresetClick = (t: SubtitleTemplate) => {
  const targets = selectedTextClips()
  if (targets.length) {
    const applied = applyTemplate(t, targets)
    if (applied) emit("applied", t.label, applied)
    return
  }
  insertText(t)
}

/** Brush button: apply the preset to every caption clip. */
const applyToAllCaptions = (t: SubtitleTemplate) => {
  const applied = applyTemplate(t, captionClips.value)
  if (applied) emit("applied", `${t.label} (captions)`, applied)
}

/** Insert a text clip styled after the chosen subtitle template. */
const insertText = (t: SubtitleTemplate) => {
  const style = templateStyle(t)
  const clip = props.elah.addClipFree({
    trackId: props.elah.topElementsTrackId(),
    type: "text",
    startFrame: props.elah.currentFrame.value,
    durationFrames: Math.max(1, secondsToFrames(3, fps.value)),
    name: t.label,
    text: {
      content: "Edit me",
      fontSize: style.fontSize,
      color: style.color,
      fontFamily: style.fontFamily,
      fontWeight: style.fontWeight,
      textAlign: style.textAlign,
    },
    transform: { x: 0.5, y: style.y, scale: 1, rotation: 0, anchor: { x: 0.5, y: 0.5 } },
  })
  if (!clip) return
  props.elah.updateClip(clip.id, clip.trackId, {
    textAnimation: { in: "fade", out: "fade", durationFrames: 8 },
    ...(style.strokeColor ? { strokeColor: style.strokeColor, strokeWidth: style.strokeWidth } : {}),
    ...(style.textShadowColor
      ? {
          textShadowColor: style.textShadowColor,
          textShadowBlur: style.textShadowBlur ?? 0,
          textShadowOffsetX: style.textShadowOffsetX ?? 0,
          textShadowOffsetY: style.textShadowOffsetY ?? 0,
        }
      : {}),
  })
  emit("inserted", t.label)
}

// =====================================================================
// Shape presets
// =====================================================================
const SHAPES: { label: string; icon: string; kind: ShapeVariant }[] = [
  { label: "Rectangle", icon: "ph:square", kind: "rect" },
  { label: "Circle", icon: "ph:circle", kind: "circle" },
  { label: "Triangle", icon: "ph:triangle", kind: "triangle" },
]

/** Insert a green shape clip centered on the stage. */
const insertShape = (shape: { label: string; kind: ShapeVariant }) => {
  const clip = props.elah.addClipFree({
    trackId: props.elah.topElementsTrackId(),
    type: "shape",
    startFrame: props.elah.currentFrame.value,
    durationFrames: Math.max(1, secondsToFrames(3, fps.value)),
    name: shape.label,
    transform: { x: 0.5, y: 0.5, scale: 0.4, rotation: 0, anchor: { x: 0.5, y: 0.5 } },
    shape: { shapeKind: shape.kind },
  })
  if (!clip) return
  props.elah.updateClip(clip.id, clip.trackId, { shapeFill: "#00DC82" })
  emit("inserted", "Shape")
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <!-- Header -->
    <div class="flex items-center gap-2 border-b border-clipper-ink/08 dark:border-white/08 px-3 py-2.5">
      <Icon name="ph:text-aa" size="14" class="text-clipper-green" />
      <span class="text-sm font-semibold text-clipper-ink dark:text-white">Elements</span>
    </div>

    <div class="min-h-0 flex-1 space-y-4 overflow-y-auto p-3">
      <!-- Text presets -->
      <section class="space-y-1.5">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-clipper-ink/50 dark:text-white/50">Text presets</p>
        <n-empty
          v-if="templates.length === 0"
          size="small"
          class="py-6"
          description="No text templates loaded"
        />
        <div
          v-for="t in templates"
          :key="t.value"
          class="group flex items-center gap-1 rounded border border-transparent transition-colors hover:border-clipper-ink/10 hover:bg-neutral-100 dark:hover:border-white/10 dark:hover:bg-neutral-800"
        >
          <button
            type="button"
            class="min-w-0 flex-1 px-2 py-2 text-left"
            :title="selectedTextHint(t)"
            @click="onPresetClick(t)"
          >
            <span
              class="block truncate font-bold text-sm"
              :style="{ color: t.color || '#ffffff', textShadow: `0 1px 2px ${t.stroke_color || '#000'}, 0 0 1px ${t.stroke_color || '#000'}` }"
            >{{ t.label }}</span>
            <span
              v-if="t.description"
              class="mt-0.5 block truncate text-[10px] text-clipper-ink/50 dark:text-white/50"
            >{{ t.description }}</span>
          </button>
          <n-tooltip v-if="captionClips.length" trigger="hover">
            <template #trigger>
              <n-button
                quaternary
                size="tiny"
                class="mr-1 shrink-0 opacity-0 group-hover:opacity-100 focus:opacity-100"
                aria-label="Apply preset to all captions"
                @click="applyToAllCaptions(t)"
              >
                <template #icon><Icon name="ph:paint-brush" size="14" /></template>
              </n-button>
            </template>
            Apply "{{ t.label }}" to all {{ captionClips.length }} caption(s)
          </n-tooltip>
        </div>
      </section>

      <!-- Shapes -->
      <section class="space-y-1.5">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-clipper-ink/50 dark:text-white/50">Shapes</p>
        <div class="flex gap-2">
          <n-button
            v-for="s in SHAPES"
            :key="s.kind"
            size="small"
            class="flex-1"
            @click="insertShape(s)"
          >
            <template #icon><Icon :name="s.icon" size="14" /></template>
            {{ s.label }}
          </n-button>
        </div>
      </section>
    </div>
  </div>
</template>
