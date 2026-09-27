<script lang="ts" setup>
/**
 * ProcessingProgress — stage indicator for the CLIPPER pipeline.
 * Shows Downloading → Transcribing → Scoring → Rendering → Done.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const props = withDefaults(defineProps<{
  stage?: string
  progress?: number
  message?: string
  currentClip?: number
  totalClips?: number
}>(), {
  stage: "idle",
  progress: 0,
  message: "",
  currentClip: 0,
  totalClips: 0,
})

const STAGES = ["downloading", "transcribing", "scoring", "rendering", "done"]

const stageIndex = computed(() => {
  const idx = STAGES.indexOf(props.stage)
  return idx === -1 ? 0 : idx
})

const activeIdx = ref(stageIndex.value)
watch(stageIndex, (v) => {
  activeIdx.value = v
})

const stageLabel = computed(() => {
  const labels: Record<string, string> = {
    downloading: "Downloading",
    transcribing: "Transcribing",
    scoring: "Scoring",
    rendering: "Rendering",
    done: "Done",
    ready: "Ready",
    idle: "Idle",
  }
  return labels[props.stage] || props.stage
})

const percent = computed(() => Math.round((props.progress || 0) * 100))
</script>

<template>
  <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-lg p-5" role="status" aria-live="polite">
    <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60 mb-4">
      {{ props.stage === 'idle' || props.stage === 'ready' || props.stage === '' ? 'Pipeline' : 'Processing' }}
    </p>

    <ol class="flex flex-wrap gap-3">
      <li
        v-for="(name, idx) in STAGES"
        :key="name"
        class="flex items-center gap-1.5 text-sm"
      >
        <!-- Completed: Ink + check -->
        <span
          v-if="idx < activeIdx" class="w-5 h-5 rounded-full bg-clipper-ink flex items-center justify-center text-white text-[11px]"
        >✓</span>
        <!-- Active: Green border with pulse -->
        <span
          v-else-if="idx === activeIdx" class="w-5 h-5 rounded-full border-2 border-clipper-green bg-white dark:bg-neutral-800"
          :style="{ animation: 'pulse 1.2s infinite' }"
        ></span>
        <!-- Pending: Ink opacity -->
        <span v-else class="w-5 h-5 rounded-full border border-clipper-ink/16 dark:border-white/15 bg-white dark:bg-neutral-800 opacity-60" />
        <span :class="idx < activeIdx ? 'text-clipper-ink' : idx === activeIdx ? 'text-clipper-ink font-medium' : 'text-clipper-ink/35 dark:text-white/40'" class="capitalize text-sm">
          {{ name }}
        </span>
      </li>
    </ol>

    <div class="mt-4 flex items-center justify-between">
      <span class="text-sm text-clipper-ink/60 dark:text-white/60">{{ props.message || stageLabel }}</span>
      <span class="text-sm font-semibold text-clipper-ink dark:text-white">{{ percent }}%</span>
    </div>

    <div class="mt-2 h-1.5 bg-clipper-ink/08 rounded-full overflow-hidden">
      <div class="h-full bg-clipper-green transition-all duration-200" :style="{ width: `${percent}%` }" />
    </div>
  </div>
</template>

<style scoped>
@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(0, 220, 130, 0.35);
  }
  50% {
    box-shadow: 0 0 0 5px rgba(0, 220, 130, 0);
  }
}
</style>