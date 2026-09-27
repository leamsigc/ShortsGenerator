<script lang="ts" setup>
/**
 * StockMediaPanel — stock video/photo search (backend pixabay-style proxy)
 * + local uploads. Clicking a tile inserts the media at the playhead on the
 * first video track via `elah.addClipFree` and records natural dimensions.
 *
 * Contract (frozen by the editor shell):
 *   props:  { elah; mode: "videos" | "photos" }
 *   emits: { inserted: [name: string] }
 */
import { secondsToFrames } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor; mode: "videos" | "photos" }>()
const emit = defineEmits<{ inserted: [name: string] }>()

const API = useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080"
const fps = computed(() => props.elah.project.value.fps)

const isVideos = computed(() => props.mode === "videos")
const acceptAttr = computed(() => (isVideos.value ? "video/*" : "image/*"))

// ---- header / source controls ----
const fileInput = ref<HTMLInputElement | null>(null)
const source = ref<"stock" | "uploads">("stock")
const sourceOptions = [
  { label: "Stock", value: "stock" },
  { label: "Uploads", value: "uploads" },
]

const fmtDuration = (sec?: number | null): string => {
  if (!sec || !Number.isFinite(sec) || sec <= 0) return ""
  const total = Math.round(sec)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}

// ---- insert-at-playhead helpers ----
const videoTrackId = (): string => props.elah.trackByKind("video")

const insertClip = (
  type: "video" | "image",
  src: string,
  name: string,
  durationSec: number,
  width?: number,
  height?: number,
): string | null => {
  const trackId = videoTrackId()
  if (!trackId) return null
  const clip = props.elah.addClipFree({
    trackId,
    type,
    src,
    name,
    startFrame: props.elah.currentFrame.value,
    durationFrames: Math.max(1, secondsToFrames(durationSec, fps.value)),
  })
  if (!clip) return null
  if (width && height) props.elah.setNaturalSize(clip.id, width, height)
  emit("inserted", name)
  return clip.id
}

// =====================================================================
// Stock search
// =====================================================================
interface StockItem {
  id: number | string
  url: string
  thumbnail: string
  duration?: number | null
  user?: string
  width?: number
  height?: number
}

const search = ref("")
const fetching = ref(false)
const results = ref<StockItem[]>([])

const fetchStock = async (query: string) => {
  fetching.value = true
  try {
    const res = await $fetch<{ status?: string; data?: StockItem[] }>(`${API}/api/stock/${props.mode}`, {
      query: { query, per_page: 24 },
    })
    results.value = res.data ?? []
  } catch (e) {
    console.error("[StockMediaPanel] stock fetch failed", e)
  } finally {
    fetching.value = false
  }
}

// 300ms-debounced search; an emptied input keeps the last successful results.
let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    const q = search.value.trim()
    if (!q) return
    void fetchStock(q)
  }, 300)
})
onBeforeUnmount(() => clearTimeout(searchTimer))

const insertStock = (item: StockItem) => {
  const name = item.user || (isVideos.value ? "Stock video" : "Stock photo")
  if (isVideos.value) {
    insertClip("video", item.url, name, Math.min(item.duration || 8, 15), item.width, item.height)
  } else {
    insertClip("image", item.url, name, 5, item.width, item.height)
  }
}

// =====================================================================
// Uploads (local, object URLs; nothing leaves the browser)
// =====================================================================
interface UploadedItem {
  name: string
  url: string
  kind: "video" | "image"
  durationSec?: number
  width?: number
  height?: number
  thumbnailUrl?: string
}

const uploads = ref<UploadedItem[]>([])
const dragOver = ref(false)

const probeVideoMeta = (url: string): Promise<{ durationSec: number; width: number; height: number }> =>
  new Promise((resolve) => {
    const el = document.createElement("video")
    el.preload = "metadata"
    el.muted = true
    const finish = (durationSec: number, width: number, height: number) =>
      resolve({ durationSec, width, height })
    el.onloadedmetadata = () =>
      finish(
        Number.isFinite(el.duration) && el.duration > 0 ? el.duration : 0,
        el.videoWidth,
        el.videoHeight,
      )
    el.onerror = () => finish(0, 0, 0)
    el.src = url
  })

const probeImageMeta = (url: string): Promise<{ width: number; height: number }> =>
  new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight })
    img.onerror = () => resolve({ width: 0, height: 0 })
    img.src = url
  })

