<script lang="ts" setup>
/**
 *
 * Global Settings
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

interface ScriptSettings {
  defaultPromptEnd: string;
  defaultPromptStart: string;
}
interface FontSettings {
  font: string;
  fontsize: number;
  color: string;
  stroke_color: string;
  stroke_width: number;
  subtitles_position:
  | "center,top"
  | "center,bottom"
  | "center,center"
  | "left,center"
  | "left,bottom"
  | "right,center"
  | "right,bottom";
  background_color: string;
  background_opacity: number;
  line_spacing: number;
  padding: number;
  google_font: string;
  text_align: "left" | "center" | "right";
  shadow_enabled: boolean;
  shadow_color: string;
  shadow_offset: [number, number];
  max_lines: number;
  word_wrap: boolean;
  aspect_ratio: string;
  max_clip_duration: number;
}

interface GlobalSettings {
  fontSettings: FontSettings;
  scriptSettings: ScriptSettings;
}
const isLoading = ref(false);
const API_URL = "http://localhost:8080";
const voiceOptions = ref<{ label: string; value: string }[]>([]);

const { globalSettings } = useGlobalSettings();

const options = [
  {
    label: "FREE",
    value: "g4f",
  },
  {
    label: "GPT 4",
    value: "gpt4",
  },
  {
    label: "GPT 3.5 Turbo",
    value: "gpt3.5-turbo",
  },
];

const settingsRule = {
  font: {
    required: true,
    trigger: ["input", "blur"],
  },
  fontColor: {
    required: true,
    trigger: ["input", "blur"],
  },
  subtitlePosition: {
    required: true,
    trigger: ["input", "blur"],
  },
  aiModel: {
    required: true,
    trigger: ["change", "blur"],
  },
};

const subtitlePositionOptions = [
  "center,top",
  "center,bottom",
  "center,center",
  "left,center",
  "left,bottom",
  "right,center",
  "right,bottom",
];

const textAlignOptions = [
  { label: "Left", value: "left" },
  { label: "Center", value: "center" },
  { label: "Right", value: "right" },
];

const aspectRatioOptions = [
  { label: "Reels/TikTok (9:16)", value: "9:16" },
  { label: "YouTube Landscape (16:9)", value: "16:9" },
  { label: "Instagram Square (1:1)", value: "1:1" },
  { label: "Instagram Portrait (4:5)", value: "4:5" },
];

const { data } = await $fetch<{ data: { voices: string[] } }>(
  `${API_URL}/api/models`
);
voiceOptions.value = data.voices.map((voice) => {
  return { label: voice, value: voice };
});

const { data: mainSettings } = await $fetch<{
  data: GlobalSettings;
}>(`${API_URL}/api/settings`);
globalSettings.value.font = mainSettings.fontSettings.font;
globalSettings.value.color = mainSettings.fontSettings.color;
globalSettings.value.fontsize = mainSettings.fontSettings.fontsize;
globalSettings.value.stroke_color = mainSettings.fontSettings.stroke_color;
globalSettings.value.stroke_width = mainSettings.fontSettings.stroke_width;
globalSettings.value.subtitles_position =
  mainSettings.fontSettings.subtitles_position;
globalSettings.value.background_color = mainSettings.fontSettings.background_color;
globalSettings.value.background_opacity = mainSettings.fontSettings.background_opacity;
globalSettings.value.line_spacing = mainSettings.fontSettings.line_spacing;
globalSettings.value.padding = mainSettings.fontSettings.padding;
globalSettings.value.google_font = mainSettings.fontSettings.google_font;
globalSettings.value.text_align = mainSettings.fontSettings.text_align;
globalSettings.value.shadow_enabled = mainSettings.fontSettings.shadow_enabled;
globalSettings.value.shadow_color = mainSettings.fontSettings.shadow_color;
globalSettings.value.shadow_offset = mainSettings.fontSettings.shadow_offset;
globalSettings.value.max_lines = mainSettings.fontSettings.max_lines;
globalSettings.value.word_wrap = mainSettings.fontSettings.word_wrap;
globalSettings.value.aspect_ratio = mainSettings.fontSettings.aspect_ratio;
globalSettings.value.max_clip_duration = mainSettings.fontSettings.max_clip_duration;

const HandleSaveSettings = async () => {
  //   Save the setting to local storage
};
</script>

<template>
  <div class="min-h-screen flex flex-col justify-center items-center">
    <header class="text-3xl leading-10 font-bold">Global Settings</header>

    <n-form ref="formRef" class="max-w-screen-md mt-10" :model="globalSettings" :rules="settingsRule" size="large"
      :disabled="isLoading">
      <n-form-item label="Model:" path="aiModel">
        <n-select v-model:value="globalSettings.aiModel" :options="options" />
      </n-form-item>
      <n-form-item label="Voice:" path="voice">
        <n-select v-model:value="globalSettings.voice" :options="voiceOptions" />
      </n-form-item>
      <n-form-item label="Font:" path="font">
        <n-input v-model:value="globalSettings.font" placeholder="Font for the subtitle" show-count clearable />
      </n-form-item>
      <n-form-item label="Color(#18A058)" path="fontcolor">
        <n-color-picker v-model:value="globalSettings.color" :show-alpha="false" />
      </n-form-item>
      <n-form-item label="Subtitle position:" path="subtitlePosition">
        <n-radio-group v-model:value="globalSettings.subtitles_position" name="subtitlePosition" size="medium">
          <n-radio-button v-for="position in subtitlePositionOptions" :key="position" :value="position">
            <span class="capitalize">
              {{ position }}
            </span>
          </n-radio-button>
        </n-radio-group>
      </n-form-item>
      <n-form-item label="Font size:">
        <n-input-number v-model:value="globalSettings.fontsize" placeholder="Font for the subtitle" class="w-full" />
      </n-form-item>

      <n-form-item label="Stroke color(#18A058)">
        <n-color-picker v-model:value="globalSettings.stroke_color" />
      </n-form-item>
      <n-form-item label="Stroke width:">
        <n-input-number v-model:value="globalSettings.stroke_width" placeholder="Font for the subtitle"
          class="w-full" />
      </n-form-item>
      <n-form-item label="Background Color">
        <n-color-picker v-model:value="globalSettings.background_color" :show-alpha="true" />
      </n-form-item>

      <n-form-item label="Background Opacity">
        <n-slider v-model:value="globalSettings.background_opacity" :min="0" :max="1" :step="0.1" />
      </n-form-item>

      <n-form-item label="Line Spacing">
        <n-input-number v-model:value="globalSettings.line_spacing" :min="1" :max="3" :step="0.1" />
      </n-form-item>

      <n-form-item label="Padding">
        <n-input-number v-model:value="globalSettings.padding" :min="0" :max="100" />
      </n-form-item>

      <n-form-item label="Google Font">
        <n-input v-model:value="globalSettings.google_font" placeholder="Enter Google Font name" />
      </n-form-item>

      <n-form-item label="Text Alignment">
        <n-select v-model:value="globalSettings.text_align" :options="textAlignOptions" />
      </n-form-item>

      <n-form-item label="Enable Shadow">
        <n-switch v-model:value="globalSettings.shadow_enabled" />
      </n-form-item>

      <n-form-item label="Shadow Color" v-if="globalSettings.shadow_enabled">
        <n-color-picker v-model:value="globalSettings.shadow_color" :show-alpha="true" />
      </n-form-item>

      <n-form-item label="Maximum Lines">
        <n-input-number v-model:value="globalSettings.max_lines" :min="1" :max="5" />
      </n-form-item>

      <n-form-item label="Word Wrap">
        <n-switch v-model:value="globalSettings.word_wrap" />
      </n-form-item>

      <n-form-item label="Video Aspect Ratio">
        <n-select v-model:value="globalSettings.aspect_ratio" :options="aspectRatioOptions" />
      </n-form-item>

      <n-form-item label="Max Clip Duration (seconds)">
        <n-input-number v-model:value="globalSettings.max_clip_duration" :min="1" :max="60" :step="1" />
      </n-form-item>

      <n-form-item>
        <n-button @click="HandleSaveSettings" type="success" ghost :loading="isLoading" :disabled="isLoading">
          Save settings
        </n-button>
      </n-form-item>
    </n-form>
  </div>
</template>
<style scoped></style>
