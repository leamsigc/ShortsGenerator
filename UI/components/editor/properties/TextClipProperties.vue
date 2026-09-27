<script lang="ts" setup>
/**
 * TextClipProperties — Style / Transform / Animate tabs for the selected
 * text clip. Continuous edits (sliders, typing, steppers) preview through
 * elah.previewClip and collapse into ONE undo entry via elah.commitInteraction
 * on release/blur; discrete controls (selects, buttons) commit directly
 * through elah.updateClip.
 */
import { framesToTimecode } from "@elah/core"
import type { Clip, TextAnimation, Transform } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const clip = computed<Clip | null>(() => props.elah.selectedClip.value)
const fps = computed(() => props.elah.project.value.fps)

// ---- single undo funnel ----
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

// ---- tabs ----
type Tab = "style" | "transform" | "animate"
const tab = ref<Tab>("style")
const TABS: { id: Tab; label: string }[] = [
  { id: "style", label: "Style" },
  { id: "transform", label: "Transform" },
  { id: "animate", label: "Animate" },
]

// ---- transform ----
const DEFAULT_TRANSFORM: Transform = { x: 0.5, y: 0.5, scale: 1, rotation: 0, anchor: { x: 0.5, y: 0.5 } }
const tf = computed<Transform>(() => clip.value?.transform ?? DEFAULT_TRANSFORM)
const previewTf = (patch: Partial<Transform>) => preview({ transform: { ...tf.value, ...patch } })

// ---- Style models ----
const FONT_OPTIONS = [
  { label: "Sans Serif", value: "sans-serif" },
  { label: "Serif", value: "serif" },
  { label: "Monospace", value: "monospace" },
  { label: "Georgia", value: "Georgia" },
  { label: "Impact", value: "Impact" },
  { label: "Poppins", value: "Poppins" },
]
const contentModel = computed<string, string | null>({
  get: () => clip.value?.content ?? "",
  set: (v) => preview({ content: v ?? "" }),
})
const fontFamilyModel = computed<string, string | null>({
  get: () => clip.value?.fontFamily ?? "sans-serif",
  set: (v) => put({ fontFamily: v ?? "sans-serif" }),
})
const fontSizeModel = computed<number>({
  get: () => clip.value?.fontSize ?? 48,
  set: (v) => preview({ fontSize: v }),
})
const formatSizeTooltip = (v: number) => `${Math.round(v)}px`
const fontWeightModel = computed<string, string | null>({
  get: () => clip.value?.fontWeight ?? "normal",
  set: (v) => put({ fontWeight: v === "bold" ? "bold" : "normal" }),
})
const colorModel = computed<string, string | null>({
  get: () => clip.value?.color ?? "#ffffff",
  set: (v) => preview({ color: v ?? "#ffffff" }),
})
const ALIGNMENTS = ["left", "center", "right"] as const
const textAlignModel = computed<"left" | "center" | "right">({
  get: () => clip.value?.textAlign ?? "center",
  set: (v) => put({ textAlign: v }),
})
const opacityModel = computed<number>({
  get: () => clip.value?.opacity ?? 1,
  set: (v) => preview({ opacity: v }),
})
const pctTooltip = (v: number) => `${Math.round(v * 100)}%`

// ---- Transform models ----
const scaleModel = computed<number>({
  get: () => tf.value.scale,
  set: (v) => previewTf({ scale: v }),
})
const posXModel = computed<number, number | null>({
  get: () => Math.round(tf.value.x * 100),
  set: (v) => previewTf({ x: (v ?? 0) / 100 }),
})
const posYModel = computed<number, number | null>({
  get: () => Math.round(tf.value.y * 100),
  set: (v) => previewTf({ y: (v ?? 0) / 100 }),
})
const rotateModel = computed<number, number | null>({
  get: () => Math.round((tf.value.rotation * 180) / Math.PI),
  set: (v) => previewTf({ rotation: ((v ?? 0) * Math.PI) / 180 }),
})

