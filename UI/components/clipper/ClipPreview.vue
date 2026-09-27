<script lang="ts" setup>
/**
 * ClipPreview — video preview with hook title (first 3s) and
 * word-synced caption bar. Face-centered framing, dynamic aspect ratio.
 *
 * @author Ismael Garcia <leamsigc@leamsigc.com>
 * @version 0.0.1
 */
const props = withDefaults(defineProps<{
  src: string
  hookTitle?: string
  caption?: string
  accent?: string
  aspectRatio?: "9:16" | "16:9" | "1:1" | "4:5"
}>(), {
  hookTitle: "",
  caption: "",
  accent: "",
  aspectRatio: "9:16",
})

const aspectClass = computed(() => ({
  "9:16": "aspect-[9/16]",
  "16:9": "aspect-video",
  "1:1": "aspect-square",
  "4:5": "aspect-[4/5]",
}[props.aspectRatio] || "aspect-[9/16]"))
</script>

<template>
  <div class="relative rounded-lg overflow-hidden bg-clipper-ink dark:bg-black flex items-stretch w-full max-w-[360px] border border-clipper-ink/08 dark:border-white/10" :class="aspectClass">
    <video
      :src="props.src"
      class="absolute inset-0 w-full h-full object-cover"
      controls
      playsinline
      preload="metadata"
    />
    <!-- Hook title overlay — top 15%, Poppins Bold, max 2 lines -->
    <div v-if="props.hookTitle" class="absolute top-[15%] left-0 right-0 px-4 z-10 pointer-events-none">
      <p class="text-center text-white font-bold leading-tight text-[28px] drop-shadow-[0_1px_3px_rgba(15,23,42,.9)] line-clamp-2">
        {{ props.hookTitle }}
      </p>
    </div>
    <!-- Caption bar lower third — karaoke highlight -->
    <div v-if="props.caption" class="absolute bottom-0 left-0 right-0 px-3 py-2.5 bg-clipper-ink/80 z-10 pointer-events-none">
      <p class="text-center text-white font-bold leading-snug text-[15px]">
        <span class="text-clipper-green">{{ props.accent }}</span>{{ props.caption }}
      </p>
    </div>
  </div>
</template>
