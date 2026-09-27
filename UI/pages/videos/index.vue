<script lang="ts" setup>
import { useStorage } from "@vueuse/core";

interface VideoMetadata {
  title: string
  description: string
  tags: string[]
  post_content?: string
  suggested_schedule?: string
}

interface VideoItem {
  filename: string
  url: string
  metadata: VideoMetadata | null
}

interface ClipperVideoItem {
  filename: string
  url: string
  project_id: string
  project_name: string
  clip_id: string
  hook_title: string
  thumbnail_url: string
  export_format: string | null
  metadata: { title: string } | null
  modified: string
}

interface DownloadItem {
  filename: string
  url: string
  metadata: null
  size_mb: number
}

interface MagicSyncAccount {
  platform: string
  accountName: string
  isActive: boolean
}

interface MagicSyncBusiness {
  id: string
  name: string
  url: string
  apiToken: string
  videoBaseUrl: string
}

type Category = "generated" | "instagram" | "clipper" | "downloads"

const videos = ref<VideoItem[]>([])
const instagramVideos = ref<VideoItem[]>([])
const clipperVideos = ref<ClipperVideoItem[]>([])
const downloads = ref<DownloadItem[]>([])
const loading = ref(true)
const scheduleModal = ref(false)
const selectedVideo = ref<VideoItem | null>(null)
const scheduleDate = ref<number | null>(null)
const scheduleTime = ref<number | null>(null)
const scheduling = ref(false)
const scheduleResult = ref<string | null>(null)

const scheduleContent = ref('')
const scheduleTitle = ref('')
const scheduleDescription = ref('')

// MagicSync state
const magicsyncBusinesses = useStorage<MagicSyncBusiness[]>("MAGICSYNC_BUSINESSES", [])
const selectedBusinessId = ref<string | null>(null)
const magicsyncAccounts = ref<MagicSyncAccount[]>([])
const magicsyncLoading = ref(false)
const selectedPlatforms = ref<string[]>([])

const { API_SETTINGS } = useApiSettings()

const API_BASE = () => API_SETTINGS.value.URL.replace(/\/+$/, '')

const resolveUrl = (url: string) => (url.startsWith('/') ? `${API_BASE()}${url}` : url)

// For a clipper item, subpath = the URL part between the project_id and the filename
// e.g. /static/clipper/projects/<pid>/exports/shorts/<file> -> "exports/shorts"
const clipperSubpath = (item: ClipperVideoItem) => {
  const prefix = `/static/clipper/projects/${item.project_id}/`
  const rest = item.url.startsWith(prefix) ? item.url.slice(prefix.length) : ''
  const parts = rest.split('/').filter(Boolean)
  parts.pop() // filename
  return parts.join('/') || 'renders'
}

const fetchVideos = async () => {
  try {
    const res = await $fetch<{
      status: string
      data: {
        videos: VideoItem[]
        instagram: VideoItem[]
        clipper: ClipperVideoItem[]
        downloads: DownloadItem[]
      }
    }>(`${API_BASE()}/api/getVideos`)
    if (res.status === 'success') {
      videos.value = res.data.videos
      instagramVideos.value = res.data.instagram
      clipperVideos.value = res.data.clipper
      downloads.value = res.data.downloads
    }
  } catch (e) {
    console.error('Failed to fetch videos', e)
  } finally {
    loading.value = false
  }
}

const openScheduleModal = async (video: VideoItem) => {
  selectedVideo.value = video
  scheduleDate.value = null
  scheduleTime.value = null
  scheduleResult.value = null
  selectedPlatforms.value = []
  magicsyncAccounts.value = []
  scheduleContent.value = video.metadata?.post_content || video.metadata?.title || video.metadata?.description || video.filename
  scheduleTitle.value = video.metadata?.title || ''
  scheduleDescription.value = video.metadata?.description || ''
  if (video.metadata?.suggested_schedule) {
    const d = new Date(video.metadata.suggested_schedule)
    scheduleDate.value = d.getTime()
    scheduleTime.value = d.getTime()
  }

  // Auto-select first business if available
  if (magicsyncBusinesses.value.length > 0) {
    selectedBusinessId.value = magicsyncBusinesses.value[0].id
    await fetchAccountsForBusiness(selectedBusinessId.value)
  } else {
    selectedBusinessId.value = null
  }

  scheduleModal.value = true
}

