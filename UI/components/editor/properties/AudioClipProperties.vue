<script lang="ts" setup>
/**
 * AudioClipProperties — volume and name for the selected audio clip.
 * Typing previews through elah.previewClip and commits on blur (one undo
 * entry per edit); the volume slider previews during drag and commits on
 * release.
 */
import { framesToTimecode } from "@elah/core"
import type { Clip } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const clip = computed<Clip | null>(() => props.elah.selectedClip.value)
const fps = computed(() => props.elah.project.value.fps)

const preview = (updates: Partial<Clip>) => {
  const c = clip.value
  if (!c) return
  props.elah.previewClip(c.id, c.trackId, updates)
}
const commit = (description?: string) => props.elah.commitInteraction(description)

const nameModel = computed<string, string | null>({
  get: () => clip.value?.name ?? "",
  set: (v) => preview({ name: v ?? "" }),
})
const volumeModel = computed<number>({
  get: () => clip.value?.volume ?? 1,
  set: (v) => preview({ volume: v }),
})
const pctTooltip = (v: number) => `${Math.round(v * 100)}%`
</script>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden bg-white dark:bg-neutral-900">
    <template v-if="clip">
      <header class="shrink-0 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
        <div class="flex min-w-0 items-center gap-2">
          <n-tag size="small" :bordered="false">Audio</n-tag>
          <span class="truncate text-sm font-semibold text-clipper-ink dark:text-white">{{ clip.name }}</span>
        </div>
        <p class="mt-0.5 text-[10px] tabular-nums text-clipper-ink/50 dark:text-white/50">
          {{ framesToTimecode(clip.startFrame, fps) }} – {{ framesToTimecode(clip.startFrame + clip.durationFrames, fps) }}
        </p>
      </header>

      <div class="flex-1 min-h-0 space-y-4 overflow-y-auto p-4">
        <div>
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

        <div>
          <label class="mb-1.5 block text-[11px] font-medium text-clipper-ink dark:text-white">Name</label>
          <n-input v-model:value="nameModel" size="small" @blur="commit('Rename clip')" />
        </div>
      </div>
    </template>

    <template v-else>
      <header class="shrink-0 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
        <span class="text-sm font-semibold text-clipper-ink dark:text-white">Properties</span>
      </header>
      <div class="flex flex-1 items-center justify-center px-4 py-8 text-center text-xs text-clipper-ink/40 dark:text-white/40">
        Select an audio clip to edit properties
      </div>
    </template>
  </div>
</template>
