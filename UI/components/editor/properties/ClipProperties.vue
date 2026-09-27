<script lang="ts" setup>
/**
 * ClipProperties — right-rail inspector shell for the selected clip.
 * Reads elah.selectedClip and dispatches to the per-type property panel
 * (text / video|image / audio / shape). Children read the clip from elah
 * themselves, mirroring the reference pattern where each panel resolves
 * its own selection.
 */
import type { ElahEditor } from "~/composables/useElahEditor"
import TextClipProperties from "./TextClipProperties.vue"
import VideoClipProperties from "./VideoClipProperties.vue"
import AudioClipProperties from "./AudioClipProperties.vue"
import ShapeClipProperties from "./ShapeClipProperties.vue"

const props = defineProps<{ elah: ElahEditor }>()

const clip = computed(() => props.elah.selectedClip.value)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden bg-white dark:bg-neutral-900">
    <template v-if="clip">
      <TextClipProperties v-if="clip.type === 'text'" :elah="elah" />
      <VideoClipProperties v-else-if="clip.type === 'video' || clip.type === 'image'" :elah="elah" />
      <AudioClipProperties v-else-if="clip.type === 'audio'" :elah="elah" />
      <ShapeClipProperties v-else-if="clip.type === 'shape'" :elah="elah" />
    </template>

    <template v-else>
      <header class="shrink-0 px-4 py-3 border-b border-clipper-ink/08 dark:border-white/08">
        <span class="text-sm font-semibold text-clipper-ink dark:text-white">Properties</span>
      </header>
      <div class="flex flex-1 items-center justify-center px-4 py-8 text-center text-xs text-clipper-ink/40 dark:text-white/40">
        Select a clip to edit properties
      </div>
    </template>
  </div>
</template>
