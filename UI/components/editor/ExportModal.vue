<script lang="ts" setup>
/**
 * ExportModal — MP4 export dialog: quality preset cards (360p..1080p),
 * advanced codec overrides, live frame progress, cancel via AbortController.
 * The render itself runs in-browser through @elah/core's exportVideo.
 */
import { exportVideo } from "@elah/core"
import type { ExportAudioCodec, ExportProgress, ExportVideoCodec } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ show: boolean; elah: ElahEditor; exportName?: string }>()
const emit = defineEmits<{ "update:show": [v: boolean] }>()

const message = useMessage()

// ---- Quality presets (bitrates follow YouTube's recommended SDR upload rates) ----
interface QualityPreset {
  label: string
  description: string
  outputHeight: number
  videoBitrate: number
  videoCodec: ExportVideoCodec
  audioCodec: ExportAudioCodec
}
const PRESETS: QualityPreset[] = [
  { label: "360p", description: "640x360 · 1 Mbps · H.264 · smaller file", outputHeight: 360, videoBitrate: 1_000_000, videoCodec: "avc", audioCodec: "aac" },
  { label: "480p", description: "854x480 · 2.5 Mbps · H.264 · recommended", outputHeight: 480, videoBitrate: 2_500_000, videoCodec: "avc", audioCodec: "aac" },
  { label: "720p", description: "1280x720 · 5 Mbps · H.264 · high quality", outputHeight: 720, videoBitrate: 5_000_000, videoCodec: "avc", audioCodec: "aac" },
  { label: "1080p", description: "1920x1080 · 8 Mbps · H.264 · full HD", outputHeight: 1080, videoBitrate: 8_000_000, videoCodec: "avc", audioCodec: "aac" },
]
const DEFAULT_PRESET = 2 // 720p

const selectedPreset = ref(DEFAULT_PRESET)
const videoCodec = ref<ExportVideoCodec>("avc")
const audioCodec = ref<ExportAudioCodec>("aac")

const onSelectPreset = (i: number) => {
  selectedPreset.value = i
  videoCodec.value = PRESETS[i].videoCodec
  audioCodec.value = PRESETS[i].audioCodec
}

const videoCodecOptions = [
  { label: "H.264", value: "avc" },
  { label: "VP9", value: "vp9" },
]
const audioCodecOptions = [
  { label: "AAC", value: "aac" },
  { label: "Opus", value: "opus" },
]

// ---- Export run (abortable, in-browser) ----
const exporting = ref(false)
const progress = ref<ExportProgress | null>(null)
let controller: AbortController | null = null

const percentage = computed(() => {
  const p = progress.value
  return p && p.totalFrames > 0 ? Math.round((p.frame / p.totalFrames) * 100) : 0
})

const canExport = computed(() => props.elah.totalFrames.value > 0)

const onUpdateShow = (v: boolean) => emit("update:show", v)

const onCancel = () => {
  controller?.abort()
  if (!exporting.value) emit("update:show", false)
}

const doExport = async () => {
  if (exporting.value || !canExport.value) return
  props.elah.pause()
  exporting.value = true
  progress.value = null
  controller = new AbortController()
  const preset = PRESETS[selectedPreset.value]
  try {
    const blob = await exportVideo(props.elah.withVideoAudio(props.elah.engine.getProject()), {
      videoCodec: videoCodec.value,
      audioCodec: audioCodec.value,
      videoBitrate: preset.videoBitrate,
      outputHeight: preset.outputHeight,
      onProgress: (p) => { progress.value = p },
      signal: controller.signal,
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${props.exportName || "clipper-export"}.mp4`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
    message.success("Export complete — check downloads")
    emit("update:show", false)
  } catch (e: unknown) {
    const err = e as { name?: string; message?: string }
    if (err?.name === "AbortError") {
      message.info("Export cancelled")
      emit("update:show", false)
    } else {
      console.error("[elah] export failed", e)
      message.error(`Export failed: ${err?.message || "unknown error"}`)
    }
  } finally {
    exporting.value = false
    controller = null
  }
}
</script>

<template>
  <n-modal
    :show="props.show"
    preset="card"
    style="width: 560px"
    :mask-closable="!exporting"
    @update:show="onUpdateShow"
  >
    <template #header>
      <div>
        <p class="text-sm font-bold text-clipper-ink dark:text-white">Export MP4</p>
        <p class="text-[11px] font-normal text-clipper-ink/50 dark:text-white/50">
          Rendered in your browser — nothing leaves this machine
        </p>
      </div>
    </template>

    <div class="space-y-4">
      <!-- Quality presets -->
      <div class="grid grid-cols-2 gap-3">
        <button
          v-for="(preset, i) in PRESETS"
          :key="preset.label"
          type="button"
          class="relative rounded-lg border p-3 text-left transition-colors"
          :class="i === selectedPreset
            ? 'border-transparent ring-2 ring-clipper-green'
            : 'border-clipper-ink/10 dark:border-white/10 hover:border-clipper-ink/25 dark:hover:border-white/25'"
          :disabled="exporting"
          @click="onSelectPreset(i)"
        >
          <span class="block text-sm font-semibold text-clipper-ink dark:text-white">{{ preset.label }}</span>
          <span class="block text-[11px] mt-0.5 text-clipper-ink/50 dark:text-white/50">{{ preset.description }}</span>
          <span
            v-if="preset.outputHeight === 1080"
            class="absolute top-2 right-2 rounded bg-clipper-green/15 px-1 py-px text-[9px] font-bold tracking-wide text-clipper-green"
          >HD</span>
        </button>
      </div>
      <p class="text-[11px] text-clipper-ink/50 dark:text-white/50">MP4 container · audio stereo 44.1 kHz</p>

      <!-- Advanced codec overrides -->
      <div class="grid grid-cols-2 gap-3">
        <div class="space-y-1">
          <label class="block text-[10px] font-semibold uppercase tracking-wider text-clipper-ink/50 dark:text-white/50">Video codec</label>
          <n-select v-model:value="videoCodec" :options="videoCodecOptions" size="small" class="w-36" :disabled="exporting" />
        </div>
        <div class="space-y-1">
          <label class="block text-[10px] font-semibold uppercase tracking-wider text-clipper-ink/50 dark:text-white/50">Audio codec</label>
          <n-select v-model:value="audioCodec" :options="audioCodecOptions" size="small" class="w-36" :disabled="exporting" />
        </div>
      </div>

      <!-- Progress -->
      <div v-if="exporting" class="space-y-1.5">
        <n-progress type="line" :percentage="percentage" :height="8" />
        <p class="text-xs font-mono tabular-nums text-clipper-ink/50 dark:text-white/50">
          frame {{ progress?.frame ?? 0 }} / {{ progress?.totalFrames ?? props.elah.totalFrames.value }}
        </p>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <n-button quaternary @click="onCancel">Cancel</n-button>
        <n-button type="primary" :loading="exporting" :disabled="!canExport" @click="doExport">
          <template #icon><Icon name="ph:file-arrow-down" size="16" /></template>
          {{ exporting ? "Rendering…" : "Export" }}
        </n-button>
      </div>
    </template>
  </n-modal>
</template>
