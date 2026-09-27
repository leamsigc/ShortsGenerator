<script lang="ts" setup>
/**
 * VideoClipProperties — Transform / Style tabs for the selected video or
 * image clip. Transform adds a Fit segmented control (Contain | Cover) that
 * derives the clip transform from its natural media size vs the stage, via
 * transformFromContainRect / transformFromCoverRect from @elah/core.
 * Continuous edits preview through elah.previewClip and collapse into ONE
 * undo entry on release; discrete controls commit via elah.updateClip.
 */
import { framesToTimecode, transformFromContainRect, transformFromCoverRect } from "@elah/core"
import type { Clip, Transform } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const clip = computed<Clip | null>(() => props.elah.selectedClip.value)
const fps = computed(() => props.elah.project.value.fps)
const stage = computed(() => props.elah.project.value.stage)

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
type Tab = "transform" | "style"
const tab = ref<Tab>("transform")
const TABS: { id: Tab; label: string }[] = [
  { id: "transform", label: "Transform" },
  { id: "style", label: "Style" },
]

// ---- natural media size: composable cache, else async Image probe for images ----
const probedSize = ref<{ width: number; height: number } | null>(null)
watch(
  () => clip.value?.id,
  (id) => {
    probedSize.value = null
    const c = clip.value
    if (!id || !c || c.type !== "image" || !c.src) return
    if (props.elah.naturalSizes.value.has(id)) return
    const img = new Image()
    img.onload = () => {
      if (clip.value?.id === id && img.naturalWidth && img.naturalHeight) {
        probedSize.value = { width: img.naturalWidth, height: img.naturalHeight }
      }
    }
    img.src = c.src
  },
  { immediate: true },
)
const naturalSize = computed<{ width: number; height: number } | null>(() => {
  const c = clip.value
  if (!c) return null
  return props.elah.naturalSizes.value.get(c.id) ?? probedSize.value ?? null
})

// ---- transform ----
const DEFAULT_TRANSFORM: Transform = { x: 0.5, y: 0.5, scale: 1, rotation: 0, anchor: { x: 0.5, y: 0.5 } }
const tf = computed<Transform>(() => clip.value?.transform ?? DEFAULT_TRANSFORM)
const previewTf = (patch: Partial<Transform>) => preview({ transform: { ...tf.value, ...patch } })

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
const pctTooltip = (v: number) => `${Math.round(v * 100)}%`

// ---- Fit (Contain | Cover) ----
const containTf = computed<Transform | null>(() => {
  const n = naturalSize.value
  if (!n) return null
  return transformFromContainRect(n.width, n.height, stage.value.width, stage.value.height)
})
const coverTf = computed<Transform | null>(() => {
  const n = naturalSize.value
  if (!n) return null
  return transformFromCoverRect(n.width, n.height, stage.value.width, stage.value.height)
})
const sameTransform = (a: Transform, b: Transform): boolean =>
  Math.abs(a.x - b.x) < 1e-6 &&
  Math.abs(a.y - b.y) < 1e-6 &&
  Math.abs(a.scale - b.scale) < 1e-4 &&
  Math.abs(a.rotation - b.rotation) < 1e-6 &&
  Math.abs(a.anchor.x - b.anchor.x) < 1e-6 &&
  Math.abs(a.anchor.y - b.anchor.y) < 1e-6
const fitMode = computed<"contain" | "cover" | null>(() => {
  const c = clip.value
  if (!c?.transform || !containTf.value || !coverTf.value) return null
  if (sameTransform(c.transform, containTf.value)) return "contain"
  if (sameTransform(c.transform, coverTf.value)) return "cover"
  return null
})
const applyFit = (mode: "contain" | "cover") => {
  const c = clip.value
  if (!c) return
  const st = stage.value
  const n = naturalSize.value ?? { width: st.width, height: st.height }
  const transform =
    mode === "contain"
      ? transformFromContainRect(n.width, n.height, st.width, st.height)
      : transformFromCoverRect(n.width, n.height, st.width, st.height)
  put({ transform })
}

// ---- Style ----
const opacityModel = computed<number>({
  get: () => clip.value?.opacity ?? 1,
  set: (v) => preview({ opacity: v }),
})
const volumeModel = computed<number>({
  get: () => clip.value?.volume ?? 1,
  set: (v) => preview({ volume: v }),
})

const typeLabel = computed(() => (clip.value?.type === "image" ? "Image" : "Video"))
</script>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden bg-white dark:bg-neutral-900">
    <template v-if="clip">
      <header class="shrink-0 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
        <div class="flex min-w-0 items-center gap-2">
          <n-tag size="small" :bordered="false">{{ typeLabel }}</n-tag>
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
        <!-- Transform -->
        <template v-if="tab === 'transform'">
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

          <div>
            <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Fit</label>
            <div class="flex gap-1.5">
              <n-button
                size="small"
                class="flex-1"
                :type="fitMode === 'contain' ? 'primary' : 'default'"
                @click="applyFit('contain')"
              >
                Contain
              </n-button>
              <n-button
                size="small"
                class="flex-1"
                :type="fitMode === 'cover' ? 'primary' : 'default'"
                @click="applyFit('cover')"
              >
                Cover
              </n-button>
            </div>
            <p v-if="naturalSize" class="mt-1.5 text-[10px] tabular-nums text-clipper-ink/40 dark:text-white/40">
              {{ naturalSize.width }} × {{ naturalSize.height }} px source
            </p>
          </div>
        </template>

        <!-- Style -->
        <template v-else>
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

          <div v-if="clip.type === 'video'">
            <div class="mb-1.5 flex items-center justify-between">
              <label class="text-[11px] font-medium text-clipper-ink dark:text-white">Volume</label>
              <span class="font-mono text-[10px] tabular-nums text-clipper-ink/50 dark:text-white/50">{{ pctTooltip(volumeModel) }}</span>
            </div>
            <n-slider
              v-model:value="volumeModel"
              :min="0"
              :max="1"
              :step="0.01"
              :format-tooltip="pctTooltip"
              @mouseup="commit('Edit volume')"
              @touchend="commit('Edit volume')"
            />
          </div>
        </template>
      </div>
    </template>

    <template v-else>
      <header class="shrink-0 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
        <span class="text-sm font-semibold text-clipper-ink dark:text-white">Properties</span>
      </header>
      <div class="flex flex-1 items-center justify-center px-4 py-8 text-center text-xs text-clipper-ink/40 dark:text-white/40">
        Select a video clip to edit properties
      </div>
    </template>
  </div>
</template>
