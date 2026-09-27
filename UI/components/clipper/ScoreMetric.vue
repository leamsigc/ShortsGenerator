<script lang="ts" setup>
/**
 * ScoreMetric — single horizontal score bar.
 * Per styleguide §21.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const props = withDefaults(defineProps<{
  label: string
  value: number
  max?: number
}>(), {
  value: 0,
  max: 100,
})

const pct = computed(() => Math.min(100, Math.round((props.value / props.max) * 100)))
</script>

<template>
  <div class="space-y-1">
    <div class="flex items-center justify-between">
      <span class="text-xs font-medium text-clipper-ink/60 dark:text-white/60">{{ props.label }}</span>
      <span class="text-xs font-semibold text-clipper-ink dark:text-white tabular-nums">{{ Math.round(props.value) }}</span>
    </div>
    <div class="h-1.5 bg-clipper-ink/08 dark:bg-neutral-700 rounded-full overflow-hidden">
      <div class="h-full bg-clipper-green rounded-full transition-all duration-300" :style="{ width: `${pct}%` }" />
    </div>
  </div>
</template>
