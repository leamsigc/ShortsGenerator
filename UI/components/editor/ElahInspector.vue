<script lang="ts" setup>
/**
 * ElahInspector — property editor for the selected clip: common props, text
 * styling, transform, source segment (in/out point) and the transition that
 * starts from this clip. All writes funnel through elah.updateClip /
 * elah.updateTransition (single undo entry per change).
 */
import { framesToSeconds, secondsToFrames } from "@elah/core"
import type { Clip, TextAnimation, Transform, Transition, TransitionKind, TransitionEasing } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const clip = computed<Clip | null>(() => props.elah.selectedClip.value)

const update = (updates: Partial<Clip>) => {
  const c = clip.value
  if (!c) return
  props.elah.updateClip(c.id, c.trackId, updates)
}

const DEFAULT_TRANSFORM: Transform = { x: 0.5, y: 0.5, scale: 1, rotation: 0, anchor: { x: 0.5, y: 0.5 } }

// ---- Common fields ----
const nameModel = computed({
  get: () => clip.value?.name ?? "",
  set: (v: string) => update({ name: v }),
})
const opacityModel = computed({
  get: () => clip.value?.opacity ?? 1,
  set: (v: number) => update({ opacity: v }),
})
const volumeModel = computed({
  get: () => clip.value?.volume ?? 1,
  set: (v: number) => update({ volume: v }),
})

// ---- Text fields ----
const contentModel = computed({
  get: () => clip.value?.content ?? "",
  set: (v: string) => update({ content: v }),
})
const fontSizeModel = computed<number>({
  get: () => clip.value?.fontSize ?? 64,
  set: (v: number | null) => update({ fontSize: v ?? 64 }),
})
const colorModel = computed({
  get: () => clip.value?.color ?? "#ffffff",
  set: (v: string) => update({ color: v }),
})
const fontWeightOptions = [
  { label: "Normal", value: "normal" },
  { label: "Bold", value: "bold" },
]
const fontWeightModel = computed({
  get: () => clip.value?.fontWeight ?? "normal",
  set: (v: string | null) => update({ fontWeight: (v === "bold" ? "bold" : "normal") }),
})
const textAlignOptions = [
  { label: "Left", value: "left" },
  { label: "Center", value: "center" },
  { label: "Right", value: "right" },
]
const textAlignModel = computed({
  get: () => clip.value?.textAlign ?? "center",
  set: (v: string | null) => update({ textAlign: (v === "left" || v === "right" ? v : "center") }),
})

const applyTextAnim = (fadeIn: boolean, fadeOut: boolean) => {
  const prev = clip.value?.textAnimation
  const anim: TextAnimation = { ...prev, durationFrames: prev?.durationFrames ?? 15 }
  if (fadeIn) anim.in = "fade"
  else delete anim.in
  if (fadeOut) anim.out = "fade"
  else delete anim.out
  update({ textAnimation: anim })
}
const fadeInModel = computed({
  get: () => clip.value?.textAnimation?.in === "fade",
  set: (v: boolean) => applyTextAnim(v, clip.value?.textAnimation?.out === "fade"),
})
const fadeOutModel = computed({
  get: () => clip.value?.textAnimation?.out === "fade",
  set: (v: boolean) => applyTextAnim(clip.value?.textAnimation?.in === "fade", v),
})

// ---- Transform (video / image) ----
const transformModel = computed<Transform>(() => clip.value?.transform ?? DEFAULT_TRANSFORM)
const posXModel = computed({
  get: () => transformModel.value.x,
  set: (v: number) => update({ transform: { ...DEFAULT_TRANSFORM, ...transformModel.value, x: v } }),
})
const posYModel = computed({
  get: () => transformModel.value.y,
  set: (v: number) => update({ transform: { ...DEFAULT_TRANSFORM, ...transformModel.value, y: v } }),
})
const scaleModel = computed({
  get: () => transformModel.value.scale,
  set: (v: number) => update({ transform: { ...DEFAULT_TRANSFORM, ...transformModel.value, scale: v } }),
})
const rotationModel = computed({
  get: () => transformModel.value.rotation,
  set: (v: number) => update({ transform: { ...DEFAULT_TRANSFORM, ...transformModel.value, rotation: v } }),
})

