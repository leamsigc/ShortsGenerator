<script lang="ts" setup>
/**
 * AudioPanel — music/SFX library (backend assets), local audio uploads and
 * URL import. "Add" inserts an audio clip at the playhead on the first audio
 * track via `elah.addClipFree`; durations are probed with a temp <audio>.
 *
 * Contract (frozen by the editor shell):
 *   props:  { elah }
 *   emits: { inserted: [name: string] }
 */
import { secondsToFrames } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()
const emit = defineEmits<{ inserted: [name: string] }>()

const API = useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080"
const fps = computed(() => props.elah.project.value.fps)

const source = ref<"library" | "uploads" | "url">("library")
const sourceOptions = [
  { label: "Library", value: "library" },
  { label: "Uploads", value: "uploads" },
  { label: "URL", value: "url" },
]

const fmtDuration = (sec?: number | null): string => {
  if (!sec || !Number.isFinite(sec) || sec <= 0) return ""
  const total = Math.round(sec)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}

// =====================================================================
// Insert + duration probing
// =====================================================================
const durationCache = new Map<string, number>()

const probeAudioDuration = (url: string): Promise<number> =>
  new Promise((resolve) => {
    const el = new Audio()
    el.preload = "metadata"
    el.onloadedmetadata = () =>
      resolve(Number.isFinite(el.duration) && el.duration > 0 ? el.duration : 0)
    el.onerror = () => resolve(0)
    el.src = url
  })

const insertAudio = (src: string, name: string, durationSec: number) => {
  const trackId = props.elah.trackByKind("audio")
  if (!trackId) return
  const clip = props.elah.addClipFree({
    trackId,
    type: "audio",
    src,
    name,
    startFrame: props.elah.currentFrame.value,
    durationFrames: Math.max(1, secondsToFrames(durationSec, fps.value)),
  })
  if (!clip) return
  emit("inserted", name)
}

// =====================================================================
// Library (music + sfx, fetched once)
// =====================================================================
interface LibraryTrack { name: string; url: string }

const music = ref<LibraryTrack[]>([])
const sfx = ref<LibraryTrack[]>([])
const libraryLoading = ref(false)
let libraryLoaded = false

const toTrack = (dir: "music" | "sfx") =>
  (name: string): LibraryTrack => ({ name, url: `${API}/static/assets/${dir}/${encodeURIComponent(name)}` })

const loadLibrary = async () => {
  if (libraryLoaded) return
  libraryLoading.value = true
  try {
    const [songsRes, sfxRes] = await Promise.all([
      $fetch<{ data?: { songs?: string[] } }>(`${API}/api/getSongs`),
      $fetch<{ data?: { sfx?: string[] } }>(`${API}/api/getSfx`),
    ])
    music.value = (songsRes.data?.songs ?? []).map(toTrack("music"))
    sfx.value = (sfxRes.data?.sfx ?? []).map(toTrack("sfx"))
    libraryLoaded = true
  } catch (e) {
    console.error("[AudioPanel] library fetch failed", e)
  } finally {
    libraryLoading.value = false
  }
}
onMounted(() => void loadLibrary())

const addLibraryTrack = async (track: LibraryTrack) => {
  let dur = durationCache.get(track.url)
  if (dur === undefined) {
    dur = await probeAudioDuration(track.url)
    durationCache.set(track.url, dur)
  }
  insertAudio(track.url, track.name, dur || 30)
}

// ---- shared preview <audio> (one element, stops the previous preview) ----
const previewEl = ref<HTMLAudioElement | null>(null)
const previewKey = ref<string | null>(null)

const stopPreview = () => {
  const el = previewEl.value
  if (!el) return
  el.pause()
  el.removeAttribute("src")
  previewKey.value = null
}

const togglePreview = (track: LibraryTrack) => {
  const el = previewEl.value
  if (!el) return
  if (previewKey.value === track.url) {
    stopPreview()
    return
  }
  el.pause()
  el.src = track.url
  previewKey.value = track.url
  el.play().catch(() => { previewKey.value = null })
}

watch(source, () => stopPreview())
onBeforeUnmount(stopPreview)

// =====================================================================
// Uploads (local audio, object URLs)
// =====================================================================
interface UploadedAudio { name: string; url: string; durationSec: number }

const uploads = ref<UploadedAudio[]>([])
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const addFiles = (files: FileList | File[] | null) => {
  if (!files) return
  for (const file of Array.from(files)) {
    if (!file.type.startsWith("audio/")) continue
    const url = URL.createObjectURL(file)
    const item: UploadedAudio = { name: file.name, url, durationSec: 0 }
    uploads.value.push(item)
    void probeAudioDuration(url).then(d => { item.durationSec = d })
  }
}

const onInputChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  addFiles(input.files)
  input.value = ""
}

const onDrop = (e: DragEvent) => {
  dragOver.value = false
  addFiles(e.dataTransfer?.files ?? null)
}

const insertUploaded = (item: UploadedAudio) => {
  insertAudio(item.url, item.name, item.durationSec || 30)
}

const removeUpload = (index: number) => {
  const [removed] = uploads.value.splice(index, 1)
  if (removed) URL.revokeObjectURL(removed.url)
}

// =====================================================================
// URL import
// =====================================================================
const urlValue = ref("")
const urlBusy = ref(false)

const nameFromUrl = (url: string): string =>
  url.split("/").pop()?.split("?")[0] || "Audio"

