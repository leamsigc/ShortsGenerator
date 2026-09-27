<script lang="ts" setup>
/**
 * ProjectManager — project dashboard (compact rows) + staged creation modal.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const props = withDefaults(defineProps<{
  projects: any[]
  currentProjectId?: string | null
}>(), {
  projects: () => [],
  currentProjectId: null,
})

const emit = defineEmits<{
  (e: "select", id: string): void
  (e: "delete", id: string): void
  (e: "create", data: any): void
}>()

const showModal = ref(false)
const step = ref(1)
const creating = ref(false)

const form = ref({
  name: "",
  description: "",
  target_platform: "tiktok" as "tiktok" | "reels" | "shorts",
  language: "en",
  source_urls: [] as string[],
  training_data: "",
  golden_urls: [] as string[],
  extra_resources: [] as string[],
  broll_enabled: false,
  broll_keyword: "",
  transition_type: "cut" as "cut" | "fade" | "zoom",
  subtitle_template: "classic",
})
const nextUrl = ref("")
const nextGoldenUrl = ref("")
const nextExtraUrl = ref("")

const platformOptions: { label: string; value: "tiktok" | "reels" | "shorts" }[] = [
  { label: "TikTok", value: "tiktok" },
  { label: "Reels", value: "reels" },
  { label: "Shorts", value: "shorts" },
]

const langOptions = [
  { label: "English", value: "en" },
  { label: "Spanish", value: "es" },
  { label: "German", value: "de" },
  { label: "French", value: "fr" },
  { label: "Portuguese", value: "pt" },
  { label: "Italian", value: "it" },
  { label: "Dutch", value: "nl" },
  { label: "Japanese", value: "ja" },
  { label: "Korean", value: "ko" },
  { label: "Chinese", value: "zh" },
  { label: "Hindi", value: "hi" },
  { label: "Arabic", value: "ar" },
]

// — System subtitle templates (same source as Generate view: GET /api/settings) —
const subtitleTemplateOptions = ref<{ label: string; value: string }[]>([
  { label: "Classic Yellow", value: "classic" },
  { label: "Modern Glow", value: "modern_glow" },
  { label: "Bold Outline", value: "bold_outline" },
  { label: "Minimal", value: "minimal" },
  { label: "Cinematic", value: "cinematic" },
])

const getApiBase = (): string => {
  try {
    return useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080"
  } catch {
    return "http://localhost:8080"
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
    console.error("Failed to load subtitle templates", e)
  }
})

const addUrl = () => {
  const u = nextUrl.value.trim()
  if (u) { form.value.source_urls.push(u); nextUrl.value = "" }
}
const addGoldenUrl = () => {
  const u = nextGoldenUrl.value.trim()
  if (u) { form.value.golden_urls.push(u); nextGoldenUrl.value = "" }
}
const addExtraUrl = () => {
  const u = nextExtraUrl.value.trim()
  if (u) { form.value.extra_resources.push(u); nextExtraUrl.value = "" }
}
const canNext = computed(() => {
  if (step.value === 1) return !!form.value.name
  if (step.value === 2) return form.value.source_urls.length > 0
  return true
})
const next = () => { if (canNext.value) step.value++ }
const prev = () => { if (step.value > 1) step.value-- }

const reset = () => {
  step.value = 1
  form.value = { name: "", description: "", target_platform: "tiktok", language: "en", source_urls: [], training_data: "", golden_urls: [], extra_resources: [], broll_enabled: false, broll_keyword: "", transition_type: "cut", subtitle_template: "classic" }
}

const submit = async () => {
  creating.value = true
  try {
    const { broll_enabled, broll_keyword, transition_type, subtitle_template, language: _lang, ...rest } = form.value as any
    emit("create", {
      ...rest,
      language: undefined,
      template: {
        broll_enabled,
        broll_keyword,
        transition_type,
        subtitle_template,
      }
    })
    showModal.value = false
    reset()
    emit("select", undefined as never)
  } finally { creating.value = false }
}

const openModal = () => { reset(); showModal.value = true }

defineExpose({ openModal })
</script>

<template>
  <div class="space-y-6">
    <!-- Dashboard -->
    <div class="flex items-center justify-between mb-2">
      <h1 class="text-2xl font-bold text-clipper-ink dark:text-white">Projects</h1>
      <button class="h-10 px-4 rounded-lg bg-clipper-green text-ink font-semibold text-sm hover:opacity-90" @click="openModal">+ New Project</button>
    </div>
    <p class="text-sm text-clipper-ink/60 dark:text-white/60">Turn long-form videos into short clips automatically.</p>

    <div v-if="!props.projects.length" class="border border-clipper-ink/08 dark:border-white/08 rounded-lg py-16 text-center">
      <Icon name="ph:play-circle" size="44" class="mx-auto text-clipper-ink dark:text-white/30 mb-4" />
      <h3 class="text-lg font-semibold text-clipper-ink dark:text-white">Create your first project</h3>
      <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-2">Paste a YouTube or direct video URL to begin.</p>
      <button class="mt-5 h-10 px-4 rounded-lg bg-clipper-green text-ink font-semibold text-sm" @click="openModal">+ New Project</button>
    </div>

    <div v-else class="space-y-3">
      <button
        v-for="p in props.projects"
        :key="p.id"
        class="w-full text-left p-4 rounded-lg border transition-colors"
        :class="p.id === props.currentProjectId ? 'border-clipper-green bg-clipper-green/5 dark:bg-clipper-green/10' : 'border-clipper-ink/10 dark:border-white/10 bg-white dark:bg-neutral-800 hover:border-clipper-ink/16 dark:hover:border-white/15'"
        @click="emit('select', p.id)"
      >
        <div class="flex items-center justify-between">
          <div class="min-w-0">
            <p class="font-semibold text-clipper-ink dark:text-white truncate">{{ p.name }}</p>
            <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-0.5">
              {{ p.source_urls.length }} videos · {{ p.target_platform }} · {{ p.status }}
            </p>
          </div>
          <Icon name="ph:caret-right" size="16" class="text-clipper-ink/40 dark:text-white/40" />
        </div>
      </button>
    </div>

    <!-- Creation modal (staged) -->
    <div v-if="showModal" class="fixed inset-0 z-50 bg-clipper-ink/35 flex items-center justify-center p-6" @click.self="showModal = false">
      <div class="w-full max-w-[600px] bg-white dark:bg-neutral-800 rounded-2xl p-6 max-h-[90vh] overflow-y-auto">
        <h2 class="text-xl font-bold text-clipper-ink dark:text-white">Create Project</h2>
        <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">Step {{ step }} of 5</p>
        <div class="mt-2 h-1 bg-clipper-ink/08 rounded-full"><div class="h-full bg-clipper-green" :style="{ width: `${step * 20}%` }" /></div>

        <!-- Step 1 -->
        <template v-if="step === 1">
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mt-6">Project name</label>
          <input v-model="form.name" class="mt-1 w-full h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 focus:outline-clipper-green" placeholder="e.g. Jürgen Klopp Analysis" />
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mt-4">Description</label>
          <textarea v-model="form.description" class="mt-1 w-full min-h-[120px] p-3 rounded-lg border border-clipper-ink/12 dark:border-white/10" placeholder="Content theme and target audience..." :rows="3" />
        </template>

        <!-- Step 2 -->
        <template v-else-if="step === 2">
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mt-6">Add Sources</label>
          <div class="flex gap-2 mt-1">
            <input v-model="nextUrl" class="flex-1 h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10" placeholder="Paste video URL... (YouTube / MP4)" @keyup.enter="addUrl" />
            <button class="h-10 px-4 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-clipper-ink dark:text-white" @click="addUrl">Add</button>
          </div>
          <div v-if="form.source_urls.length" class="mt-3 space-y-2">
            <div v-for="(u, i) in form.source_urls" :key="i" class="flex items-center gap-2 px-3 py-2 rounded-md bg-neutral-100 dark:bg-neutral-800 text-sm">
              <span class="flex-1 truncate text-clipper-ink dark:text-white/80">{{ u }}</span>
              <button class="text-clipper-ink/40 dark:text-white/40" @click="form.source_urls.splice(i, 1)" aria-label="Remove source">✕</button>
            </div>
          </div>
        </template>

        <!-- Step 3 -->
        <template v-else-if="step === 3">
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mt-6">Audience & Content Guidelines</label>
          <textarea v-model="form.training_data" class="mt-1 w-full min-h-[120px] p-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-clipper-ink dark:text-white placeholder:text-clipper-ink/35" placeholder="Describe your audience, tone, viral patterns, topics and content style..." :rows="5" />
          <p class="text-xs text-clipper-ink/50 dark:text-white/50 mt-1">Used to score clips for value & shareability. Example: "motivational, teamwork, hook with question, fast cuts"</p>
        </template>

        <!-- Step 4 — Golden standards (reels as examples) -->
        <template v-else-if="step === 4">
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mt-6">Golden Standards — Example Reels</label>
          <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-1">Paste URLs of viral reels/shorts you like. We’ll transcribe them and use their patterns as reference for scoring. Leave empty to use heuristics only.</p>
          <div class="flex gap-2 mt-3">
            <input v-model="nextGoldenUrl" class="flex-1 h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm" placeholder="https://instagram.com/reels/... or https://tiktok.com/..." @keyup.enter="addGoldenUrl" />
            <button class="h-10 px-4 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-clipper-ink dark:text-white text-sm" @click="addGoldenUrl">Add</button>
          </div>
          <div v-if="form.golden_urls.length" class="mt-3 space-y-2">
            <div v-for="(u, i) in form.golden_urls" :key="i" class="flex items-center gap-2 px-3 py-2 rounded-lg bg-clipper-green/10 dark:bg-neutral-800 border border-clipper-green/20 text-sm">
              <Icon name="ph:star" size="14" class="text-clipper-green shrink-0" />
              <span class="flex-1 truncate text-clipper-ink dark:text-white/80">{{ u }}</span>
              <button class="text-clipper-ink/40 dark:text-white/40 hover:text-clipper-ink" @click="form.golden_urls.splice(i, 1)" aria-label="Remove golden reel">✕</button>
            </div>
          </div>
          <div class="mt-6">
            <label class="block text-sm font-medium text-clipper-ink dark:text-white">Extra Resources (optional)</label>
            <p class="text-xs text-clipper-ink/50 dark:text-white/50 mt-1">Additional source URLs to enrich this project (docs, more videos, etc.)</p>
            <div class="flex gap-2 mt-2">
              <input v-model="nextExtraUrl" class="flex-1 h-10 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm" placeholder="https://..." @keyup.enter="addExtraUrl" />
              <button class="h-10 px-4 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-clipper-ink dark:text-white text-sm" @click="addExtraUrl">Add</button>
            </div>
            <div v-if="form.extra_resources.length" class="mt-2 space-y-1">
              <div v-for="(u, i) in form.extra_resources" :key="i" class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-neutral-100 dark:bg-neutral-800 text-xs">
                <span class="flex-1 truncate text-clipper-ink/70 dark:text-white/70">{{ u }}</span>
                <button class="text-clipper-ink/40" @click="form.extra_resources.splice(i,1)">✕</button>
              </div>
            </div>
          </div>
        </template>

        <!-- Step 5 -->
        <template v-else>
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mt-6">Target Platform</label>
          <div class="mt-1 flex gap-2">
            <button v-for="opt in platformOptions" :key="opt.value" class="flex-1 h-10 rounded-lg text-sm font-medium border" :class="form.target_platform === opt.value ? 'border-clipper-green text-clipper-ink bg-clipper-green/10' : 'border-clipper-ink/12 dark:border-white/10 text-clipper-ink/60 dark:text-white/60'" @click="form.target_platform = opt.value">{{ opt.label }}</button>
          </div>
          <label class="block text-sm font-medium text-clipper-ink dark:text-white mt-4">Transcription language</label>
          <n-select v-model:value="form.language" :options="langOptions" class="mt-1" />

          <label class="block text-sm font-medium text-clipper-ink dark:text-white mt-4">Subtitle style</label>
          <p class="text-xs text-clipper-ink/50 dark:text-white/50 mt-1">System subtitle template used when rendering this project's clips.</p>
          <n-select v-model:value="form.subtitle_template" :options="subtitleTemplateOptions" class="mt-1" />

          <div class="mt-6 p-3 rounded-lg border border-clipper-ink/08 dark:border-white/08 bg-neutral-100 dark:bg-neutral-800">
            <label class="flex items-center gap-2 cursor-pointer">
              <n-checkbox v-model:checked="form.broll_enabled" />
              <span class="text-sm font-medium text-clipper-ink dark:text-white">Enable B-roll overlay (Pexels)</span>
              <span class="text-xs text-clipper-ink/50 dark:text-white/50 ml-auto">Optional</span>
            </label>
            <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-1">Overlays a short stock clip (e.g., nature, city) as picture-in-picture during rendering. Uses existing Pexels search.</p>
            <div v-if="form.broll_enabled" class="mt-3 space-y-3">
              <div>
                <label class="block text-xs font-medium text-clipper-ink/70 dark:text-white/70">B-roll keyword</label>
                <input v-model="form.broll_keyword" placeholder="e.g., nature, city skyline, abstract" class="mt-1 w-full h-9 px-3 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm" />
              </div>
              <div>
                <label class="block text-xs font-medium text-clipper-ink/70 dark:text-white/70">Transition</label>
                <n-select
                  v-model:value="form.transition_type"
                  class="mt-1"
                  :options="[
                    { label: 'Cut (instant)', value: 'cut' },
                    { label: 'Fade (0.5s)', value: 'fade' },
                    { label: 'Zoom', value: 'zoom' },
                  ]"
                />
              </div>
            </div>
          </div>
        </template>

        <div class="flex justify-end gap-3 pt-6 border-t border-clipper-ink/10 dark:border-white/10">
          <button class="h-10 px-4 rounded-lg border border-clipper-ink/12 dark:border-white/10 text-clipper-ink dark:text-white" @click="step > 1 ? prev() : (showModal = false)">{{ step > 1 ? 'Back' : 'Cancel' }}</button>
          <button v-if="step < 5" class="h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm" :disabled="!canNext" @click="next()">Continue</button>
          <button v-else class="h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm" :disabled="creating" @click="submit()">Create Project</button>
        </div>
      </div>
    </div>
  </div>
</template>