// ---- Source segment (video / audio in-out point, seconds) ----
const fps = computed(() => props.elah.project.value.fps)
const sourceStartSecModel = computed<number>({
  get: () => Number(framesToSeconds(clip.value?.sourceStartFrame ?? 0, fps.value).toFixed(3)),
  set: (v: number | null) => {
    const c = clip.value
    if (!c) return
    const frame = Math.max(0, Math.min(secondsToFrames(v ?? 0, fps.value), c.sourceStartFrame + c.sourceDurationFrames - 1))
    update({ sourceStartFrame: frame, sourceDurationFrames: Math.max(1, c.sourceStartFrame + c.sourceDurationFrames - frame) })
  },
})
const sourceEndSecModel = computed<number>({
  get: () => Number(framesToSeconds((clip.value?.sourceStartFrame ?? 0) + (clip.value?.sourceDurationFrames ?? 0), fps.value).toFixed(3)),
  set: (v: number | null) => {
    const c = clip.value
    if (!c) return
    const endFrame = Math.max(c.sourceStartFrame + 1, secondsToFrames(v ?? 0, fps.value))
    update({ sourceDurationFrames: endFrame - c.sourceStartFrame })
  },
})

// ---- Transition that starts from the selected clip ----
const outgoingTransitions = computed<Transition[]>(() => {
  const c = clip.value
  if (!c || (c.type !== "video" && c.type !== "image")) return []
  return props.elah.project.value.transitions.filter(t => t.fromClipId === c.id)
})
const transitionClipName = (t: Transition) => props.elah.findClip(t.toClipId)?.clip.name ?? t.toClipId
const transitionKindOptions = [
  { label: "Fade", value: "fade" },
  { label: "Slide", value: "slide" },
  { label: "Wipe", value: "wipe" },
]
const transitionEasingOptions = [
  { label: "Linear", value: "linear" },
  { label: "Ease in", value: "ease-in" },
  { label: "Ease out", value: "ease-out" },
]
const updateTransitionKind = (t: Transition, kind: TransitionKind | null) => {
  if (kind) props.elah.updateTransition(t.id, { kind })
}
const updateTransitionEasing = (t: Transition, easing: TransitionEasing | null) => {
  if (easing) props.elah.updateTransition(t.id, { easing })
}
const updateTransitionDuration = (t: Transition, frames: number | null) => {
  props.elah.updateTransition(t.id, { durationFrames: Math.max(2, Math.round(frames ?? 15)) })
}
</script>

