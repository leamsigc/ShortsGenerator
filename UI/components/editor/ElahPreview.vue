<script lang="ts" setup>
/**
 * ElahPreview — WebGL2 preview stage for the @elah/core editor with
 * interactive transform overlays (move / corner-scale handles / double-click
 * text editing), mapped onto the letterboxed stage viewport.
 *
 * Overlay rects are pure projections of resolveTimeline() output through
 * resolveDrawRect()/computeTextLayout(), scaled stage-px → CSS-px via the
 * computed contain viewport — the preview canvas and overlays always agree.
 */
import {
  resolveTimeline,
  resolveDrawRect,
  computeTextLayout,
  transformFromContainRect,
  computeContainViewport,
} from "@elah/core"
import type { Transform } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const outerEl = ref<HTMLElement | null>(null)
const stageEl = ref<HTMLElement | null>(null)
const overlayEl = ref<HTMLElement | null>(null)

const viewport = ref<{ x: number; y: number; width: number; height: number }>({ x: 0, y: 0, width: 0, height: 0 })

const applySize = () => {
  const outer = outerEl.value
  if (!outer) return
  const stage = props.elah.project.value.stage
  const rect = outer.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  const vp = computeContainViewport(rect.width, rect.height, stage.width, stage.height)
  const width = Math.max(1, Math.floor(vp.width))
  const height = Math.max(1, Math.floor(vp.height))
  viewport.value = { x: vp.x, y: vp.y, width, height }
  props.elah.resizePreview(width, height)
}

let resizeObserver: ResizeObserver | null = null

// ---- Fullscreen ------------------------------------------------------------
const isFullscreen = ref(false)
const onFullscreenChange = () => { isFullscreen.value = document.fullscreenElement === outerEl.value }
const toggleFullscreen = () => {
  const outer = outerEl.value
  if (!outer || !document.fullscreenEnabled) return
  if (document.fullscreenElement) void document.exitFullscreen()
  else void outer.requestFullscreen()
}

onMounted(() => {
  if (stageEl.value) props.elah.mountPreview(stageEl.value)
  if (outerEl.value) {
    resizeObserver = new ResizeObserver(applySize)
    resizeObserver.observe(outerEl.value)
  }
  document.addEventListener("fullscreenchange", onFullscreenChange)
  applySize()
})

watch(() => props.elah.project.value.stage, applySize)

onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onFullscreenChange)
  resizeObserver?.disconnect()
  resizeObserver = null
  endOverlayDrag(false)
})

// ---- Overlay projections ------------------------------------------------
interface OverlayItem {
  id: string
  trackId: string
  clipType: "video" | "image" | "text"
  name: string
  x: number
  y: number
  width: number
  height: number
  rotationDeg: number
  locked: boolean
  selected: boolean
  text?: string
}

let measureCtx: CanvasRenderingContext2D | null = null
const getMeasure = (): CanvasRenderingContext2D | null => {
  if (!measureCtx) measureCtx = document.createElement("canvas").getContext("2d")
  return measureCtx
}

const overlayScene = computed(() =>
  resolveTimeline(props.elah.currentFrame.value, props.elah.project.value),
)

const overlays = computed<OverlayItem[]>(() => {
  const stage = props.elah.project.value.stage
  const vp = viewport.value
  const s = vp.width > 0 ? vp.width / stage.width : 0
  if (!s) return []
  const items: OverlayItem[] = []
  const base = (id: string, trackId: string, clipType: OverlayItem["clipType"], name: string) => {
    const found = props.elah.findClip(id)
    const locked = found
      ? Boolean(found.clip.locked) || props.elah.engine.isTrackLocked(found.clip.trackId)
      : false
    return {
      id,
      trackId,
      clipType,
      name,
      locked,
      selected: props.elah.selectedClipIds.value.includes(id),
    }
  }
  for (const v of overlayScene.value.videos) {
    const nat = props.elah.naturalSizes.value.get(v.id)
    const r = resolveDrawRect(v.transform, stage.width, stage.height, nat?.width, nat?.height)
    items.push({
      ...base(v.id, v.trackId, "video", v.name),
      x: r.x * s, y: r.y * s, width: r.width * s, height: r.height * s,
      rotationDeg: (r.rotation * 180) / Math.PI,
    })
  }
  for (const im of overlayScene.value.images) {
    const nat = props.elah.naturalSizes.value.get(im.id)
    const r = resolveDrawRect(im.transform, stage.width, stage.height, nat?.width, nat?.height)
    items.push({
      ...base(im.id, im.trackId, "image", im.name),
      x: r.x * s, y: r.y * s, width: r.width * s, height: r.height * s,
      rotationDeg: (r.rotation * 180) / Math.PI,
    })
  }
  const measure = getMeasure()
  for (const t of overlayScene.value.texts) {
    const layout = measure ? computeTextLayout(measure, t, stage) : null
    const box = layout?.box ?? { x: 0.2 * stage.width, y: 0.45 * stage.height, width: 0.6 * stage.width, height: 0.1 * stage.height }
    items.push({
      ...base(t.id, t.trackId, "text", t.name),
      x: box.x * s, y: box.y * s, width: Math.max(24, box.width * s), height: Math.max(18, box.height * s),
      rotationDeg: ((t.transform?.rotation ?? 0) * 180) / Math.PI,
      text: t.content,
    })
  }
  return items
})

