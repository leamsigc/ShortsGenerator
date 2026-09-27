<script lang="ts" setup>
/**
 * ElahAssetPanel — media import (buttons + native drag & drop) + project
 * media list with thumbnails, duration, insert-at-playhead and remove.
 * Adds clips to the appropriate tracks via the shared elah editor instance;
 * media duration/dimensions are probed with temporary elements so preview
 * overlays can resolve real draw rects.
 */
import { secondsToFrames, framesToTimecode } from "@elah/core"
import type { Clip, CreateClipOptions } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const fps = computed(() => props.elah.project.value.fps)
const trackIdOf = (kind: "video" | "audio" | "elements") =>
  props.elah.tracks.value.find(t => t.kind === kind)?.id ?? ""

const mediaInput = ref<HTMLInputElement | null>(null)
const audioInput = ref<HTMLInputElement | null>(null)

// ---- Duration + dimension probing via temp media elements (URL revoked after) ----
interface ProbeResult { durationSec: number; width: number; height: number }

const probeMedia = (url: string, kind: "video" | "audio" | "image"): Promise<ProbeResult> =>
  new Promise((resolve) => {
    const done = (durationSec: number, width = 0, height = 0) => {
      URL.revokeObjectURL(url)
      resolve({
        durationSec: Number.isFinite(durationSec) && durationSec > 0 ? durationSec : 0,
        width,
        height,
      })
    }
    if (kind === "image") {
      const img = new Image()
      img.onload = () => done(5, img.naturalWidth, img.naturalHeight)
      img.onerror = () => done(5)
      img.src = url
      return
    }
    const el = document.createElement(kind === "audio" ? "audio" : "video")
    el.preload = "metadata"
    el.src = url
    el.onloadedmetadata = () => done(el.duration, kind === "video" ? (el as HTMLVideoElement).videoWidth : 0, kind === "video" ? (el as HTMLVideoElement).videoHeight : 0)
    el.onerror = () => done(0)
  })

const importFiles = async (files: FileList | File[] | null) => {
  if (!files) return
  for (const file of Array.from(files)) {
    const src = URL.createObjectURL(file)
    const isAudio = file.type.startsWith("audio")
    const isVideo = file.type.startsWith("video")
    const kind: "video" | "audio" | "image" = isAudio ? "audio" : isVideo ? "video" : "image"
    const trackId = trackIdOf(isAudio ? "audio" : "video")
    if (!trackId) { URL.revokeObjectURL(src); continue }
    const probe = await probeMedia(src, kind)
    const opts: CreateClipOptions = {
      trackId,
      type: kind,
      src,
      name: file.name,
      startFrame: props.elah.currentFrame.value,
      durationFrames: Math.max(1, secondsToFrames(probe.durationSec || 5, fps.value)),
    }
    const clip = props.elah.addClipFree(opts)
    if (clip && probe.width && probe.height) props.elah.setNaturalSize(clip.id, probe.width, probe.height)
  }
}

const onMediaChange = (e: Event) => {
  importFiles((e.target as HTMLInputElement).files)
  ;(e.target as HTMLInputElement).value = ""
}
const onAudioChange = (e: Event) => {
  importFiles((e.target as HTMLInputElement).files)
  ;(e.target as HTMLInputElement).value = ""
}

// ---- Native drag & drop import ----
const isDragOver = ref(false)
let dragDepth = 0
const onDragEnter = (e: DragEvent) => {
  if (!e.dataTransfer?.types.includes("Files")) return
  dragDepth++
  isDragOver.value = true
}
const onDragLeave = () => {
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) isDragOver.value = false
}
const onDragOver = (e: DragEvent) => {
  if (!e.dataTransfer?.types.includes("Files")) return
  e.preventDefault()
  e.dataTransfer.dropEffect = "copy"
}
const onDrop = (e: DragEvent) => {
  dragDepth = 0
  isDragOver.value = false
  importFiles(e.dataTransfer?.files ?? null)
}

const addText = () => {
  const trackId = trackIdOf("elements")
  if (!trackId) return
  props.elah.addClipFree({
    trackId,
    type: "text",
    name: "Text",
    startFrame: props.elah.currentFrame.value,
    durationFrames: Math.max(1, secondsToFrames(3, fps.value)),
    text: { content: "Your text here", fontSize: 64, color: "#ffffff", fontWeight: "bold", textAlign: "center" },
  })
}

const allClips = computed<Clip[]>(() => {
  const out: Clip[] = []
  for (const list of Object.values(props.elah.clipsByTrack.value)) out.push(...list)
  return out
})

const clipLabel = (clip: Clip) => clip.name || clip.content || clip.type

/** Insert a copy of this clip at the playhead (falls back to end of track on overlap). */
const insertAtPlayhead = (clip: Clip) => {
  const trackClips = props.elah.clipsByTrack.value[clip.trackId] ?? []
  const trackEnd = trackClips.reduce((m, c) => Math.max(m, c.startFrame + c.durationFrames), 0)
  const id = props.elah.engine.cloneClip(clip.id, clip.trackId, props.elah.currentFrame.value)
    ?? props.elah.engine.cloneClip(clip.id, clip.trackId, trackEnd)
  if (id) {
    props.elah.setSelection([id])
    const nat = props.elah.naturalSizes.value.get(clip.id)
    if (nat) props.elah.setNaturalSize(id, nat.width, nat.height)
  }
}

