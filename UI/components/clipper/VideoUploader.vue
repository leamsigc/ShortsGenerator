<script lang="ts" setup>
/**
 * Component Description: Source URL management panel for a CLIPPER project.
 * Add/remove source video URLs (YouTube, direct MP4, Instagram).
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */
interface Props {
  sourceUrls: string[]
  sourceIds?: string[]
  disabled?: boolean
  projectId?: string
}

const props = withDefaults(defineProps<Props>(), {
  sourceIds: () => [],
  disabled: false,
  projectId: "",
})

const emit = defineEmits<{
  (e: "add", url: string): void
  (e: "remove", sourceId: string): void
  (e: "uploaded", sourceId: string): void
}>()

const clipperStore = useClipperStore()

const newUrl = ref("")
const isAdding = ref(false)

const handleAdd = () => {
  const url = newUrl.value.trim()
  if (!url || props.disabled) return
  isAdding.value = true
  emit("add", url)
  newUrl.value = ""
  setTimeout(() => (isAdding.value = false), 500)
}

const sourceType = (url: string): string => {
  if (url.startsWith("local://")) return "mdi:file-video-outline"
  if (url.includes("youtube.com") || url.includes("youtu.be")) return "ph:youtube-logo"
  if (url.includes("instagram.com")) return "ph:instagram-logo"
  if (url.includes("tiktok.com")) return "ph:tiktok-logo"
  return "ph:file-video"
}

const sourceLabel = (url: string): string => {
  if (url.startsWith("local://")) return decodeURIComponent(url.slice("local://".length)) || url
  return url
}

const videoFileInput = ref<HTMLInputElement | null>(null)
const srtFileInput = ref<HTMLInputElement | null>(null)
const selectedVideo = ref<File | null>(null)
const selectedSrt = ref<File | null>(null)
const uploading = ref(false)
const uploadResult = ref<string | null>(null)
const uploadError = ref<string | null>(null)

const triggerVideoPick = () => {
  videoFileInput.value?.click()
}

const triggerSrtPick = () => {
  srtFileInput.value?.click()
}

const onVideoPicked = (event: Event) => {
  const input = event.target as HTMLInputElement
  selectedVideo.value = input.files?.[0] || null
}

const onSrtPicked = (event: Event) => {
  const input = event.target as HTMLInputElement
  selectedSrt.value = input.files?.[0] || null
}

