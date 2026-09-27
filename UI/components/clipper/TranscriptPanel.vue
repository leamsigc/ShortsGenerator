<script lang="ts" setup>
/**
 * TranscriptPanel — clickable word/sentence transcript synced to playhead.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const props = withDefaults(defineProps<{
  sentences?: { text: string; start: number; end: number }[]
  currentTime?: number
}>(), {
  sentences: () => [],
  currentTime: 0,
})

const emit = defineEmits<{ (e: "seek", time: number): void }>()

const activeIdx = computed(() =>
  props.sentences.findIndex(s => props.currentTime >= s.start && props.currentTime < s.end)
)

const fmt = (t: number) => {
  const m = Math.floor(t / 60)
  const s = Math.floor(t % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}
</script>

<template>
  <div class="space-y-1 max-h-[320px] overflow-y-auto">
    <button
      v-for="(s, idx) in props.sentences"
      :key="idx"
      class="w-full text-left px-2.5 py-1.5 rounded text-sm leading-6 transition-colors hover:bg-neutral-100 dark:hover:bg-white/5"
      :class="idx === activeIdx ? 'bg-clipper-green/16 dark:bg-clipper-green/20' : 'bg-transparent'"
      @click="emit('seek', s.start)"
    >
      <span class="inline-flex w-9 text-[10px] font-medium text-clipper-ink/50 dark:text-white/50 dark:text-white/40 tabular-nums">{{ fmt(s.start) }}</span>
      <span :class="idx === activeIdx ? 'text-clipper-ink dark:text-white font-medium' : 'text-clipper-ink/70 dark:text-white/70'">{{ s.text }}</span>
    </button>
    <p v-if="!props.sentences.length" class="text-sm text-clipper-ink/35 dark:text-white/40 py-6 text-center">
      No transcript yet — process sources to transcribe them.
    </p>
  </div>
</template>
