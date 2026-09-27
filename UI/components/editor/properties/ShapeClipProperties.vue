<script lang="ts" setup>
/**
 * ShapeClipProperties — shape kind, fill, stroke and opacity for the
 * selected shape clip. Color picks and the width stepper preview through
 * elah.previewClip and collapse into one undo entry on release; discrete
 * controls commit via elah.updateClip.
 */
import { framesToTimecode } from "@elah/core"
import type { Clip, ShapeVariant } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const clip = computed<Clip | null>(() => props.elah.selectedClip.value)
const fps = computed(() => props.elah.project.value.fps)

const put = (updates: Partial<Clip>) => {
  const c = clip.value
  if (!c) return
  props.elah.updateClip(c.id, c.trackId, updates)
}
const preview = (updates: Partial<Clip>) => {
  const c = clip.value
  if (!c) return
  props.elah.previewClip(c.id, c.trackId, updates)
}
const commit = (description?: string) => props.elah.commitInteraction(description)

const SHAPE_OPTIONS: { label: string; value: ShapeVariant }[] = [
  { label: "Rect", value: "rect" },
  { label: "Circle", value: "circle" },
  { label: "Triangle", value: "triangle" },
]
const shapeKindModel = computed<ShapeVariant, string | null>({
  get: () => clip.value?.shapeKind ?? "rect",
  set: (v) => put({ shapeKind: v === "circle" || v === "triangle" ? v : "rect" }),
})
// 'transparent' (the engine default) is not a color the picker can render —
// fall back to a neutral swatch, same as the reference.
const shapeFillModel = computed<string, string | null>({
  get: () => {
    const fill = clip.value?.shapeFill
    return !fill || fill === "transparent" ? "#000000" : fill
  },
  set: (v) => preview({ shapeFill: v ?? "#000000" }),
})
const shapeStrokeModel = computed<string, string | null>({
  get: () => {
    const stroke = clip.value?.shapeStroke
    return !stroke || stroke === "transparent" ? "#ffffff" : stroke
  },
  set: (v) => preview({ shapeStroke: v ?? "#ffffff" }),
})
const strokeWidthModel = computed<number, number | null>({
  get: () => clip.value?.shapeStrokeWidth ?? 2,
  set: (v) => preview({ shapeStrokeWidth: Math.max(0, Math.min(40, Math.round(v ?? 2))) }),
})
const opacityModel = computed<number>({
  get: () => clip.value?.opacity ?? 1,
  set: (v) => preview({ opacity: v }),
})
const pctTooltip = (v: number) => `${Math.round(v * 100)}%`
</script>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden bg-white dark:bg-neutral-900">
    <template v-if="clip">
      <header class="shrink-0 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
        <div class="flex min-w-0 items-center gap-2">
          <n-tag size="small" :bordered="false">Shape</n-tag>
          <span class="truncate text-sm font-semibold text-clipper-ink dark:text-white">{{ clip.name }}</span>
        </div>
        <p class="mt-0.5 text-[10px] tabular-nums text-clipper-ink/50 dark:text-white/50">
          {{ framesToTimecode(clip.startFrame, fps) }} – {{ framesToTimecode(clip.startFrame + clip.durationFrames, fps) }}
        </p>
      </header>

      <div class="flex-1 min-h-0 space-y-4 overflow-y-auto p-4">
        <div>
          <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Shape</label>
          <n-radio-group v-model:value="shapeKindModel" size="small" class="flex w-full">
            <n-radio-button
              v-for="s in SHAPE_OPTIONS"
              :key="s.value"
              :value="s.value"
              class="flex-1 text-center"
            >
              {{ s.label }}
            </n-radio-button>
          </n-radio-group>
        </div>

        <div>
          <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Fill</label>
          <n-color-picker
            v-model:value="shapeFillModel"
            size="small"
            :show-alpha="false"
            @update:show="(show: boolean) => !show && commit('Edit fill')"
          />
        </div>

        <div>
          <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Stroke</label>
          <n-color-picker
            v-model:value="shapeStrokeModel"
            size="small"
            :show-alpha="false"
            @update:show="(show: boolean) => !show && commit('Edit stroke')"
          />
        </div>

        <div>
          <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Stroke width</label>
          <n-input-number
            v-model:value="strokeWidthModel"
            size="small"
            :min="0"
            :max="40"
            class="w-full"
            @blur="commit('Edit stroke width')"
          >
            <template #suffix>px</template>
          </n-input-number>
        </div>

        <div>
          <div class="mb-1.5 flex items-center justify-between">
            <label class="text-[11px] font-medium text-clipper-ink dark:text-white">Opacity</label>
            <span class="font-mono text-[10px] tabular-nums text-clipper-ink/50 dark:text-white/50">{{ pctTooltip(opacityModel) }}</span>
          </div>
          <n-slider
            v-model:value="opacityModel"
            :min="0"
            :max="1"
            :step="0.01"
            :format-tooltip="pctTooltip"
            @mouseup="commit('Edit opacity')"
            @touchend="commit('Edit opacity')"
          />
        </div>
      </div>
    </template>

    <template v-else>
      <header class="shrink-0 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
        <span class="text-sm font-semibold text-clipper-ink dark:text-white">Properties</span>
      </header>
      <div class="flex flex-1 items-center justify-center px-4 py-8 text-center text-xs text-clipper-ink/40 dark:text-white/40">
        Select a shape clip to edit properties
      </div>
    </template>
  </div>
</template>