const handleUpload = async () => {
  const projectId = props.projectId || clipperStore.currentProject?.id
  if (!selectedVideo.value || !projectId || props.disabled) return
  uploading.value = true
  uploadResult.value = null
  uploadError.value = null
  try {
    const data = await clipperStore.uploadLocalSource(projectId, selectedVideo.value, selectedSrt.value)
    if (!data) {
      uploadError.value = "Upload failed"
      return
    }
    uploadResult.value = "Uploaded successfully!"
    emit("uploaded", data.source_id)
    selectedVideo.value = null
    selectedSrt.value = null
    if (videoFileInput.value) videoFileInput.value.value = ""
    if (srtFileInput.value) srtFileInput.value.value = ""
    setTimeout(() => (uploadResult.value = null), 2500)
  } catch (e: any) {
    uploadError.value = e?.data?.message || e?.message || "Upload failed"
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-lg p-4">
    <div class="flex items-center justify-between mb-3">
      <h4 class="font-semibold text-sm text-clipper-ink dark:text-white">Sources</h4>
      <span class="text-xs font-medium text-clipper-ink/60 dark:text-white/60 bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 rounded-full">{{ sourceUrls.length }}</span>
    </div>

    <div class="flex gap-2 mb-3">
      <input
        v-model="newUrl"
        placeholder="Paste video URL... (YouTube / MP4)"
        class="flex-1 h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm text-clipper-ink placeholder:text-clipper-ink/35 dark:text-white/40 focus:outline-none focus:border-clipper-green focus:ring-1 focus:ring-clipper-green/20 disabled:opacity-50"
        :disabled="props.disabled"
        @keyup.enter="handleAdd"
      />
      <button
        class="h-10 px-3 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 disabled:opacity-50 flex items-center justify-center"
        :disabled="props.disabled || isAdding"
        @click="handleAdd"
        aria-label="Add source"
      >
        <Icon name="ph:plus" size="16" />
      </button>
    </div>

    <!-- Local file upload -->
    <div class="mb-3 border border-dashed border-clipper-ink/12 dark:border-white/10 rounded-lg p-3 space-y-2">
      <div class="flex items-center gap-2">
        <span class="text-xs font-medium text-clipper-ink/60 dark:text-white/60">Or upload a local file</span>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          class="h-9 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm font-medium text-clipper-ink dark:text-white hover:border-clipper-ink/20 dark:hover:border-white/20 disabled:opacity-50 flex items-center gap-1.5"
          :disabled="props.disabled || uploading"
          @click="triggerVideoPick"
        >
          <Icon name="ph:upload-simple" size="14" />
          {{ selectedVideo ? selectedVideo.name : "Choose video" }}
        </button>
        <button
          class="h-9 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-xs font-medium text-clipper-ink/60 dark:text-white/60 hover:border-clipper-ink/20 dark:hover:border-white/20 disabled:opacity-50 flex items-center gap-1.5"
          :disabled="props.disabled || uploading || !selectedVideo"
          @click="triggerSrtPick"
        >
          <Icon name="ph:file-text" size="14" />
          {{ selectedSrt ? selectedSrt.name : "+ SRT (optional)" }}
        </button>
        <button
          class="h-9 px-3 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 disabled:opacity-50"
          :disabled="props.disabled || uploading || !selectedVideo"
          @click="handleUpload"
        >
          {{ uploading ? "Uploading…" : "Upload" }}
        </button>
      </div>
      <input ref="videoFileInput" type="file" accept="video/mp4,video/webm,video/quicktime,.mkv,.avi" class="hidden" @change="onVideoPicked" />
      <input ref="srtFileInput" type="file" accept=".srt" class="hidden" @change="onSrtPicked" />
      <p v-if="uploading" class="text-xs text-clipper-ink/60 dark:text-white/60">Uploading {{ selectedVideo?.name }}…</p>
      <p v-else-if="uploadResult" class="text-xs text-clipper-green font-medium">{{ uploadResult }}</p>
      <p v-else-if="uploadError" class="text-xs text-red-500 font-medium">{{ uploadError }}</p>
    </div>

    <div class="space-y-2 max-h-64 overflow-y-auto">
      <div
        v-for="(url, idx) in sourceUrls"
        :key="sourceIds[idx] || url || idx"
        class="flex items-center gap-2 text-sm bg-neutral-100 dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-lg px-3 py-2"
      >
        <Icon :name="sourceType(url)" class="shrink-0 text-clipper-ink/60 dark:text-white/60" size="16" />
        <span class="flex-1 truncate text-clipper-ink dark:text-white/80 text-sm" :title="url">{{ sourceLabel(url) }}</span>
        <button
          v-if="sourceIds[idx]"
          class="w-7 h-7 rounded-md flex items-center justify-center text-clipper-ink/40 dark:text-white/40 hover:text-clipper-ink dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-white/5 disabled:opacity-50"
          :disabled="props.disabled"
          @click="emit('remove', sourceIds[idx])"
          aria-label="Remove source"
        >
          <Icon name="ph:x" size="14" />
        </button>
      </div>
      <div v-if="sourceUrls.length === 0" class="text-xs text-clipper-ink/35 dark:text-white/40 text-center py-4 border border-dashed border-clipper-ink/12 dark:border-white/10 rounded-lg">
        No sources yet — add a video URL above.
      </div>
    </div>
  </div>
</template>
