<script lang="ts" setup>
/**
 * ViralityScore — inspector visualisation: overall score + metric bars.
 * Uses only Ink + Nuxt Green (no colored traffic lights).
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
interface ScoreShape {
  hook_score: number
  engagement_score: number
  value_score: number
  shareability_score: number
  overall_score: number
  pause_count?: number
  excitement_markers?: number
  question_marks?: number
  has_cta?: boolean
}

const props = withDefaults(defineProps<{
  scores: ScoreShape
  compact?: boolean
}>(), {
  scores: () => ({
    hook_score: 0,
    engagement_score: 0,
    value_score: 0,
    shareability_score: 0,
    overall_score: 0,
    pause_count: 0,
    excitement_markers: 0,
    question_marks: 0,
    has_cta: false,
  }),
  compact: false,
})

const overall = computed(() => Math.round(props.scores.overall_score))

const label = computed(() => {
  const s = props.scores.overall_score
  if (s >= 80) return "Exceptional"
  if (s >= 60) return "Strong"
  if (s >= 40) return "Promising"
  return "Developing"
})

const metrics = computed(() => [
  { label: "Hook Strength", value: props.scores.hook_score },
  { label: "Engagement", value: props.scores.engagement_score },
  { label: "Value", value: props.scores.value_score },
  { label: "Shareability", value: props.scores.shareability_score },
])

const activeMetric = computed(() => {
  const items = metrics.value
  const max = Math.max(...items.map(m => m.value))
  const top = items.find(m => m.value === max) || items[0]
  const reasons: Record<string, string> = {
    "Hook Strength": "opens with a curiosity or contrast hook.",
    "Engagement": "high pause density and emotional markers.",
    "Value": "dense with keyword-relevant insight.",
    "Shareability": "universal appeal with a clear takeaway.",
  }
  return {
    label: top.label,
    suggestion: `${top.label}: ${reasons[top.label]}`,
  }
})
</script>

<template>
  <div class="space-y-4" :class="{ 'p-5 bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl': !props.compact }">
    <div class="flex items-start justify-between">
      <div>
        <p v-if="!props.compact" class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60">
          Clip Score
        </p>
        <p v-if="!props.compact" class="mt-1 inline-flex px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-neutral-100 dark:bg-neutral-700 border border-clipper-ink/08 dark:border-white/10 text-clipper-ink dark:text-white/80">
          {{ label }}
        </p>
        <span v-else class="text-[11px] font-medium uppercase text-clipper-ink/60 dark:text-white/60">Score</span>
      </div>
      <span class="text-[32px] font-bold text-clipper-ink dark:text-white leading-none tabular-nums">{{ overall }}</span>
    </div>

    <div v-if="!props.compact" class="pt-2 space-y-3">
      <ClipperScoreMetric
        v-for="m in metrics"
        :key="m.label"
        :label="m.label"
        :value="m.value"
      />

      <p class="pt-2 text-xs leading-5 text-clipper-ink/60 dark:text-white/60 border-t border-clipper-ink/08 dark:border-white/08">
        {{ activeMetric.suggestion }}
      </p>
    </div>
  </div>
</template>
