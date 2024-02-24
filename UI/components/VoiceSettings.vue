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
const voiceOptions = ref<{ label: string; value: string }[]>([]);

const { video } = useVideoSettings();

const { data } = await $fetch<{ data: { voices: string[] } }>(
  `${API_SETTINGS.value.URL}/api/models`
);
voiceOptions.value = data.voices.map((voice) => {
  return { label: voice, value: voice };
});
</script>

<template>
  <n-form-item label="Voice:" path="voice">
    <n-select v-model:value="video.voice" :options="voiceOptions" />
  </n-form-item>
</template>
<style scoped></style>
