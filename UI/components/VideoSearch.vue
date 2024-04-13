<script lang="ts" setup>
/**
 *
 * Component to preview and select videos base on the user related search terms
 *
 * @author Ismael García <leamsigc@leamsigc.com>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */
interface VideoResult {
  url: string;
  image: string;
  video_files: {
    fileType: string;
    link: string;
    quality: string;
  }[];
}

const { video } = useVideoSettings();

const searchResults = ref<VideoResultFormat[]>([]);

const $URL_SEARCH = `https://api.pexels.com/videos/search`;

const {
  public: { pexelsApiKey },
} = useRuntimeConfig();
const HandleSearch = async () => {
  const termsToSearch: string[] = video.value.search.split(",");
  termsToSearch.forEach(async (term) => {
    // Fetch result from pexels
    console.log("Key", pexelsApiKey);

    const { data } = await useFetch<{ videos: VideoResult[] }>(
      `${$URL_SEARCH}?query=${term}&per_page=20`,
      {
        headers: {
          Authorization: `${pexelsApiKey}`,
        },
      }
    );

    //Get the video of the results
    if (!data.value?.videos) return;
    const formattedVideos = data.value.videos.map((video) => {
      return {
        url: video.url,
        image: video.image,
        videoUrl: video.video_files.find(
          (videoFile) => videoFile.link && videoFile.quality === "hd"
        ),
      };
    });
    searchResults.value = [...searchResults.value, ...formattedVideos];
  });
};

const HandleSelectVideo = (v: VideoResultFormat) => {
  if (selectedUrls.value.includes(v.url)) {
    video.value.selectedVideoUrls = video.value.selectedVideoUrls.filter(
      (video) => video.url !== v.url
    );
  } else {
    if (!video.value.selectedVideoUrls) {
      video.value.selectedVideoUrls = [];
    }
    video.value.selectedVideoUrls.push(v);
  }
};

const selectedUrls = computed(() => {
  return video.value.selectedVideoUrls?.map((video) => video.url) || [];
});
</script>

<template>
  <div>
    <div class="max-w-5xl mx-auto">
      <n-input-group>
        <n-input v-model:value="video.search" />
        <n-button type="success" ghost @click="HandleSearch"> Search </n-button>
      </n-input-group>
    </div>
    <div class="max-w-5xl mx-auto mt-10">
      <section class="grid grid-cols-3 gap-10">
        <div
          v-for="result in searchResults"
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
            :type="selectedUrls.includes(result.url) ? 'success' : 'primary'"
            @click="HandleSelectVideo(result)"
            circle
            size="small"
            class="absolute top-2 right-2"
          >
            <template #icon>
              <Icon
                :name="
                  selectedUrls.includes(result.url) ? 'mdi:check' : 'mdi:plus'
                "
              />
            </template>
          </n-button>
        </div>
      </section>
    </div>
  </div>
</template>
<style scoped></style>