// ---- Deterministic audio waveform (seeded PRNG from clip id) ----
const waveformBars = (seed: string, count = 28): number[] => {
  let h = 2166136261
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  const out: number[] = []
  for (let i = 0; i < count; i++) {
    h ^= h << 13
    h ^= h >>> 17
    h ^= h << 5
    out.push(0.25 + (Math.abs(h) % 1000) / 1000 * 0.75)
  }
  return out
}
</script>

<template>
  <div
    class="w-64 shrink-0 border-r border-clipper-ink/08 dark:border-white/08 bg-white dark:bg-neutral-900 flex flex-col overflow-y-auto relative"
    @dragenter="onDragEnter"
    @dragleave="onDragLeave"
    @dragover="onDragOver"
    @drop.prevent="onDrop"
  >
    <!-- Drop highlight -->
    <div
      v-if="isDragOver"
      class="absolute inset-0 z-20 m-2 rounded-xl border-2 border-dashed border-clipper-green bg-neutral-50 dark:bg-neutral-800 flex flex-col items-center justify-center gap-2 pointer-events-none"
    >
      <Icon name="ph:upload-simple" size="28" class="text-clipper-green" />
      <p class="text-xs font-medium text-clipper-ink dark:text-white">Drop media to import</p>
    </div>

    <!-- Add to timeline -->
    <div class="p-3 space-y-2 border-b border-clipper-ink/08 dark:border-white/08">
      <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50">Add to timeline</p>
      <n-button size="small" block secondary @click="mediaInput?.click()">
        <template #icon><Icon name="ph:plus" size="14" /></template>
        Video / Image
      </n-button>
      <input ref="mediaInput" type="file" accept="video/*,image/*" multiple class="hidden" @change="onMediaChange">
      <n-button size="small" block secondary @click="audioInput?.click()">
        <template #icon><Icon name="ph:music-notes" size="14" /></template>
        Audio
      </n-button>
      <input ref="audioInput" type="file" accept="audio/*" multiple class="hidden" @change="onAudioChange">
      <n-button size="small" block secondary @click="addText()">
        <template #icon><Icon name="ph:text-aa" size="14" /></template>
        Text
      </n-button>
    </div>

    <!-- Media in project -->
    <div class="p-3 space-y-1.5 flex-1 overflow-y-auto">
      <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50 mb-2">Media in project</p>
      <div v-if="allClips.length === 0">
        <n-empty size="small" description="No media yet" />
      </div>
      <div
        v-for="clip in allClips"
        :key="clip.id"
        class="group flex items-center gap-2 rounded-lg border px-2 py-1.5 cursor-pointer"
        :class="elah.selectedClipIds.value.includes(clip.id)
          ? 'border-clipper-green bg-clipper-green/10'
          : 'border-clipper-ink/08 dark:border-white/08 hover:border-clipper-ink/20 dark:hover:border-white/20'"
        @click="elah.setSelection([clip.id])"
      >
        <!-- Thumbnail -->
        <div class="w-20 h-11 shrink-0 rounded overflow-hidden bg-neutral-900 flex items-center justify-center">
          <video
            v-if="clip.type === 'video' && clip.src"
            :src="clip.src"
            preload="metadata"
            muted
            playsinline
            class="w-full h-full object-cover"
          />
          <img
            v-else-if="clip.type === 'image' && clip.src"
            :src="clip.src"
            alt=""
            class="w-full h-full object-cover"
          >
          <svg
            v-else-if="clip.type === 'audio'"
            viewBox="0 0 80 44"
            class="w-full h-full text-blue-400"
            preserveAspectRatio="none"
            aria-label="audio"
          >
            <rect
              v-for="(bar, i) in waveformBars(clip.id)"
              :key="i"
              :x="i * (80 / 28) + 0.5"
              :y="22 - bar * 20"
              :width="80 / 28 - 1"
              :height="bar * 40"
              rx="1"
              fill="currentColor"
            />
          </svg>
          <div
            v-else
            class="w-full h-full flex items-center justify-center px-1"
            :style="{ backgroundColor: '#171717' }"
          >
            <span
              class="text-[10px] font-bold truncate text-center leading-tight"
              :style="{ color: clip.color || '#ffffff' }"
            >{{ clip.content || "Text" }}</span>
          </div>
        </div>

        <!-- Meta -->
        <div class="flex-1 min-w-0">
          <p class="truncate text-xs text-clipper-ink dark:text-white">{{ clipLabel(clip) }}</p>
          <p class="text-[10px] font-mono text-clipper-ink/40 dark:text-white/40 tabular-nums">
            {{ framesToTimecode(clip.durationFrames, fps) }}
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center shrink-0">
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button size="tiny" quaternary @click.stop="insertAtPlayhead(clip)">
                <template #icon><Icon name="ph:plus-circle" size="14" /></template>
              </n-button>
            </template>
            Add at playhead
          </n-tooltip>
          <n-popconfirm @positive-click="elah.removeClip(clip)">
            <template #trigger>
              <n-button size="tiny" quaternary title="Remove clip" @click.stop>
                <template #icon><Icon name="ph:trash" size="12" /></template>
              </n-button>
            </template>
            Remove '{{ clipLabel(clip) }}'?
          </n-popconfirm>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="p-3 border-t border-clipper-ink/08 dark:border-white/08 text-[11px] text-clipper-ink/50 dark:text-white/50 font-mono">
      <p>Duration: {{ framesToTimecode(elah.totalFrames.value, fps) }} · {{ elah.totalFrames.value }} frames</p>
      <p>Stage: {{ elah.project.value.stage.width }}×{{ elah.project.value.stage.height }} @ {{ fps }} fps</p>
    </div>
  </div>
</template>
