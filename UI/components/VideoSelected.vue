<script lang="ts" setup>
/**
 *
 * Selected videos — with clip order control.
 *
 * Order modes:
 * - random (default): backend shuffles clips on every generation.
 * - selection: backend uses the order videos were selected in.
 * - custom: user-defined order via up/down controls; backend respects it.
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.2
 */

const { video } = useVideoSettings();

type VideoOrderMode = "random" | "selection" | "custom";

const orderModeOptions = [
  { label: "Random (default)", value: "random" },
  { label: "Selected sequence", value: "selection" },
  { label: "Specific order", value: "custom" },
];

const orderModeDescriptions: Record<VideoOrderMode, string> = {
  random: "Clips are shuffled on every generation.",
  selection: "Clips play in the order you selected them.",
  custom: "Drag the order with the arrows — the backend respects this exact sequence.",
};

// Backwards-compat: localStorage from older builds may lack the key.
const orderMode = computed<VideoOrderMode>({
  get: () => {
    const m = (video.value as any).videoOrderMode as VideoOrderMode | undefined;
    return m === "selection" || m === "custom" ? m : "random";
  },
  set: (v: VideoOrderMode) => {
    (video.value as any).videoOrderMode = v;
  },
});

const isCustom = computed(() => orderMode.value === "custom");

const HandleSelectVideo = (v: VideoResultFormat) => {
  if (selectedUrls.value.includes(v.url)) {
    video.value.selectedVideoUrls = video.value.selectedVideoUrls.filter(
      (video) => video.url !== v.url
    );
  } else {
    video.value.selectedVideoUrls.push(v);
  }
};

const moveVideo = (index: number, direction: -1 | 1) => {
  const list = video.value.selectedVideoUrls;
  const target = index + direction;
  if (target < 0 || target >= list.length) return;
  const [item] = list.splice(index, 1);
  list.splice(target, 0, item);
  // Reordering is inherently a custom order — reflect it in the mode.
  if (orderMode.value !== "custom") {
    orderMode.value = "custom";
  }
};

const moveToTop = (index: number) => {
  const list = video.value.selectedVideoUrls;
  if (index <= 0 || index >= list.length) return;
  const [item] = list.splice(index, 1);
  list.unshift(item);
  if (orderMode.value !== "custom") {
    orderMode.value = "custom";
  }
};

const selectedUrls = computed(() => {
  return video.value.selectedVideoUrls?.map((video) => video.url) || [];
});
</script>

<template>
  <div class="max-w-5xl mx-auto mt-6">
    <!-- Order mode selector -->
    <div
      class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-4 mb-6"
    >
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-sm font-semibold">Clip order:</span>
        <n-radio-group v-model:value="orderMode" name="videoOrderMode" size="small">
          <n-radio-button
            v-for="opt in orderModeOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </n-radio-button>
        </n-radio-group>
        <span class="text-xs opacity-60 ml-auto">
          {{ video.selectedVideoUrls.length }} clip(s) selected
        </span>
      </div>
      <p class="text-xs opacity-60 mt-2">
        {{ orderModeDescriptions[orderMode] }}
      </p>
      <p v-if="isCustom" class="text-xs text-clipper-green mt-1">
        Use the ◀ ▶ arrows on each clip to set the exact playback sequence (1 → N).
      </p>
    </div>

    <section
      v-if="video.selectedVideoUrls.length > 0"
      class="grid grid-cols-3 gap-10"
    >
      <div v-for="(result, idx) in video.selectedVideoUrls" :key="result.url" :value="result.url" class="relative">
        <video v-if="result.videoUrl" :src="result.videoUrl?.link" controls :poster="result.image"></video>
        <div v-else class="aspect-[9/16] bg-gray-800 flex items-center justify-center text-gray-400 text-sm rounded">
          No video available
        </div>
        <!-- Order badge -->
        <span
          v-if="orderMode !== 'random'"
          class="absolute top-2 left-2 min-w-7 h-7 px-2 rounded-full bg-black/70 text-white text-sm font-bold flex items-center justify-center"
          :title="orderMode === 'custom' ? 'Playback position (change with arrows)' : 'Selection order'"
        >
          {{ idx + 1 }}
        </span>
        <span
          v-else
          class="absolute top-2 left-2 min-w-7 h-7 px-2 rounded-full bg-black/50 text-white text-xs flex items-center justify-center"
          title="Order will be shuffled at generation time"
        >
          🔀
        </span>
        <n-button :type="video.selectedVideoUrls.includes(result) ? 'success' : 'primary'
          " @click="HandleSelectVideo(result)" circle size="small" class="absolute top-2 right-2">
          <template #icon>
            <Icon :name="video.selectedVideoUrls.includes(result)
              ? 'mdi:check'
              : 'mdi:plus'
              " />
          </template>
        </n-button>
        <!-- Reorder controls (specific order mode) -->
        <div
          v-if="isCustom"
          class="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-black/70 rounded-full px-2 py-1"
        >
          <n-button
            size="tiny"
            quaternary
            :disabled="idx === 0"
            title="Move earlier"
            @click="moveVideo(idx, -1)"
          >
            <template #icon><span class="text-white text-sm leading-none">◀</span></template>
          </n-button>
          <span class="text-white text-xs font-bold min-w-8 text-center">{{ idx + 1 }}/{{ video.selectedVideoUrls.length }}</span>
          <n-button
            size="tiny"
            quaternary
            :disabled="idx === video.selectedVideoUrls.length - 1"
            title="Move later"
            @click="moveVideo(idx, 1)"
          >
            <template #icon><span class="text-white text-sm leading-none">▶</span></template>
          </n-button>
          <n-button
            v-if="idx !== 0"
            size="tiny"
            quaternary
            title="Move to first"
            @click="moveToTop(idx)"
          >
            <template #icon><span class="text-white text-xs leading-none">⏮</span></template>
          </n-button>
        </div>
      </div>
    </section>
    <n-empty
      v-else
      description="No videos selected yet — pick some from Search and select, Instagram or Upload."
    />
  </div>
</template>
<style scoped></style>
