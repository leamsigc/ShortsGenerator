<script lang="ts" setup>
/**
 * CLIPPER — main workspace page.
 * Stripe-inspired, Poppins, Ink + Green only.
 * Layout per STYLEGUIDE §14, §71-72: horizontal header already in layout,
 * body = title + control bar + 3-column workspace + timeline full-width.
 * No sidebar, no gradients, no dark slate.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
import { useClipperStore, EXPORT_FORMATS, EXPORT_QUALITIES } from "~/stores/ClipperStore"
import type { PublishRecord, OutlineItem } from "~/stores/ClipperStore"
import { useStorage } from "@vueuse/core"
import ClipperProjectManager from "~/components/clipper/ProjectManager.vue"

const clipperStore = useClipperStore()
const message = useMessage()
const route = useRoute()

const loading = ref(false)
const searchQuery = ref("")
const filterMode = ref<"top" | "recent" | "all">("top")
const showNewProjectFromHeader = ref(false)

// View sync with header navigation via query ?view=
type ViewKey = "clips" | "sources" | "transcript" | "publish" | "settings"
const syncViewFromRoute = () => {
  const v = route.query.view as ViewKey
  if (v && ["clips", "sources", "transcript", "publish", "settings"].includes(v)) {
    clipperStore.activeView = v
  } else if (!route.query.view && clipperStore.currentProject) {
    clipperStore.activeView = "clips"
  }
}
syncViewFromRoute()
watch(() => route.query.view, () => syncViewFromRoute())

// Project creation
const handleCreateProject = async (data: {
  name: string
  description: string
  source_urls: string[]
  training_data: string
  target_platform: string
}) => {
  loading.value = true
  try {
    const project = await clipperStore.createProject(data)
    if (project) {
      await clipperStore.setCurrentProject(project.id)
      clipperStore.activeView = "clips"
      navigateTo("/clipper?view=clips")
      message.success(`Project "${project.name}" created`)
    }
  } catch (e) {
    console.error("Failed to create project", e)
    message.error("Failed to create project")
  } finally {
    loading.value = false
  }
}

const selectProject = async (projectId: string) => {
  await clipperStore.setCurrentProject(projectId)
  await clipperStore.fetchProjectClips(projectId)
  await clipperStore.loadTranscripts(projectId)
  clipperStore.activeView = "clips"
  navigateTo("/clipper?view=clips")
}

// Listen for header "+ New Project" event
onMounted(() => {
  const handler = () => {
    const mgr: any = projectManagerRef.value
    if (mgr?.openModal) mgr.openModal()
  }
  window.addEventListener("clipper-new-project", handler)
  onUnmounted(() => window.removeEventListener("clipper-new-project", handler))
})

// Processing — "auto" lets Whisper detect the video's spoken language so
// subtitles match the audio instead of forcing English.
const transcriptionLanguage = ref("auto")
const whisperModelSize = ref("")
const handleProcessProject = async () => {
  if (!clipperStore.currentProject) return
  loading.value = true
  try {
    const result = await clipperStore.processProject(clipperStore.currentProject.id, transcriptionLanguage.value, {
      modelSize: whisperModelSize.value || undefined,
    })
    if (result) message.success("Sources processed")
    else message.info("Processing cancelled")
  } catch (e) {
    console.error("Failed to process project", e)
    message.error("Failed to process project")
  } finally {
    loading.value = false
  }
}

const handleSelectClips = async () => {
  if (!clipperStore.currentProject) return
  loading.value = true
  try {
    const result = await clipperStore.selectClips(clipperStore.currentProject.id, {
      max_clips: 7,
      // ai_model omitted on purpose: backend uses the configured provider (gemini by default)
      model_size: whisperModelSize.value || undefined,
    })
    if (result) message.success("Top clips selected")
    else message.info("Processing cancelled")
  } catch (e) {
    console.error("Failed to select clips", e)
    message.error("Failed to select clips")
  } finally {
    loading.value = false
  }
}

const handleCancelProcessing = async () => {
  try {
    await clipperStore.cancelProcessing(clipperStore.currentProject?.id)
    message.info("Processing cancelled")
  } catch (e) {
    console.error("Failed to cancel processing", e)
    message.error("Failed to cancel processing")
  }
}

const handleAddSource = async (url: string) => {
  if (!clipperStore.currentProject) return
  try {
    await clipperStore.addSource(clipperStore.currentProject.id, url)
    message.success("Source added")
  } catch (e) {
    console.error("Failed to add source", e)
    message.error("Failed to add source")
  }
}

const handleRemoveSource = async (sourceId: string) => {
  if (!clipperStore.currentProject) return
  try {
    await clipperStore.removeSource(clipperStore.currentProject.id, sourceId)
    message.success("Source removed")
  } catch (e) {
    console.error("Failed to remove source", e)
    message.error("Failed to remove source")
  }
}

const exportFormat = ref<string>("tiktok")
const exportQuality = ref<string>("high")
const exportBurn = ref(false)

const handleExportClips = async () => {
  if (!clipperStore.currentProject || clipperStore.selectedClips.length === 0) return
  loading.value = true
  try {
    const result = await clipperStore.exportClips(
      clipperStore.currentProject.id,
      clipperStore.selectedClips,
      exportFormat.value,
      exportQuality.value,
      exportBurn.value
    )
    if (result) message.success("Export finished")
    else message.info("Processing cancelled")
  } catch (e) {
    console.error("Failed to export clips", e)
    message.error("Failed to export clips")
  } finally {
    loading.value = false
  }
}

const handleProjectUpdate = async (data: any) => {
  if (!clipperStore.currentProject) return
  try {
    await clipperStore.updateProject(clipperStore.currentProject.id, data)
    message.success("Project updated")
  } catch (e) {
    message.error("Could not update project")
  }
}

const handleDeleteCurrentProject = async () => {
  if (!clipperStore.currentProject) return
  const id = clipperStore.currentProject.id
  try {
    await clipperStore.deleteProject(id)
    message.success("Project deleted")
    clipperStore.activeView = "clips"
    navigateTo("/clipper")
  } catch (e) {
    message.error("Failed to delete project")
  }
}

const filteredClips = computed(() => {
  let list = [...clipperStore.clips]
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(c =>
      (c.hook_title || "").toLowerCase().includes(q) ||
      (c.transcript || "").toLowerCase().includes(q)
    )
  }
  if (filterMode.value === "top") {
    list = list.sort((a, b) => b.scores.overall_score - a.scores.overall_score)
  } else if (filterMode.value === "recent") {
    list = list.sort((a, b) => b.index - a.index)
  }
  return list
})

const projectManagerRef = ref<InstanceType<typeof ClipperProjectManager> | null>(null)

// Transcript aggregation for "transcript" view
const allSentences = computed(() => {
  const p = clipperStore.currentProject
  if (!p) return []
  const all: any[] = []
  for (const sid of p.source_ids || []) {
    const t = clipperStore.transcripts[`${p.id}/${sid}`]
    if (t?.sentences) all.push(...t.sentences)
  }
  return all.slice(0, 800)
})

// Topic outline across all transcripts for "transcript" view
const transcriptOutlines = computed<OutlineItem[]>(() => {
  const p = clipperStore.currentProject
  if (!p) return []
  const outlines: OutlineItem[] = []
  for (const sid of p.source_ids || []) {
    const t = clipperStore.transcripts[`${p.id}/${sid}`]
    if (t?.outline?.length) outlines.push(...t.outline)
  }
  return outlines
})

const fmtTime = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`

// Filters popover — min score
const showFilters = ref(false)
const minScoreFilter = ref(0)
const minScoreOptions = [0, 40, 60, 70]
const applyMinScore = async (score: number) => {
  minScoreFilter.value = score
  showFilters.value = false
  if (clipperStore.currentProject) {
    await clipperStore.fetchProjectClips(clipperStore.currentProject.id, score)
  }
}

// Publish view — records grouped by day
const publishLoading = ref(false)
const loadPublishRecords = async () => {
  if (!clipperStore.currentProject) return
  publishLoading.value = true
  try {
    await clipperStore.fetchPublishRecords(clipperStore.currentProject.id)
  } finally {
    publishLoading.value = false
  }
}
watch(() => clipperStore.activeView, (v) => {
  if (v === "publish") loadPublishRecords()
})

const groupedPublishRecords = computed<{ date: string; records: PublishRecord[] }[]>(() => {
  const sorted = [...clipperStore.publishRecords].sort(
    (a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime()
  )
  const groups: { date: string; records: PublishRecord[] }[] = []
  for (const r of sorted) {
    const key = new Date(r.scheduled_at).toLocaleDateString()
    let g = groups.find(g => g.date === key)
    if (!g) {
      g = { date: key, records: [] }
      groups.push(g)
    }
    g.records.push(r)
  }
  return groups
})

const handleDeletePublishRecord = async (recordId: string) => {
  if (!clipperStore.currentProject) return
  try {
    await clipperStore.deletePublishRecord(clipperStore.currentProject.id, recordId)
    message.success("Publish record deleted")
  } catch (e) {
    console.error("Failed to delete publish record", e)
    message.error("Failed to delete publish record")
  }
}

// Add source dialog for Sources view
const showAddSource = ref(false)
const pendingUrl = ref("")

const submitAddSource = async () => {
  const url = pendingUrl.value.trim()
  if (!url) return
  await handleAddSource(url)
  pendingUrl.value = ""
  showAddSource.value = false
}

const pendingGoldenUrl = ref("")
const handleAddGolden = async () => {
  const u = pendingGoldenUrl.value.trim()
  if (!u || !clipperStore.currentProject) return
  const next = [...(clipperStore.currentProject.golden_urls || []), u]
  await handleProjectUpdate({ golden_urls: next })
  pendingGoldenUrl.value = ""
}
const handleRemoveGolden = async (idx: number) => {
  if (!clipperStore.currentProject) return
  const next = (clipperStore.currentProject.golden_urls || []).filter((_:string, i:number) => i!==idx)
  await handleProjectUpdate({ golden_urls: next })
}
const pendingExtraUrl = ref("")
const handleAddExtra = async () => {
  const u = pendingExtraUrl.value.trim()
  if (!u || !clipperStore.currentProject) return
  const next = [...(clipperStore.currentProject.extra_resources || []), u]
  await handleProjectUpdate({ extra_resources: next })
  pendingExtraUrl.value = ""
}
const handleRemoveExtra = async (idx: number) => {
  if (!clipperStore.currentProject) return
  const next = (clipperStore.currentProject.extra_resources || []).filter((_:string, i:number) => i!==idx)
  await handleProjectUpdate({ extra_resources: next })
}

// Batch schedule for selected clips (like generate view)
const batchScheduleModal = ref(false)
const batchScheduleDate = ref<number | null>(null)
const batchScheduleTime = ref<number | null>(null)
const batchScheduling = ref(false)
const batchScheduleResult = ref<string | null>(null)
const batchVisibility = ref("")
const batchSelectedPlatforms = ref<string[]>([])
const batchMagicsyncAccounts = ref<any[]>([])
const batchMagicsyncLoading = ref(false)
const batchMagicsyncBusinesses = useStorage<any[]>("MAGICSYNC_BUSINESSES", [])
const batchSelectedBusinessId = ref<string | null>(null)

const openBatchSchedule = async () => {
  if (clipperStore.selectedClips.length === 0) return
  batchScheduleDate.value = null; batchScheduleTime.value = null; batchScheduleResult.value = null
  batchVisibility.value = ""
  batchSelectedPlatforms.value = []; batchMagicsyncAccounts.value = []
  if (batchMagicsyncBusinesses.value.length > 0) {
    batchSelectedBusinessId.value = batchMagicsyncBusinesses.value[0].id
    await fetchBatchAccounts(batchSelectedBusinessId.value)
  } else batchSelectedBusinessId.value = null
  batchScheduleModal.value = true
}
async function fetchBatchAccounts(businessId: string | null) {
  if (!businessId) { batchMagicsyncAccounts.value = []; batchSelectedPlatforms.value = []; return }
  const biz = batchMagicsyncBusinesses.value.find((b:any) => b.id === businessId)
  if (!biz) return
  batchMagicsyncLoading.value = true; batchMagicsyncAccounts.value = []; batchSelectedPlatforms.value = []
  try {
    const res = await $fetch<{ status: string; data: { accounts: any[] } }>(`${useApiSettings().API_SETTINGS.value.URL}/api/magicsync/accounts`, { method: 'POST', body: { url: biz.url, apiToken: biz.apiToken } })
    if (res.status === 'success') {
      batchMagicsyncAccounts.value = res.data.accounts.filter((a:any) => a.isActive)
      batchSelectedPlatforms.value = [...new Set(batchMagicsyncAccounts.value.map((a:any) => a.platform))]
    }
  } catch(e){ console.error(e) } finally { batchMagicsyncLoading.value = false }
}
const batchUniquePlatforms = computed(() => [...new Set(batchMagicsyncAccounts.value.map((a:any) => a.platform))])
const toggleBatchPlatform = (p:string)=> {
  const i=batchSelectedPlatforms.value.indexOf(p)
  if(i>=0) batchSelectedPlatforms.value.splice(i,1); else batchSelectedPlatforms.value.push(p)
}
const handleBatchSchedule = async () => {
  if (!batchScheduleDate.value || !batchScheduleTime.value || batchSelectedPlatforms.value.length===0 || !batchSelectedBusinessId.value) return
  const biz = batchMagicsyncBusinesses.value.find((b:any)=> b.id===batchSelectedBusinessId.value)
  if (!biz) return
  batchScheduling.value = true; batchScheduleResult.value = null
  try {
    const date = new Date(batchScheduleDate.value); const time = new Date(batchScheduleTime.value)
    date.setHours(time.getHours(), time.getMinutes(), 0,0)
    const scheduledAt = date.toISOString()
    for (const clipId of clipperStore.selectedClips) {
      const clip = clipperStore.clipById(clipId)
      if (!clip) continue
      await clipperStore.scheduleClip(clipId, {
        scheduledAt,
        content: clip.post_content || clip.title || clip.hook_title || "",
        title: clip.title || clip.hook_title || "",
        description: clip.description || clip.transcript?.slice(0,200) || "",
        platforms: batchSelectedPlatforms.value,
        url: biz.url,
        apiToken: biz.apiToken,
        videoBaseUrl: biz.videoBaseUrl,
        visibility: batchVisibility.value,
      })
    }
    batchScheduleResult.value = 'success'
    setTimeout(()=> batchScheduleModal.value=false, 1500)
  } catch(e:any){ batchScheduleResult.value = `Error: ${e?.data?.message || e?.message || 'Unknown'}` }
  finally { batchScheduling.value = false }
}

const languageOptions = [
  { label: "Auto-detect", value: "auto" },
  { label: "English", value: "en" },
  { label: "Spanish", value: "es" },
  { label: "German", value: "de" },
  { label: "French", value: "fr" },
  { label: "Portuguese", value: "pt" },
  { label: "Italian", value: "it" },
  { label: "Dutch", value: "nl" },
]

const whisperModelOptions = [
  { label: "Default", value: "" },
  { label: "Tiny", value: "tiny" },
  { label: "Base", value: "base" },
  { label: "Small", value: "small" },
  { label: "Medium", value: "medium" },
  { label: "Large v3", value: "large-v3" },
]

onMounted(async () => {
  await clipperStore.fetchProjects()
  if (clipperStore.currentProject?.id) {
    await clipperStore.fetchProjectClips(clipperStore.currentProject.id)
    await clipperStore.loadTranscripts(clipperStore.currentProject.id)
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- No project yet → dashboard -->
    <template v-if="!clipperStore.currentProject">
      <ClipperProjectManager
        ref="projectManagerRef"
        :projects="clipperStore.projects"
        :current-project-id="null"
        @select="selectProject"
        @delete="(id: string) => clipperStore.deleteProject(id)"
        @create="handleCreateProject"
      />
      <!-- Secondary: allow processing demo without project? no -->
    </template>

    <!-- Project workspace -->
    <template v-else>
      <!-- Title block per §71 -->
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-start gap-3">
          <button
            class="mt-1 w-9 h-9 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 flex items-center justify-center hover:border-clipper-ink/20 dark:hover:border-white/20 shrink-0"
            title="Back to projects"
            aria-label="Back to projects"
            @click="() => { clipperStore.currentProject = null; navigateTo('/clipper') }"
          >
            <Icon name="ph:arrow-left" size="16" class="text-clipper-ink dark:text-white" />
          </button>
          <div>
            <h1 class="text-[30px] font-bold leading-tight text-clipper-ink dark:text-white tracking-tight">
              {{ { clips: 'Clips', sources: 'Sources', transcript: 'Transcript', publish: 'Publish', settings: 'Settings' }[clipperStore.activeView] }}
            </h1>
            <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">
              <template v-if="clipperStore.activeView === 'clips'">Top clips from your sources</template>
              <template v-else-if="clipperStore.activeView === 'sources'">Manage your source videos</template>
              <template v-else-if="clipperStore.activeView === 'transcript'">Word-level transcript synced to timeline</template>
              <template v-else-if="clipperStore.activeView === 'publish'">Scheduled posts and publish history</template>
              <template v-else>Configure output and language</template>
            </p>
          </div>
        </div>
        <div v-if="clipperStore.activeView === 'clips'" class="hidden sm:flex items-center gap-2">
          <button
            v-if="clipperStore.selectedClips.length > 0"
            class="h-10 px-4 rounded-lg text-sm font-semibold bg-clipper-green text-clipper-ink hover:opacity-90 disabled:opacity-50"
            :disabled="loading"
            @click="openBatchSchedule"
          >
            Schedule Selected ({{ clipperStore.selectedClips.length }})
          </button>
          <template v-if="clipperStore.selectedClips.length > 0">
            <n-select
              v-model:value="exportFormat"
              size="small"
              class="w-28"
              title="Export format"
              :options="EXPORT_FORMATS.map(f => ({ label: f, value: f }))" />
            <n-select
              v-model:value="exportQuality"
              size="small"
              class="w-24"
              title="Export quality"
              :options="EXPORT_QUALITIES.map(q => ({ label: q, value: q }))" />
            <n-checkbox v-model:checked="exportBurn" title="Burn subtitles into exported video">
              <span class="text-xs font-medium text-clipper-ink/60 dark:text-white/60">Subs</span>
            </n-checkbox>
            <button
              class="h-10 px-4 rounded-lg text-sm font-semibold bg-clipper-green text-clipper-ink hover:opacity-90 disabled:opacity-50"
              :disabled="loading"
              @click="handleExportClips"
            >
              Export Selected ({{ clipperStore.selectedClips.length }})
            </button>
          </template>
          <button
            class="h-10 w-10 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 flex items-center justify-center hover:border-clipper-ink/20 dark:hover:border-white/20"
            title="Undo"
            aria-label="Undo"
            @click="searchQuery = ''; filterMode = 'top'"
          >
            <Icon name="ph:arrow-u-up-left" size="16" class="text-clipper-ink/60 dark:text-white/60" />
          </button>
        </div>
      </div>

      <!-- Control bar per §71: [Search] [Top Clips] [Filters] [9:16] -->
      <div
        v-if="clipperStore.activeView === 'clips'"
        class="flex flex-wrap items-center gap-3 border-y border-clipper-ink/08 dark:border-white/08 py-3"
      >
        <div class="flex items-center gap-2 flex-1 min-w-[220px] max-w-[400px]">
          <div class="relative flex-1">
            <Icon name="ph:magnifying-glass" size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-clipper-ink/35 dark:text-white/40" />
            <input
              v-model="searchQuery"
              placeholder="Search clips..."
              class="w-full h-10 pl-9 pr-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm text-clipper-ink placeholder:text-clipper-ink/35 dark:text-white/40 focus:outline-none focus:border-clipper-green focus:ring-1 focus:ring-clipper-green/20"
            />
          </div>
        </div>

        <div class="flex items-center gap-2">
          <n-select
            v-model:value="filterMode"
            size="small"
            class="w-32"
            :options="[
              { label: 'Top Clips', value: 'top' },
              { label: 'Recent', value: 'recent' },
              { label: 'All', value: 'all' },
            ]"
          />
          <div class="relative">
            <button
              class="h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm font-medium text-clipper-ink dark:text-white hover:border-clipper-ink/20 dark:hover:border-white/20 flex items-center gap-1.5"
              :class="{ 'border-clipper-green': minScoreFilter > 0 }"
              @click="showFilters = !showFilters"
            >
              <Icon name="ph:funnel" size="14" /> Filters{{ minScoreFilter > 0 ? ` (${minScoreFilter}+)` : '' }}
            </button>
            <div
              v-if="showFilters"
              class="absolute right-0 top-11 z-30 w-44 bg-white dark:bg-neutral-800 border border-clipper-ink/12 dark:border-white/10 rounded-lg p-2 space-y-1 shadow-lg"
            >
              <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50 px-1 py-1">Minimum score</p>
              <button
                v-for="s in minScoreOptions"
                :key="s"
                class="w-full h-8 px-2 rounded-md text-sm font-medium text-left"
                :class="minScoreFilter === s ? 'bg-clipper-green/15 text-clipper-ink dark:text-white' : 'text-clipper-ink/60 dark:text-white/60 hover:bg-neutral-100 dark:hover:bg-white/5'"
                @click="applyMinScore(s)"
              >
                {{ s === 0 ? 'All clips' : `${s}+` }}
              </button>
            </div>
          </div>
        </div>

        <div class="ml-auto flex items-center gap-2">
          <button class="h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm font-medium text-clipper-ink dark:text-white hover:border-clipper-ink/20 flex items-center gap-1.5" @click="showAddSource = true">
            <Icon name="ph:plus" size="14" /> Add Source
          </button>
          <button v-if="clipperStore.currentProject" class="h-10 w-10 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 flex items-center justify-center hover:border-red-300 hover:text-red-500 text-clipper-ink/60 dark:text-white/60" title="Delete project" @click="handleDeleteCurrentProject">
            <Icon name="ph:trash" size="16" />
          </button>
          <span class="hidden sm:inline text-xs font-medium text-clipper-ink/60 dark:text-white/60 border border-clipper-ink/10 dark:border-white/10 rounded-md px-2 py-1">9:16</span>
          <n-select
            v-model:value="whisperModelSize"
            size="small"
            class="w-32"
            title="Whisper model size"
            :options="whisperModelOptions"
          />
          <n-select
            v-model:value="transcriptionLanguage"
            size="small"
            class="w-32"
            :options="languageOptions"
          />
        </div>
      </div>

      <!-- Inline source list for quick add/delete in clips view (so user doesn't need to switch to Sources) -->
      <div v-if="clipperStore.currentProject?.source_urls?.length" class="flex flex-wrap items-center gap-2 py-2">
        <span class="text-xs font-medium text-clipper-ink/50 dark:text-white/50">Sources:</span>
        <span v-for="(url, idx) in clipperStore.currentProject.source_urls" :key="idx" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-neutral-100 dark:bg-neutral-700 border border-clipper-ink/08 dark:border-white/10 text-clipper-ink dark:text-white/80">
          <Icon :name="url.startsWith('local://') ? 'mdi:file-video-outline' : url.includes('youtube') || url.includes('youtu.be') ? 'ph:youtube-logo' : url.includes('instagram') ? 'ph:instagram-logo' : 'ph:file-video'" size="12" />
          <span class="max-w-[180px] truncate">{{ url.startsWith('local://') ? decodeURIComponent(url.slice(8)) : (url.split('/').pop() || url.slice(0,24)) }}</span>
          <button class="ml-1 text-clipper-ink/40 hover:text-red-500" @click="handleRemoveSource(clipperStore.currentProject.source_ids[idx])" title="Remove source">✕</button>
        </span>
        <button class="text-xs text-clipper-green hover:underline" @click="showAddSource = true">+ Add</button>
        <NuxtLink to="/clipper?view=sources" class="text-xs text-clipper-ink/60 dark:text-white/60 hover:text-clipper-ink underline ml-2">Manage →</NuxtLink>
      </div>

      <!-- Processing progress (highly visible per §38-39) -->
      <div v-if="clipperStore.progress" class="flex items-start gap-3">
        <div class="flex-1 min-w-0">
          <ClipperProcessingProgress
            :stage="clipperStore.progress.stage"
            :progress="clipperStore.progress.progress"
            :message="clipperStore.progress.message"
            :current-clip="clipperStore.progress.current_clip"
            :total-clips="clipperStore.progress.total_clips"
          />
        </div>
        <button
          v-if="clipperStore.processing"
          class="h-10 px-4 shrink-0 rounded-lg border border-red-200 dark:border-red-500/30 bg-white dark:bg-neutral-800 text-sm font-semibold text-red-500 hover:border-red-400"
          @click="handleCancelProcessing"
        >
          <Icon name="ph:x-circle" size="16" class="inline mr-1 -mt-0.5" />
          Cancel
        </button>
      </div>

      <!-- ───── View: CLIPS (main workspace) ───── -->
      <div v-if="clipperStore.activeView === 'clips'">
        <!-- When no clips, show empty + actions -->
        <div v-if="!loading && filteredClips.length === 0 && clipperStore.clips.length === 0" class="border border-clipper-ink/08 dark:border-white/08 rounded-xl py-16 text-center bg-white dark:bg-neutral-800">
          <Icon name="ph:scissors" size="44" class="mx-auto text-clipper-ink dark:text-white/20 mb-3" />
          <h3 class="text-base font-semibold text-clipper-ink dark:text-white">No clips yet</h3>
          <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">Process your sources to discover high-potential moments.</p>
          <div class="mt-5 flex gap-2 justify-center">
            <button class="h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 disabled:opacity-50" :disabled="loading || !clipperStore.currentProject.source_urls.length" @click="handleProcessProject">
              Process Sources
            </button>
            <button class="h-10 px-4 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm font-medium text-clipper-ink dark:text-white hover:border-clipper-ink/20 dark:hover:border-white/20" @click="handleSelectClips">
              Select Top Clips
            </button>
          </div>
        </div>

        <!-- Clip workspace: use ClipEditor which already implements 3-col layout per §15 -->
        <ClipperClipEditor v-else-if="filteredClips.length > 0" />

        <!-- Search empty -->
        <div v-else-if="filteredClips.length === 0 && clipperStore.clips.length > 0" class="border border-clipper-ink/08 dark:border-white/08 rounded-xl py-12 text-center bg-white dark:bg-neutral-800">
          <p class="text-sm text-clipper-ink/60 dark:text-white/60">No clips match "{{ searchQuery }}"</p>
          <button class="mt-3 text-sm font-medium text-clipper-green hover:underline" @click="searchQuery = ''">Clear search</button>
        </div>
      </div>

      <!-- ───── View: SOURCES ───── -->
      <div v-else-if="clipperStore.activeView === 'sources'" class="space-y-4">
        <ClipperVideoUploader
          :source-urls="clipperStore.currentProject.source_urls"
          :source-ids="clipperStore.currentProject.source_ids"
          :project-id="clipperStore.currentProject.id"
          @add="handleAddSource"
          @remove="handleRemoveSource"
        />
        <ClipperSourceList
          :sources="(clipperStore.currentProject.source_urls || []).map((url: string, idx: number) => ({
            id: clipperStore.currentProject!.source_ids[idx] || `src-${idx}`,
            url,
            platform: url.includes('youtube') || url.includes('youtu.be') ? 'YouTube' : url.includes('instagram') ? 'Instagram' : 'MP4',
            duration: 0,
            transcribed: false,
          }))"
          :project-id="clipperStore.currentProject.id"
          @add="showAddSource = true"
          @remove="handleRemoveSource"
        />

        <!-- Add source dialog -->
        <div v-if="showAddSource" class="fixed inset-0 z-50 bg-clipper-ink/35 flex items-center justify-center p-6" @click.self="showAddSource = false">
          <div class="w-full max-w-[480px] bg-white dark:bg-neutral-800 rounded-xl p-6 border border-clipper-ink/08 dark:border-white/08">
            <h3 class="text-base font-semibold text-clipper-ink dark:text-white">Add Source</h3>
            <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">Paste a YouTube or direct video URL</p>
            <input
              v-model="pendingUrl"
              placeholder="Paste video URL..."
              class="mt-4 w-full h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm focus:outline-none focus:border-clipper-green focus:ring-1 focus:ring-clipper-green/20"
              @keyup.enter="submitAddSource"
            />
            <div class="flex justify-end gap-2 mt-5">
              <button class="h-10 px-4 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-sm font-medium text-clipper-ink dark:text-white" @click="showAddSource = false">Cancel</button>
              <button class="h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90" @click="submitAddSource">Add Source</button>
            </div>
          </div>
        </div>

        <!-- Golden standards -->
        <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 space-y-3">
          <div class="flex items-center gap-2">
            <Icon name="ph:star" size="16" class="text-clipper-green" />
            <h3 class="text-sm font-semibold text-clipper-ink dark:text-white">Golden Standards — Example Reels</h3>
          </div>
          <p class="text-xs text-clipper-ink/60 dark:text-white/60">Paste viral reel URLs to use as reference. We transcribe them and match your source's best moments against their patterns.</p>
          <div class="flex gap-2">
            <input v-model="pendingGoldenUrl" placeholder="https://instagram.com/reels/... or https://tiktok.com/..." class="flex-1 h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm" @keyup.enter="handleAddGolden" />
            <button class="h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm" @click="handleAddGolden">Add</button>
          </div>
          <div v-if="clipperStore.currentProject?.golden_urls?.length" class="space-y-1">
            <div v-for="(u,i) in clipperStore.currentProject.golden_urls" :key="i" class="flex items-center gap-2 px-3 py-2 rounded-lg bg-clipper-green/10 dark:bg-neutral-800 border border-clipper-green/20 text-sm">
              <span class="flex-1 truncate text-clipper-ink dark:text-white/80">{{ u }}</span>
              <button class="text-clipper-ink/40 hover:text-clipper-ink" @click="handleRemoveGolden(i)">✕</button>
            </div>
          </div>
          <p v-else class="text-xs text-clipper-ink/40 dark:text-white/40">No golden standards yet — add 2–5 viral examples for best results.</p>
        </div>

        <!-- Extra resources -->
        <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 space-y-3">
          <h3 class="text-sm font-semibold text-clipper-ink dark:text-white">Extra Resources</h3>
          <p class="text-xs text-clipper-ink/60 dark:text-white/60">Additional URLs to enrich clipping (docs, more videos)</p>
          <div class="flex gap-2">
            <input v-model="pendingExtraUrl" placeholder="https://..." class="flex-1 h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm" @keyup.enter="handleAddExtra" />
            <button class="h-10 px-4 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-sm" @click="handleAddExtra">Add</button>
          </div>
          <div v-if="clipperStore.currentProject?.extra_resources?.length" class="space-y-1">
            <div v-for="(u,i) in clipperStore.currentProject.extra_resources" :key="i" class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-neutral-100 dark:bg-neutral-800 text-xs">
              <span class="flex-1 truncate text-clipper-ink/70 dark:text-white/70">{{ u }}</span>
              <button class="text-clipper-ink/40" @click="handleRemoveExtra(i)">✕</button>
            </div>
          </div>
        </div>

        <!-- Process controls under sources (per spec, processing is highly visible) -->
        <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-sm font-semibold text-clipper-ink dark:text-white">Process sources</p>
            <div class="flex items-center gap-2">
              <n-select
                v-model:value="whisperModelSize"
                size="small"
                class="w-32"
                title="Whisper model size"
                :options="whisperModelOptions"
              />
              <n-select
                v-model:value="transcriptionLanguage"
                size="small"
                class="w-32"
                :options="languageOptions"
              />
            </div>
          </div>
          <p class="text-xs text-clipper-ink/60 dark:text-white/60">Downloading → Transcribing → Scoring → Rendering → Done. Progress is streamed via SSE.</p>
          <div class="flex gap-2">
            <button class="flex-1 h-10 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 disabled:opacity-50" :disabled="loading || !clipperStore.currentProject.source_urls.length" @click="handleProcessProject">
              Process Sources
            </button>
            <button class="flex-1 h-10 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm font-medium text-clipper-ink dark:text-white hover:border-clipper-ink/20 dark:hover:border-white/20 disabled:opacity-50" :disabled="loading" @click="handleSelectClips">
              Select Top Clips
            </button>
          </div>
        </div>
      </div>

      <!-- ───── View: TRANSCRIPT ───── -->
      <div v-else-if="clipperStore.activeView === 'transcript'" class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5">
          <div class="flex items-center justify-between">
            <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60">Transcript</p>
            <span class="text-xs text-clipper-ink/35 dark:text-white/40">{{ allSentences.length }} sentences</span>
          </div>
          <div v-if="transcriptOutlines.length" class="mt-3 border border-clipper-green/25 bg-clipper-green/[0.05] rounded-lg p-3 space-y-2">
            <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60">Topic timeline</p>
            <div class="space-y-1.5">
              <div
                v-for="(o, idx) in transcriptOutlines"
                :key="idx"
                class="flex items-start gap-2 px-2.5 py-1.5 rounded-md bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 hover:border-clipper-green/40 cursor-default"
              >
                <Icon name="ph:hash" size="12" class="mt-1 shrink-0 text-clipper-green" />
                <div class="min-w-0">
                  <p class="text-sm font-medium text-clipper-ink dark:text-white leading-snug">
                    {{ o.topic }}
                    <span class="ml-1 text-[11px] font-medium text-clipper-ink/50 dark:text-white/50 tabular-nums">({{ fmtTime(o.start) }}–{{ fmtTime(o.end) }})</span>
                  </p>
                  <p v-if="o.summary" class="text-xs text-clipper-ink/60 dark:text-white/60 leading-relaxed">{{ o.summary }}</p>
                </div>
              </div>
            </div>
          </div>
          <div v-if="allSentences.length" class="mt-4 space-y-1 max-h-[560px] overflow-y-auto pr-1">
            <button
              v-for="(s, idx) in allSentences"
              :key="idx"
              class="w-full text-left px-3 py-2 rounded-lg text-sm leading-6 hover:bg-neutral-100 dark:hover:bg-white/5 border border-transparent hover:border-clipper-ink/08 dark:hover:border-white/08"
            >
              <span class="inline-flex w-10 text-[11px] font-medium text-clipper-ink/40 dark:text-white/40 tabular-nums">{{ Math.floor(s.start/60) }}:{{ String(Math.floor(s.start%60)).padStart(2,'0') }}</span>
              <span class="text-clipper-ink dark:text-white/80">{{ s.text }}</span>
            </button>
          </div>
          <div v-else class="py-16 text-center">
            <Icon name="ph:article" size="32" class="mx-auto text-clipper-ink dark:text-white/20 mb-2" />
            <p class="text-sm text-clipper-ink/60 dark:text-white/60">No transcript yet</p>
            <p class="text-xs text-clipper-ink/35 dark:text-white/40 mt-1">Process sources to transcribe them.</p>
            <button class="mt-4 h-9 px-3 rounded-lg bg-clipper-green text-clipper-ink text-sm font-semibold" @click="clipperStore.activeView = 'sources'; navigateTo('/clipper?view=sources')">Add sources</button>
          </div>
        </div>
        <div class="space-y-4">
          <ClipperViralityScore v-if="clipperStore.clips[0]" :scores="clipperStore.clips[0].scores" />
          <div v-else class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 text-center text-sm text-clipper-ink/35 dark:text-white/40">
            Select top clips to see virality scores.
          </div>
          <ClipperSourceList
            v-if="clipperStore.currentProject"
            :sources="(clipperStore.currentProject.source_urls || []).slice(0,3).map((url: string, idx: number) => ({
              id: clipperStore.currentProject!.source_ids[idx] || `src-${idx}`,
              url,
              platform: 'YouTube',
              duration: 0,
              transcribed: false,
            }))"
            :project-id="clipperStore.currentProject.id"
            @add="showAddSource = true"
            @remove="handleRemoveSource"
          />
        </div>
      </div>

      <!-- ───── View: PUBLISH ───── -->
      <div v-else-if="clipperStore.activeView === 'publish'" class="space-y-4">
        <div v-if="publishLoading" class="border border-clipper-ink/08 dark:border-white/08 rounded-xl py-12 text-center bg-white dark:bg-neutral-800">
          <p class="text-sm text-clipper-ink/60 dark:text-white/60">Loading publish records…</p>
        </div>
        <div v-else-if="!groupedPublishRecords.length" class="border border-clipper-ink/08 dark:border-white/08 rounded-xl py-16 text-center bg-white dark:bg-neutral-800">
          <Icon name="ph:calendar-check" size="44" class="mx-auto text-clipper-ink dark:text-white/20 mb-3" />
          <h3 class="text-base font-semibold text-clipper-ink dark:text-white">No scheduled posts</h3>
          <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">Schedule clips from the Clips view to see them here.</p>
          <button class="mt-5 h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90" @click="clipperStore.activeView = 'clips'; navigateTo('/clipper?view=clips')">Go to Clips</button>
        </div>
        <template v-else>
          <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5">
            <div class="flex items-center justify-between mb-4">
              <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60">Upcoming schedule</p>
              <span class="text-xs text-clipper-ink/35 dark:text-white/40">{{ clipperStore.publishRecords.length }} record(s)</span>
            </div>
            <div class="space-y-5">
              <div v-for="group in groupedPublishRecords" :key="group.date">
                <div class="flex items-center gap-2 mb-2">
                  <Icon name="ph:calendar" size="14" class="text-clipper-green" />
                  <p class="text-sm font-semibold text-clipper-ink dark:text-white">{{ group.date }}</p>
                </div>
                <div class="space-y-2">
                  <div
                    v-for="record in group.records"
                    :key="record.id"
                    class="flex items-center gap-3 bg-neutral-100 dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-lg px-3 py-2.5"
                  >
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-medium text-clipper-ink dark:text-white truncate">{{ record.clip_hook_title || record.title || record.clip_id }}</p>
                      <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-0.5 flex items-center gap-2 flex-wrap">
                        <span class="tabular-nums">{{ new Date(record.scheduled_at).toLocaleString() }}</span>
                        <span v-if="record.visibility" class="capitalize">· {{ record.visibility }}</span>
                        <span
                          class="px-1.5 py-0.5 rounded-full text-[11px] font-medium"
                          :class="record.status === 'error' ? 'bg-red-500/10 text-red-500' : 'bg-clipper-green/15 text-clipper-green'"
                        >{{ record.status }}</span>
                      </p>
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                      <span
                        v-for="p in record.platforms"
                        :key="p"
                        class="px-2 py-0.5 rounded-full text-[11px] font-medium bg-neutral-100 dark:bg-neutral-700 border border-clipper-ink/08 dark:border-white/10 text-clipper-ink dark:text-white/80 capitalize"
                      >{{ p }}</span>
                      <button
                        class="w-7 h-7 rounded-md flex items-center justify-center text-clipper-ink/40 dark:text-white/40 hover:text-red-500 hover:bg-neutral-100 dark:hover:bg-white/5"
                        title="Delete publish record"
                        aria-label="Delete publish record"
                        @click="handleDeletePublishRecord(record.id)"
                      >
                        <Icon name="ph:trash" size="14" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- ───── View: SETTINGS ───── -->
      <div v-else-if="clipperStore.activeView === 'settings'">
        <!-- AI Model Provider lives in Global Settings (/settings) -->
        <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-5 mb-6">
          <div class="flex items-center gap-2">
            <Icon name="ph:cpu" size="16" class="text-clipper-green" />
            <h3 class="text-sm font-semibold text-clipper-ink dark:text-white">AI Model Provider</h3>
          </div>
          <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-1">Provider, API key and cookie settings moved to Global Settings.</p>
          <NuxtLink to="/settings" class="mt-3 inline-flex h-9 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm items-center">
            Open AI settings
          </NuxtLink>
        </div>

        <ClipperProjectSettings
          :project="clipperStore.currentProject"
          @update="handleProjectUpdate"
          @delete="handleDeleteCurrentProject"
        />
      </div>
    </template>

    <!-- Global Add Source dialog (available from Clips view as well) -->
    <div v-if="showAddSource && clipperStore.currentProject && clipperStore.activeView === 'clips'" class="fixed inset-0 z-50 bg-clipper-ink/35 flex items-center justify-center p-6" @click.self="showAddSource = false">
      <div class="w-full max-w-[480px] bg-white dark:bg-[#0F172A] rounded-xl p-6 border border-clipper-ink/08 dark:border-white/10">
        <h3 class="text-base font-semibold text-clipper-ink dark:text-white">Add Source</h3>
        <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">Paste a YouTube or direct video URL — we'll extract the most viral 30-90s moments.</p>
        <input
          v-model="pendingUrl"
          placeholder="Paste video URL..."
          class="mt-4 w-full h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm focus:outline-none focus:border-clipper-green focus:ring-1 focus:ring-clipper-green/20"
          @keyup.enter="submitAddSource"
        />
        <div class="flex justify-end gap-2 mt-5">
          <button class="h-10 px-4 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-sm font-medium text-clipper-ink dark:text-white" @click="showAddSource = false">Cancel</button>
          <button class="h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90" @click="submitAddSource">Add Source</button>
        </div>
        <p class="text-xs text-clipper-ink/40 dark:text-white/40 mt-3">After adding, go to <span class="font-medium">Sources → Process</span> to generate new viral clips.</p>
      </div>
    </div>

    <!-- Minimal AI philosophy banner (only in clips view when clips exist) -->
    <div v-if="clipperStore.currentProject && clipperStore.activeView==='clips' && clipperStore.clips.length" class="rounded-lg border border-clipper-ink/08 dark:border-white/08 bg-neutral-100 dark:bg-neutral-800 px-4 py-3 flex items-start gap-3">
      <Icon name="ph:leaf" size="16" class="text-clipper-green mt-0.5 shrink-0" />
      <p class="text-xs leading-relaxed text-clipper-ink/70 dark:text-white/60">
        <span class="font-semibold text-clipper-ink dark:text-white">Minimal AI — maximum signal.</span>
        Clips are scored from transcription + heuristics (hook, engagement, value, shareability). LLM only ranks the top 20 candidates and writes hook titles — no full analysis of every segment.
      </p>
    </div>

    <!-- Batch schedule modal -->
    <n-modal
      v-model:show="batchScheduleModal"
      preset="card"
      :title="`Schedule ${clipperStore.selectedClips.length} Clip(s)`"
      style="max-width: 520px"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <p class="text-xs text-clipper-ink/60 dark:text-white/60">Same flow as Generate → Videos. Each clip will be posted with its own metadata.</p>

        <div v-if="batchMagicsyncBusinesses.length > 0">
          <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">Business</label>
          <n-select
            v-model:value="batchSelectedBusinessId"
            :options="batchMagicsyncBusinesses.map((b: any) => ({ label: b.name, value: b.id }))"
            class="w-full"
            @update:value="fetchBatchAccounts"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">Date</label>
            <n-date-picker v-model:value="batchScheduleDate" type="date" class="w-full" />
          </div>
          <div>
            <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">Time</label>
            <n-time-picker v-model:value="batchScheduleTime" class="w-full" />
          </div>
        </div>

        <div>
          <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">Visibility</label>
          <n-select
            v-model:value="batchVisibility"
            :options="[
              { label: 'Default', value: '' },
              { label: 'Private', value: 'private' },
              { label: 'Public', value: 'public' },
            ]"
            class="w-full"
          />
        </div>

        <div>
          <p class="text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">
            Post to
            <span v-if="batchMagicsyncLoading" class="font-normal">(loading…)</span>
          </p>
          <div v-if="batchMagicsyncLoading" class="flex items-center gap-2 text-xs text-clipper-ink/60 dark:text-white/60">
            <n-spin size="small" /> Fetching accounts…
          </div>
          <div v-else-if="!batchMagicsyncBusinesses.length" class="text-xs text-clipper-ink/60 dark:text-white/60 border border-dashed border-clipper-ink/12 dark:border-white/10 rounded-lg p-2">
            No businesses. <NuxtLink to="/settings" class="underline text-clipper-green">Add in Settings</NuxtLink>
          </div>
          <div v-else-if="!batchUniquePlatforms.length" class="text-xs text-clipper-ink/60 dark:text-white/60">No connected accounts.</div>
          <div v-else class="space-y-1">
            <n-checkbox
              v-for="pl in batchUniquePlatforms"
              :key="pl"
              :checked="batchSelectedPlatforms.includes(pl)"
              @update:checked="toggleBatchPlatform(pl)"
            >
              <span class="text-sm capitalize">{{ pl }}</span>
            </n-checkbox>
          </div>
        </div>

        <div v-if="batchScheduleResult==='success'" class="text-sm text-clipper-green">✓ Scheduled {{ clipperStore.selectedClips.length }} clip(s)!</div>
        <div v-else-if="batchScheduleResult" class="text-sm text-red-500">{{ batchScheduleResult }}</div>

        <div class="flex gap-3 pt-2">
          <n-button class="flex-1" @click="batchScheduleModal = false">Cancel</n-button>
          <n-button
            class="flex-1"
            type="primary"
            :disabled="!batchScheduleDate || !batchScheduleTime || !batchSelectedPlatforms.length || batchScheduling"
            :loading="batchScheduling"
            @click="handleBatchSchedule"
          >
            {{ batchScheduling ? 'Scheduling…' : `Schedule ${clipperStore.selectedClips.length} Clip(s)` }}
          </n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>
