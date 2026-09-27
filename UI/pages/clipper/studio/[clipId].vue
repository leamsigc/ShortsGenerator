<script lang="ts" setup>
/**
 * Studio — full browser-native editor for a single clip (route /clipper/studio/:clipId).
 *
 * Loads the clip segment (clip.start_time..clip.end_time of the source) as the
 * timeline video clip via the elah in-point (sourceStartFrame /
 * sourceDurationFrames) and auto-generates karaoke caption text clips from the
 * transcript, styled after the project's subtitle template.
 */
import { framesToSeconds, secondsToFrames } from "@elah/core"
import ElahEditor from "~/components/editor/ElahEditor.vue"
import type { CaptionSpec } from "~/components/editor/ElahEditor.vue"
import type { ClipSegment, Transcript, WordTimestamp } from "~/stores/ClipperStore"

definePageMeta({ layout: "clipper" })

const route = useRoute()
const router = useRouter()
const clipperStore = useClipperStore()
const message = useMessage()
const FPS = 30

interface SubtitleTemplate {
  value: string
  label: string
  color?: string
  fontsize?: number
  position?: string
  stroke_color?: string
  stroke_width?: number
}

const clipId = computed(() => String(route.params.clipId))
const clip = ref<ClipSegment | null>(null)
const loading = ref(true)
const notFound = ref(false)
const sourceUrl = ref("")
const sourceStartSec = ref(0)
const sourceDurationSec = ref(60)
const captions = ref<CaptionSpec[]>([])

type AspectRatio = "9:16" | "16:9" | "1:1" | "4:5"
const ASPECT_STAGES: Record<AspectRatio, { width: number; height: number }> = {
  "9:16": { width: 1080, height: 1920 },
  "16:9": { width: 1920, height: 1080 },
  "1:1": { width: 1080, height: 1080 },
  "4:5": { width: 1080, height: 1350 },
}
const ASPECT_OPTIONS = (Object.keys(ASPECT_STAGES) as AspectRatio[]).map(ratio => ({
  label: ratio,
  value: ratio,
}))
const selectedAspect = ref<AspectRatio>("9:16")

const editorRef = ref<InstanceType<typeof ElahEditor> | null>(null)

// ---- Karaoke captions from transcript + subtitle template ----
const MAX_WORDS_PER_CAPTION = 4
const captionFontSize = (fontsize: number | undefined, stageHeight: number): number =>
  Math.min(160, Math.max(32, Math.round((fontsize ?? 100) * stageHeight / 288 / 7)))

const captionY = (position: string | undefined): number => {
  const v = (position || "center,bottom").split(",")[1]
  if (v === "top") return 0.15
  if (v === "center") return 0.5
  return 0.85
}
const captionAlign = (position: string | undefined): "left" | "center" | "right" => {
  const h = (position || "center,bottom").split(",")[0]
  if (h === "left" || h === "right") return h
  return "center"
}

const buildCaptions = (transcript: Transcript | null, clipData: ClipSegment, template: SubtitleTemplate | null): CaptionSpec[] => {
  const words = (transcript?.words ?? []).filter(
    (w: WordTimestamp) => w.start >= clipData.start_time && w.end <= clipData.end_time,
  )
  if (!words.length) return []
  const chunks: WordTimestamp[][] = []
  for (let i = 0; i < words.length; i += MAX_WORDS_PER_CAPTION) chunks.push(words.slice(i, i + MAX_WORDS_PER_CAPTION))
  // Merge a trailing short chunk into the previous one.
  if (chunks.length > 1 && chunks[chunks.length - 1].length < 2) {
    chunks[chunks.length - 2].push(...chunks.pop()!)
  }
  const stageHeight = ASPECT_STAGES[selectedAspect.value].height
  const fontSize = captionFontSize(template?.fontsize, stageHeight)
  const color = template?.color || "#FFFF00"
  const y = captionY(template?.position)
  const textAlign = captionAlign(template?.position)
  let lastEndFrame = 0
  return chunks.map(ws => {
    // Frame-rounding can make adjacent chunks overlap by a frame — clamp.
    const startFrame = Math.max(lastEndFrame, secondsToFrames(ws[0].start - clipData.start_time, FPS))
    const endFrame = Math.max(startFrame + 2, secondsToFrames(ws[ws.length - 1].end - clipData.start_time, FPS))
    lastEndFrame = endFrame
    return {
      startFrame,
      durationFrames: endFrame - startFrame,
      content: ws.map(w => w.word).join(" "),
      color,
      fontSize,
      fontFamily: "Poppins",
      fontWeight: "bold",
      textAlign,
      y,
    }
  })
}

const fetchSubtitleTemplate = async (): Promise<SubtitleTemplate | null> => {
  try {
    const API_URL = useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080"
    const res = await $fetch<{ data: { subtitleTemplates?: { options?: SubtitleTemplate[] } } }>(
      `${API_URL}/api/settings`,
    )
    const options = res?.data?.subtitleTemplates?.options ?? []
    const wanted = clipperStore.currentProject?.template?.subtitle_template ?? "classic"
    return options.find(t => t.value === wanted) ?? options[0] ?? null
  } catch (e) {
    console.error("Failed to load subtitle templates", e)
    return null
  }
}

