<script lang="ts" setup">
/**
 * TransportBar — video transport under the preview: current | total timecode
 * (current in accent), big round play/pause, and a stop (pause + seek 0) ghost.
 */
import { framesToTimecode } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const totalTimecode = computed(() =>
  framesToTimecode(props.elah.totalFrames.value, props.elah.project.value.fps),
)

const onStop = () => {
  props.elah.pause()
  props.elah.seek(0)
}
</script>

<template>
  <div class="shrink-0 h-11 px-4 grid grid-cols-[1fr_auto_1fr] items-center border-t border-white/10">
    <!-- Left: current | total -->
    <span class="font-mono text-xs tabular-nums whitespace-nowrap">
      <span class="text-clipper-green">{{ elah.timecode.value }}</span>
      <span class="text-white/40 mx-1.5">|</span>
      <span class="text-white/60">{{ totalTimecode }}</span>
    </span>

    <!-- Center: play/pause + stop -->
    <div class="flex items-center gap-3">
      <button
        type="button"
        class="w-9 h-9 rounded-full bg-white text-black flex items-center justify-center hover:opacity-90 transition-opacity cursor-pointer shrink-0"
        :title="elah.isPlaying.value ? 'Pause (Space)' : 'Play (Space)'"
        @click="elah.togglePlay()"
      >
        <Icon :name="elah.isPlaying.value ? 'ph:pause' : 'ph:play'" size="16" :class="{ 'ml-0.5': !elah.isPlaying.value }" />
      </button>
      <n-tooltip trigger="hover">
        <template #trigger>
          <button
            type="button"
            class="w-8 h-8 flex items-center justify-center rounded-md text-white/70 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            title="Stop"
            @click="onStop"
          >
            <Icon name="ph:circle-stop" size="16" />
          </button>
        </template>
        Stop
      </n-tooltip>
    </div>

    <!-- Right: reserved -->
    <span />
  </div>
</template>
