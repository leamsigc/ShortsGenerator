<script lang="ts" setup>
/**
 *
 * Component Description:Desc
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

const { API_SETTINGS } = useApiSettings();
const { video } = useVideoSettings();

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
</script>

<template>
  <section>
    <n-form-item label="Model:" path="aiModel">
      <n-select v-model:value="video.aiModel" :options="options" />
    </n-form-item>
    <n-form-item label="Video subject:" path="videoSubject">
      <n-input
        v-model:value="video.videoSubject"
        placeholder="Video Subject"
        type="textarea"
        show-count
        clearable
        :autosize="{
          minRows: 10,
          maxRows: 20,
        }"
      />
    </n-form-item>
    <n-form-item label="Extra Prompt:">
      <n-input
        v-model:value="video.extraPrompt"
        placeholder="Video Subject"
        type="textarea"
        show-count
        clearable
      />
    </n-form-item>
    <n-form-item label="Search:">
      <n-input
        v-model:value="video.search"
        placeholder="Search"
        type="textarea"
        show-count
        clearable
      />
    </n-form-item>
    <VoiceSettings />
    <MusicSettings />
    <SubtitleSettings />
  </section>
</template>
<style scoped></style>
