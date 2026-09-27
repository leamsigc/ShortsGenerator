<script lang="ts" setup>
/**
 * ElahTimeline — NLE timeline: header controls (snap / zoom / tracks),
 * ruler + playhead + track rows with drag-to-move / edge-trim (frame-snapped
 * ghost while dragging), transition markers + context menu, and the full
 * keyboard shortcut set. All mutations funnel through the elah engine.
 */
import { buildSnapPoints, snapFrame } from "@elah/core"
import type { Clip, Track, Transition } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor; height?: number }>()

const rootEl = ref<HTMLElement | null>(null)
const rulerEl = ref<HTMLElement | null>(null)
const scrollEl = ref<HTMLElement | null>(null)

const pixelsPerFrame = ref(8)
const snapEnabled = ref(true)

const fps = computed(() => props.elah.project.value.fps)
const sortedTracks = computed(() => [...props.elah.tracks.value].sort((a, b) => a.order - b.order))
const contentFrames = computed(() => Math.max(props.elah.totalFrames.value + 5 * fps.value, 10 * fps.value))
const contentWidth = computed(() => contentFrames.value * pixelsPerFrame.value)
const playheadX = computed(() => props.elah.currentFrame.value * pixelsPerFrame.value)

// ---- Ruler ticks (adaptive density) ----
interface Tick { frame: number; label: string; minor: boolean }
const TICK_STEP_SECONDS = [0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600]
const majorStepFrames = computed(() => {
  for (const sec of TICK_STEP_SECONDS) {
    const frames = Math.max(1, Math.round(sec * fps.value))
    if (frames * pixelsPerFrame.value >= 80) return frames
  }
  return Math.round(600 * fps.value)
})
const ticks = computed<Tick[]>(() => {
  const major = majorStepFrames.value
  const minor = Math.max(1, Math.round(major / 5))
  const out: Tick[] = []
  for (let f = 0; f <= contentFrames.value; f += minor) {
    const isMajor = f % major === 0
    const totalSec = Math.floor(f / fps.value)
    const m = Math.floor(totalSec / 60)
    const s = totalSec % 60
    out.push({ frame: f, label: isMajor ? `${m}:${String(s).padStart(2, "0")}` : "", minor: !isMajor })
  }
  return out
})

// ---- Zoom: Ctrl/Cmd+wheel + Fit ----
const ZOOM_MIN = 2
const ZOOM_MAX = 60
const clampZoom = (v: number) => Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.round(v)))
const onWheel = (e: WheelEvent) => {
  if (!e.ctrlKey && !e.metaKey) return
  e.preventDefault()
  const factor = e.deltaY < 0 ? 1.2 : 1 / 1.2
  pixelsPerFrame.value = clampZoom(pixelsPerFrame.value * factor)
}
const fitZoom = () => {
  const scroller = scrollEl.value
  if (!scroller) return
  const total = Math.max(props.elah.totalFrames.value, 1)
  pixelsPerFrame.value = clampZoom((scroller.clientWidth - 8) / total)
}

// ---- Ruler scrub (click / drag playhead) ----
const frameFromClientX = (clientX: number): number => {
  const ruler = rulerEl.value
  if (!ruler) return 0
  const rect = ruler.getBoundingClientRect()
  return Math.max(0, Math.min(Math.round((clientX - rect.left) / pixelsPerFrame.value), contentFrames.value))
}
const scrubbing = ref(false)
const onRulerPointerDown = (e: PointerEvent) => {
  e.preventDefault()
  scrubbing.value = true
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  props.elah.seek(frameFromClientX(e.clientX))
}
const onRulerPointerMove = (e: PointerEvent) => {
  if (scrubbing.value) props.elah.seek(frameFromClientX(e.clientX))
}
const onRulerPointerUp = () => { scrubbing.value = false }

// ---- Snapping ----
const snapThresholdFrames = computed(() => Math.max(1, Math.round(6 / pixelsPerFrame.value)))
const snapTargets = (excludeClipId: string): number[] => {
  const pts = buildSnapPoints(props.elah.project.value.clips, excludeClipId)
  pts.push(props.elah.currentFrame.value)
  return pts
}

// ---- Clip drag: move / trim edges ----
interface DragState { mode: "move" | "trim-start" | "trim-end"; clip: Clip; startX: number; origStart: number; origDuration: number }
let drag: DragState | null = null
const ghost = ref<{ clipId: string; startFrame: number; durationFrames: number } | null>(null)

const displayStart = (clip: Clip) => (ghost.value?.clipId === clip.id ? ghost.value.startFrame : clip.startFrame)
const displayDuration = (clip: Clip) => (ghost.value?.clipId === clip.id ? ghost.value.durationFrames : clip.durationFrames)

