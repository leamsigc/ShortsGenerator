<script lang="ts" setup>
/**
 *
 * Subtitle settings - 10 templates with live preview
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

interface SubtitleTemplate {
  value: string;
  label: string;
  description: string;
  color: string;
  stroke_color: string;
  stroke_width: number;
  fontsize: number;
  position: string;
}

const { API_SETTINGS } = useApiSettings();
const { video } = useVideoSettings();

const templates = ref<SubtitleTemplate[]>([]);
const aspectRatios = ref<{ value: string; label: string; width: number; height: number }[]>([]);

// Google Fonts — most popular, grouped. Selected font is applied to subtitles.
const fontFamilies = [
  { group: "Display / Impact (great for shorts)", fonts: ["Anton", "Bebas Neue", "Archivo Black", "Oswald", "Montserrat ExtraBold"] },
  { group: "Sans (clean, popular)", fonts: ["Inter", "Roboto", "Open Sans", "Lato", "Poppins", "Montserrat", "Nunito", "Raleway", "Rubik", "Work Sans", "DM Sans", "Manrope"] },
  { group: "Serif / Mono / Fun", fonts: ["Merriweather", "Playfair Display", "Roboto Mono", "JetBrains Mono", "Comic Neue", "Bangers"] },
];
const fontOptions = [
  { label: "Default (bold_font)", value: "" },
  ...fontFamilies.flatMap((g) => g.fonts.map((f) => ({ label: f, value: f, group: g.group }))),
];
const selectedFont = computed({
  get: () => video.value.subtitleFont || "",
  set: (v) => (video.value.subtitleFont = v || ""),
});

// Load the chosen Google Font in the browser so the preview renders it
const previewFontHref = computed(() =>
  selectedFont.value
    ? `https://fonts.googleapis.com/css2?family=${encodeURIComponent(selectedFont.value).replace(/%20/g, "+")}&display=swap`
    : ""
);
const aspectRatio = computed({
  get: () => video.value.aspectRatio || "9:16",
  set: (v) => (video.value.aspectRatio = v),
});

const subtitleTemplate = computed({
  get: () => video.value.subtitleTemplate || "classic",
  set: (v) => (video.value.subtitleTemplate = v),
});

const customSubtitle = computed({
  get: () => video.value.customSubtitle || "",
  set: (v) => (video.value.customSubtitle = v),
});

const selectedTemplate = computed(
  () => templates.value.find((t) => t.value === subtitleTemplate.value) || templates.value[0]
);

const previewText = computed(() => {
  if (customSubtitle.value && customSubtitle.value.trim()) {
    return customSubtitle.value.split("\n")[0].slice(0, 60) || "Preview text";
  }
  if (video.value.script) {
    const firstLine = video.value.script.split(/[.\n]/)[0]?.trim();
    if (firstLine) return firstLine.slice(0, 60);
  }
  return "This is how your subtitles will look";
});

const previewStyle = computed(() => {
  const t = selectedTemplate.value;
  if (!t) return {};
  const scale = currentAspectScale.value;
  return {
    color: t.color,
    "-webkit-text-stroke": `${Math.max(1, Math.round(t.stroke_width * scale))}px ${t.stroke_color}`,
    "text-stroke": `${Math.max(1, Math.round(t.stroke_width * scale))}px ${t.stroke_color}`,
    "font-size": `${Math.max(18, Math.round(t.fontsize * scale * 0.35))}px`,
    "font-weight": t.stroke_width >= 4 ? "900" : "700",
    "font-family": selectedFont.value ? `"${selectedFont.value}", sans-serif` : "inherit",
    "letter-spacing": "0.02em",
    "text-shadow":
      t.stroke_width < 2
        ? "0 2px 8px rgba(0,0,0,0.6)"
        : "none",
    "line-height": "1.2",
    "max-width": "90%",
    "text-align": "center" as const,
  };
});

const currentAspectScale = computed(() => {
  const a = aspectRatio.value;
  if (a === "16:9" || a === "21:9") return 0.7;
  if (a === "1:1") return 0.85;
  if (a === "4:5") return 0.92;
  return 1;
});

const previewContainerStyle = computed(() => {
  const map: Record<string, string> = {
    "9:16": "9 / 16",
    "16:9": "16 / 9",
    "1:1": "1 / 1",
    "4:5": "4 / 5",
    "21:9": "21 / 9",
  };
  return {
    "aspect-ratio": map[aspectRatio.value] || "9 / 16",
    "background":
      "linear-gradient(135deg, #1e293b 0%, #0f172a 50%, #020617 100%)",
  };
});

const positionStyle = computed(() => {
  const t = selectedTemplate.value;
  if (!t) return {};
  const [h, v] = (t.position || "center,bottom").split(",");
  const verticalMap: Record<string, string> = {
    top: "8%",
    center: "50%",
    bottom: "88%",
  };
  return {
    left: h === "center" ? "50%" : h === "right" ? "auto" : "5%",
    right: h === "right" ? "5%" : "auto",
    top: verticalMap[v] || "88%",
    transform: h === "center" ? "translate(-50%, -50%)" : "none",
  };
});

onMounted(async () => {
  try {
    const res = await $fetch<{ data: any }>(`${API_SETTINGS.value.URL}/api/settings`);
    if (res?.data?.subtitleTemplates?.options) {
      templates.value = res.data.subtitleTemplates.options;
    }
    if (res?.data?.aspectRatioSettings?.options) {
      aspectRatios.value = res.data.aspectRatioSettings.options;
    }
  } catch (e) {
    console.error("Failed to load subtitle settings", e);
  }
});
</script>

<template>
  <div class="space-y-5">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <n-form-item label="Aspect Ratio" :show-feedback="false">
        <n-select
          v-model:value="aspectRatio"
          :options="aspectRatios"
          size="medium"
        />
      </n-form-item>

      <n-form-item label="Subtitle Template" :show-feedback="false">
        <n-select
          v-model:value="subtitleTemplate"
          :options="templates.map((t) => ({ label: t.label, value: t.value }))"
          size="medium"
        />
      </n-form-item>
    </div>

    <n-form-item label="Font (Google Fonts)" :show-feedback="false">
      <n-select
        v-model:value="selectedFont"
        :options="fontOptions"
        size="medium"
        filterable
        placeholder="Default (bold_font)"
      />
    </n-form-item>
    <link v-if="previewFontHref" rel="stylesheet" :href="previewFontHref" />

    <div class="rounded-xl border border-clipper-ink/08 dark:border-white/08 overflow-hidden bg-neutral-100 dark:bg-neutral-800">
      <div class="px-4 py-2 text-xs uppercase tracking-wide text-clipper-ink/60 dark:text-white/60 border-b border-clipper-ink/08 dark:border-white/08 flex items-center justify-between">
        <span>Live Preview</span>
        <span class="text-clipper-ink/35 dark:text-white/40">{{ aspectRatio }} • {{ selectedTemplate?.label }}</span>
      </div>
      <div class="flex items-center justify-center p-4">
        <div
          class="relative w-full max-w-[260px] rounded-lg overflow-hidden shadow-lg"
          :style="previewContainerStyle"
        >
          <div class="absolute inset-0 grid place-items-center text-slate-600 text-xs">
            Video preview
          </div>
          <div
            v-if="selectedTemplate"
            class="absolute font-black"
            :style="{ ...previewStyle, ...positionStyle }"
          >
            {{ previewText }}
          </div>
        </div>
      </div>
    </div>

    <n-collapse>
      <n-collapse-item title="Custom Subtitle Text" name="custom">
        <n-input
          v-model:value="customSubtitle"
          type="textarea"
          placeholder="Enter your custom subtitle text. Each line is a subtitle segment. Use new lines to split segments."
          :autosize="{ minRows: 3, maxRows: 8 }"
        />
        <p class="text-xs text-clipper-ink/35 dark:text-white/40 mt-2">
          When provided, this text will be used for subtitle timing instead of the script.
          Leave empty to use the generated script.
        </p>
      </n-collapse-item>
    </n-collapse>

    <div>
      <h4 class="text-sm font-bold mb-2 text-clipper-ink dark:text-white">Templates</h4>
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        <button
          v-for="t in templates"
          :key="t.value"
          type="button"
          class="group relative rounded-lg overflow-hidden border-2 transition-all p-2 text-left"
          :class="subtitleTemplate === t.value
            ? 'border-clipper-green bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08'
            : 'border-clipper-ink/08 dark:border-white/08 hover:border-slate-500 bg-neutral-100 dark:bg-neutral-800'"
          @click="subtitleTemplate = t.value"
        >
          <div
            class="aspect-[9/16] max-h-32 w-full rounded mb-1 flex items-center justify-center"
            :style="{
              background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
            }"
          >
            <span
              :style="{
                color: t.color,
                '-webkit-text-stroke': `${Math.max(1, Math.round(t.stroke_width * 0.4))}px ${t.stroke_color}`,
                'text-stroke': `${Math.max(1, Math.round(t.stroke_width * 0.4))}px ${t.stroke_color}`,
                'font-size': `${Math.max(14, Math.round(t.fontsize * 0.18))}px`,
                'font-weight': t.stroke_width >= 4 ? 900 : 700,
                'text-align': 'center',
                'padding': '0 4px',
                'line-height': 1.1,
              }"
            >
              Hello World
            </span>
          </div>
          <div class="text-xs font-bold text-clipper-ink dark:text-white">{{ t.label }}</div>
          <div class="text-[10px] text-clipper-ink/35 dark:text-white/40 line-clamp-1">{{ t.description }}</div>
          <div
            v-if="subtitleTemplate === t.value"
            class="absolute top-1 right-1 w-5 h-5 bg-clipper-green rounded-full flex items-center justify-center"
          >
            <Icon name="mdi:check" size="12" class="text-white" />
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
