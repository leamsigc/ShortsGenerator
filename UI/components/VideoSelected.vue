<script lang="ts" setup>
/**
 *
 * Selected videos
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

const { video } = useVideoSettings();

const HandleSelectVideo = (v: VideoResultFormat) => {
  if (selectedUrls.value.includes(v.url)) {
    video.value.selectedVideoUrls = video.value.selectedVideoUrls.filter(
      (video) => video.url !== v.url
    );
  } else {
    video.value.selectedVideoUrls.push(v);
  }
};

const selectedUrls = computed(() => {
  return video.value.selectedVideoUrls?.map((video) => video.url) || [];
});
</script>

<template>
  <div class="max-w-5xl mx-auto mt-10">
    <section class="grid grid-cols-3 gap-10">
      <div
        v-for="result in video.selectedVideoUrls"
        :key="result.url"
        :value="result.url"
        class="relative"
      >
        <video
          v-if="result.videoUrl"
          :src="result.videoUrl?.link"
          controls
          :poster="result.image"
        ></video>
        <n-button
          :type="
            video.selectedVideoUrls.includes(result) ? 'success' : 'primary'
          "
          @click="HandleSelectVideo(result)"
          circle
          size="small"
          class="absolute top-2 right-2"
        >
          <template #icon>
            <Icon
              :name="
                video.selectedVideoUrls.includes(result)
                  ? 'mdi:check'
                  : 'mdi:plus'
              "
            />
          </template>
        </n-button>
      </div>
    </section>
  </div>
</template>
<style scoped></style>
