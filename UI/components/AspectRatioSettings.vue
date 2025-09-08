<script lang="ts" setup>
/**
 *
 * Component Description: Aspect Ratio Settings Component
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

const { globalSettings } = useGlobalSettings();
const API_URL = "http://localhost:8080";

const aspectRatioOptions = [
  { label: '9:16 (TikTok/Reels)', value: '9:16' },
  { label: '16:9 (YouTube)', value: '16:9' },
  { label: '1:1 (Square)', value: '1:1' },
  { label: '4:5 (Instagram Portrait)', value: '4:5' }
];

const handleAspectRatioChange = async (value: string) => {
  globalSettings.value.aspect_ratio = value;

  // Save to backend
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: {
        type: "FONT",
        settings: {
          aspect_ratio: value
        }
      }
    });
  } catch (error) {
    console.error('Failed to save aspect ratio:', error);
  }
};
</script>

<template>
  <div class="aspect-ratio-settings">
    <n-form label-placement="left" label-width="160">
      <n-form-item label="Aspect Ratio">
        <n-select
          v-model:value="globalSettings.aspect_ratio"
          :options="aspectRatioOptions"
          @update:value="handleAspectRatioChange"
          placeholder="Select aspect ratio"
        />
      </n-form-item>
    </n-form>
  </div>
</template>

<style scoped>
.aspect-ratio-settings {
  margin-top: 1rem;
}
</style>