<template>
  <div class="w-80 shrink-0 border-l border-clipper-ink/08 dark:border-white/08 bg-white dark:bg-neutral-900 overflow-y-auto">
    <div v-if="clip" class="p-4 space-y-4 text-xs">
      <div class="flex items-center justify-between">
        <n-tag size="small" :bordered="false">{{ clip.type }}</n-tag>
        <span class="font-mono text-[11px] text-clipper-ink/40 dark:text-white/40 tabular-nums">{{ elah.timecode.value }}</span>
      </div>

      <!-- Common -->
      <div class="space-y-1">
        <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Name</label>
        <n-input v-model:value="nameModel" size="small" />
      </div>

      <div class="space-y-1">
        <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">
          Opacity <span class="font-mono">{{ opacityModel.toFixed(2) }}</span>
        </label>
        <n-slider v-model:value="opacityModel" :min="0" :max="1" :step="0.05" />
      </div>

      <div v-if="clip.type === 'video' || clip.type === 'audio'" class="space-y-1">
        <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">
          Volume <span class="font-mono">{{ volumeModel.toFixed(2) }}</span>
        </label>
        <n-slider v-model:value="volumeModel" :min="0" :max="1" :step="0.05" />
      </div>

      <!-- Text -->
      <template v-if="clip.type === 'text'">
        <div class="pt-3 border-t border-clipper-ink/08 dark:border-white/08 space-y-4">
          <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50">Text</p>
          <div class="space-y-1">
            <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Content</label>
            <n-input v-model:value="contentModel" type="textarea" :rows="3" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
              <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Font size</label>
              <n-input-number v-model:value="fontSizeModel" size="small" :min="8" :max="400" class="w-full" />
            </div>
            <div class="space-y-1">
              <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Color</label>
              <n-color-picker v-model:value="colorModel" :show-alpha="false" size="small" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
              <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Weight</label>
              <n-select v-model:value="fontWeightModel" size="small" :options="fontWeightOptions" />
            </div>
            <div class="space-y-1">
              <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Align</label>
              <n-select v-model:value="textAlignModel" size="small" :options="textAlignOptions" />
            </div>
          </div>
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-clipper-ink/60 dark:text-white/60">Fade in</span>
              <n-switch v-model:value="fadeInModel" size="small" />
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-clipper-ink/60 dark:text-white/60">Fade out</span>
              <n-switch v-model:value="fadeOutModel" size="small" />
            </div>
          </div>
        </div>
      </template>

      <!-- Transform -->
      <template v-if="clip.type === 'video' || clip.type === 'image'">
        <div class="pt-3 border-t border-clipper-ink/08 dark:border-white/08 space-y-4">
          <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50">Transform</p>
          <div class="space-y-1">
            <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">
              Position (x) <span class="font-mono">{{ posXModel.toFixed(2) }}</span>
            </label>
            <n-slider v-model:value="posXModel" :min="0" :max="1" :step="0.01" />
          </div>
          <div class="space-y-1">
            <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">
              Position (y) <span class="font-mono">{{ posYModel.toFixed(2) }}</span>
            </label>
            <n-slider v-model:value="posYModel" :min="0" :max="1" :step="0.01" />
          </div>
          <div class="space-y-1">
            <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">
              Scale <span class="font-mono">{{ scaleModel.toFixed(2) }}</span>
            </label>
            <n-slider v-model:value="scaleModel" :min="0.2" :max="3" :step="0.05" />
          </div>
          <div class="space-y-1">
            <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">
              Rotation <span class="font-mono">{{ rotationModel.toFixed(2) }} rad</span>
            </label>
            <n-slider v-model:value="rotationModel" :min="-1.57" :max="1.57" :step="0.01" />
          </div>
        </div>
      </template>

      <!-- Source segment (in / out point) -->
      <template v-if="clip.type === 'video' || clip.type === 'audio'">
        <div class="pt-3 border-t border-clipper-ink/08 dark:border-white/08 space-y-4">
          <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50">Source segment</p>
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
              <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">In (s)</label>
              <n-input-number v-model:value="sourceStartSecModel" size="small" :min="0" :step="0.5" :precision="2" class="w-full" />
            </div>
            <div class="space-y-1">
              <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Out (s)</label>
              <n-input-number v-model:value="sourceEndSecModel" size="small" :min="0" :step="0.5" :precision="2" class="w-full" />
            </div>
          </div>
          <p class="text-[11px] text-clipper-ink/40 dark:text-white/40">
            Plays {{ sourceStartSecModel }}s → {{ sourceEndSecModel }}s of the source media.
          </p>
        </div>
      </template>

      <!-- Transition starting from this clip -->
      <template v-if="outgoingTransitions.length">
        <div class="pt-3 border-t border-clipper-ink/08 dark:border-white/08 space-y-4">
          <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/50 dark:text-white/50">Transition</p>
          <div
            v-for="t in outgoingTransitions"
            :key="t.id"
            class="space-y-3 rounded-lg border border-clipper-ink/08 dark:border-white/08 p-3"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs text-clipper-ink/60 dark:text-white/60 truncate">
                → {{ transitionClipName(t) }}
              </span>
              <n-popconfirm @positive-click="elah.removeTransition(t.id)">
                <template #trigger>
                  <n-button size="tiny" quaternary title="Remove transition">
                    <template #icon><Icon name="ph:trash" size="12" /></template>
                  </n-button>
                </template>
                Remove this transition?
              </n-popconfirm>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1">
                <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Kind</label>
                <n-select :value="t.kind" size="small" :options="transitionKindOptions" @update:value="updateTransitionKind(t, $event)" />
              </div>
              <div class="space-y-1">
                <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Easing</label>
                <n-select :value="t.easing ?? 'ease-out'" size="small" :options="transitionEasingOptions" @update:value="updateTransitionEasing(t, $event)" />
              </div>
            </div>
            <div class="space-y-1">
              <label class="block text-xs font-medium text-clipper-ink/60 dark:text-white/60">Duration (frames)</label>
              <n-input-number :value="t.durationFrames" size="small" :min="2" :step="2" class="w-full" @update:value="updateTransitionDuration(t, $event)" />
            </div>
          </div>
        </div>
      </template>

      <!-- Danger zone -->
      <div class="pt-3 border-t border-clipper-ink/08 dark:border-white/08">
        <n-popconfirm @positive-click="elah.removeClip(clip)">
          <template #trigger>
            <n-button size="small" block type="error" secondary>
              <template #icon><Icon name="ph:trash" size="14" /></template>
              Delete clip
            </n-button>
          </template>
          Delete '{{ clip.name }}'?
        </n-popconfirm>
      </div>
    </div>

    <div v-else class="p-6 text-center text-xs text-clipper-ink/40 dark:text-white/40">
      Select a clip to edit its properties.
    </div>
  </div>
</template>