const onDragMove = (e: PointerEvent) => {
  if (!drag) return
  const deltaFrames = Math.round((e.clientX - drag.startX) / pixelsPerFrame.value)
  const pts = snapEnabled.value ? snapTargets(drag.clip.id) : null
  const threshold = snapThresholdFrames.value
  if (drag.mode === "move") {
    let start = Math.max(0, drag.origStart + deltaFrames)
    if (pts) start = snapFrame(start, pts, threshold)
    ghost.value = { clipId: drag.clip.id, startFrame: start, durationFrames: drag.origDuration }
  } else if (drag.mode === "trim-start") {
    let start = Math.max(0, Math.min(drag.origStart + deltaFrames, drag.origStart + drag.origDuration - 1))
    if (pts) start = Math.min(snapFrame(start, pts, threshold), drag.origStart + drag.origDuration - 1)
    ghost.value = {
      clipId: drag.clip.id,
      startFrame: start,
      durationFrames: drag.origDuration - (start - drag.origStart),
    }
  } else {
    let end = drag.origStart + Math.max(1, drag.origDuration + deltaFrames)
    if (pts) end = Math.max(drag.origStart + 1, snapFrame(end, pts, threshold))
    ghost.value = { clipId: drag.clip.id, startFrame: drag.origStart, durationFrames: end - drag.origStart }
  }
}
const endDrag = () => {
  window.removeEventListener("pointermove", onDragMove)
  if (drag && ghost.value) {
    const { clip } = drag
    const g = ghost.value
    if (drag.mode === "move") props.elah.moveClip(clip.id, clip.trackId, clip.trackId, g.startFrame)
    else props.elah.trimClip(clip.id, clip.trackId, g.startFrame, g.durationFrames)
  }
  drag = null
  ghost.value = null
}
const startDrag = (e: PointerEvent, clip: Clip, mode: DragState["mode"]) => {
  if (clip.locked || props.elah.engine.isTrackLocked(clip.trackId)) return
  e.preventDefault()
  e.stopPropagation()
  focusRoot()
  if (e.ctrlKey || e.metaKey) {
    props.elah.toggleSelection(clip.id)
    return
  }
  props.elah.setSelection([clip.id])
  drag = { mode, clip, startX: e.clientX, origStart: clip.startFrame, origDuration: clip.durationFrames }
  window.addEventListener("pointermove", onDragMove)
  window.addEventListener("pointerup", endDrag, { once: true })
}
onBeforeUnmount(() => {
  window.removeEventListener("pointermove", onDragMove)
  window.removeEventListener("pointerup", endDrag)
})

// ---- Track lane: click empty area = seek + deselect (clips stopPropagation) ----
const onLanePointerDown = (e: PointerEvent) => {
  const lane = e.currentTarget as HTMLElement
  const rect = lane.getBoundingClientRect()
  const frame = Math.round((e.clientX - rect.left) / pixelsPerFrame.value)
  props.elah.seek(Math.max(0, frame))
  props.elah.selectNone()
}

// ---- Track controls ----
const trackIcon = (kind: string) =>
  kind === "audio" ? "ph:music-notes" : kind === "elements" ? "ph:text-aa" : "ph:film-strip"

const updateTrack = (trackId: string, updates: Parameters<ElahEditor["updateTrack"]>[1]) =>
  props.elah.updateTrack(trackId, updates)
const setTrackMuted = (track: Track, value: boolean | string | number) =>
  updateTrack(track.id, { muted: Boolean(value) })
const removeTrack = (track: Track) => props.elah.removeTrack(track.id)
const addTrackOfKind = (kind: "audio" | "elements") =>
  props.elah.addTrack(kind, kind === "audio" ? "Audio" : "Elements")

const clipClass = (clip: Clip) => {
  switch (clip.type) {
    case "video": return "bg-clipper-green/15 border-clipper-green/60 dark:bg-clipper-green/20 dark:border-clipper-green/70"
    case "audio": return "bg-blue-100 border-blue-400 dark:bg-blue-500/25 dark:border-blue-400"
    case "text": return "bg-amber-100 border-amber-400 dark:bg-amber-500/25 dark:border-amber-400"
    case "image": return "bg-violet-100 border-violet-400 dark:bg-violet-500/25 dark:border-violet-400"
    default: return "bg-neutral-100 border-neutral-300 dark:bg-neutral-700 dark:border-neutral-500"
  }
}