// ---- Overlay interactions ------------------------------------------------
type OverlayDrag = {
  id: string
  trackId: string
  kind: "move" | "scale"
  startX: number
  startY: number
  orig: Transform
  centerX: number
  centerY: number
  startDist: number
}
let overlayDrag: OverlayDrag | null = null

const clamp01 = (v: number) => Math.max(0, Math.min(1, v))

const startOverlayDrag = (e: PointerEvent, item: OverlayItem, kind: OverlayDrag["kind"]) => {
  e.preventDefault()
  e.stopPropagation()
  const elah = props.elah
  elah.setSelection([item.id])
  if (item.locked) return
  const found = elah.findClip(item.id)
  if (!found) return
  const stage = elah.project.value.stage
  // Clips without a transform render as "contain" — materialize that as the
  // drag baseline so the first drag does not visually jump.
  const nat = elah.naturalSizes.value.get(item.id)
  const orig: Transform = found.clip.transform
    ? { ...found.clip.transform, anchor: { ...found.clip.transform.anchor } }
    : transformFromContainRect(nat?.width ?? stage.width, nat?.height ?? stage.height, stage.width, stage.height)
  let centerX = 0
  let centerY = 0
  let startDist = 1
  if (kind === "scale") {
    const layer = overlayEl.value
    if (!layer) return
    const rect = layer.getBoundingClientRect()
    centerX = item.x + item.width / 2
    centerY = item.y + item.height / 2
    startDist = Math.max(2, Math.hypot(e.clientX - rect.left - centerX, e.clientY - rect.top - centerY))
  }
  overlayDrag = { id: item.id, trackId: item.trackId, kind, startX: e.clientX, startY: e.clientY, orig, centerX, centerY, startDist }
  window.addEventListener("pointermove", onOverlayPointerMove)
  window.addEventListener("pointerup", onOverlayPointerUp, { once: true })
}

const onOverlayPointerMove = (e: PointerEvent) => {
  const drag = overlayDrag
  if (!drag) return
  const elah = props.elah
  const vp = viewport.value
  if (drag.kind === "move") {
    const dx = (e.clientX - drag.startX) / Math.max(1, vp.width)
    const dy = (e.clientY - drag.startY) / Math.max(1, vp.height)
    elah.previewClip(drag.id, drag.trackId, {
      transform: { ...drag.orig, x: clamp01(drag.orig.x + dx), y: clamp01(drag.orig.y + dy) },
    })
  } else {
    const layer = overlayEl.value
    if (!layer) return
    const rect = layer.getBoundingClientRect()
    const dist = Math.hypot(e.clientX - rect.left - drag.centerX, e.clientY - rect.top - drag.centerY)
    const scale = Math.max(0.05, Math.min(10, drag.orig.scale * (dist / drag.startDist)))
    elah.previewClip(drag.id, drag.trackId, { transform: { ...drag.orig, scale } })
  }
}

const onOverlayPointerUp = () => endOverlayDrag(true)

const endOverlayDrag = (commit: boolean) => {
  window.removeEventListener("pointermove", onOverlayPointerMove)
  if (overlayDrag) {
    if (commit) props.elah.commitInteraction(overlayDrag.kind === "move" ? "Move clip" : "Scale clip")
    else props.elah.cancelInteraction()
  }
  overlayDrag = null
}

const onOverlayBackgroundPointerDown = (e: PointerEvent) => {
  if (e.target === e.currentTarget) props.elah.selectNone()
}

// ---- Inline text editing (double-click a text overlay) -------------------
const editingId = ref<string | null>(null)
const editingText = ref("")
const editingRect = ref<{ x: number; y: number; width: number; height: number } | null>(null)
const editInputRef = ref<{ focus: () => void } | null>(null)