const loadClip = async () => {
  loading.value = true
  notFound.value = false
  captions.value = []
  try {
    const found = await clipperStore.fetchClip(clipId.value)
    if (!found) {
      notFound.value = true
      return
    }
    clip.value = found
    // clipVideoUrl streams the FULL source video (with Range support) — the
    // clip segment is applied via the elah in-point on the timeline clip.
    sourceUrl.value = clipperStore.clipVideoUrl(found.id)
    sourceStartSec.value = found.start_time || 0
    sourceDurationSec.value = found.duration || Math.max(1, (found.end_time || 0) - (found.start_time || 0)) || 60

    // Transcript → captions, template from the clip's project settings.
    if (found.project_id) {
      if (!clipperStore.projectById(found.project_id)) {
        await clipperStore.fetchProject(found.project_id)
      }
      clipperStore.setCurrentProject(found.project_id)
    }
    const [transcript, template] = await Promise.all([
      found.project_id && found.source_id
        ? clipperStore.fetchTranscript(found.project_id, found.source_id)
        : Promise.resolve(null),
      fetchSubtitleTemplate(),
    ])
    captions.value = buildCaptions(transcript ?? null, found, template)
  } catch (e) {
    console.error("Failed to load clip for studio", e)
    notFound.value = true
  } finally {
    loading.value = false
  }
}

const onAspectChange = (ratio: string | null) => {
  if (!ratio) return
  const stage = ASPECT_STAGES[ratio as AspectRatio]
  editorRef.value?.elah.setStage(stage.width, stage.height)
}

// "Use this edit" — sends the first video clip's source in/out point back to the backend.
const firstVideoClip = computed(() => {
  const elah = editorRef.value?.elah
  if (!elah) return null
  const trackId = elah.tracks.value.find(t => t.kind === "video")?.id
  const clips = trackId ? elah.clipsByTrack.value[trackId] : undefined
  return clips && clips.length > 0 ? clips[0] : null
})

const savingTrim = ref(false)
const useThisEdit = async () => {
  const elah = editorRef.value?.elah
  const videoClip = firstVideoClip.value
  if (!elah || !videoClip || !clip.value) return
  const fps = elah.project.value.fps
  const startSec = framesToSeconds(videoClip.sourceStartFrame, fps)
  const endSec = framesToSeconds(videoClip.sourceStartFrame + videoClip.durationFrames, fps)
  savingTrim.value = true
  try {
    await clipperStore.trimClip(clip.value.id, startSec, endSec)
    clip.value = { ...clip.value, start_time: startSec, end_time: endSec, duration: Math.max(0.1, endSec - startSec) }
    message.success("Trim saved")
  } catch {
    message.error("Could not save trim")
  } finally {
    savingTrim.value = false
  }
}

const goBack = () => router.push("/clipper")

onMounted(loadClip)
watch(clipId, loadClip)
</script>

<template>
  <div class="w-full -my-8">
    <!-- Studio header -->
    <div class="flex items-center gap-3 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
      <n-button size="small" quaternary aria-label="Back to CLIPPER" @click="goBack">
        <template #icon>
          <Icon name="ph:arrow-left" size="18" />
        </template>
      </n-button>
      <div class="min-w-0">
        <h1 class="text-lg font-bold text-clipper-ink dark:text-white tracking-tight truncate">
          Studio — {{ clip?.hook_title || `Clip #${clipId}` }}
        </h1>
        <p class="text-xs text-clipper-ink/60 dark:text-white/60">
          Full in-browser editor · everything renders locally, nothing is uploaded
        </p>
      </div>
      <div class="flex-1" />
      <div class="flex items-center gap-1.5">
        <Icon name="ph:crop" size="14" class="text-clipper-ink/40 dark:text-white/40" />
        <n-select
          :value="selectedAspect"
          :options="ASPECT_OPTIONS"
          size="small"
          class="w-28"
          @update:value="onAspectChange"
        />
      </div>
      <n-button size="small" secondary :loading="savingTrim" :disabled="!firstVideoClip" @click="useThisEdit">
        <template #icon>
          <Icon name="ph:scissors" size="14" />
        </template>
        Use this edit
      </n-button>
    </div>

    <div v-if="loading" class="flex justify-center py-24">
      <n-spin size="large" />
    </div>

    <div v-else-if="notFound" class="text-center py-24 border border-clipper-ink/08 dark:border-white/08 rounded-xl bg-white dark:bg-neutral-800">
      <Icon name="ph:warning-circle" size="56" class="mx-auto text-clipper-ink dark:text-white/20 mb-4" />
      <h3 class="text-lg font-semibold text-clipper-ink dark:text-white">Clip not found</h3>
      <p class="text-clipper-ink/60 dark:text-white/60 mt-1 text-sm">It may have been removed or the link is invalid.</p>
      <n-button class="mt-4" type="primary" @click="goBack">Back to CLIPPER</n-button>
    </div>

    <client-only>
      <ElahEditor
        v-if="sourceUrl && !loading && !notFound"
        :key="clipId"
        ref="editorRef"
        :fps="FPS"
        :source-url="sourceUrl"
        :source-start-sec="sourceStartSec"
        :source-duration-sec="sourceDurationSec"
        :captions="captions"
        :storage-key="`elah-project:${clipId}`"
        :export-name="clip?.hook_title || `clip-${clipId}`"
        :stage="ASPECT_STAGES[selectedAspect]"
      />
    </client-only>
  </div>
</template>
