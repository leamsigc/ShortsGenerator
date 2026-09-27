<script lang="ts" setup>
/**
 * CLIPPER Layout — Stripe-inspired, no sidebar, white application shell.
 * Used only by /clipper routes (set via definePageMeta in each page).
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const clipperStore = useClipperStore()
const router = useRouter()

const goHome = () => {
  router.push("/clipper")
}
</script>

<template>
  <div class="min-h-screen bg-white dark:bg-[#0F172A] text-clipper-ink dark:text-white font-poppins antialiased">
    <ClipperHeader />
    <main class="w-full px-6 py-8">
      <slot />
    </main>
  </div>
</template>