async function fetchAccountsForBusiness(businessId: string | null) {
  if (!businessId) {
    magicsyncAccounts.value = []
    selectedPlatforms.value = []
    return
  }
  const biz = magicsyncBusinesses.value.find(b => b.id === businessId)
  if (!biz) return

  magicsyncLoading.value = true
  magicsyncAccounts.value = []
  selectedPlatforms.value = []
  try {
    const res = await $fetch<{ status: string; data: { accounts: MagicSyncAccount[] }; message?: string }>(
      `${API_BASE()}/api/magicsync/accounts`,
      { method: 'POST', body: { url: biz.url, apiToken: biz.apiToken } }
    )
    if (res.status === 'success') {
      magicsyncAccounts.value = res.data.accounts.filter(a => a.isActive)
      selectedPlatforms.value = [...new Set(magicsyncAccounts.value.map(a => a.platform))]
    }
  } catch (e) {
    console.error('Failed to fetch MagicSync accounts', e)
  } finally {
    magicsyncLoading.value = false
  }
}

const togglePlatform = (platform: string) => {
  const idx = selectedPlatforms.value.indexOf(platform)
  if (idx >= 0) {
    selectedPlatforms.value.splice(idx, 1)
  } else {
    selectedPlatforms.value.push(platform)
  }
}

const handleSchedule = async () => {
  if (!selectedVideo.value || !scheduleDate.value || !scheduleTime.value) return
  if (selectedPlatforms.value.length === 0) return
  if (!selectedBusinessId.value) return

  const biz = magicsyncBusinesses.value.find(b => b.id === selectedBusinessId.value)
  if (!biz) return

  scheduling.value = true
  scheduleResult.value = null

  try {
    const date = new Date(scheduleDate.value)
    const time = new Date(scheduleTime.value)
    date.setHours(time.getHours(), time.getMinutes(), 0, 0)
    const scheduledAt = date.toISOString()

    // Derive the correct fetch path from the item url: generated videos live
    // at /api/video/<f>, Instagram videos at /api/video/instagram/<f>.
    // Passing the bare filename alone produces a broken URL for Instagram.
    const videoFilename = selectedVideo.value.url.startsWith('/api/video/')
      ? selectedVideo.value.url.replace('/api/video/', '')
      : selectedVideo.value.filename

    await $fetch(`${API_BASE()}/api/schedule-to-magicsync`, {
      method: 'POST',
      body: {
        videoFilename,
        scheduledAt,
        content: scheduleContent.value,
        title: scheduleTitle.value,
        description: scheduleDescription.value,
        platforms: selectedPlatforms.value,
        url: biz.url,
        apiToken: biz.apiToken,
        videoBaseUrl: biz.videoBaseUrl,
      }
    })

    scheduleResult.value = 'success'
    setTimeout(() => { scheduleModal.value = false }, 2000)
  } catch (e: any) {
    scheduleResult.value = `Error: ${e?.data?.message || e?.message || 'Unknown error'}`
  } finally {
    scheduling.value = false
  }
}

// — Delete (per-category, with n-popconfirm) —
const deletingKey = ref<string | null>(null)

const confirmDelete = async (category: Category, item: VideoItem | ClipperVideoItem | DownloadItem) => {
  const key = `${category}:${item.filename}`
  deletingKey.value = key
  try {
    const body: Record<string, unknown> = { filename: item.filename, category }
    if (category === 'clipper') {
      const clipperItem = item as ClipperVideoItem
      body.project_id = clipperItem.project_id
      body.subpath = clipperSubpath(clipperItem)
    }
    await $fetch(`${API_BASE()}/api/video/delete`, { method: 'POST', body })
    if (category === 'generated') {
      videos.value = videos.value.filter(v => v.filename !== item.filename)
    } else if (category === 'instagram') {
      instagramVideos.value = instagramVideos.value.filter(v => v.filename !== item.filename)
    } else if (category === 'clipper') {
      clipperVideos.value = clipperVideos.value.filter(v => v.filename !== item.filename)
    } else {
      downloads.value = downloads.value.filter(v => v.filename !== item.filename)
    }
  } catch (e: any) {
    console.error('Delete failed', e)
  } finally {
    deletingKey.value = null
  }
}

