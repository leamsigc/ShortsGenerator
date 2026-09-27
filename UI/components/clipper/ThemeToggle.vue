<script lang="ts" setup>
/**
 * ThemeToggle — light/dark switch for CLIPPER.
 * Delegates to nuxt-naiveui's color mode system (cookie-backed) so Naive UI
 * components, html.dark and the Tailwind dark: variants always agree.
 * Migrates the legacy `clipper-theme` localStorage key once.
 */
const { colorMode, colorModePreference } = useNaiveColorMode()

const isDark = computed(() => colorMode.value === 'dark')

const toggle = () => {
  colorModePreference.set(isDark.value ? 'light' : 'dark')
}

onMounted(() => {
  // One-time migration from the old manual system
  try {
    const saved = localStorage.getItem('clipper-theme')
    if (saved) {
      colorModePreference.set(saved === 'dark' ? 'dark' : 'light')
      localStorage.removeItem('clipper-theme')
    }
  } catch {}
})
</script>

<template>
  <button
    class="w-10 h-10 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 flex items-center justify-center hover:border-clipper-ink/20 dark:hover:border-white/20 text-clipper-ink dark:text-white/80 hover:text-clipper-ink dark:hover:text-white transition-colors"
    :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
    :title="isDark ? 'Light mode' : 'Dark mode'"
    @click="toggle"
  >
    <Icon v-if="isDark" name="ph:sun" size="18" />
    <Icon v-else name="ph:moon" size="18" />
  </button>
</template>
