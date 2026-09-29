<script lang="ts" setup>
/**
 * ElahEditor — elah production playground shell, wired to @elah/core:
 * header / left rail / panel column / preview + transport / properties /
 * resizable timeline. The editor engine lives in the shared useElahEditor
 * composable; this shell only wires controls to it and owns dispose on
 * unmount.
 *
 * On mount it seeds the timeline from the page props: one video clip for the
 * source (with its in/out point applied via sourceStartFrame /
 * sourceDurationFrames) plus karaoke caption text clips generated from the
 * transcript. When a `storageKey` is provided the project auto-saves to
 * localStorage (300ms debounce) and a previously saved edit can be restored.
 */
import { secondsToFrames } from "@elah/core"
import { useElahEditor } from "~/composables/useElahEditor"
import type { ElahEditor as ElahEditorInstance } from "~/composables/useElahEditor"
import EditorHeader from "./EditorHeader.vue"
import TransportBar from "./TransportBar.vue"
import AspectControl from "./AspectControl.vue"
import ElahPreview from "./ElahPreview.vue"
import ElahTimeline from "./ElahTimeline.vue"
import TimelineControls from "./TimelineControls.vue"
import ExportModal from "./ExportModal.vue"
import CodePanel from "./CodePanel.vue"
import TracePanel from "./TracePanel.vue"
import StockMediaPanel from "./panels/StockMediaPanel.vue"
import AudioPanel from "./panels/AudioPanel.vue"
import ElementsPanel from "./panels/ElementsPanel.vue"
import AgenticPanel from "./panels/AgenticPanel.vue"
import ClipProperties from "./properties/ClipProperties.vue"

export interface CaptionSpec {
  startFrame: number
  durationFrames: number
  content: string
  color: string
  fontSize: number
  fontFamily: string
  fontWeight: "normal" | "bold"
  textAlign: "left" | "center" | "right"
  y: number
  strokeColor?: string
  strokeWidth?: number
  textShadowColor?: string
  textShadowBlur?: number
  textShadowOffsetX?: number
  textShadowOffsetY?: number
}

const props = withDefaults(defineProps<{
  fps?: number
  stage?: { width: number; height: number }
  sourceUrl?: string
  /** In-point of the source media (seconds) — becomes the clip's sourceStartFrame. */
  sourceStartSec?: number
  /** Segment duration (seconds) — timeline duration of the source clip. */
  sourceDurationSec?: number
  captions?: CaptionSpec[]
  /** When set, the project auto-saves to localStorage under this key. */
  storageKey?: string
  exportName?: string
}>(), {
  fps: 30,
  stage: () => ({ width: 1080, height: 1920 }),
  sourceUrl: "",
  sourceStartSec: 0,
  sourceDurationSec: 60,
  captions: () => [],
  storageKey: "",
  exportName: "clipper-studio",
})

const emit = defineEmits<{ ready: [elah: ElahEditorInstance] }>()

const message = useMessage()

// ssr:false globally — TimelineEngine/PlaybackEngine are client libs; real
// browser APIs are only touched inside mountPreview/playback.
const elah: ElahEditorInstance = useElahEditor({ fps: props.fps, stage: props.stage })

const mounted = ref(false)

// ---- Editor fullscreen (whole shell, not just the preview) -----------------
const editorRootEl = ref<HTMLElement | null>(null)
const isFullscreen = ref(false)
const onEditorFullscreenChange = () => {
  isFullscreen.value = document.fullscreenElement === editorRootEl.value
}
const toggleEditorFullscreen = () => {
  const root = editorRootEl.value
  if (!root || !document.fullscreenEnabled) return
  if (document.fullscreenElement) void document.exitFullscreen()
  else void root.requestFullscreen().catch(() => { /* denied — stay windowed */ })
}

const trackIdOf = (kind: "video" | "audio" | "elements") =>
  elah.tracks.value.find(t => t.kind === kind)?.id ?? ""

