<script lang="ts" setup>
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()

const ASPECTS = [
  { label: "16:9", w: 1920, h: 1080, gw: 14, gh: 8 },
] as const

const isActive = (w: number, h: number) => {
  const stage = props.elah.project.value.stage
  return Math.abs(stage.width / stage.height - w / h) < 0.001
}
</script>

<template>
  <div>
    <button v-for="a in ASPECTS" :key="a.label" type="button" @click="elah.setStage(a.w, a.h)">
      <span :style="{ width: `${a.gw}px`, height: `${a.gh}px` }" />
      {{ a.label }}
    </button>
  </div>
</template>
