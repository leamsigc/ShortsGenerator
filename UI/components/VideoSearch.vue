<script lang="ts" setup>
/**
 *
 * Component to preview and select videos base on the user related search terms
 *
 * @author Ismael García <leamsigc@leamsigc.com>
 * @version 0.0.2
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
const searching = ref(false);
const searchError = ref<string | null>(null);
const searchedTerms = ref<string[]>([]);

const $URL_SEARCH = `https://api.pexels.com/videos/search`;

const {
  public: { pexelsApiKey },
} = useRuntimeConfig();

const HandleSearch = async () => {
  if (!video.value.search.trim()) {
    searchError.value = "Enter at least one search term";
    return;
  }
  searching.value = true;
  searchError.value = null;

  const termsToSearch = video.value.search
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .filter((t) => !searchedTerms.value.includes(t));

  if (termsToSearch.length === 0) {
    searching.value = false;
    searchError.value = "All terms already searched — edit the terms to search again";
    return;
  }

  // Sequential (not parallel): Pexels rate-limits bursts; parallel calls 429'd silently
  for (const term of termsToSearch) {
    try {
      const res = await $fetch<{ videos: VideoResult[] }>(
        `${$URL_SEARCH}?query=${encodeURIComponent(term)}&per_page=20`,
        {
          headers: {
            Authorization: `${pexelsApiKey}`,
          },
        }
      );

      const formattedVideos = (res.videos || []).map((v) => {
        const files = v.video_files || [];
        // Prefer hd, fall back to sd, then any file with a link
        const pick =
          files.find((f) => f.link && f.quality === "hd") ||
          files.find((f) => f.link && f.quality === "sd") ||
          files.find((f) => f.link);
        return {
          url: v.url,
          image: v.image,
          videoUrl: pick,
        } as VideoResultFormat;
      });

      // Dedupe against existing results (same term can overlap previous ones)
      const existing = new Set(searchResults.value.map((r) => r.url));
      const fresh = formattedVideos.filter((r) => !existing.has(r.url));
      searchResults.value = [...searchResults.value, ...fresh];
      searchedTerms.value.push(term);
    } catch (e: any) {
      const status = e?.status || e?.response?.status;
      if (status === 429) {
        searchError.value = "Pexels rate limit hit — wait a moment and retry the remaining terms";
      } else if (status === 401 || status === 403) {
        searchError.value = "Pexels API key missing or invalid (set PEXELS_API_KEY)";
      } else {
        searchError.value = `Search failed for "${term}": ${e?.message || "unknown error"}`;
      }
      // Stop the loop on auth/rate-limit errors; continue on single-term failures otherwise
      if (status === 429 || status === 401 || status === 403) break;
    }
  }

  searching.value = false;
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
        <n-input v-model:value="video.search" placeholder="Search terms (comma separated)" @keyup.enter="HandleSearch" />
        <n-button type="success" ghost :loading="searching" @click="HandleSearch"> Search </n-button>
      </n-input-group>
      <p v-if="searchError" class="text-xs text-red-400 mt-2">{{ searchError }}</p>
      <p class="text-xs opacity-50 mt-2">
        {{ searchResults.length }} results · {{ searchedTerms.length }} terms searched · new terms are appended (existing results kept)
      </p>
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
