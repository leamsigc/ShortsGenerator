<script lang="ts" setup>
/**
 * Component Description: Dedicated CLIPPER clip editor page
 * (route /clipper/editor/:clipId).
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */
import { useClipperStore } from "~/stores/ClipperStore"

const route = useRoute()
const router = useRouter()
const clipperStore = useClipperStore()

const clipId = computed(() => String(route.params.clipId))
const clip = computed(() => clipperStore.clipById(clipId.value))
const isLoading = ref(true)
const notFound = ref(false)

const loadClip = async () => {
  isLoading.value = true
  notFound.value = false
  try {
    if (!clipperStore.projects.length) {
      await clipperStore.fetchProjects()
    }
    const found = await clipperStore.fetchClip(clipId.value)
    if (!found) {
      notFound.value = true
      return
    }
    clipperStore.activeClipId = found.id
    // Transcripts power the word timeline, caption overlay and transcript panel —
    // without them the editor renders empty. Make sure the project + its transcripts are loaded.
    if (!clipperStore.projectById(found.project_id)) {
      await clipperStore.fetchProject(found.project_id)
    }
    clipperStore.setCurrentProject(found.project_id)
    const transcript = await clipperStore.fetchTranscript(found.project_id, found.source_id)
    if (!transcript) {
      await clipperStore.loadTranscripts(found.project_id)
    }
  } finally {
    isLoading.value = false
  }
}

const goBack = () => {
  router.push("/clipper")
}

onMounted(loadClip)

watch(clipId, loadClip)
</script>

<template>
  <div class="w-full">
    <header class="mb-6 flex items-center gap-3 border-b border-clipper-ink/08 dark:border-white/08 pb-4">
      <button
        class="w-10 h-10 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 flex items-center justify-center hover:border-clipper-ink/20 dark:hover:border-white/20"
        @click="goBack"
        aria-label="Back to CLIPPER"
      >
        <Icon name="ph:arrow-left" size="18" class="text-clipper-ink dark:text-white" />
      </button>
      <div>
        <h1 class="text-2xl font-bold text-clipper-ink dark:text-white tracking-tight">
          Clip Editor
        </h1>
        <p v-if="clip" class="text-clipper-ink/60 dark:text-white/60 text-sm mt-0.5">
          {{ clip.hook_title || `Clip #${clip.index + 1}` }} · {{ clip.duration.toFixed(0) }}s
        </p>
      </div>
    </header>

    <div v-if="isLoading" class="flex justify-center py-24">
      <n-spin size="large" />
    </div>

    <div v-else-if="notFound || !clip" class="text-center py-24 border border-clipper-ink/08 dark:border-white/08 rounded-xl bg-white dark:bg-neutral-800">
      <Icon name="ph:warning-circle" size="56" class="mx-auto text-clipper-ink dark:text-white/20 mb-4" />
      <h3 class="text-lg font-semibold text-clipper-ink dark:text-white">Clip not found</h3>
      <p class="text-clipper-ink/60 dark:text-white/60 mt-1 text-sm">It may have been removed or the link is invalid.</p>
      <button class="mt-4 h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm" @click="goBack">Back to CLIPPER</button>
    </div>

    <ClipperClipEditor v-else :key="clip.id" :clip="clip" />
  </div>
</template>
