<script lang="ts" setup>
/**
 * TimelineControls — bottom toolbar of the timeline:
 * track + clip tools on the left, zoom / fit on the right.
 * Zoom state lives in the parent (pixelsPerFrame, v-model style) so the
 * timeline canvas and this bar always share one source of truth.
 */
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor; pixelsPerFrame: number }>()
const emit = defineEmits<{ "update:pixelsPerFrame": [v: number]; fit: [] }>()

// ---- Zoom: logarithmic slider mapping (2..60 px/frame) ----
const ZOOM_MIN = 2
const ZOOM_MAX = 60
const sliderToZoom = (v: number) =>
  Math.exp(Math.log(ZOOM_MIN) + v * (Math.log(ZOOM_MAX) - Math.log(ZOOM_MIN)))
const zoomToSlider = (z: number) =>
  (Math.log(z) - Math.log(ZOOM_MIN)) / (Math.log(ZOOM_MAX) - Math.log(ZOOM_MIN))
const clampZoom = (v: number) => Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.round(v)))

const zoomSlider = computed<number>({
  get: () => zoomToSlider(props.pixelsPerFrame),
  set: (v: number | null) => {
    emit("update:pixelsPerFrame", clampZoom(sliderToZoom(typeof v === "number" ? v : 0)))
  },
})
const nudgeZoom = (delta: number) => {
  const s = Math.min(1, Math.max(0, zoomToSlider(props.pixelsPerFrame) + delta))
  emit("update:pixelsPerFrame", clampZoom(sliderToZoom(s)))
}

// ---- Add track dropdown ----
const addTrackOptions = [
  { label: "Audio Track", key: "audio" },
  { label: "Text Track", key: "elements" },
]
const onAddTrack = (key: string | number) => {
  const kind = key === "audio" ? ("audio" as const) : ("elements" as const)
  const n = props.elah.tracks.value.filter(t => t.kind === kind).length + 1
  props.elah.addTrack(kind, kind === "audio" ? `Audio ${n}` : `Elements ${n}`)
}

// ---- Clip tools (all mutations funnel through the elah engine) ----
const hasSelection = computed(() => !!props.elah.selectedClip.value)

const onSplit = () => {
  const clip = props.elah.selectedClip.value
  if (!clip) return
  try {
    props.elah.splitAtPlayhead(clip.id, clip.trackId)
  } catch (e) {
    console.warn("[elah] split failed", e)
  }
}
const onDuplicate = () => {
  try {
    props.elah.duplicateSelected()
  } catch (e) {
    console.warn("[elah] duplicate failed", e)
  }
}
const onDelete = () => {
  try {
    props.elah.removeSelectedClips()
  } catch (e) {
    console.warn("[elah] delete failed", e)
  }
}
</script>

<template>
  <div class="h-10 flex items-center justify-between px-3 border-t border-clipper-ink/10 dark:border-white/10 bg-white dark:bg-neutral-900">
    <!-- Left — track + clip tools -->
    <div class="flex items-center gap-1">
      <n-dropdown :options="addTrackOptions" trigger="click" @select="onAddTrack">
        <n-button size="tiny" quaternary title="Add a track">
          <template #icon><Icon name="ph:plus" size="14" /></template>
          Add Track
          <Icon name="ph:caret-down" size="12" class="ml-0.5" />
        </n-button>
      </n-dropdown>

      <span class="w-px h-5 bg-clipper-ink/10 dark:bg-white/10 mx-1" />

      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary :disabled="!hasSelection" @click="onSplit">
            <template #icon><Icon name="ph:scissors" size="14" /></template>
            Split
          </n-button>
        </template>
        Split at playhead (S)
      </n-tooltip>
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary circle :disabled="!hasSelection" @click="onDuplicate">
            <template #icon><Icon name="ph:copy" size="14" /></template>
          </n-button>
        </template>
        Duplicate clip
      </n-tooltip>
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary circle :disabled="!hasSelection" @click="onDelete">
            <template #icon><Icon name="ph:trash" size="14" /></template>
          </n-button>
        </template>
        Delete clip
      </n-tooltip>
    </div>

    <!-- Right — zoom, fit -->
    <div class="flex items-center gap-1.5">
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary circle title="Zoom out" @click="nudgeZoom(-0.08)">
            <template #icon><Icon name="ph:minus" size="14" /></template>
          </n-button>
        </template>
        Zoom out
      </n-tooltip>
      <n-slider
        v-model:value="zoomSlider"
        class="w-28"
        :min="0"
        :max="1"
        :step="0.001"
        :tooltip="false"
      />
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary circle title="Zoom in" @click="nudgeZoom(0.08)">
            <template #icon><Icon name="ph:plus" size="14" /></template>
          </n-button>
        </template>
        Zoom in
      </n-tooltip>
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary @click="emit('fit')">
            <template #icon><Icon name="ph:frame-corners" size="14" /></template>
            Fit
          </n-button>
        </template>
        Zoom to fit timeline
      </n-tooltip>
    </div>
  </div>
</template>
