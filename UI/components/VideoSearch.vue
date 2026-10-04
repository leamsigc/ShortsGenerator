<script lang="ts" setup>
/**
 *
 * Component to preview and select videos base on the user related search terms
 *
 * Search goes through the backend proxy (`GET /api/stock/videos`) so the
 * browser never needs the Pexels key — the backend reads PEXELS_API_KEY
 * from the repo-root `.env`. Direct Pexels calls are kept only as a
 * fallback when the backend is unreachable AND a frontend key exists
 * (Nuxt only auto-loads `UI/.env`, not the root `.env`, which is why the
 * old direct-only search 401'd even with the root `.env` set).
 *
 * @author Ismael García <leamsigc@leamsigc.com>
 * @version 0.0.3
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

interface StockItem {
  id: number | string;
  url: string;
  thumbnail: string;
  duration?: number;
  user?: string;
  width?: number;
  height?: number;
}

const { video } = useVideoSettings();

const searchResults = ref<VideoResultFormat[]>([]);
const searching = ref(false);
const searchError = ref<string | null>(null);
const searchedTerms = ref<string[]>([]);

const $URL_SEARCH = `https://api.pexels.com/videos/search`;

const apiBase = (): string => {
  try {
    return useApiSettings().API_SETTINGS.value.URL?.replace(/\/+$/, "") || "http://localhost:8080";
  } catch {
    return "http://localhost:8080";
  }
};

const {
  public: { pexelsApiKey },
} = useRuntimeConfig();

const searchViaBackend = async (term: string): Promise<VideoResultFormat[]> => {
  const res = await $fetch<{ status: string; data: StockItem[]; message?: string }>(
    `${apiBase()}/api/stock/videos`,
    { query: { query: term, per_page: 20 } }
  );
  if (res.status !== "success") {
    throw new Error(res.message || "Backend stock search failed");
  }
  return (res.data || [])
    .filter((item) => item?.url)
    .map((item) => ({
      // Backend proxy has no Pexels page URL — the file link is unique per clip.
      url: item.url,
      image: item.thumbnail || "",
      videoUrl: { fileType: "mp4", link: item.url, quality: "hd" },
    } as VideoResultFormat));
};

const searchViaPexelsDirect = async (term: string): Promise<VideoResultFormat[]> => {
  const res = await $fetch<{ videos: VideoResult[] }>(
    `${$URL_SEARCH}?query=${encodeURIComponent(term)}&per_page=20`,
    {
      headers: {
        Authorization: `${pexelsApiKey}`,
      },
    }
  );

  return (res.videos || []).map((v) => {
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
};

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
      // Primary path: backend proxy (uses server-side PEXELS_API_KEY).
      let formattedVideos: VideoResultFormat[];
      try {
        formattedVideos = await searchViaBackend(term);
      } catch (backendErr: any) {
        const backendMsg = backendErr?.data?.message || backendErr?.message || "";
        // Backend explicitly says the key is missing server-side — surface that,
        // don't silently fall back to a direct call that will 401 too.
        if (/PEXELS_API_KEY not configured/i.test(backendMsg)) {
          throw new Error(
            "Backend PEXELS_API_KEY is not set — add it to the repo-root .env and restart the Flask backend on :8080."
          );
        }
        // Backend unreachable? Fall back to direct Pexels only if a frontend key exists.
        if (pexelsApiKey) {
          formattedVideos = await searchViaPexelsDirect(term);
        } else {
          throw new Error(
            `Backend stock search failed (${backendMsg || "is the Flask backend running on ${apiBase()}?"}) — ` +
            "no frontend Pexels key either (Nuxt only reads UI/.env, not the root .env)."
          );
        }
      }

      // Dedupe against existing results (same term can overlap previous ones)
      const existing = new Set(searchResults.value.map((r) => r.url));
      const fresh = formattedVideos.filter((r) => r?.url && !existing.has(r.url));
      searchResults.value = [...searchResults.value, ...fresh];
      searchedTerms.value.push(term);
    } catch (e: any) {
      const status = e?.status || e?.response?.status;
      if (status === 429) {
        searchError.value = "Pexels rate limit hit — wait a moment and retry the remaining terms";
      } else if (status === 401 || status === 403) {
        searchError.value =
          "Pexels API key rejected (401/403). The app now searches via the backend — " +
          "make sure PEXELS_API_KEY is set in the repo-root .env and the backend on :8080 was restarted after adding it. " +
          "(The old direct-browser search needed the key duplicated into UI/.env.)";
      } else {
        searchError.value = `Search failed for "${term}": ${e?.data?.message || e?.message || "unknown error"}`;
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