// ---- Transitions: context menu + markers ----
const menuShow = ref(false)
const menuX = ref(0)
const menuY = ref(0)
const menuClip = ref<Clip | null>(null)

const nextClipOf = (clip: Clip): Clip | null => {
  const clips = props.elah.clipsByTrack.value[clip.trackId] ?? []
  const end = clip.startFrame + clip.durationFrames
  return [...clips].filter(c => c.startFrame >= end).sort((a, b) => a.startFrame - b.startFrame)[0] ?? null
}

interface MenuOption { label?: string; key: string; type?: string; [key: string]: unknown }
const menuOptions = computed<MenuOption[]>(() => {
  const clip = menuClip.value
  if (!clip) return []
  const options: MenuOption[] = []
  if (nextClipOf(clip)) {
    options.push(
      { label: "Add fade transition (0.5s)", key: "transition:fade" },
      { label: "Add slide transition (0.5s)", key: "transition:slide" },
      { type: "divider", key: "d1" },
    )
  }
  options.push(
    { label: "Duplicate at playhead", key: "duplicate" },
    { label: "Delete clip", key: "delete" },
  )
  return options
})

const onClipContextMenu = (e: MouseEvent, clip: Clip) => {
  e.preventDefault()
  e.stopPropagation()
  props.elah.setSelection([clip.id])
  menuClip.value = clip
  menuX.value = e.clientX
  menuY.value = e.clientY
  menuShow.value = true
}
const onMenuSelect = (key: string) => {
  const clip = menuClip.value
  menuShow.value = false
  if (!clip) return
  if (key.startsWith("transition:")) {
    const next = nextClipOf(clip)
    if (!next) return
    props.elah.addTransition({
      fromClipId: clip.id,
      toClipId: next.id,
      trackId: clip.trackId,
      kind: key === "transition:slide" ? "slide" : "fade",
      durationFrames: Math.max(2, Math.round(fps.value * 0.5)),
      easing: "ease-out",
    })
  } else if (key === "duplicate") {
    const trackClips = props.elah.clipsByTrack.value[clip.trackId] ?? []
    const trackEnd = trackClips.reduce((m, c) => Math.max(m, c.startFrame + c.durationFrames), 0)
    const id = props.elah.engine.cloneClip(clip.id, clip.trackId, props.elah.currentFrame.value)
      ?? props.elah.engine.cloneClip(clip.id, clip.trackId, trackEnd)
    if (id) props.elah.setSelection([id])
  } else if (key === "delete") {
    props.elah.removeClip(clip)
  }
}

// Transition markers between adjacent clips.
const transitionsForTrack = (trackId: string): Transition[] =>
  props.elah.project.value.transitions.filter(t => t.trackId === trackId)
const markerLeft = (t: Transition): number => {
  const toClip = (props.elah.clipsByTrack.value[t.trackId] ?? []).find(c => c.id === t.toClipId)
  return (toClip ? toClip.startFrame : t.startFrame + Math.floor(t.durationFrames / 2)) * pixelsPerFrame.value
}
const openTransitionConfirm = ref<string | null>(null)
const transitionLabel = (t: Transition) => `${t.kind} · ${(t.durationFrames / fps.value).toFixed(2)}s`

// ---- Keyboard ----
const onKeydown = (e: KeyboardEvent) => {
  const target = e.target as HTMLElement | null
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target?.isContentEditable) return
  const elah = props.elah
  const mod = e.ctrlKey || e.metaKey
  const key = e.key.toLowerCase()

  if (mod && key === "c") {
    e.preventDefault()
    elah.copySelectedClips()
    return
  }
  if (mod && key === "v") {
    e.preventDefault()
    elah.pasteClips()
    return
  }
  if (mod && key === "z") {
    e.preventDefault()
    if (e.shiftKey) elah.redo()
    else elah.undo()
    return
  }
  if (mod && key === "y") {
    e.preventDefault()
    elah.redo()
    return
  }
  if (mod && key === "a") {
    e.preventDefault()
    elah.selectAll()
    return
  }

  switch (e.key) {
    case " ":
      e.preventDefault()
      elah.togglePlay()
      break
    case "Delete":
    case "Backspace": {
      elah.removeSelectedClips()
      break
    }
    case "s":
    case "S": {
      const c = elah.selectedClip.value
      if (c) elah.splitAtPlayhead(c.id, c.trackId)
      break
    }
    case "ArrowLeft":
      e.preventDefault()
      elah.seek(elah.currentFrame.value - 1)
      break
    case "ArrowRight":
      e.preventDefault()
      elah.seek(elah.currentFrame.value + 1)
      break
  }
}

const focusRoot = () => rootEl.value?.focus({ preventScroll: true })
</script>