// ---- Animate models ----
const FADE_OPTIONS = [
  { label: "None", value: "none" },
  { label: "Fade", value: "fade" },
]
const applyFade = (which: "in" | "out", val: string | null) => {
  const c = clip.value
  if (!c) return
  const prev = c.textAnimation
  const anim: TextAnimation = { durationFrames: prev?.durationFrames ?? 15 }
  if (which === "in" ? val === "fade" : prev?.in === "fade") anim.in = "fade"
  if (which === "out" ? val === "fade" : prev?.out === "fade") anim.out = "fade"
  put({ textAnimation: anim })
}
const fadeInModel = computed<string, string | null>({
  get: () => (clip.value?.textAnimation?.in === "fade" ? "fade" : "none"),
  set: (v) => applyFade("in", v),
})
const fadeOutModel = computed<string, string | null>({
  get: () => (clip.value?.textAnimation?.out === "fade" ? "fade" : "none"),
  set: (v) => applyFade("out", v),
})
const hasFade = computed(() => {
  const anim = clip.value?.textAnimation
  return anim?.in === "fade" || anim?.out === "fade"
})
const animDurationModel = computed<number, number | null>({
  get: () => clip.value?.textAnimation?.durationFrames ?? 15,
  set: (v) => {
    const c = clip.value
    if (!c) return
    const frames = Math.max(1, Math.round(v ?? 15))
    const anim: TextAnimation = { ...(c.textAnimation ?? { durationFrames: frames }), durationFrames: frames }
    preview({ textAnimation: anim })
  },
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden bg-white dark:bg-neutral-900">
    <template v-if="clip">
      <header class="shrink-0 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
        <div class="flex min-w-0 items-center gap-2">
          <n-tag size="small" :bordered="false">Text</n-tag>
          <span class="truncate text-sm font-semibold text-clipper-ink dark:text-white">{{ clip.name }}</span>
        </div>
        <p class="mt-0.5 text-[10px] tabular-nums text-clipper-ink/50 dark:text-white/50">
          {{ framesToTimecode(clip.startFrame, fps) }} – {{ framesToTimecode(clip.startFrame + clip.durationFrames, fps) }}
        </p>
      </header>

      <div class="flex shrink-0 items-center gap-4 px-4 border-b border-clipper-ink/08 dark:border-white/08">
        <button
          v-for="t in TABS"
          :key="t.id"
          type="button"
          class="relative py-2.5 text-xs transition-colors"
          :class="tab === t.id
            ? 'font-medium text-clipper-ink dark:text-white'
            : 'text-clipper-ink/50 dark:text-white/50 hover:text-clipper-ink dark:hover:text-white'"
          @click="tab = t.id"
        >
          {{ t.label }}
          <span v-if="tab === t.id" class="absolute left-0 right-0 -bottom-px h-0.5 rounded-full bg-clipper-green" />
        </button>
      </div>

      <div class="flex-1 min-h-0 space-y-4 overflow-y-auto p-4">
        <!-- Style -->
        <template v-if="tab === 'style'">
          <div>
            <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Text</label>
            <n-input
              v-model:value="contentModel"
              type="textarea"
              :rows="2"
              @blur="commit('Edit text')"
            />
          </div>

          <div>
            <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Font</label>
            <n-select v-model:value="fontFamilyModel" size="small" :options="FONT_OPTIONS" />
          </div>

          <div>
            <div class="mb-1.5 flex items-center justify-between">
              <label class="text-[11px] font-medium text-clipper-ink dark:text-white">Size</label>
              <span class="font-mono text-[10px] tabular-nums text-clipper-ink/50 dark:text-white/50">{{ Math.round(fontSizeModel) }}px</span>
            </div>
            <n-slider
              v-model:value="fontSizeModel"
              :min="16"
              :max="200"
              :step="1"
              :format-tooltip="formatSizeTooltip"
              @mouseup="commit('Edit font size')"
              @touchend="commit('Edit font size')"
            />
          </div>

          <div>
            <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Weight</label>
            <n-radio-group v-model:value="fontWeightModel" size="small" class="w-full">
              <n-radio-button value="normal" class="flex-1 text-center">Normal</n-radio-button>
              <n-radio-button value="bold" class="flex-1 text-center">Bold</n-radio-button>
            </n-radio-group>
          </div>

          <div>
            <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Color</label>
            <n-color-picker
              v-model:value="colorModel"
              size="small"
              :show-alpha="false"
              @update:show="(show: boolean) => !show && commit('Edit text color')"
            />
          </div>

          <div>
            <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Align</label>
            <div class="flex gap-1.5">
              <n-button
                v-for="a in ALIGNMENTS"
                :key="a"
                size="small"
                class="flex-1"
                :type="textAlignModel === a ? 'primary' : 'default'"
                :title="`Align ${a}`"
                @click="textAlignModel = a"
              >
                <template #icon>
                  <Icon :name="`ph:text-align-${a}`" />
                </template>
              </n-button>
            </div>
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
        </template>

        <!-- Transform -->
        <template v-else-if="tab === 'transform'">
          <div>
            <div class="mb-1.5 flex items-center justify-between">
              <label class="text-[11px] font-medium text-clipper-ink dark:text-white">Scale</label>
              <span class="font-mono text-[10px] tabular-nums text-clipper-ink/50 dark:text-white/50">{{ pctTooltip(scaleModel) }}</span>
            </div>
            <n-slider
              v-model:value="scaleModel"
              :min="0.05"
              :max="4"
              :step="0.01"
              :format-tooltip="pctTooltip"
              @mouseup="commit('Edit transform')"
              @touchend="commit('Edit transform')"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Position X</label>
              <n-input-number v-model:value="posXModel" size="small" :min="0" :max="100" class="w-full" @blur="commit('Edit transform')">
                <template #suffix>%</template>
              </n-input-number>
            </div>
            <div>
              <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Position Y</label>
              <n-input-number v-model:value="posYModel" size="small" :min="0" :max="100" class="w-full" @blur="commit('Edit transform')">
                <template #suffix>%</template>
              </n-input-number>
            </div>
          </div>

          <div>
            <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Rotate</label>
            <n-input-number v-model:value="rotateModel" size="small" class="w-full" @blur="commit('Edit transform')">
              <template #suffix>°</template>
            </n-input-number>
          </div>
        </template>

        <!-- Animate -->
        <template v-else>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Fade In</label>
              <n-select v-model:value="fadeInModel" size="small" :options="FADE_OPTIONS" />
            </div>
            <div>
              <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Fade Out</label>
              <n-select v-model:value="fadeOutModel" size="small" :options="FADE_OPTIONS" />
            </div>
          </div>

          <div v-if="hasFade">
            <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Duration</label>
            <n-input-number v-model:value="animDurationModel" size="small" :min="1" class="w-full" @blur="commit('Edit animation duration')">
              <template #suffix>f</template>
            </n-input-number>
          </div>
        </template>
      </div>
    </template>

    <template v-else>
      <header class="shrink-0 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
        <span class="text-sm font-semibold text-clipper-ink dark:text-white">Properties</span>
      </header>
      <div class="flex flex-1 items-center justify-center px-4 py-8 text-center text-xs text-clipper-ink/40 dark:text-white/40">
        Select a text clip to edit properties
      </div>
    </template>
  </div>
</template>