// ---- Initial timeline: source clip (with in-point) + karaoke captions ----
const buildInitialTimeline = () => {
  const fps = elah.project.value.fps
  const videoTrackId = trackIdOf("video")
  if (props.sourceUrl && videoTrackId) {
    elah.engine.batch(() => {
      const clip = elah.addClip({
        trackId: videoTrackId,
        type: "video",
        src: props.sourceUrl,
        name: props.exportName || "Source video",
        startFrame: 0,
        durationFrames: Math.max(1, secondsToFrames(props.sourceDurationSec || 60, fps)),
      })
      // Clip segment in-point: the timeline clip plays [sourceStartSec,
      // sourceStartSec + sourceDurationSec) of the source media.
      elah.updateClip(clip.id, clip.trackId, {
        sourceStartFrame: Math.max(0, secondsToFrames(props.sourceStartSec, fps)),
        sourceDurationFrames: Math.max(1, secondsToFrames(props.sourceDurationSec || 60, fps)),
      })
    }, "Load clip")
    elah.selectNone()
  }
  addCaptions()
}

const addCaptions = () => {
  if (!props.captions.length) return
  const elementsTrackId = trackIdOf("elements")
  if (!elementsTrackId) return
  // Dedupe: never double-caption the elements track.
  const existing = elah.clipsByTrack.value[elementsTrackId] ?? []
  if (existing.some(c => c.type === "text" && c.name.startsWith("Caption"))) return
  elah.engine.batch(() => {
    for (const cap of props.captions) {
      const clip = elah.engine.addClip({
        trackId: elementsTrackId,
        type: "text",
        name: "Caption",
        startFrame: Math.max(0, Math.round(cap.startFrame)),
        durationFrames: Math.max(2, Math.round(cap.durationFrames)),
        text: {
          content: cap.content,
          fontSize: cap.fontSize,
          color: cap.color,
          fontFamily: cap.fontFamily,
          fontWeight: cap.fontWeight,
          textAlign: cap.textAlign,
        },
        transform: { x: 0.5, y: cap.y, scale: 1, rotation: 0, anchor: { x: 0.5, y: 0.5 } },
      })
      elah.updateClip(clip.id, clip.trackId, {
        textAnimation: { in: "fade", out: "fade", durationFrames: 8 },
        ...(cap.strokeColor && (cap.strokeWidth ?? 0) > 0
          ? { strokeColor: cap.strokeColor, strokeWidth: cap.strokeWidth }
          : {}),
        ...(cap.textShadowColor
          ? {
              textShadowColor: cap.textShadowColor,
              textShadowBlur: cap.textShadowBlur ?? 0,
              textShadowOffsetX: cap.textShadowOffsetX ?? 0,
              textShadowOffsetY: cap.textShadowOffsetY ?? 0,
            }
          : {}),
      })
    }
    elah.selectNone()
  }, "Add captions")
}

onMounted(() => {
  document.addEventListener("fullscreenchange", onEditorFullscreenChange)
  buildInitialTimeline()
  initialSnapshot = elah.saveProject()
  elah.seek(0)
  mounted.value = true
  emit("ready", elah)

  // Auto-saved edit found? Offer a restore (popover confirm on the strip).
  if (props.storageKey) {
    try {
      const saved = localStorage.getItem(props.storageKey)
      if (saved && saved !== initialSnapshot) {
        savedJson.value = saved
        showRestore.value = true
      }
    } catch {
      /* storage unavailable — ignore */
    }
  }
})

onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onEditorFullscreenChange)
  clearTimeout(saveTimer)
  clearTimeout(noticeTimer)
  elah.dispose()
})

// ---- Auto-save / restore / reset ----
const savedJson = ref<string | null>(null)
const showRestore = ref(false)
let initialSnapshot = ""
let saveTimer: ReturnType<typeof setTimeout> | undefined

watch(
  () => elah.project.value,
  () => {
    if (!props.storageKey || showRestore.value) return
    clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      try {
        localStorage.setItem(props.storageKey, elah.saveProject())
      } catch {
        /* storage full/unavailable — ignore */
      }
    }, 300)
  },
)

const restoreSaved = () => {
  if (savedJson.value) {
    try {
      elah.loadProject(savedJson.value)
      message.success("Restored saved edit")
    } catch {
      message.error("Could not restore the saved edit")
    }
  }
  showRestore.value = false
}
const discardSaved = () => {
  if (props.storageKey) {
    try { localStorage.removeItem(props.storageKey) } catch { /* ignore */ }
  }
  savedJson.value = null
  showRestore.value = false
}