const onItemDblClick = (e: MouseEvent, item: OverlayItem) => {
  if (item.clipType !== "text") return
  e.stopPropagation()
  // Cancel any in-flight pointer drag from the double-click itself.
  if (overlayDrag) endOverlayDrag(false)
  const found = props.elah.findClip(item.id)
  if (!found) return
  editingId.value = item.id
  editingText.value = found.clip.content ?? ""
  editingRect.value = { x: item.x, y: item.y, width: item.width, height: item.height }
  nextTick(() => editInputRef.value?.focus())
}
const commitEditing = () => {
  const id = editingId.value
  if (id) {
    const found = props.elah.findClip(id)
    if (found) props.elah.updateClip(id, found.trackId, { content: editingText.value })
  }
  editingId.value = null
}
const cancelEditing = () => { editingId.value = null }

const HANDLES = ["tl", "tr", "bl", "br"] as const
const handleClass = (h: (typeof HANDLES)[number]) => ({
  tl: "left-0 top-0 -translate-x-1/2 -translate-y-1/2 cursor-nwse-resize",
  tr: "right-0 top-0 translate-x-1/2 -translate-y-1/2 cursor-nesw-resize",
  bl: "left-0 bottom-0 -translate-x-1/2 translate-y-1/2 cursor-nesw-resize",
  br: "right-0 bottom-0 translate-x-1/2 translate-y-1/2 cursor-nwse-resize",
}[h])
</script>

<template>
  <div
    ref="outerEl"
    class="flex-1 min-w-0 relative overflow-hidden bg-neutral-950"
  >
    <!-- Stage viewport (letterboxed) -->
    <div
      class="absolute"
      :style="{
        left: `${viewport.x}px`,
        top: `${viewport.y}px`,
        width: `${viewport.width}px`,
        height: `${viewport.height}px`,
      }"
    >
      <div
        ref="stageEl"
        class="absolute inset-0 bg-black overflow-hidden"
      />

      <!-- Interactive transform overlay layer -->
      <div
        ref="overlayEl"
        class="absolute inset-0 z-10"
        @pointerdown="onOverlayBackgroundPointerDown"
      >
        <div
          v-for="item in overlays"
          :key="item.id"
          class="absolute select-none touch-none"
          :class="[
            item.selected ? 'border-2 border-solid border-clipper-green' : 'border border-dashed border-clipper-green/70 hover:border-clipper-green',
            item.locked ? 'cursor-not-allowed' : 'cursor-move',
          ]"
          :style="{
            left: `${item.x}px`,
            top: `${item.y}px`,
            width: `${item.width}px`,
            height: `${item.height}px`,
            transform: `rotate(${item.rotationDeg}deg)`,
            transformOrigin: 'center center',
          }"
          :title="item.name"
          @pointerdown="startOverlayDrag($event, item, 'move')"
          @dblclick="onItemDblClick($event, item)"
        >
          <div
            v-for="h in HANDLES"
            v-show="item.selected && !item.locked"
            :key="h"
            class="absolute w-3 h-3 rounded-full bg-clipper-green border border-white dark:border-neutral-900"
            :class="handleClass(h)"
            @pointerdown="startOverlayDrag($event, item, 'scale')"
          />
        </div>

        <!-- Inline text editor (double-click) -->
        <div
          v-if="editingId && editingRect"
          class="absolute z-20"
          :style="{
            left: `${editingRect.x}px`,
            top: `${editingRect.y}px`,
            width: `${Math.max(120, editingRect.width)}px`,
          }"
          @pointerdown.stop
        >
          <n-input
            ref="editInputRef"
            v-model:value="editingText"
            size="small"
            placeholder="Caption text"
            @keyup.enter.stop="commitEditing"
            @keyup.esc.stop="cancelEditing"
            @keydown.space.stop
            @blur="commitEditing"
          />
        </div>
      </div>

      <!-- Timecode chip -->
      <span class="absolute bottom-3 right-14 z-20 text-xs font-mono bg-black/70 text-white px-2 py-0.5 rounded pointer-events-none">
        {{ elah.timecode.value }}
      </span>
    </div>

    <!-- Floating fullscreen toggle -->
    <div class="absolute bottom-3 right-3 z-30">
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button
            quaternary
            class="!w-9 !h-9 !rounded-full !bg-black/60 !border !border-white/10 !text-white"
            aria-label="Fullscreen"
            @click="toggleFullscreen"
          >
            <template #icon>
              <Icon :name="isFullscreen ? 'ph:arrows-in' : 'ph:arrows-out'" size="16" />
            </template>
          </n-button>
        </template>
        Fullscreen
      </n-tooltip>
    </div>
  </div>
</template>
