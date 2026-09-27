<script lang="ts" setup>
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const ASPECTS = [
  { label: "16:9", w: 1920, h: 1080, gw: 14, gh: 8 },
  { label: "9:16", w: 1080, h: 1920, gw: 8, gh: 14 },
  { label: "1:1", w: 1080, h: 1080, gw: 11, gh: 11 },
] as const

const isActive = (w: number, h: number) => {
  const stage = props.elah.project.value.stage
  return Math.abs(stage.width / stage.height - w / h) < 0.001
}
</script>

<template>
  <div class="shrink-0 flex items-center justify-center py-2">
    <div class="flex items-center gap-1">
      <button
        v-for="a in ASPECTS"
        :key="a.label"
        type="button"
        class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs cursor-pointer transition-colors"
        :class="isActive(a.w, a.h)
          ? 'ring-1 ring-clipper-green text-clipper-ink dark:text-white bg-white dark:bg-neutral-800'
          : 'text-clipper-ink/50 dark:text-white/50 hover:text-clipper-ink dark:hover:text-white'"
        @click="elah.setStage(a.w, a.h)"
      >
        <span class="rounded-sm bg-current shrink-0" :style="{ width: `${a.gw}px`, height: `${a.gh}px` }" />
        {{ a.label }}
      </button>
    </div>
  </div>
</template>