// ---- Shell state: header toggles, panels, timeline zoom + height ----
const showCode = ref(false)
const showTrace = ref(false)
const showExport = ref(false)

type PanelId = "videos" | "photos" | "audio" | "elements" | "ai"
const activePanel = ref<PanelId>("videos")

const RAIL: { id: PanelId; label: string; icon: string }[] = [
  { id: "videos", label: "Videos", icon: "ph:film-strip" },
  { id: "photos", label: "Photos", icon: "ph:image" },
  { id: "audio", label: "Audio", icon: "ph:music-notes" },
  { id: "elements", label: "Elements", icon: "ph:text-t" },
  { id: "ai", label: "AI", icon: "ph:sparkle" },
]

// Insert notice toast — fades after 1.6s.
const noticeText = ref("")
let noticeTimer: ReturnType<typeof setTimeout> | undefined
const notice = (text: string) => {
  noticeText.value = text
  clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => { noticeText.value = "" }, 1600)
}
const onInserted = (name: string) => notice(`Added ${name}`)
const onApplied = (name: string, count: number) => notice(`Applied ${name} to ${count} clip${count === 1 ? "" : "s"}`)
const onComposed = () => notice("AI composition added")

// Timeline zoom (raw px/frame; the log-scale slider lives in TimelineControls).
const ppf = ref(8)

// Resizable timeline: drag the handle up/down; clamped to
// [120, workspace height - 140] so the top section never collapses.
const TIMELINE_MIN = 120
const timelineHeight = ref(186)
const workspaceEl = ref<HTMLElement | null>(null)
const timelineWrapEl = ref<HTMLElement | null>(null)

const startResize = (e: PointerEvent) => {
  e.preventDefault()
  const startY = e.clientY
  const startH = timelineHeight.value
  const maxH = Math.max((workspaceEl.value?.clientHeight ?? 800) - 140, TIMELINE_MIN)
  const onMove = (ev: PointerEvent) => {
    const next = startH + (startY - ev.clientY) // drag up → taller
    timelineHeight.value = Math.min(Math.max(next, TIMELINE_MIN), maxH)
  }
  const onUp = () => {
    window.removeEventListener("pointermove", onMove)
    window.removeEventListener("pointerup", onUp)
    document.body.style.userSelect = ""
  }
  window.addEventListener("pointermove", onMove)
  window.addEventListener("pointerup", onUp)
  document.body.style.userSelect = "none"
}

// Fit: one px/frame value that fits the whole project in the timeline width
// (minus the 160px track gutter + scrollbar allowance).
const fitValue = () => {
  const width = timelineWrapEl.value?.clientWidth ?? 0
  const total = Math.max(elah.totalFrames.value, 1)
  return Math.max(2, Math.min(60, (width - 168) / total))
}

const goBack = () => navigateTo("/clipper")

defineExpose({ elah })
</script>