const addFiles = (files: FileList | File[] | null) => {
  if (!files) return
  const wanted = isVideos.value ? "video" : "image"
  for (const file of Array.from(files)) {
    const kind: "video" | "image" | null = file.type.startsWith("video/")
      ? "video"
      : file.type.startsWith("image/")
        ? "image"
        : null
    if (kind !== wanted) continue
    const url = URL.createObjectURL(file)
    const item: UploadedItem = { name: file.name, url, kind }
    if (kind === "image") item.thumbnailUrl = url
    uploads.value.push(item)
    if (kind === "video") {
      void probeVideoMeta(url).then(meta => {
        item.durationSec = meta.durationSec
        item.width = meta.width
        item.height = meta.height
      })
    } else {
      void probeImageMeta(url).then(meta => {
        item.durationSec = 5
        item.width = meta.width
        item.height = meta.height
      })
    }
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

const insertUploaded = (item: UploadedItem) => {
  if (item.kind === "video") {
    insertClip("video", item.url, item.name, Math.min(item.durationSec || 8, 15), item.width, item.height)
  } else {
    insertClip("image", item.url, item.name, 5, item.width, item.height)
  }
}

const removeUpload = (index: number) => {
  const [removed] = uploads.value.splice(index, 1)
  if (removed) URL.revokeObjectURL(removed.url)
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <!-- Header: title + upload -->
    <div class="flex items-center justify-between border-b border-clipper-ink/08 dark:border-white/08 px-3 py-2.5">
      <span class="text-sm font-semibold text-clipper-ink dark:text-white">
        {{ isVideos ? "Videos" : "Photos" }}
      </span>
      <n-button size="tiny" type="primary" @click="fileInput?.click()">
        <template #icon><Icon name="ph:plus" size="12" /></template>
        Upload
      </n-button>
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        :accept="acceptAttr"
        multiple
        @change="onInputChange"
      >
    </div>

    <!-- Search + source -->
    <div class="flex items-center gap-2 px-3 py-2">
      <n-input
        v-if="source === 'stock'"
        v-model:value="search"
        size="small"
        :placeholder="`Search ${mode}…`"
        clearable
        class="min-w-0 flex-1"
      >
        <template #prefix><Icon name="ph:magnifying-glass" size="14" /></template>
      </n-input>
      <div v-else class="flex-1" />
      <n-select v-model:value="source" size="small" class="w-24" :options="sourceOptions" />
    </div>

    <!-- Body -->
    <div class="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
      <!-- Stock results -->
      <template v-if="source === 'stock'">
        <div v-if="fetching" class="flex h-full min-h-40 items-center justify-center">
          <n-spin size="small" />
        </div>
        <n-empty
          v-else-if="results.length === 0"
          size="small"
          class="py-8"
          :description="search.trim() ? 'No results' : 'Type to search stock media'"
        />
        <div v-else class="grid grid-cols-2 gap-2">
          <div
            v-for="item in results"
            :key="`${item.id}`"
            class="group relative aspect-video cursor-pointer overflow-hidden rounded-md border border-clipper-ink/10 dark:border-white/10 bg-neutral-100 dark:bg-neutral-800"
            :title="item.user"
            @click="insertStock(item)"
          >
            <img :src="item.thumbnail" alt="" class="h-full w-full object-cover">
            <span
              v-if="isVideos && fmtDuration(item.duration)"
              class="pointer-events-none absolute bottom-1 right-1 rounded bg-black/70 px-1 font-mono text-[10px] text-white"
            >{{ fmtDuration(item.duration) }}</span>
          </div>
        </div>
      </template>

      <!-- Uploads -->
      <template v-else>
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
        <div v-else class="grid grid-cols-2 gap-2">
          <div
            v-for="(item, i) in uploads"
            :key="item.url"
            class="group relative aspect-video cursor-pointer overflow-hidden rounded-md border border-clipper-ink/10 dark:border-white/10 bg-neutral-100 dark:bg-neutral-800"
            :title="item.name"
            @click="insertUploaded(item)"
          >
            <video
              v-if="item.kind === 'video'"
              :src="item.url"
              muted
              preload="metadata"
              class="h-full w-full object-cover"
            />
            <img v-else :src="item.thumbnailUrl || item.url" alt="" class="h-full w-full object-cover">
            <span
              v-if="item.kind === 'video' && fmtDuration(item.durationSec)"
              class="pointer-events-none absolute bottom-1 right-1 rounded bg-black/70 px-1 font-mono text-[10px] text-white"
            >{{ fmtDuration(item.durationSec) }}</span>
            <button
              type="button"
              class="absolute top-1 right-1 flex h-5 w-5 items-center justify-center rounded bg-neutral-800 text-white opacity-0 transition-opacity hover:bg-red-600 group-hover:opacity-100"
              title="Remove"
              @click.stop="removeUpload(i)"
            >
              <Icon name="ph:trash" size="11" />
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
