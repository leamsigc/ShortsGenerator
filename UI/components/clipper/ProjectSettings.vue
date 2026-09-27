<script lang="ts" setup>
/**
 * ProjectSettings — project configuration panel (platform, language, training data).
 * Per styleguide §42-46.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const props = withDefaults(defineProps<{
  project: any
}>(), {
  project: () => ({}),
})

const emit = defineEmits<{
  (e: 'update', data: any): void
  (e: 'delete', id: string): void
}>()

const platformOptions = [
  { label: 'TikTok', value: 'tiktok' },
  { label: 'Reels', value: 'reels' },
  { label: 'Shorts', value: 'shorts' },
]

const langOptions = [
  { label: 'English', value: 'en' },
  { label: 'Spanish', value: 'es' },
  { label: 'German', value: 'de' },
  { label: 'French', value: 'fr' },
  { label: 'Portuguese', value: 'pt' },
  { label: 'Italian', value: 'it' },
  { label: 'Dutch', value: 'nl' },
  { label: 'Japanese', value: 'ja' },
  { label: 'Korean', value: 'ko' },
  { label: 'Chinese', value: 'zh' },
  { label: 'Hindi', value: 'hi' },
  { label: 'Arabic', value: 'ar' },
]

// — System subtitle templates (same source as Generate view: GET /api/settings) —
const subtitleTemplateOptions = ref<{ label: string; value: string }[]>([
  { label: 'Classic Yellow', value: 'classic' },
  { label: 'Modern Glow', value: 'modern_glow' },
  { label: 'Bold Outline', value: 'bold_outline' },
  { label: 'Minimal', value: 'minimal' },
  { label: 'Cinematic', value: 'cinematic' },
])

const getApiBase = (): string => {
  try {
    return useApiSettings().API_SETTINGS.value.URL || 'http://localhost:8080'
  } catch {
    return 'http://localhost:8080'
  }
}

onMounted(async () => {
  try {
    const res = await $fetch<{ data: { subtitleTemplates?: { options?: { label: string; value: string }[] } } }>(`${getApiBase()}/api/settings`)
    if (res?.data?.subtitleTemplates?.options?.length) {
      subtitleTemplateOptions.value = res.data.subtitleTemplates.options.map((t: { label: string; value: string }) => ({
        label: t.label,
        value: t.value,
      }))
    }
  } catch (e) {
    console.error('Failed to load subtitle templates', e)
  }
})

const subtitleTemplate = computed(() => props.project?.template?.subtitle_template || 'classic')

const updateSubtitleTemplate = (value: string) => {
  emit('update', { template: { ...(props.project?.template || {}), subtitle_template: value } })
}

const addGoldenFromButton = (e: MouseEvent) => {
  const input = (e.currentTarget as HTMLElement).previousElementSibling as HTMLInputElement
  const v = input.value.trim()
  if (v) {
    emit('update', { golden_urls: [...(props.project?.golden_urls || []), v] })
    input.value = ''
  }
}

const addExtraFromButton = (e: MouseEvent) => {
  const input = (e.currentTarget as HTMLElement).previousElementSibling as HTMLInputElement
  const v = input.value.trim()
  if (v) {
    emit('update', { extra_resources: [...(props.project?.extra_resources || []), v] })
    input.value = ''
  }
}
</script>

<template>
  <div class="space-y-6">
    <h2 class="text-xl font-bold text-clipper-ink dark:text-white">Settings</h2>
    <p class="text-sm text-clipper-ink/60 dark:text-white/60">Configure your project output and transcription language.</p>

    <div class="border border-clipper-ink/08 dark:border-white/08 rounded-lg p-5 space-y-5">
      <div>
        <label class="block text-sm font-medium text-clipper-ink dark:text-white">Target Platform</label>
        <div class="mt-1 flex gap-2">
          <button v-for="opt in platformOptions" :key="opt.value" class="flex-1 h-10 rounded-lg text-sm font-medium border" :class="props.project?.target_platform === opt.value ? 'border-clipper-green text-clipper-ink' : 'border-clipper-ink/12 dark:border-white/10 text-clipper-ink/60 dark:text-white/60'" @click="emit('update', { target_platform: opt.value })">{{ opt.label }}</button>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-clipper-ink dark:text-white">Transcription language</label>
        <n-select
          class="mt-1"
          :value="props.project?.language || 'en'"
          :options="langOptions"
          @update:value="(v: string) => emit('update', { language: v })"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-clipper-ink dark:text-white">Subtitle style</label>
        <p class="text-xs text-clipper-ink/50 dark:text-white/50 mt-1">System subtitle template used when rendering this project's clips.</p>
        <n-select
          class="mt-1"
          :value="subtitleTemplate"
          :options="subtitleTemplateOptions"
          @update:value="updateSubtitleTemplate"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-clipper-ink dark:text-white">Audience & Content Guidelines</label>
        <textarea :value="props.project?.training_data" class="mt-1 w-full min-h-[120px] p-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-clipper-ink dark:text-white" placeholder="Describe your audience, tone, viral patterns, topics and content style..." :rows="5" @change="emit('update', { training_data: ($event.target as HTMLTextAreaElement).value })" />
      </div>

      <div>
        <label class="block text-sm font-medium text-clipper-ink dark:text-white">Golden Standards — Example Reels</label>
        <p class="text-xs text-clipper-ink/50 dark:text-white/50 mt-1">Viral reels used as reference. Their transcripts help pick best moments.</p>
        <div v-if="props.project?.golden_urls?.length" class="mt-2 space-y-1">
          <div v-for="(u, i) in props.project.golden_urls" :key="i" class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-clipper-green/10 dark:bg-neutral-800 border border-clipper-green/20 text-xs">
            <Icon name="ph:star" size="12" class="text-clipper-green shrink-0" />
            <span class="flex-1 truncate text-clipper-ink dark:text-white/80">{{ u }}</span>
            <button class="text-clipper-ink/40 hover:text-clipper-ink text-xs" @click="emit('update', { golden_urls: props.project.golden_urls.filter((_:string, idx:number)=> idx!==i) })">✕</button>
          </div>
        </div>
        <div class="flex gap-2 mt-2">
          <input :id="`golden-input-${props.project?.id}`" placeholder="https://instagram.com/reels/..." class="flex-1 h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm" @keyup.enter="(e: any)=> { const v=e.target.value.trim(); if(v){ emit('update', { golden_urls: [...(props.project.golden_urls||[]), v]}); e.target.value=''} }" />
          <button class="h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-sm" @click="addGoldenFromButton">Add</button>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-clipper-ink dark:text-white">Extra Resources</label>
        <p class="text-xs text-clipper-ink/50 dark:text-white/50 mt-1">More URLs to enrich clipping (docs, more videos)</p>
        <div v-if="props.project?.extra_resources?.length" class="mt-2 space-y-1">
          <div v-for="(u,i) in props.project.extra_resources" :key="i" class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-neutral-100 dark:bg-neutral-800 text-xs">
            <span class="flex-1 truncate text-clipper-ink/70 dark:text-white/70">{{ u }}</span>
            <button class="text-clipper-ink/40" @click="emit('update', { extra_resources: props.project.extra_resources.filter((_:string, idx:number)=> idx!==i) })">✕</button>
          </div>
        </div>
        <div class="flex gap-2 mt-2">
          <input :id="`extra-input-${props.project?.id}`" placeholder="https://..." class="flex-1 h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm" @keyup.enter="(e:any)=>{ const v=e.target.value.trim(); if(v){ emit('update', { extra_resources: [...(props.project.extra_resources||[]), v]}); e.target.value=''} }" />
          <button class="h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-sm" @click="addExtraFromButton">Add</button>
        </div>
      </div>

      <div class="p-3 rounded-lg border border-clipper-ink/08 dark:border-white/08 bg-neutral-100 dark:bg-neutral-800">
        <label class="flex items-center gap-2 cursor-pointer">
          <n-checkbox
            :checked="props.project?.template?.broll_enabled"
            @update:checked="(v: boolean) => emit('update', { template: { ...props.project.template, broll_enabled: v } })"
          />
          <span class="text-sm font-medium text-clipper-ink dark:text-white">B-roll overlay (Pexels)</span>
        </label>
        <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-1">When enabled, fetched Pexels clip is overlaid picture-in-picture.</p>
        <div v-if="props.project?.template?.broll_enabled" class="mt-3 space-y-2">
          <input :value="props.project?.template?.broll_keyword" @change="emit('update', { template: { ...props.project.template, broll_keyword: ($event.target as HTMLInputElement).value } })" placeholder="Keyword e.g., nature, city" class="w-full h-9 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm" />
          <n-select
            :value="props.project?.template?.transition_type || 'cut'"
            :options="[
              { label: 'Cut', value: 'cut' },
              { label: 'Fade', value: 'fade' },
              { label: 'Zoom', value: 'zoom' },
            ]"
            @update:value="(v: string) => emit('update', { template: { ...props.project.template, transition_type: v } })"
          />
        </div>
      </div>
    </div>

    <div class="pt-4 border-t border-clipper-ink/10 dark:border-white/10">
      <button class="h-10 px-4 rounded-lg text-sm font-medium text-clipper-ink/60 dark:text-white/60 border border-clipper-ink/12 dark:border-white/10 hover:border-clipper-ink/20 dark:hover:border-white/20" @click="emit('delete', props.project?.id)">Delete project</button>
    </div>
  </div>
</template>
