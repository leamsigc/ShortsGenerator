<script lang="ts" setup>
/**
 * Default Layout — Stripe-inspired horizontal header, no sidebar.
 * Applies CLIPPER design system to all non-clipper routes.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const route = useRoute()
const router = useRouter()

const nav = [
  { label: "Generate", path: "/generate" },
  { label: "Videos", path: "/videos" },
  { label: "Search", path: "/search" },
  { label: "Clipper", path: "/clipper" },
  { label: "Settings", path: "/settings" },
  { label: "Docs", path: "/docs" },
] as const

const isActive = (path: string) => {
  if (path === "/") return route.path === "/"
  return route.path.startsWith(path)
}
</script>

<template>
  <div class="min-h-screen bg-white dark:bg-[#0F172A] text-clipper-ink dark:text-white font-poppins antialiased">
    <!-- Global horizontal header — no sidebar per styleguide §8 -->
    <header class="h-16 bg-white dark:bg-[#0F172A] border-b border-clipper-ink/10 dark:border-white/10 sticky top-0 z-40">
      <div class="w-full px-6 h-full flex items-center gap-6">
        <!-- Brand -->
        <NuxtLink to="/generate" class="flex items-center gap-2.5 shrink-0">
          <span class="w-6 h-6 rounded-[4px] bg-clipper-green flex items-center justify-center text-clipper-ink text-[13px] font-bold leading-none">▶</span>
          <span class="font-bold text-clipper-ink dark:text-white text-[17px] tracking-tight">SHORTGENERATOR</span>
        </NuxtLink>

        <span class="w-px h-6 bg-clipper-ink/10 dark:bg-white/10 hidden sm:block" />

        <!-- Main nav — no overflow scroll -->
        <nav class="flex-1 flex items-center gap-3 sm:gap-6 min-w-0 overflow-hidden" aria-label="Main navigation">
          <NuxtLink
            v-for="item in nav"
            :key="item.path"
            :to="item.path"
            class="text-sm whitespace-nowrap relative py-1"
            :class="isActive(item.path) ? 'font-medium text-clipper-ink dark:text-white' : 'text-clipper-ink/60 dark:text-white/60 hover:text-clipper-ink dark:hover:text-white'"
          >
            {{ item.label }}
            <span
              v-if="isActive(item.path)"
              class="absolute left-0 right-0 -bottom-1 h-0.5 bg-clipper-green rounded"
            />
          </NuxtLink>
        </nav>

        <!-- Theme + CTA -->
        <ClipperThemeToggle />
        <NuxtLink
          to="/clipper"
          class="hidden sm:inline-flex h-10 px-4 rounded-lg text-clipper-ink font-semibold text-sm bg-clipper-green hover:opacity-90 items-center justify-center shrink-0"
        >
          + New Project
        </NuxtLink>
      </div>
    </header>

    <main class="w-full px-6 py-8">
      <slot />
    </main>

    <SearchDialog />
  </div>
</template>