<template>
  <div
    ref="rootEl"
    tabindex="0"
    class="h-full flex flex-col overflow-hidden outline-none bg-white dark:bg-neutral-900"
    :style="{ height: height ? height + 'px' : undefined }"
    @keydown="onKeydown"
    @pointerdown="focusRoot"
  >
    <!-- Timeline header: tracks + snap + zoom -->
    <div class="h-9 shrink-0 flex items-center gap-1.5 px-2 border-b border-clipper-ink/08 dark:border-white/08 bg-white dark:bg-neutral-900">
      <span class="w-40 shrink-0 text-[10px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50">Tracks</span>
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary @click="addTrackOfKind('audio')">
            <template #icon><Icon name="ph:music-notes-plus" size="14" /></template>
          </n-button>
        </template>
        Add audio track
      </n-tooltip>
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="tiny" quaternary @click="addTrackOfKind('elements')">
            <template #icon><Icon name="ph:shapes" size="14" /></template>
          </n-button>
        </template>
        Add elements track
      </n-tooltip>

      <span class="w-px h-4 bg-clipper-ink/08 dark:bg-white/08 mx-1" />

      <span class="flex items-center gap-1.5">
        <n-switch v-model:value="snapEnabled" size="small" />
        <span class="text-xs font-medium text-clipper-ink/50 dark:text-white/50">Snap</span>
      </span>

      <div class="flex-1" />

      <span class="text-[10px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50">Zoom</span>
      <n-slider v-model:value="pixelsPerFrame" :min="ZOOM_MIN" :max="ZOOM_MAX" :step="1" class="w-28" :tooltip="false" />
      <n-button size="tiny" secondary @click="fitZoom">Fit</n-button>
    </div>

    <!-- Body: fixed gutter + scrollable lanes (overflow-y-auto so extra tracks scroll when height is constrained) -->
    <div class="flex-1 min-h-0 flex items-start overflow-x-hidden overflow-y-auto">
      <!-- Fixed left gutter -->
      <div class="w-40 shrink-0 border-r border-clipper-ink/08 dark:border-white/08 flex flex-col">
        <div class="h-6 shrink-0 border-b border-clipper-ink/08 dark:border-white/08" />
        <div
          v-for="track in sortedTracks"
          :key="track.id"
          class="h-14 shrink-0 border-b border-clipper-ink/08 dark:border-white/08 flex flex-col justify-center gap-0.5 px-2"
          :class="track.order % 2 === 0 ? 'bg-neutral-100 dark:bg-neutral-800' : 'bg-neutral-50 dark:bg-neutral-900'"
        >
          <div class="flex items-center gap-1 min-w-0">
            <Icon :name="trackIcon(track.kind)" size="14" class="shrink-0 text-clipper-ink/60 dark:text-white/60" />
            <span class="flex-1 truncate text-xs font-medium text-clipper-ink dark:text-white">{{ track.name }}</span>
          </div>
          <div class="flex items-center gap-0.5">
            <n-tooltip trigger="hover">
              <template #trigger>
                <span class="flex items-center">
                  <n-switch
                    :value="track.muted"
                    size="small"
                    @update:value="setTrackMuted(track, $event)"
                  />
                </span>
              </template>
              {{ track.muted ? "Unmute track" : "Mute track" }}
            </n-tooltip>
            <n-button
              size="tiny"
              quaternary
              :type="track.solo ? 'primary' : 'default'"
              title="Solo track"
              @click="updateTrack(track.id, { solo: !track.solo })"
            >
              <template #icon><Icon name="ph:headphones" size="12" /></template>
            </n-button>
            <n-button
              size="tiny"
              quaternary
              :type="track.locked ? 'warning' : 'default'"
              :title="track.locked ? 'Unlock track' : 'Lock track'"
              @click="updateTrack(track.id, { locked: !track.locked })"
            >
              <template #icon><Icon :name="track.locked ? 'ph:lock' : 'ph:lock-open'" size="12" /></template>
            </n-button>
            <n-popconfirm @positive-click="removeTrack(track)">
              <template #trigger>
                <n-button size="tiny" quaternary title="Delete track">
                  <template #icon><Icon name="ph:trash" size="12" /></template>
                </n-button>
              </template>
              Delete track '{{ track.name }}' and its clips?
            </n-popconfirm>
          </div>
        </div>
      </div>

      <!-- Scrollable body -->
      <div ref="scrollEl" class="flex-1 min-w-0 overflow-x-auto overflow-y-hidden" @wheel="onWheel">
        <div class="relative" :style="{ width: `${contentWidth}px` }">
          <!-- Ruler -->
          <div
            ref="rulerEl"
            class="h-6 relative border-b border-clipper-ink/08 dark:border-white/08 bg-white dark:bg-neutral-900 cursor-pointer select-none"
            @pointerdown="onRulerPointerDown"
            @pointermove="onRulerPointerMove"
            @pointerup="onRulerPointerUp"
            @pointercancel="onRulerPointerUp"
          >
            <div
              v-for="tick in ticks"
              :key="tick.frame"
              class="absolute bottom-0"
              :class="tick.minor ? 'w-px h-2 bg-clipper-ink/20 dark:bg-white/20' : 'w-px h-3 bg-clipper-ink/40 dark:bg-white/40'"
              :style="{ left: `${tick.frame * pixelsPerFrame}px` }"
            />
            <span
              v-for="tick in ticks.filter(t => t.label)"
              :key="`label-${tick.frame}`"
              class="absolute top-0.5 text-[10px] font-mono text-clipper-ink/60 dark:text-white/60 -translate-x-1/2 pointer-events-none"
              :style="{ left: `${tick.frame * pixelsPerFrame}px` }"
            >{{ tick.label }}</span>
          </div>

          <!-- Track bodies -->
          <div
            v-for="track in sortedTracks"
            :key="track.id"
            class="h-14 relative border-b border-clipper-ink/08 dark:border-white/08"
            :class="[track.order % 2 === 0 ? 'bg-neutral-100 dark:bg-neutral-800' : 'bg-neutral-50 dark:bg-neutral-900', track.muted ? 'opacity-50' : '']"
            @pointerdown="onLanePointerDown"
          >
            <div
              v-for="clip in (elah.clipsByTrack.value[track.id] ?? [])"
              :key="clip.id"
              class="group absolute top-1 bottom-1 rounded-md border overflow-hidden select-none"
              :class="[
                clipClass(clip),
                elah.selectedClipIds.value.includes(clip.id) ? 'ring-2 ring-clipper-green' : '',
                clip.locked || track.locked ? 'cursor-not-allowed' : 'cursor-grab active:cursor-grabbing',
              ]"
              :style="{
                left: `${displayStart(clip) * pixelsPerFrame}px`,
                width: `${Math.max(2, displayDuration(clip) * pixelsPerFrame)}px`,
              }"
              @pointerdown="startDrag($event, clip, 'move')"
              @contextmenu="onClipContextMenu($event, clip)"
            >
              <div
                class="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-clipper-ink/10 dark:hover:bg-white/10"
                @pointerdown.stop="startDrag($event, clip, 'trim-start')"
              />
              <div
                class="absolute right-0 top-0 bottom-0 w-1.5 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-clipper-ink/10 dark:hover:bg-white/10"
                @pointerdown.stop="startDrag($event, clip, 'trim-end')"
              />
              <span class="absolute left-2 right-2 top-1 text-[11px] font-medium truncate text-clipper-ink dark:text-white pointer-events-none">
                {{ clip.name || clip.content || clip.type }}
              </span>
            </div>

            <!-- Transition markers (double-click diamond to remove) -->
            <n-popconfirm
              v-for="t in transitionsForTrack(track.id)"
              :key="t.id"
              trigger="manual"
              :show="openTransitionConfirm === t.id"
              @positive-click="elah.removeTransition(t.id); openTransitionConfirm = null"
              @clickoutside="openTransitionConfirm = null"
            >
              <template #trigger>
                <div
                  class="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-10 cursor-pointer"
                  :style="{ left: `${markerLeft(t)}px` }"
                  :title="transitionLabel(t)"
                  @pointerdown.stop
                  @dblclick.stop="openTransitionConfirm = t.id"
                >
                  <Icon name="ph:diamond-fill" size="14" class="text-clipper-green drop-shadow" />
                </div>
              </template>
              Remove {{ transitionLabel(t) }} transition?
            </n-popconfirm>
          </div>

          <!-- Playhead -->
          <div
            class="absolute top-0 bottom-0 w-0.5 bg-clipper-green z-20 pointer-events-none"
            :style="{ left: `${playheadX}px` }"
          >
            <div class="absolute -top-0 -left-[3px] w-2 h-2 rounded-sm bg-clipper-green" />
          </div>
        </div>
      </div>
    </div>

    <!-- Clip context menu -->
    <n-dropdown
      v-model:show="menuShow"
      trigger="manual"
      placement="bottom-start"
      :x="menuX"
      :y="menuY"
      :options="menuOptions"
      @select="onMenuSelect"
      @clickoutside="menuShow = false"
    />
  </div>
</template>