const isDeleting = (category: Category, filename: string) => deletingKey.value === `${category}:${filename}`

const deleteButtonClass = (disabled: boolean) => [
  'h-9 w-9 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 flex items-center justify-center text-clipper-ink/60 dark:text-white/60',
  disabled ? 'opacity-50' : 'hover:border-clipper-ink/20 dark:hover:border-white/20 hover:text-clipper-ink',
]

const applySuggestedSchedule = (video: VideoItem) => {
  if (!video.metadata?.suggested_schedule) return
  const date = new Date(video.metadata.suggested_schedule)
  scheduleDate.value = date.getTime()
  scheduleTime.value = date.getTime()
  if (video.metadata.post_content) {
    scheduleContent.value = video.metadata.post_content
  }
  openScheduleModal(video)
}

const uniquePlatforms = computed(() => {
  const seen = new Set<string>()
  for (const acc of magicsyncAccounts.value) {
    seen.add(acc.platform)
  }
  return [...seen]
})

onMounted(fetchVideos)
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-[30px] font-bold leading-tight text-clipper-ink dark:text-white tracking-tight">Videos</h1>
      <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">Your rendered Shorts, CLIPPER exports, Instagram renders and downloads — ready to schedule or delete</p>
    </div>

    <div v-if="loading" class="flex justify-center items-center min-h-[200px]">
      <n-spin size="large" />
    </div>

    <n-tabs v-else type="line" animated>
      <!-- ───── Generated ───── -->
      <n-tab-pane name="generated">
        <template #tab>
          <span class="inline-flex items-center gap-1.5">
            Generated
            <n-badge :value="videos.length" :max="99" type="success" />
          </span>
        </template>

        <div v-if="videos.length === 0" class="py-14 flex justify-center">
          <n-empty description="No generated videos yet. Generate a Short from the workspace.">
            <template #extra>
              <NuxtLink to="/generate" class="inline-flex h-9 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm items-center">Generate video</NuxtLink>
            </template>
          </n-empty>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div v-for="video in videos" :key="video.filename" class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl overflow-hidden flex flex-col hover:border-clipper-ink/16 dark:hover:border-white/15 transition-colors">
            <div class="relative aspect-[9/16] bg-black">
              <video
                class="w-full h-full object-cover"
                :src="resolveUrl(video.url)"
                controls
                preload="metadata"
                crossorigin="anonymous"
              ></video>
            </div>

            <div class="p-4 flex-1 flex flex-col gap-2 min-w-0">
              <h3 class="font-semibold text-clipper-ink dark:text-white truncate text-sm">
                {{ video.metadata?.title || video.filename }}
              </h3>
              <p v-if="video.metadata?.description" class="text-sm text-clipper-ink/60 dark:text-white/60 line-clamp-2">
                {{ video.metadata.description }}
              </p>
              <div v-if="video.metadata?.tags?.length" class="flex flex-wrap gap-1">
                <n-tag v-for="tag in video.metadata.tags" :key="tag" size="small" :bordered="false" class="rounded-full">
                  {{ tag }}
                </n-tag>
              </div>
              <p v-if="video.metadata?.post_content" class="text-xs text-clipper-ink/35 dark:text-white/40 line-clamp-2 italic">
                {{ video.metadata.post_content }}
              </p>
              <div v-if="video.metadata?.suggested_schedule" class="mt-1">
                <span
                  class="text-xs text-clipper-ink/60 dark:text-white/60 cursor-pointer hover:text-clipper-green underline decoration-dotted"
                  @click="applySuggestedSchedule(video)"
                >
                  <Icon name="mdi:calendar-clock" class="inline align-text-bottom" />
                  Schedule: {{ new Date(video.metadata.suggested_schedule).toLocaleString() }}
                </span>
              </div>
            </div>

            <div class="px-4 pb-4 mt-auto flex gap-2">
              <button class="flex-1 h-9 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 flex items-center justify-center gap-1.5" @click="openScheduleModal(video)">
                <Icon name="mdi:calendar-clock" size="14" /> Schedule
              </button>
              <n-popconfirm @positive-click="confirmDelete('generated', video)">
                <template #trigger>
                  <button :class="deleteButtonClass(isDeleting('generated', video.filename))" :disabled="isDeleting('generated', video.filename)" aria-label="Delete video">
                    <Icon name="ph:trash" size="16" />
                  </button>
                </template>
                Delete '{{ video.metadata?.title || video.filename }}'?
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <!-- ───── Clipper ───── -->
      <n-tab-pane name="clipper">
        <template #tab>
          <span class="inline-flex items-center gap-1.5">
            Clipper
            <n-badge :value="clipperVideos.length" :max="99" type="success" />
          </span>
        </template>

        <div v-if="clipperVideos.length === 0" class="py-14 flex justify-center">
          <n-empty description="No CLIPPER renders or exports yet. Process a project to see them here.">
            <template #extra>
              <NuxtLink to="/clipper" class="inline-flex h-9 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm items-center">Open CLIPPER</NuxtLink>
            </template>
          </n-empty>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div v-for="clip in clipperVideos" :key="clip.url" class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl overflow-hidden flex flex-col hover:border-clipper-ink/16 dark:hover:border-white/15 transition-colors">
            <div class="relative aspect-[9/16] bg-black">
              <video
                class="w-full h-full object-cover"
                :src="resolveUrl(clip.url)"
                :poster="clip.thumbnail_url ? resolveUrl(clip.thumbnail_url) : undefined"
                controls
                preload="metadata"
                crossorigin="anonymous"
              ></video>
            </div>

            <div class="p-4 flex-1 flex flex-col gap-2 min-w-0">
              <h3 class="font-semibold text-clipper-ink dark:text-white truncate text-sm">
                {{ clip.hook_title || clip.metadata?.title || clip.filename }}
              </h3>
              <div class="flex flex-wrap gap-1">
                <n-tag v-if="clip.project_name" size="small" :bordered="false" class="rounded-full">
                  {{ clip.project_name }}
                </n-tag>
                <n-tag v-if="clip.export_format" size="small" type="success" :bordered="false" class="rounded-full">
                  {{ clip.export_format }}
                </n-tag>
              </div>
              <p v-if="clip.modified" class="text-xs text-clipper-ink/35 dark:text-white/40">
                {{ new Date(clip.modified).toLocaleString() }}
              </p>
            </div>

            <div class="px-4 pb-4 mt-auto flex gap-2">
              <NuxtLink
                v-if="clip.clip_id"
                :to="`/clipper/studio/${clip.clip_id}`"
                class="flex-1 h-9 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 flex items-center justify-center gap-1.5"
              >
                <Icon name="ph:pencil-simple" size="14" /> Open in editor
              </NuxtLink>
              <n-popconfirm @positive-click="confirmDelete('clipper', clip)">
                <template #trigger>
                  <button :class="deleteButtonClass(isDeleting('clipper', clip.filename))" :disabled="isDeleting('clipper', clip.filename)" aria-label="Delete clipper video">
                    <Icon name="ph:trash" size="16" />
                  </button>
                </template>
                Delete '{{ clip.hook_title || clip.filename }}'?
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <!-- ───── Instagram ───── -->
      <n-tab-pane name="instagram">
        <template #tab>
          <span class="inline-flex items-center gap-1.5">
            Instagram
            <n-badge :value="instagramVideos.length" :max="99" type="success" />
          </span>
        </template>

        <div v-if="instagramVideos.length === 0" class="py-14 flex justify-center">
          <n-empty description="No Instagram renders yet." />
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div v-for="video in instagramVideos" :key="video.filename" class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl overflow-hidden flex flex-col hover:border-clipper-ink/16 dark:hover:border-white/15 transition-colors">
            <div class="relative aspect-[9/16] bg-black">
              <video
                class="w-full h-full object-cover"
                :src="resolveUrl(video.url)"
                controls
                preload="metadata"
                crossorigin="anonymous"
              ></video>
            </div>

            <div class="p-4 flex-1 flex flex-col gap-2 min-w-0">
              <h3 class="font-semibold text-clipper-ink dark:text-white truncate text-sm">
                {{ video.metadata?.title || video.filename }}
              </h3>
              <p v-if="video.metadata?.description" class="text-sm text-clipper-ink/60 dark:text-white/60 line-clamp-2">
                {{ video.metadata.description }}
              </p>
              <div v-if="video.metadata?.tags?.length" class="flex flex-wrap gap-1">
                <n-tag v-for="tag in video.metadata.tags" :key="tag" size="small" :bordered="false" class="rounded-full">
                  {{ tag }}
                </n-tag>
              </div>
              <p v-if="video.metadata?.post_content" class="text-xs text-clipper-ink/35 dark:text-white/40 line-clamp-2 italic">
                {{ video.metadata.post_content }}
              </p>
              <div v-if="video.metadata?.suggested_schedule" class="mt-1">
                <span
                  class="text-xs text-clipper-ink/60 dark:text-white/60 cursor-pointer hover:text-clipper-green underline decoration-dotted"
                  @click="applySuggestedSchedule(video)"
                >
                  <Icon name="mdi:calendar-clock" class="inline align-text-bottom" />
                  Schedule: {{ new Date(video.metadata.suggested_schedule).toLocaleString() }}
                </span>
              </div>
            </div>

            <div class="px-4 pb-4 mt-auto flex gap-2">
              <button class="flex-1 h-9 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 flex items-center justify-center gap-1.5" @click="openScheduleModal(video)">
                <Icon name="mdi:calendar-clock" size="14" /> Schedule
              </button>
              <n-popconfirm @positive-click="confirmDelete('instagram', video)">
                <template #trigger>
                  <button :class="deleteButtonClass(isDeleting('instagram', video.filename))" :disabled="isDeleting('instagram', video.filename)" aria-label="Delete video">
                    <Icon name="ph:trash" size="16" />
                  </button>
                </template>
                Delete '{{ video.metadata?.title || video.filename }}'?
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <!-- ───── Downloads ───── -->
      <n-tab-pane name="downloads">
        <template #tab>
          <span class="inline-flex items-center gap-1.5">
            Downloads
            <n-badge :value="downloads.length" :max="99" type="success" />
          </span>
        </template>

        <div v-if="downloads.length === 0" class="py-14 flex justify-center">
          <n-empty description="No downloaded assets yet." />
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div v-for="file in downloads" :key="file.filename" class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl overflow-hidden flex flex-col hover:border-clipper-ink/16 dark:hover:border-white/15 transition-colors">
            <div class="relative aspect-video bg-black">
              <video
                class="w-full h-full object-cover"
                :src="resolveUrl(file.url)"
                controls
                preload="metadata"
                crossorigin="anonymous"
              ></video>
            </div>

            <div class="p-4 flex-1 flex flex-col gap-2 min-w-0">
              <h3 class="font-semibold text-clipper-ink dark:text-white truncate text-sm">
                {{ file.filename }}
              </h3>
              <div class="flex flex-wrap gap-1">
                <n-tag size="small" :bordered="false" class="rounded-full">
                  {{ file.size_mb }} MB
                </n-tag>
              </div>
            </div>

            <div class="px-4 pb-4 mt-auto flex gap-2">
              <a
                :href="resolveUrl(file.url)"
                :download="file.filename"
                class="flex-1 h-9 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 flex items-center justify-center gap-1.5"
              >
                <Icon name="ph:download-simple" size="14" /> Download
              </a>
              <n-popconfirm @positive-click="confirmDelete('downloads', file)">
                <template #trigger>
                  <button :class="deleteButtonClass(isDeleting('downloads', file.filename))" :disabled="isDeleting('downloads', file.filename)" aria-label="Delete download">
                    <Icon name="ph:trash" size="16" />
                  </button>
                </template>
                Delete '{{ file.filename }}'?
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-tab-pane>
    </n-tabs>

    <n-modal
      v-model:show="scheduleModal"
      preset="card"
      title="Schedule Upload"
      style="max-width: 520px"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <div v-if="selectedVideo">
          <p class="text-sm text-clipper-ink/60 dark:text-white/60">
            Video:
            <span class="text-clipper-ink dark:text-white font-medium">{{ selectedVideo.metadata?.title || selectedVideo.filename }}</span>
          </p>
        </div>

        <div v-if="magicsyncBusinesses.length > 0">
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mb-1">Business</label>
          <n-select
            v-model:value="selectedBusinessId"
            :options="magicsyncBusinesses.map(b => ({ label: b.name, value: b.id }))"
            class="w-full"
            @update:value="fetchAccountsForBusiness"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mb-1">Date</label>
          <n-date-picker v-model:value="scheduleDate" type="date" class="w-full" />
        </div>

        <div>
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mb-1">Time</label>
          <n-time-picker v-model:value="scheduleTime" class="w-full" />
        </div>

        <div>
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mb-1">Post Content</label>
          <n-input v-model:value="scheduleContent" type="textarea" :rows="3" placeholder="Post text..." class="w-full" />
        </div>

        <div>
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mb-1">Title (optional)</label>
          <n-input v-model:value="scheduleTitle" placeholder="Video title" class="w-full" />
        </div>

        <div>
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mb-1">Description (optional)</label>
          <n-input v-model:value="scheduleDescription" type="textarea" :rows="2" placeholder="Video description" class="w-full" />
        </div>

        <div>
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mb-1">
            Post to
            <span v-if="magicsyncLoading" class="text-xs ml-1">(loading...)</span>
          </label>
          <div v-if="magicsyncLoading" class="flex items-center gap-2 text-sm text-clipper-ink/60 dark:text-white/60">
            <n-spin size="small" />
            Fetching connected accounts...
          </div>
          <div v-else-if="magicsyncBusinesses.length === 0" class="text-sm text-clipper-ink/60 dark:text-white/60 border border-dashed border-clipper-ink/12 dark:border-white/10 rounded-lg p-3">
            No MagicSync businesses configured.
            <NuxtLink to="/settings" class="underline text-clipper-green">Add one in Settings</NuxtLink>
          </div>
          <div v-else-if="uniquePlatforms.length === 0 && !magicsyncLoading" class="text-sm text-clipper-ink/60 dark:text-white/60 border border-dashed border-clipper-ink/12 dark:border-white/10 rounded-lg p-3">
            No connected accounts for this business.
          </div>
          <div v-else class="space-y-2">
            <div v-for="platform in uniquePlatforms" :key="platform" class="flex items-center gap-2">
              <n-checkbox
                :checked="selectedPlatforms.includes(platform)"
                @update:checked="togglePlatform(platform)"
              >
                <span class="text-sm capitalize">{{ platform }}</span>
              </n-checkbox>
            </div>
          </div>
        </div>

        <div v-if="scheduleResult === 'success'" class="text-clipper-ink dark:text-white text-sm font-medium flex items-center gap-1">
          <Icon name="ph:check-circle" class="text-clipper-green" /> Scheduled successfully!
        </div>
        <div v-else-if="scheduleResult" class="text-sm text-clipper-ink/60 dark:text-white/60">
          {{ scheduleResult }}
        </div>

        <div class="flex gap-3 pt-2">
          <button class="flex-1 h-10 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm font-medium text-clipper-ink dark:text-white" @click="scheduleModal = false">Cancel</button>
          <button
            class="flex-1 h-10 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 disabled:opacity-50"
            :disabled="!scheduleDate || !scheduleTime || selectedPlatforms.length === 0 || scheduling"
            @click="handleSchedule"
          >
            {{ scheduling ? 'Scheduling...' : 'Schedule' }}
          </button>
        </div>
      </div>
    </n-modal>
  </div>
</template>
