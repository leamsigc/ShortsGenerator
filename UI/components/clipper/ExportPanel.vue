<script lang="ts" setup>
/**
 * ExportPanel — export controls for clips (single + batch).
 * Per styleguide §47-48.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const props = withDefaults(defineProps<{
  clipCount?: number
  selectedCount?: number
  disabled?: boolean
}>(), {
  clipCount: 0,
  selectedCount: 0,
  disabled: false,
})

interface ExportOptions {
  format: string
  quality: string
  burnSubtitles: boolean
}

const emit = defineEmits<{
  (e: 'export', opts: ExportOptions): void
  (e: 'export-selected', opts: ExportOptions): void
}>()

const formats = [
  { label: 'TikTok', value: 'tiktok' },
  { label: 'Reels', value: 'reels' },
  { label: 'Shorts', value: 'shorts' },
  { label: 'Douyin', value: 'douyin' },
  { label: 'Xiaohongshu', value: 'xiaohongshu' },
  { label: 'Bilibili', value: 'bilibili' },
  { label: 'YouTube', value: 'youtube' },
]

const qualities = ['high', 'medium', 'low']

const showOptions = ref(false)
const selectedFormat = ref('tiktok')
const selectedQuality = ref('high')
const burnSubtitles = ref(false)

const currentOptions = (): ExportOptions => ({
  format: selectedFormat.value,
  quality: selectedQuality.value,
  burnSubtitles: burnSubtitles.value,
})
</script>

<template>
  <div class="space-y-3">
    <p class="text-[11px] font-medium uppercase tracking-wide text-clipper-ink/60 dark:text-white/60">Export</p>
    <div class="flex gap-2 relative">
      <button class="h-10 px-4 rounded-lg text-ink font-semibold text-sm bg-clipper-green hover:opacity-90 flex-1 disabled:opacity-50" :disabled="props.disabled" @click="emit('export', currentOptions())">
        Export Clip
      </button>
      <button class="h-10 w-10 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-clipper-ink dark:text-white disabled:opacity-50" :disabled="props.disabled" title="More options" aria-label="More export options" @click="showOptions = !showOptions">
        <Icon name="ph:caret-down" size="16" />
      </button>
      <div v-if="showOptions" class="absolute right-0 top-12 z-30 w-48 bg-white dark:bg-neutral-800 border border-clipper-ink/12 dark:border-white/10 rounded-lg p-3 space-y-2 shadow-lg">
        <div>
          <label class="block text-[11px] font-medium text-clipper-ink/50 dark:text-white/50 mb-1">Format</label>
          <select v-model="selectedFormat" class="w-full h-9 px-2 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm">
            <option v-for="f in formats" :key="f.value" :value="f.value">{{ f.label }}</option>
          </select>
        </div>
        <div>
          <label class="block text-[11px] font-medium text-clipper-ink/50 dark:text-white/50 mb-1">Quality</label>
          <select v-model="selectedQuality" class="w-full h-9 px-2 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm">
            <option v-for="q in qualities" :key="q" :value="q">{{ q }}</option>
          </select>
        </div>
        <label class="flex items-center gap-2 text-sm cursor-pointer">
          <input v-model="burnSubtitles" type="checkbox" class="rounded" />
          <span class="text-clipper-ink dark:text-white">Burn subtitles</span>
        </label>
      </div>
    </div>
    <div v-if="props.selectedCount > 1" class="pt-2 border-t border-clipper-ink/10 dark:border-white/10">
      <button class="h-9 px-3 rounded-lg text-sm font-medium text-clipper-ink dark:text-white bg-white dark:bg-neutral-800 border border-clipper-ink/12 dark:border-white/10 hover:border-clipper-ink/20 dark:hover:border-white/20 w-full" @click="emit('export-selected', currentOptions())">
        Export Selected ({{ props.selectedCount }})
      </button>
    </div>
  </div>
</template>
