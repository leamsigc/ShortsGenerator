<script lang="ts" setup>
/**
 * ClipperHeader — 64px horizontal header: logo, project selector, nav, CTA.
 * No sidebar (per design system).
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const clipperStore = useClipperStore()
const router = useRouter()

const goHome = () => router.push("/clipper")

const createNew = () => {
  clipperStore.currentProject = null
  router.push("/clipper")
  setTimeout(() => window.dispatchEvent(new CustomEvent("clipper-new-project")), 60)
}
</script>

<template>
  <header class="h-16 bg-white dark:bg-[#0F172A] border-b border-clipper-ink/10 dark:border-white/10 sticky top-0 z-40">
    <div class="w-full px-6 h-full flex items-center gap-6">
      <!-- Brand + project selector -->
      <button
        class="flex items-center gap-2.5 bg-transparent border-0 cursor-pointer"
        @click="goHome"
        aria-label="SHORTGENERATOR home"
      >
        <span class="w-6 h-6 rounded-[4px] bg-clipper-green flex items-center justify-center text-clipper-ink text-[13px] font-bold leading-none">
          ▶
        </span>
        <span class="font-bold text-clipper-ink dark:text-white text-[17px] tracking-tight">SHORTGENERATOR</span>
      </button>

      <span class="w-px h-6 bg-clipper-ink/10 dark:bg-neutral-700" />

      <button
        v-if="clipperStore.currentProject"
        class="h-10 min-w-[160px] rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 px-3 flex items-center gap-2 text-left hover:border-clipper-ink/20 dark:hover:border-white/20 focus:outline-clipper-green"
        @click="router.push('/clipper')"
        :aria-label="`Project: ${clipperStore.currentProject.name}`"
      >
        <span class="flex-1 truncate text-sm font-medium text-clipper-ink dark:text-white">{{ clipperStore.currentProject.name }}</span>
        <Icon name="ph:caret-down" size="16" class="text-clipper-ink/60 dark:text-white/60" />
      </button>
      <span v-else class="text-sm text-clipper-ink/35 dark:text-white/40">No project selected</span>

      <nav class="flex-1 min-w-0 overflow-hidden" aria-label="Main navigation">
        <div class="flex gap-4 sm:gap-7 overflow-hidden">
          <button
            class="text-sm whitespace-nowrap relative pb-1"
            :class="!clipperStore.currentProject ? 'font-medium text-clipper-ink dark:text-white' : 'text-clipper-ink/60 dark:text-white/60 hover:text-clipper-ink dark:hover:text-white'"
            @click="() => { clipperStore.currentProject = null; router.push('/clipper') }"
          >
            <span>Projects</span>
            <span v-if="!clipperStore.currentProject" class="absolute left-0 right-0 -bottom-0.5 h-0.5 bg-clipper-green rounded" />
          </button>
          <NuxtLink
            v-for="(label, key) in { clips: 'Clips', sources: 'Sources', transcript: 'Transcript', publish: 'Publish', settings: 'Settings' }"
            :key="key"
            :to="`/clipper?view=${key}`"
            class="text-sm whitespace-nowrap relative pb-1"
            :class="clipperStore.activeView === key && clipperStore.currentProject ? 'font-medium text-clipper-ink dark:text-white' : 'text-clipper-ink/60 dark:text-white/60 hover:text-clipper-ink dark:hover:text-white'"
          >
            <span>{{ label }}</span>
            <span
              v-if="clipperStore.activeView === key && clipperStore.currentProject"
              class="absolute left-0 right-0 -bottom-0.5 h-0.5 bg-clipper-green rounded"
            />
          </NuxtLink>
        </div>
      </nav>

      <ClipperThemeToggle />
      <button
        class="h-10 px-4 rounded-lg text-clipper-ink font-semibold text-sm bg-clipper-green hover:opacity-90 active:scale-[0.98] transition-opacity"
        @click="createNew"
      >
        + New Project
      </button>
    </div>
  </header>
</template>