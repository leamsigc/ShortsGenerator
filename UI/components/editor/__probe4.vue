<script lang="ts" setup>
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const totalTimecode = "00:00:00:00"

const onStop = () => {
  props.elah.pause()
  props.elah.seek(0)
}
</script>

<template>
  <div class="shrink-0 h-11 px-4 grid grid-cols-[1fr_auto_1fr] items-center border-t border-white/10">
    <span class="font-mono text-xs tabular-nums whitespace-nowrap">
      <span class="text-clipper-green">{{ elah.timecode.value }}</span>
      <span class="text-white/40 mx-1.5">|</span>
      <span class="text-white/60">{{ totalTimecode }}</span>
    </span>
    <div class="flex items-center gap-3">
      <button type="button" class="playbtn" @click="elah.togglePlay()">
        Play
      </button>
      <button type="button" class="stopbtn" @click="onStop">
        Stop
      </button>
    </div>
    <span />
  </div>
</template>
