<script lang="ts" setup>
/**
 * ElementsPanel — text presets (system subtitle templates from
 * GET /api/settings) + shape presets. Clicking a preset inserts a 3s clip
 * at the playhead on the topmost elements track via `elah.addClipFree`.
 *
 * Contract (frozen by the editor shell):
 *   props:  { elah }
 *   emits: { inserted: [name: string] }
 */
import { secondsToFrames } from "@elah/core"
import type { ShapeVariant } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()
const emit = defineEmits<{ inserted: [name: string] }>()

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

/** Insert a text clip styled after the chosen subtitle template. */
const insertText = (t: SubtitleTemplate) => {
  const stage = props.elah.project.value.stage
  const fontSize = Math.min(160, Math.max(32, Math.round((t.fontsize ?? 20) * stage.height / 288 / 7)))
  const y = t.position?.includes("center,center") ? 0.5 : t.position?.includes("top") ? 0.15 : 0.85
  const clip = props.elah.addClipFree({
    trackId: props.elah.topElementsTrackId(),
    type: "text",
    startFrame: props.elah.currentFrame.value,
    durationFrames: Math.max(1, secondsToFrames(3, fps.value)),
    name: t.label,
    text: {
      content: "Edit me",
      fontSize,
      color: t.color,
      fontFamily: "Poppins",
      fontWeight: "bold",
      textAlign: "center",
    },
    transform: { x: 0.5, y, scale: 1, rotation: 0, anchor: { x: 0.5, y: 0.5 } },
  })
  if (!clip) return
  props.elah.updateClip(clip.id, clip.trackId, { textAnimation: { in: "fade", out: "fade", durationFrames: 8 } })
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
        <button
          v-for="t in templates"
          :key="t.value"
          type="button"
          class="block w-full rounded border border-transparent px-2 py-2 text-left transition-colors hover:border-clipper-ink/10 hover:bg-neutral-100 dark:hover:border-white/10 dark:hover:bg-neutral-800"
          :title="t.description"
          @click="insertText(t)"
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
