<script lang="ts" setup>
/**
 * SourceList — displays source videos for a project with status indicators.
 * Per styleguide §36-37.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const props = withDefaults(defineProps<{
  sources: any[]
  projectId: string
}>(), {
  sources: () => [],
})

const emit = defineEmits<{
  (e: 'add'): void
  (e: 'remove', sourceId: string): void
  (e: 'process', projectId: string): void
}>()

const getApiBase = (): string => {
  try {
    return useApiSettings().API_SETTINGS.value.URL || 'http://localhost:8080'
  } catch {
    return 'http://localhost:8080'
  }
}

const thumbnail = (s: any) => {
  const raw = s.thumbnail_url || ''
  return raw ? (raw.startsWith('http') ? raw : `${getApiBase()}${raw}`) : ''
}

const fmtDuration = (d: number) => {
  if (!d) return '—'
  const m = Math.floor(d / 60)
  const s = Math.floor(d % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-bold text-clipper-ink dark:text-white">Sources</h2>
      <button class="h-10 px-4 rounded-lg bg-clipper-green text-ink font-semibold text-sm hover:opacity-90" @click="emit('add')">
        + Add Source
      </button>
    </div>
    <p class="text-sm text-clipper-ink/60 dark:text-white/60">Paste YouTube or direct video URLs to begin.</p>

    <div v-if="!props.sources.length" class="border border-clipper-ink/08 dark:border-white/08 rounded-lg py-16 text-center">
      <Icon name="ph:link" size="44" class="mx-auto text-clipper-ink dark:text-white/30 mb-4" />
      <h3 class="text-lg font-semibold text-clipper-ink dark:text-white">Add a source video</h3>
      <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-2">Paste a YouTube or direct video URL to begin.</p>
      <button class="mt-5 h-10 px-4 rounded-lg bg-clipper-green text-ink font-semibold text-sm" @click="emit('add')">+ Add Source</button>
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="s in props.sources"
        :key="s.id"
        class="border border-clipper-ink/08 dark:border-white/08 rounded-lg p-4 flex items-center gap-4 hover:border-clipper-ink/16 dark:hover:border-white/15 transition-colors"
      >
        <div class="w-20 h-14 shrink-0 rounded-md bg-clipper-ink/06 overflow-hidden flex items-center justify-center">
          <img v-if="thumbnail(s)" :src="thumbnail(s)" class="w-full h-full object-cover" />
          <Icon v-else name="ph:film-strip" size="20" class="text-clipper-ink/35 dark:text-white/40" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-medium text-sm text-clipper-ink dark:text-white truncate">{{ s.url }}</p>
          <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-0.5">
            {{ s.platform || 'YouTube' }} · {{ fmtDuration(s.duration) }}
            <span v-if="s.transcribed" class="ml-2 text-clipper-green">✓ Transcribed</span>
          </p>
        </div>
        <button
          class="h-9 px-3 rounded-lg text-sm font-medium text-clipper-ink/60 dark:text-white/60 hover:text-clipper-ink hover:bg-clipper-ink/04 dark:hover:bg-white/5"
          @click="emit('remove', s.id)"
          aria-label="Remove source"
        >
          <Icon name="ph:trash" size="16" />
        </button>
      </div>
    </div>
  </div>
</template>
