<script lang="ts" setup>
/**
 * ClipEditor — three-column workspace: ClipList / Preview+Transcript+Timeline / Inspector.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const clipperStore = useClipperStore()
const message = useMessage()
import { useStorage } from "@vueuse/core"

const activeClip = computed(() => clipperStore.activeClip)
// Handle to the controlled segment preview (play/pause/seek exposed by ClipPreview).
interface PreviewHandle {
  play: () => void
  pause: () => void
  seek: (t: number) => void
}
const previewRef = ref<PreviewHandle | null>(null)
const currentTime = ref(activeClip.value?.start_time || 0)
const videoDuration = ref(0)
const clipStart = ref(activeClip.value?.start_time || 0)
const clipEnd = ref(activeClip.value?.end_time || 0)
const isPlaying = ref(false)
const busy = ref(false)

const videoSrc = computed(() => {
  if (renderedOutputUrl.value) return renderedOutputUrl.value
  if (!activeClip.value) return ""
  // Stream the full source (Range-supported). The clip segment is enforced
  // in JS: seek to clipStart on load + loop between clipStart/clipEnd.
  // NOTE: no `#t=` media fragment — fragments reset video.currentTime to a
  // segment-relative clock in some browsers, which desyncs the timeline
  // (absolute source timestamps) from the preview playhead.
  return clipperStore.clipVideoUrl(activeClip.value!.id)
})

// — Aspect ratio (user-selected; wins over format presets on render) —
type AspectRatio = "9:16" | "16:9" | "1:1" | "4:5"
const ASPECT_OPTIONS: { label: string; value: AspectRatio }[] = [
  { label: "9:16 Vertical", value: "9:16" },
  { label: "16:9 Landscape", value: "16:9" },
  { label: "1:1 Square", value: "1:1" },
  { label: "4:5 Portrait", value: "4:5" },
]
const selectedAspect = ref<AspectRatio>("9:16")
const aspectBoxClass = computed(() => ({
  "9:16": "aspect-[9/16]",
  "16:9": "aspect-video",
  "1:1": "aspect-square",
  "4:5": "aspect-[4/5]",
}[selectedAspect.value] || "aspect-[9/16]"))

// — Rendered output (kept visible until re-render) —
const renderedOutput = ref<string | null>(null)
const resolveUrl = (u: string) => (u && u.startsWith("/") ? `${getApiBase()}${u}` : u)
const renderedOutputUrl = computed(() => (renderedOutput.value ? resolveUrl(renderedOutput.value) : ""))

const transcriptWords = computed(() => {
  const p = clipperStore.currentProject
  const c = activeClip.value
  if (!p || !c) return []
  return clipperStore.transcripts[`${p.id}/${c.source_id}`]?.words || []
})

const transcriptSentences = computed(() => {
  const p = clipperStore.currentProject
  const c = activeClip.value
  if (!p || !c) return []
  return clipperStore.transcripts[`${p.id}/${c.source_id}`]?.sentences || []
})

const caption = computed(() => {
  const words = transcriptWords.value
  const idx = words.findIndex(w => currentTime.value >= w.start && currentTime.value < w.end)
  if (idx === -1) return ""
  const group = words.slice(idx, idx + 3).map(w => w.word).join(" ")
  return group
})

const currentWord = computed(() => {
  const words = transcriptWords.value
  const idx = words.findIndex(w => currentTime.value >= w.start && currentTime.value < w.end)
  return idx === -1 ? "" : words[idx].word
})

// The preview owns the <video> element: it seeks to the segment start on
// load and loops inside the trim region. Here we only mirror its state so
// captions, the timeline playhead and split position stay in sync.
const onPreviewMeta = (dur: number) => {
  // The streamed source can report 0 until Range data arrives — fall back
  // to the clip end so the timeline still maps correctly.
  videoDuration.value = dur > 0 ? dur : (activeClip.value?.end_time || clipEnd.value || 1)
  currentTime.value = clipStart.value
}
const onPreviewTime = (t: number) => {
  currentTime.value = t
}
const seek = (t: number) => {
  const target = Math.max(clipStart.value, Math.min(t, Math.max(clipStart.value + 0.05, clipEnd.value - 0.02)))
  previewRef.value?.seek(target)
  currentTime.value = target
  // If the user seeks while paused on the last frame, keep it paused there.
}
const togglePlay = () => {
  // isPlaying mirrors the preview's play/pause events below.
  if (isPlaying.value) previewRef.value?.pause()
  else previewRef.value?.play()
}
const saveTrim = async () => {
  if (!activeClip.value) return
  busy.value = true
  try {
    await clipperStore.trimClip(activeClip.value!.id, clipStart.value, clipEnd.value)
    message.success("Trim saved")
  } catch { message.error("Could not save trim") }
  finally { busy.value = false }
}
const splitAt = async () => {
  const t = currentTime.value
  if (!activeClip.value || t <= clipStart.value + 0.5 || t >= clipEnd.value - 0.5) return
  busy.value = true
  try {
    await clipperStore.splitClip(activeClip.value!.id, t)
    message.success("Clip split")
  } catch { message.error("Could not split") }
  finally { busy.value = false }
}
const render = async () => {
  if (!activeClip.value) return
  busy.value = true
  try {
    const r = await clipperStore.renderClip(activeClip.value!.id, activeClip.value!.face_x ?? 0.5, activeClip.value!.face_y ?? 0.35, {
      aspect: selectedAspect.value,
    })
    if (r?.output_url) {
      renderedOutput.value = r.output_url
      message.success("Clip rendered")
    } else if (r) {
      message.success("Clip rendered")
    }
  } catch { message.error("Render failed") }
  finally { busy.value = false }
}
const openFull = (id: string) => navigateTo(`/clipper/editor/${id}`)

// — Export with preset —
const EXPORT_FORMATS_LOCAL = ["tiktok", "reels", "shorts", "douyin", "xiaohongshu", "bilibili", "youtube"]
const EXPORT_QUALITIES_LOCAL = ["high", "medium", "low"]
const showExportOptions = ref(false)
const exportFormat = ref("tiktok")
const exportQuality = ref("high")
const exportBurn = ref(false)
const exporting = ref(false)
const handleExportClip = async () => {
  if (!activeClip.value) return
  exporting.value = true
  try {
    const r = await clipperStore.renderClip(activeClip.value!.id, activeClip.value!.face_x ?? 0.5, activeClip.value!.face_y ?? 0.35, {
      format: exportFormat.value,
      quality: exportQuality.value,
      burnSubtitles: exportBurn.value,
    })
    if (r) message.success(`Clip exported (${exportFormat.value})`)
  } catch { message.error("Export failed") }
  finally { exporting.value = false; showExportOptions.value = false }
}

// — Cover —
const generatingCover = ref(false)
const handleGenerateCover = async () => {
  if (!activeClip.value) return
  generatingCover.value = true
  try {
    const coverUrl = await clipperStore.generateCover(activeClip.value.id)
    if (coverUrl) message.success("Cover generated")
    else message.error("Cover generation failed")
  } catch { message.error("Cover generation failed") }
  finally { generatingCover.value = false }
}
const getApiBase = (): string => {
  try {
    return useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080"
  } catch {
    return "http://localhost:8080"
  }
}
const coverThumbnail = computed(() => {
  const raw = activeClip.value?.thumbnail_url
  return raw ? (raw.startsWith("http") ? raw : `${getApiBase()}${raw}`) : ""
})

// — Metadata —
const generatingMeta = ref(false)
const handleGenerateMetadata = async () => {
  if (!activeClip.value) return
  generatingMeta.value = true
  try {
    const meta = await clipperStore.generateClipMetadata(activeClip.value.id)
    if (meta) message.success("Metadata generated")
  } catch { message.error("Failed to generate metadata") }
  finally { generatingMeta.value = false }
}

// — Schedule —
const scheduleModal = ref(false)
const scheduleDate = ref<number | null>(null)
const scheduleTime = ref<number | null>(null)
const scheduleContent = ref("")
const scheduleTitle = ref("")
const scheduleDescription = ref("")
const scheduleVisibility = ref("")
const scheduling = ref(false)
const scheduleResult = ref<string | null>(null)
const selectedPlatforms = ref<string[]>([])
const magicsyncAccounts = ref<any[]>([])
const magicsyncLoading = ref(false)
const magicsyncBusinesses = useStorage<any[]>("MAGICSYNC_BUSINESSES", [])
const selectedBusinessId = ref<string | null>(null)

const openScheduleModal = async () => {
  if (!activeClip.value) return
  scheduleDate.value = null; scheduleTime.value = null; scheduleResult.value = null
  scheduleVisibility.value = ""
  selectedPlatforms.value = []; magicsyncAccounts.value = []
  scheduleContent.value = activeClip.value.post_content || activeClip.value.title || activeClip.value.hook_title || activeClip.value.transcript?.slice(0,120) || ""
  scheduleTitle.value = activeClip.value.title || activeClip.value.hook_title || ""
  scheduleDescription.value = activeClip.value.description || activeClip.value.transcript?.slice(0,200) || ""
  if (activeClip.value.suggested_schedule) {
    const d = new Date(activeClip.value.suggested_schedule)
    scheduleDate.value = d.getTime(); scheduleTime.value = d.getTime()
  }
  if (magicsyncBusinesses.value.length > 0) {
    selectedBusinessId.value = magicsyncBusinesses.value[0].id
    await fetchAccountsForBusiness(selectedBusinessId.value)
  } else selectedBusinessId.value = null
  scheduleModal.value = true
}
async function fetchAccountsForBusiness(businessId: string | null) {
  if (!businessId) { magicsyncAccounts.value = []; selectedPlatforms.value = []; return }
  const biz = magicsyncBusinesses.value.find((b:any) => b.id === businessId)
  if (!biz) return
  magicsyncLoading.value = true; magicsyncAccounts.value = []; selectedPlatforms.value = []
  try {
    const res = await $fetch<{ status: string; data: { accounts: any[] } }>(`${useApiSettings().API_SETTINGS.value.URL}/api/magicsync/accounts`, { method: 'POST', body: { url: biz.url, apiToken: biz.apiToken } })
    if (res.status === 'success') {
      magicsyncAccounts.value = res.data.accounts.filter((a:any) => a.isActive)
      selectedPlatforms.value = [...new Set(magicsyncAccounts.value.map((a:any) => a.platform))]
    }
  } catch (e) { console.error('Failed to fetch accounts', e) }
  finally { magicsyncLoading.value = false }
}
const togglePlatform = (p: string) => {
  const i = selectedPlatforms.value.indexOf(p)
  if (i >= 0) selectedPlatforms.value.splice(i,1); else selectedPlatforms.value.push(p)
}
const uniquePlatforms = computed(() => [...new Set(magicsyncAccounts.value.map((a:any) => a.platform))])
const handleSchedule = async () => {
  if (!activeClip.value || !scheduleDate.value || !scheduleTime.value) return
  if (selectedPlatforms.value.length === 0 || !selectedBusinessId.value) return
  const biz = magicsyncBusinesses.value.find((b:any) => b.id === selectedBusinessId.value)
  if (!biz) return
  scheduling.value = true; scheduleResult.value = null
  try {
    const date = new Date(scheduleDate.value); const time = new Date(scheduleTime.value)
    date.setHours(time.getHours(), time.getMinutes(), 0, 0)
    await clipperStore.scheduleClip(activeClip.value.id, {
      scheduledAt: date.toISOString(),
      content: scheduleContent.value,
      title: scheduleTitle.value,
      description: scheduleDescription.value,
      platforms: selectedPlatforms.value,
      url: biz.url,
      apiToken: biz.apiToken,
      videoBaseUrl: biz.videoBaseUrl,
      visibility: scheduleVisibility.value,
    })
    scheduleResult.value = 'success'
    message.success('Clip scheduled')
    setTimeout(()=> scheduleModal.value = false, 1500)
  } catch (e:any) { scheduleResult.value = `Error: ${e?.data?.message || e?.message || 'Unknown'}` }
  finally { scheduling.value = false }
}

watch(() => clipperStore.activeClipId, () => {
  const c = activeClip.value
  clipStart.value = c?.start_time || 0
  clipEnd.value = c?.end_time || 0
  currentTime.value = c?.start_time || 0
  videoDuration.value = 0
  // A render belongs to its clip — drop it so the newly selected clip
  // previews its own source segment instead of the previous clip's output.
  renderedOutput.value = null
  isPlaying.value = false
})
</script>

<template>
  <div class="grid grid-cols-[300px_minmax(0,1fr)_320px] gap-6 items-start">
    <!-- Clip list -->
    <aside class="space-y-1 border border-clipper-ink/08 dark:border-white/08 rounded-lg p-3">
      <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60 mb-3">Clips</p>
      <ClipperClipCard
        v-for="clip in clipperStore.sortedClips"
        :key="clip.id"
        :clip="clip"
        :selected="clip.id === clipperStore.activeClipId"
        @select="clipperStore.activeClipId = $event"
        @edit="openFull($event)"
      />
      <ClipperEmptyState v-if="!clipperStore.sortedClips.length" icon="ph:film-strip" title="No clips yet" description="Process your sources to discover high-potential moments." @action="$emit('process')" />
    </aside>

    <!-- Center: preview + transcript + timeline -->
    <div v-if="activeClip" class="space-y-4 min-w-0">
      <div class="relative flex justify-center">
        <ClipperClipPreview
          ref="previewRef"
          :src="videoSrc"
          :start-time="clipStart"
          :end-time="clipEnd"
          :hook-title="activeClip.hook_title"
          :caption="caption.replace(currentWord, '')"
          :accent="currentWord"
          :aspect-ratio="selectedAspect"
          @loadedmetadata="onPreviewMeta"
          @timeupdate="onPreviewTime"
          @play="isPlaying = true"
          @pause="isPlaying = false"
        />
        <n-button
          ghost
          size="small"
          class="absolute top-0 right-0"
          title="Open in full editor"
          @click="navigateTo(`/clipper/studio/${activeClip.id}`)"
        >
          <template #icon>
            <Icon name="ph:arrow-square-out" size="14" />
          </template>
          Full editor
        </n-button>
      </div>

      <!-- Rendered output panel (visible until re-render) -->
      <div v-if="renderedOutputUrl" class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-lg p-4 space-y-3">
        <div class="flex items-center justify-between">
          <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60">
            Rendered output ({{ selectedAspect }})
          </p>
          <a
            :href="renderedOutputUrl"
            :download="`${activeClip.id}.mp4`"
            class="h-7 px-2 rounded-md text-xs font-medium border border-clipper-ink/12 dark:border-white/10 hover:border-clipper-green flex items-center gap-1 text-clipper-ink dark:text-white"
          >
            <Icon name="ph:download-simple" size="12" /> Download
          </a>
        </div>
        <video
          controls
          playsinline
          preload="metadata"
          :src="renderedOutputUrl"
          class="w-full max-w-[360px] mx-auto rounded-lg bg-black"
          :class="aspectBoxClass"
        ></video>
        <p class="text-xs text-clipper-ink/50 dark:text-white/50 break-all">{{ renderedOutput }}</p>
      </div>

      <!-- editor toolbar -->
      <div class="flex items-center gap-2 flex-wrap">
        <button class="h-9 px-3 rounded-lg text-sm font-medium text-clipper-ink dark:text-white bg-white dark:bg-neutral-800 border border-clipper-ink/12 dark:border-white/10 hover:border-clipper-ink/20 dark:hover:border-white/20" @click="togglePlay">
          <Icon :name="isPlaying ? 'ph:pause' : 'ph:play'" size="16" />
          {{ isPlaying ? 'Pause' : 'Play' }}
        </button>
        <button class="h-9 px-3 rounded-lg text-sm font-medium text-clipper-ink dark:text-white bg-white dark:bg-neutral-800 border border-clipper-ink/12 dark:border-white/10 hover:border-clipper-ink/20 dark:hover:border-white/20" :disabled="busy" @click="splitAt">
          <Icon name="ph:scissors" size="16" />
          Split
        </button>
        <button class="h-9 px-3 rounded-lg text-sm font-medium text-clipper-ink dark:text-white bg-white dark:bg-neutral-800 border border-clipper-ink/12 dark:border-white/10 hover:border-clipper-ink/20 dark:hover:border-white/20" :disabled="busy" @click="saveTrim">
          <Icon name="ph:floppy-disk" size="16" />
          Trim
        </button>
        <div class="flex items-center gap-1.5">
          <Icon name="ph:crop" size="14" class="text-clipper-ink/40 dark:text-white/40" />
          <n-select v-model:value="selectedAspect" :options="ASPECT_OPTIONS" size="small" class="w-40" />
        </div>
        <button class="h-9 px-4 rounded-lg text-sm font-semibold text-clipper-ink bg-clipper-green hover:opacity-90" :disabled="busy" @click="render">Render Clip</button>
        <button class="h-9 px-3 rounded-lg text-sm font-medium text-clipper-ink/60 dark:text-white/60 hover:text-clipper-green" @click="openFull(activeClip.id)">Open editor →</button>
      </div>

      <!-- transcript -->
      <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-lg p-3">
        <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60">Transcript</p>
        <ClipperTranscriptPanel :sentences="transcriptSentences" :current-time="currentTime" @seek="seek" />
      </div>

      <!-- timeline -->
      <ClipperTranscriptTimeline
        :words="transcriptWords"
        :clip-start="clipStart"
        :clip-end="clipEnd"
        :current-time="currentTime"
        :video-duration="videoDuration || activeClip.end_time"
        @seek="seek"
        @update-start="clipStart = $event"
        @update-end="clipEnd = $event"
      />
    </div>
    <div v-else class="min-w-0" />

    <!-- Inspector -->
    <aside class="space-y-4 border border-clipper-ink/08 dark:border-white/08 rounded-lg p-4 min-w-0">
      <ClipperViralityScore v-if="activeClip" :scores="activeClip.scores" />
      <div v-else class="text-sm text-clipper-ink/35 dark:text-white/40 py-6 text-center">Select a clip to inspect its virality score.</div>

      <!-- Metadata — YouTube + Social -->
      <div v-if="activeClip" class="pt-3 border-t border-clipper-ink/10 dark:border-white/10 space-y-3">
        <div class="flex items-center justify-between">
          <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60">Metadata</p>
          <div class="flex items-center gap-2">
            <button class="h-7 px-2 rounded-md text-xs font-medium border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 hover:border-clipper-ink/20" :disabled="generatingCover" title="Generate cover" @click="handleGenerateCover">
              <span v-if="generatingCover">Cover…</span><span v-else><Icon name="ph:image" size="12" class="inline -mt-0.5" /> Cover</span>
            </button>
            <button class="h-7 px-2 rounded-md text-xs font-medium border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 hover:border-clipper-ink/20" :disabled="generatingMeta" @click="handleGenerateMetadata">
              <span v-if="generatingMeta">Generating…</span><span v-else>Generate</span>
            </button>
          </div>
        </div>
        <div v-if="coverThumbnail" class="w-full aspect-video rounded-lg overflow-hidden border border-clipper-ink/08 dark:border-white/10">
          <img :src="coverThumbnail" class="w-full h-full object-cover" alt="Clip cover" />
        </div>
        <div v-if="activeClip.title" class="space-y-2 text-sm">
          <div>
            <p class="text-[11px] font-medium text-clipper-ink/50 dark:text-white/50">Title</p>
            <p class="font-medium text-clipper-ink dark:text-white leading-snug">{{ activeClip.title }}</p>
          </div>
          <div v-if="activeClip.description">
            <p class="text-[11px] font-medium text-clipper-ink/50 dark:text-white/50">Description</p>
            <p class="text-xs text-clipper-ink/70 dark:text-white/70 leading-relaxed line-clamp-3">{{ activeClip.description }}</p>
          </div>
          <div v-if="activeClip.tags?.length">
            <p class="text-[11px] font-medium text-clipper-ink/50 dark:text-white/50">Tags</p>
            <div class="flex flex-wrap gap-1 mt-1">
              <span v-for="t in activeClip.tags" :key="t" class="px-2 py-0.5 rounded-full text-[11px] bg-neutral-100 dark:bg-neutral-700 text-clipper-ink dark:text-white/80">{{ t }}</span>
            </div>
          </div>
          <div v-if="activeClip.post_content">
            <p class="text-[11px] font-medium text-clipper-ink/50 dark:text-white/50">Social Post</p>
            <p class="text-xs text-clipper-ink/70 dark:text-white/70 bg-neutral-100 dark:bg-neutral-800 rounded-lg p-2">{{ activeClip.post_content }}</p>
          </div>
          <div v-if="activeClip.suggested_schedule" class="text-xs text-clipper-ink/60 dark:text-white/60">
            <Icon name="ph:calendar" size="12" class="inline" /> Suggested: {{ new Date(activeClip.suggested_schedule).toLocaleString() }}
          </div>
        </div>
        <div v-else class="text-xs text-clipper-ink/40 dark:text-white/40 py-2 text-center border border-dashed border-clipper-ink/12 dark:border-white/10 rounded-lg">
          No metadata yet — click Generate to create YouTube & social copy.
        </div>
        <button class="w-full h-9 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm font-medium hover:border-clipper-ink/20 flex items-center justify-center gap-1.5" @click="openScheduleModal" :disabled="!activeClip">
          <Icon name="ph:calendar" size="14" /> Schedule Clip
        </button>
      </div>

      <div class="pt-3 border-t border-clipper-ink/10 dark:border-white/10 px-3">
        <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60 mb-3">Export</p>
        <div class="flex gap-2 relative">
          <button class="h-10 px-4 rounded-lg text-ink font-semibold text-sm bg-clipper-green hover:opacity-90 flex-1 disabled:opacity-50" :disabled="!activeClip || exporting" @click="handleExportClip">
            {{ exporting ? 'Exporting…' : 'Export Clip' }}
          </button>
          <button class="h-10 w-10 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-clipper-ink dark:text-white" :disabled="!activeClip || exporting" title="More options" aria-label="More export options" @click="showExportOptions = !showExportOptions">
            <Icon name="ph:caret-down" size="16" />
          </button>
          <div v-if="showExportOptions" class="absolute right-0 top-12 z-30 w-48 bg-white dark:bg-neutral-800 border border-clipper-ink/12 dark:border-white/10 rounded-lg p-3 space-y-2 shadow-lg">
            <div>
              <label class="block text-[11px] font-medium text-clipper-ink/50 dark:text-white/50 mb-1">Format</label>
              <n-select
                v-model:value="exportFormat"
                size="small"
                :options="EXPORT_FORMATS_LOCAL.map(f => ({ label: f, value: f }))"
              />
            </div>
            <div>
              <label class="block text-[11px] font-medium text-clipper-ink/50 dark:text-white/50 mb-1">Quality</label>
              <n-select
                v-model:value="exportQuality"
                size="small"
                :options="EXPORT_QUALITIES_LOCAL.map(q => ({ label: q, value: q }))"
              />
            </div>
            <n-checkbox v-model:checked="exportBurn">
              <span class="text-sm text-clipper-ink dark:text-white">Burn subtitles</span>
            </n-checkbox>
          </div>
        </div>
      </div>
    </aside>

    <!-- Schedule modal -->
    <n-modal
      v-model:show="scheduleModal"
      preset="card"
      title="Schedule Clip"
      style="max-width: 520px"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <p class="text-xs text-clipper-ink/60 dark:text-white/60">Post this short directly — same flow as Generate view.</p>

        <div v-if="magicsyncBusinesses.length > 0">
          <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">Business</label>
          <n-select
            v-model:value="selectedBusinessId"
            :options="magicsyncBusinesses.map((b: any) => ({ label: b.name, value: b.id }))"
            class="w-full"
            @update:value="fetchAccountsForBusiness"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">Date</label>
            <n-date-picker v-model:value="scheduleDate" type="date" class="w-full" />
          </div>
          <div>
            <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">Time</label>
            <n-time-picker v-model:value="scheduleTime" class="w-full" />
          </div>
        </div>

        <div>
          <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">Visibility</label>
          <n-select
            v-model:value="scheduleVisibility"
            :options="[
              { label: 'Default', value: '' },
              { label: 'Private', value: 'private' },
              { label: 'Public', value: 'public' },
            ]"
            class="w-full"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">Post Content</label>
          <n-input v-model:value="scheduleContent" type="textarea" :rows="3" placeholder="Post text + hashtags" />
        </div>

        <n-input v-model:value="scheduleTitle" placeholder="Title (optional)" />
        <n-input v-model:value="scheduleDescription" type="textarea" :rows="2" placeholder="Description (optional)" />

        <div>
          <p class="text-xs font-medium text-clipper-ink/60 dark:text-white/60 mb-1">
            Post to
            <span v-if="magicsyncLoading" class="font-normal">(loading…)</span>
          </p>
          <div v-if="magicsyncLoading" class="flex items-center gap-2 text-xs text-clipper-ink/60 dark:text-white/60">
            <n-spin size="small" /> Fetching accounts…
          </div>
          <div v-else-if="!magicsyncBusinesses.length" class="text-xs text-clipper-ink/60 dark:text-white/60 border border-dashed border-clipper-ink/12 dark:border-white/10 rounded-lg p-2">
            No businesses. <NuxtLink to="/settings" class="underline text-clipper-green">Add in Settings</NuxtLink>
          </div>
          <div v-else-if="!uniquePlatforms.length" class="text-xs text-clipper-ink/60 dark:text-white/60">No connected accounts.</div>
          <div v-else class="space-y-1">
            <n-checkbox
              v-for="pl in uniquePlatforms"
              :key="pl"
              :checked="selectedPlatforms.includes(pl)"
              @update:checked="togglePlatform(pl)"
            >
              <span class="text-sm capitalize">{{ pl }}</span>
            </n-checkbox>
          </div>
        </div>

        <div v-if="scheduleResult==='success'" class="text-sm text-clipper-green">✓ Scheduled!</div>
        <div v-else-if="scheduleResult" class="text-sm text-red-500">{{ scheduleResult }}</div>

        <div class="flex gap-3 pt-2">
          <n-button class="flex-1" @click="scheduleModal = false">Cancel</n-button>
          <n-button
            class="flex-1"
            type="primary"
            :disabled="!scheduleDate || !scheduleTime || !selectedPlatforms.length || scheduling"
            :loading="scheduling"
            @click="handleSchedule"
          >
            {{ scheduling ? 'Scheduling…' : 'Schedule' }}
          </n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>
