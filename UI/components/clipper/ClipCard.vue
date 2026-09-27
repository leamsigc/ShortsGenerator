<script lang="ts" setup>
/**
 * ClipCard — compact clip list item: thumbnail, hook title, time range,
 * tags and score. Selected state = Nuxt Green border.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
import type { ClipSegment } from "~/stores/ClipperStore"

const props = withDefaults(defineProps<{
  clip: ClipSegment
  selected?: boolean
}>(), {
  selected: false,
})

const emit = defineEmits<{
  (e: "select", clipId: string): void
  (e: "edit", clipId: string): void
  (e: "render", clipId: string): void
  (e: "export", clipId: string): void
}>()

const getApiBase = (): string => {
  try {
    return useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080"
  } catch {
    return "http://localhost:8080"
  }
}

const thumbnail = computed(() => {
  const raw = props.clip.thumbnail_url
  return raw ? (raw.startsWith("http") ? raw : `${getApiBase()}${raw}`) : ""
})

const score = computed(() => Math.round(props.clip.scores.overall_score))

const tags = computed(() => {
  const t: string[] = []
  if (props.clip.scores.hook_score >= 70) t.push("Hook")
  if (props.clip.scores.engagement_score >= 70) t.push("Emotional")
  if (props.clip.scores.value_score >= 70) t.push("Value")
  if (props.clip.scores.shareability_score >= 70) t.push("Relatable")
  return t.slice(0, 3)
})

const fmt = (t: number, base = t) => {
  const m = Math.floor(base / 60)
  const s = Math.floor(base % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}
</script>

<template>
  <button
    class="w-full text-left border rounded-lg transition-colors"
    :class="props.selected ? 'bg-clipper-green/[0.04] dark:bg-clipper-green/10 border-clipper-green' : 'bg-white dark:bg-neutral-800 border-clipper-ink/08 dark:border-white/08 hover:border-clipper-ink/16 dark:hover:border-white/15'"
    @click="emit('select', clip.id)"
    :aria-pressed="props.selected"
  >
    <div class="p-3 flex items-center gap-3 min-h-[96px]">
      <div class="w-[72px] h-[72px] shrink-0 rounded-[6px] bg-neutral-100 dark:bg-neutral-800 overflow-hidden flex items-center justify-center border border-clipper-ink/08 dark:border-white/10">
        <img v-if="thumbnail" :src="thumbnail" class="w-full h-full object-cover" alt="" />
        <Icon v-else name="ph:film-strip" size="22" class="text-clipper-ink/35 dark:text-white/40" />
      </div>
      <div class="flex-1 min-w-0">
        <p class="font-medium text-[13px] leading-tight line-clamp-2 text-clipper-ink dark:text-white">
          {{ clip.hook_title || `Clip ${clip.index + 1}` }}
        </p>
        <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-0.5 tabular-nums">
          {{ fmt(clip.start_time) }} — {{ fmt(clip.end_time) }} · {{ clip.duration.toFixed(0) }}s
        </p>
        <div class="mt-1.5 flex flex-wrap gap-1">
          <span v-for="tag in tags" :key="tag"
            class="px-[9px] py-1 rounded-full text-[11px] font-medium bg-neutral-100 dark:bg-neutral-700 text-clipper-ink dark:text-white/80">
            {{ tag }}
          </span>
        </div>
      </div>
      <span class="shrink-0 text-xl font-bold text-clipper-ink dark:text-white tabular-nums">{{ score }}</span>
    </div>
  </button>
</template>
