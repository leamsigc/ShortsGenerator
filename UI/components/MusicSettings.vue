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
const availableSongs = ref<string[]>([]);

const { video } = useVideoSettings();

onMounted(async () => {
  const { data: songsResponse } = await $fetch<{ data: { songs: string[] } }>(
    `${API_SETTINGS.value.URL}/api/getSongs`
  );
  availableSongs.value = songsResponse.songs;
});
</script>

<template>
  <n-form
    ref="reviewFormRef"
    class="max-w-screen-md"
    :model="video"
    size="large"
  >
    <n-form-item label="Select audio:" path="voice">
      <n-radio-group v-model:value="video.selectedAudio" name="radiogroup">
        <n-space :vertical="true">
          <n-radio
            v-for="song in availableSongs"
            :key="song"
            :value="song"
            :label="song"
          />
        </n-space>
      </n-radio-group>
    </n-form-item>
    <div>
      <audio controls v-for="song in availableSongs" :key="song" class="mb-5">
        <source
          :src="`${API_SETTINGS.URL}/static/assets/music/${song}`"
          type="audio/mp4"
        />
      </audio>
    </div>
  </n-form>
</template>
<style scoped></style>
