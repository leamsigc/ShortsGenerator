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

const HandleSaveSettings = async () => {
  //   Save the setting to local storage
};
</script>

<template>
  <div class="min-h-screen flex flex-col justify-center items-center">
    <header class="text-3xl leading-10 font-bold">Global Settings</header>

    <n-form
      ref="formRef"
      class="max-w-screen-md mt-10"
      :model="globalSettings"
      :rules="settingsRule"
      size="large"
      :disabled="isLoading"
    >
      <n-form-item label="Model:" path="aiModel">
        <n-select v-model:value="globalSettings.aiModel" :options="options" />
      </n-form-item>
      <n-form-item label="Voice:" path="voice">
        <n-select
          v-model:value="globalSettings.voice"
          :options="voiceOptions"
        />
      </n-form-item>
      <n-form-item label="Font:" path="font">
        <n-input
          v-model:value="globalSettings.font"
          placeholder="Font for the subtitle"
          show-count
          clearable
        />
      </n-form-item>
      <n-form-item label="Color(#18A058)" path="fontcolor">
        <n-color-picker
          v-model:value="globalSettings.color"
          :show-alpha="false"
        />
      </n-form-item>
      <n-form-item label="Subtitle position:" path="subtitlePosition">
        <n-radio-group
          v-model:value="globalSettings.subtitles_position"
          name="subtitlePosition"
          size="medium"
        >
          <n-radio-button
            v-for="position in subtitlePositionOptions"
            :key="position"
            :value="position"
          >
            <span class="capitalize">
              {{ position }}
            </span>
          </n-radio-button>
        </n-radio-group>
      </n-form-item>
      <n-form-item label="Font size:">
        <n-input-number
          v-model:value="globalSettings.fontsize"
          placeholder="Font for the subtitle"
          class="w-full"
        />
      </n-form-item>

      <n-form-item label="Stroke color(#18A058)">
        <n-color-picker v-model:value="globalSettings.stroke_color" />
      </n-form-item>
      <n-form-item label="Stroke width:">
        <n-input-number
          v-model:value="globalSettings.stroke_width"
          placeholder="Font for the subtitle"
          class="w-full"
        />
      </n-form-item>
      <n-form-item>
        <n-button
          @click="HandleSaveSettings"
          type="success"
          ghost
          :loading="isLoading"
          :disabled="isLoading"
        >
          Save settings
        </n-button>
      </n-form-item>
    </n-form>
  </div>
</template>
<style scoped></style>
