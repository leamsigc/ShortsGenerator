<script lang="ts" setup>
/**
 * TranscriptTimeline — word-synced timeline with draggable trim handles.
 * Colors: waveform ink/opacity, selected region Nuxt Green, playhead Ink.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
import type { WordTimestamp } from "~/stores/ClipperStore"

const props = defineProps<{
  words: WordTimestamp[]
  clipStart: number
  clipEnd: number
  currentTime: number
  videoDuration: number
}>()

const emit = defineEmits<{
  (e: "seek", time: number): void
  (e: "updateStart", time: number): void
  (e: "updateEnd", time: number): void
}>()

const timelineEl = ref<HTMLElement | null>(null)
const dragging = ref<null | "start" | "end" | "playhead">(null)

const duration = computed(() => props.videoDuration || Math.max(props.clipEnd, 1))
const pct = (time: number) => `${Math.min(100, Math.max(0, (time / duration.value) * 100))}%`

const visibleWords = computed(() =>
  props.words.filter(w => w.end > props.clipStart && w.start < props.clipEnd).slice(0, 400)
)

const timeFromEvent = (event: PointerEvent | MouseEvent): number => {
  if (!timelineEl.value) return 0
  const rect = timelineEl.value.getBoundingClientRect()
  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width))
  return ratio * duration.value
}

const onDown = (mode: "start" | "end" | "playhead") => (event: PointerEvent) => {
  event.preventDefault()
  dragging.value = mode
  if (mode === "playhead") emit("seek", timeFromEvent(event))
}
const onMove = (event: PointerEvent) => {
  const mode = dragging.value
  if (!mode) return
  const time = timeFromEvent(event)
  if (mode === "start") emit("updateStart", Math.min(time, props.clipEnd - 1))
  else if (mode === "end") emit("updateEnd", Math.max(time, props.clipStart + 1))
  else emit("seek", time)
}
const onUp = () => { dragging.value = null }

const fmt = (t: number) => `${Math.floor(t / 60)}:${(Math.floor(t % 60)).toString().padStart(2, "0")}`
</script>

<template>
  <div class="space-y-2">
    <div class="flex items-center justify-between text-xs text-clipper-ink/50 dark:text-white/50 tabular-nums px-1">
      <span>{{ fmt(clipStart) }}</span>
      <span class="text-clipper-ink/35 dark:text-white/40">Drag handles to trim · click to seek</span>
      <span>{{ fmt(clipEnd) }}</span>
    </div>

    <div
      ref="timelineEl"
      class="relative h-14 bg-neutral-100 dark:bg-neutral-800 rounded-lg border border-clipper-ink/12 dark:border-white/10 select-none cursor-crosshair overflow-hidden"
      @pointerdown="onDown('playhead')"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onUp"
    >
      <!-- waveform words -->
      <div
        v-for="(word, idx) in visibleWords"
        :key="`${word.start}-${idx}`"
        class="absolute top-1 bottom-5 rounded-sm"
        :class="idx % 2 === 0 ? 'bg-clipper-ink/30 dark:bg-white/30' : 'bg-clipper-ink/50 dark:bg-neutral-8000'"
        :style="{ left: pct(word.start), width: `${Math.max(0.4, ((word.end - word.start) / duration) * 100)}%` }"
      />

      <!-- selected region -->
      <div
        class="absolute top-0 bottom-0 bg-clipper-green/12 pointer-events-none"
        :style="{ left: pct(clipStart), width: `${((clipEnd - clipStart) / duration) * 100}%` }"
      />

      <!-- start handle — 44px hit area, 8px visual -->
      <div
        class="absolute top-0 bottom-0 w-11 cursor-ew-resize flex items-center justify-start z-10"
        :style="{ left: `calc(${pct(clipStart)} - 22px)` }"
        @pointerdown.stop="onDown('start')"
        @pointermove="onMove"
        @pointerup="onUp"
      >
        <div class="w-2 h-9 bg-clipper-green rounded ml-[17px]" />
      </div>

      <!-- end handle — 44px hit area, 8px visual -->
      <div
        class="absolute top-0 bottom-0 w-11 cursor-ew-resize flex items-center justify-end z-10"
        :style="{ left: `calc(${pct(clipEnd)} - 22px)` }"
        @pointerdown.stop="onDown('end')"
        @pointermove="onMove"
        @pointerup="onUp"
      >
        <div class="w-2 h-9 bg-clipper-green rounded mr-[17px]" />
      </div>

      <!-- playhead -->
      <div class="absolute top-0 bottom-0 w-0.5 bg-clipper-ink dark:bg-white pointer-events-none z-10" :style="{ left: pct(currentTime) }">
        <div class="w-2 h-2 bg-clipper-ink dark:bg-white rounded-full -ml-1 mt-0.5" />
      </div>
    </div>
  </div>
</template>