<template>
  <div ref="editorRootEl" class="flex flex-col h-[calc(100vh-64px)] min-h-[560px] bg-white dark:bg-neutral-900 overflow-hidden">
    <EditorHeader
      v-model:show-code="showCode"
      v-model:show-trace="showTrace"
      :elah="elah"
      :is-fullscreen="isFullscreen"
      @back="goBack"
      @export="showExport = true"
      @toggle-fullscreen="toggleEditorFullscreen"
    />
    <CodePanel v-model:show="showCode" :elah="elah" />
    <TracePanel v-model:show="showTrace" />

    <!-- Saved-edit restore strip -->
    <div v-if="showRestore" class="shrink-0 flex items-center gap-2 px-3 py-1.5 bg-clipper-green/10 border-b border-clipper-green/30">
      <Icon name="ph:clock-counter-clockwise" size="14" class="text-clipper-green shrink-0" />
      <span class="text-xs text-clipper-ink dark:text-white flex-1">An auto-saved edit was found for this clip.</span>
      <n-popconfirm @positive-click="restoreSaved">
        <template #trigger>
          <n-button size="tiny" type="primary">Restore</n-button>
        </template>
        Restore saved edit? This replaces the current timeline.
      </n-popconfirm>
      <n-button size="tiny" quaternary @click="discardSaved">Discard</n-button>
    </div>

    <template v-if="mounted">
      <!-- Workspace -->
      <div ref="workspaceEl" class="flex flex-1 min-h-0">
        <!-- Left rail -->
        <nav class="w-16 shrink-0 flex flex-col items-center gap-1 py-2 border-r border-clipper-ink/08 dark:border-white/08 bg-white dark:bg-neutral-900">
          <button
            v-for="item in RAIL"
            :key="item.id"
            type="button"
            class="w-full flex flex-col items-center gap-1 py-1.5 rounded-xl cursor-pointer transition-colors"
            :class="activePanel === item.id
              ? 'text-clipper-green bg-clipper-green/10'
              : 'text-clipper-ink/60 dark:text-white/60 hover:text-clipper-ink dark:hover:text-white'"
            @click="activePanel = item.id"
          >
            <Icon :name="item.icon" size="20" />
            <span class="text-[10px] leading-none font-medium">{{ item.label }}</span>
          </button>
        </nav>

        <!-- Panel column -->
        <div class="relative w-60 shrink-0 min-h-0 flex flex-col border-r border-clipper-ink/08 dark:border-white/08 bg-white dark:bg-neutral-900 overflow-hidden">
          <transition name="fade">
            <div
              v-if="noticeText"
              class="absolute top-2 left-1/2 -translate-x-1/2 z-20 px-3 py-1 rounded-md whitespace-nowrap shadow-sm bg-white dark:bg-neutral-800 border border-clipper-green/40 text-clipper-green text-xs font-medium"
            >{{ noticeText }}</div>
          </transition>
          <StockMediaPanel v-if="activePanel === 'videos'" :elah="elah" mode="videos" class="flex-1 min-h-0" @inserted="onInserted" />
          <StockMediaPanel v-else-if="activePanel === 'photos'" :elah="elah" mode="photos" class="flex-1 min-h-0" @inserted="onInserted" />
          <AudioPanel v-else-if="activePanel === 'audio'" :elah="elah" class="flex-1 min-h-0" @inserted="onInserted" />
          <ElementsPanel v-else-if="activePanel === 'elements'" :elah="elah" class="flex-1 min-h-0" @inserted="onInserted" @applied="onApplied" />
          <AgenticPanel v-else :elah="elah" class="flex-1 min-h-0" @composed="onComposed" />
        </div>

        <!-- Center: aspect + preview + transport -->
        <div class="flex-1 min-w-0 min-h-0 flex flex-col bg-neutral-950">
          <AspectControl :elah="elah" />
          <ElahPreview :elah="elah" class="flex-1 min-h-0" />
          <TransportBar :elah="elah" />
        </div>

        <!-- Clip properties -->
        <ClipProperties :elah="elah" class="w-[300px] shrink-0 border-l border-clipper-ink/08 dark:border-white/08 bg-white dark:bg-neutral-900" />
      </div>

      <!-- Timeline resize handle -->
      <div
        role="separator"
        aria-orientation="horizontal"
        title="Drag to resize timeline"
        class="group shrink-0 h-3 flex items-center justify-center cursor-ns-resize border-t border-clipper-ink/08 dark:border-white/08 bg-white dark:bg-neutral-900 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
        @pointerdown="startResize"
      >
        <span class="h-1 w-12 rounded-full bg-clipper-ink/20 dark:bg-white/20 group-hover:bg-clipper-green transition-colors" />
      </div>

      <TimelineControls v-model:pixels-per-frame="ppf" :elah="elah" @fit="ppf = fitValue()" />
      <div ref="timelineWrapEl" class="shrink-0 min-h-0 overflow-hidden" :style="{ height: `${timelineHeight}px` }">
        <ElahTimeline :elah="elah" :pixels-per-frame="ppf" :height="timelineHeight" class="h-full" />
      </div>
    </template>
    <div v-else class="flex-1 flex items-center justify-center">
      <n-spin size="large" />
    </div>

    <!-- Export funnel (modal owns codec/quality/progress) -->
    <ExportModal v-model:show="showExport" :elah="elah" :export-name="exportName" />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
