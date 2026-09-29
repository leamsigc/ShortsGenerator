<script lang="ts" setup>
/**
 * ClipPreview — controlled clip-segment preview with hook title (first 3s)
 * and word-synced caption bar. Face-centered framing, dynamic aspect ratio.
 *
 * The parent drives the segment via startTime/endTime (absolute source
 * timestamps): the video seeks to startTime on load — and whenever src or
 * startTime changes, so selecting a different clip previews THAT clip — and
 * loops inside the segment. Transport state is reported through events;
 * imperative play/pause/seek are exposed for the editor toolbar (the video
 * has no native controls: they would allow seeking outside the segment and
 * desync the captions).
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.2
 */
const props = withDefaults(defineProps<{
  src: string
  startTime?: number
  endTime?: number
  hookTitle?: string
  caption?: string
  accent?: string
  aspectRatio?: "9:16" | "16:9" | "1:1" | "4:5"
}>(), {
  startTime: 0,
  endTime: 0,
  hookTitle: "",
  caption: "",
  accent: "",
  aspectRatio: "9:16",
})

const emit = defineEmits<{
  (e: "loadedmetadata", duration: number): void
  (e: "timeupdate", time: number): void
  (e: "play"): void
  (e: "pause"): void
}>()

const videoRef = ref<HTMLVideoElement | null>(null)

const segStart = computed(() => Math.max(0, props.startTime || 0))
const segEnd = computed(() => {
  const end = props.endTime || 0
  return end > segStart.value ? end : Number.POSITIVE_INFINITY
})

const safeSeek = (t: number) => {
  const v = videoRef.value
  if (!v || !props.src) return
  try {
    v.currentTime = Math.max(0, t)
  } catch {
    // Metadata not ready yet — the loadedmetadata handler seeks instead.
  }
}

const seekToSegmentStart = () => {
  const v = videoRef.value
  if (!v) return
  if (Math.abs((v.currentTime || 0) - segStart.value) > 0.35) safeSeek(segStart.value)
}

const onLoadedMeta = () => {
  const v = videoRef.value
  const dur = v && Number.isFinite(v.duration) && v.duration > 0 ? v.duration : 0
  emit("loadedmetadata", dur)
  // A (re)loaded source always starts at the segment — selecting another
  // clip must preview that clip, never 0:00 of the source video.
  safeSeek(segStart.value)
}

const onTime = () => {
  const v = videoRef.value
  if (!v) return
  const t = v.currentTime || 0
  if (t >= segEnd.value - 0.05) {
    if (!v.paused) {
      safeSeek(segStart.value)
      emit("timeupdate", segStart.value)
    } else {
      emit("timeupdate", Math.min(t, segEnd.value))
    }
    return
  }
  emit("timeupdate", t)
}

const play = async () => {
  const v = videoRef.value
  if (!v) return
  // Restart the segment when playback begins at/past its end.
  if ((v.currentTime || 0) >= segEnd.value - 0.15) safeSeek(segStart.value)
  try {
    await v.play()
  } catch {
    // Autoplay policy — playback needs a user gesture; the toolbar provides it.
  }
}
const pause = () => {
  try {
    videoRef.value?.pause()
  } catch { /* noop */ }
}
const seek = (t: number) => {
  const end = segEnd.value === Number.POSITIVE_INFINITY ? t : segEnd.value
  safeSeek(Math.max(segStart.value, Math.min(t, end)))
}
const toggle = () => {
  const v = videoRef.value
  if (!v) return
  if (v.paused) play()
  else pause()
}

// New clip (src change) → jump to its segment start once ready.
watch(() => props.src, () => {
  nextTick(() => safeSeek(segStart.value))
})
// Trim edits → keep the playhead inside the segment.
watch(segStart, (s) => {
  const t = videoRef.value?.currentTime || 0
  if (t < s - 0.3 || t > segEnd.value) seekToSegmentStart()
})

defineExpose({ play, pause, seek })

const aspectClass = computed(() => ({
  "9:16": "aspect-[9/16]",
  "16:9": "aspect-video",
  "1:1": "aspect-square",
  "4:5": "aspect-[4/5]",
}[props.aspectRatio] || "aspect-[9/16]"))
</script>

<template>
  <div class="relative rounded-lg overflow-hidden bg-clipper-ink dark:bg-black flex items-stretch w-full max-w-[360px] border border-clipper-ink/08 dark:border-white/10" :class="aspectClass">
    <video
      ref="videoRef"
      :src="props.src"
      class="absolute inset-0 w-full h-full object-cover cursor-pointer"
      playsinline
      preload="metadata"
      @loadedmetadata="onLoadedMeta"
      @timeupdate="onTime"
      @play="emit('play')"
      @pause="emit('pause')"
      @click="toggle"
    />
    <!-- Hook title overlay — top 15%, Poppins Bold, max 2 lines -->
    <div v-if="props.hookTitle" class="absolute top-[15%] left-0 right-0 px-4 z-10 pointer-events-none">
      <p class="text-center text-white font-bold leading-tight text-[28px] drop-shadow-[0_1px_3px_rgba(15,23,42,.9)] line-clamp-2">
        {{ props.hookTitle }}
      </p>
    </div>
    <!-- Caption bar lower third — karaoke highlight -->
    <div v-if="props.caption" class="absolute bottom-0 left-0 right-0 px-3 py-2.5 bg-clipper-ink/80 z-10 pointer-events-none">
      <p class="text-center text-white font-bold leading-snug text-[15px]">
        <span class="text-clipper-green">{{ props.accent }}</span>{{ props.caption }}
      </p>
    </div>
  </div>
</template>