const addFromUrl = async () => {
  const url = urlValue.value.trim()
  if (!url || urlBusy.value) return
  urlBusy.value = true
  try {
    const dur = await probeAudioDuration(url)
    insertAudio(url, nameFromUrl(url), dur || 30)
    urlValue.value = ""
  } finally {
    urlBusy.value = false
  }
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <!-- Header: title + upload -->
    <div class="flex items-center justify-between border-b border-clipper-ink/08 dark:border-white/08 px-3 py-2.5">
      <span class="text-sm font-semibold text-clipper-ink dark:text-white">Audio</span>
      <n-button size="tiny" type="primary" @click="fileInput?.click()">
        <template #icon><Icon name="ph:plus" size="12" /></template>
        Upload
      </n-button>
      <input
        ref="fileInput"
        type="file"
        accept="audio/*"
        multiple
        class="hidden"
        @change="onInputChange"
      >
    </div>

    <!-- Source -->
    <div class="px-3 py-2">
      <n-select v-model:value="source" size="small" :options="sourceOptions" />
    </div>

    <!-- Body -->
    <div class="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
      <!-- Library -->
      <template v-if="source === 'library'">
        <div v-if="libraryLoading" class="flex min-h-40 items-center justify-center">
          <n-spin size="small" />
        </div>
        <n-empty
          v-else-if="music.length === 0 && sfx.length === 0"
          size="small"
          class="py-8"
          description="Library is empty"
        />
        <template v-else>
          <template v-if="music.length > 0">
            <n-divider title-placement="left" class="!my-2">
              <span class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50">Music</span>
            </n-divider>
            <div
              v-for="track in music"
              :key="track.url"
              class="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              <button
                type="button"
                class="flex h-5 w-5 shrink-0 items-center justify-center rounded text-clipper-ink/70 hover:text-clipper-green dark:text-white/70"
                :title="previewKey === track.url ? 'Stop preview' : 'Preview'"
                @click="togglePreview(track)"
              >
                <Icon :name="previewKey === track.url ? 'ph:pause' : 'ph:play'" size="12" />
              </button>
              <Icon name="ph:music-notes" size="14" class="shrink-0 text-clipper-ink/40 dark:text-white/40" />
              <span class="min-w-0 flex-1 truncate text-xs text-clipper-ink dark:text-white" :title="track.name">{{ track.name }}</span>
              <n-button size="tiny" secondary @click="addLibraryTrack(track)">Add</n-button>
            </div>
          </template>
          <template v-if="sfx.length > 0">
            <n-divider title-placement="left" class="!my-2">
              <span class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50">SFX</span>
            </n-divider>
            <div
              v-for="track in sfx"
              :key="track.url"
              class="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              <button
                type="button"
                class="flex h-5 w-5 shrink-0 items-center justify-center rounded text-clipper-ink/70 hover:text-clipper-green dark:text-white/70"
                :title="previewKey === track.url ? 'Stop preview' : 'Preview'"
                @click="togglePreview(track)"
              >
                <Icon :name="previewKey === track.url ? 'ph:pause' : 'ph:play'" size="12" />
              </button>
              <Icon name="ph:music-notes" size="14" class="shrink-0 text-clipper-ink/40 dark:text-white/40" />
              <span class="min-w-0 flex-1 truncate text-xs text-clipper-ink dark:text-white" :title="track.name">{{ track.name }}</span>
              <n-button size="tiny" secondary @click="addLibraryTrack(track)">Add</n-button>
            </div>
          </template>
        </template>
      </template>

      <!-- Uploads -->
      <template v-else-if="source === 'uploads'">
        <div
          class="mb-3 flex flex-col items-center gap-1 rounded-lg border-2 border-dashed py-4 transition-colors"
          :class="dragOver
            ? 'border-clipper-green bg-neutral-100 dark:bg-neutral-800'
            : 'border-clipper-ink/15 dark:border-white/15 bg-neutral-50 dark:bg-neutral-800'"
          @dragover.prevent="dragOver = true"
          @dragleave="dragOver = false"
          @drop.prevent="onDrop"
        >
          <Icon name="ph:upload-simple" size="20" class="text-clipper-green" />
          <span class="text-[11px] text-clipper-ink/60 dark:text-white/60">Drop files here</span>
        </div>
        <n-empty v-if="uploads.length === 0" size="small" class="py-8" description="No uploads yet" />
        <div
          v-for="(item, i) in uploads"
          v-else
          :key="item.url"
          class="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800"
        >
          <Icon name="ph:music-notes" size="14" class="shrink-0 text-clipper-ink/40 dark:text-white/40" />
          <span class="min-w-0 flex-1 truncate text-xs text-clipper-ink dark:text-white" :title="item.name">{{ item.name }}</span>
          <span class="shrink-0 font-mono text-[10px] text-clipper-ink/50 dark:text-white/50">{{ fmtDuration(item.durationSec) }}</span>
          <n-button size="tiny" secondary @click="insertUploaded(item)">Add</n-button>
          <n-button size="tiny" quaternary title="Remove" @click="removeUpload(i)">
            <template #icon><Icon name="ph:trash" size="12" /></template>
          </n-button>
        </div>
      </template>

      <!-- URL -->
      <template v-else>
        <div class="flex gap-2">
          <n-input
            v-model:value="urlValue"
            size="small"
            placeholder="https://…/track.mp3"
            class="min-w-0 flex-1"
            @keydown.enter="addFromUrl"
          />
          <n-button size="small" type="primary" :loading="urlBusy" :disabled="!urlValue.trim()" @click="addFromUrl">
            Add
          </n-button>
        </div>
      </template>
    </div>

    <!-- Shared preview element -->
    <audio ref="previewEl" class="hidden" @ended="previewKey = null" />
  </div>
</template>
