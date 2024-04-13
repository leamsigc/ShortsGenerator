<script lang="ts" setup>
/**
 *
 * Generate view
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */
const router = useRouter();
const API_URL = "http://localhost:8080";

const { globalSettings } = useGlobalSettings();
const { video } = useVideoSettings();
console.log(video.value);

const showModal = ref(!video.value.script);
const extraPrompt = ref(false);

const currentState = ref<"script" | "loading" | "Error">("script");

const HandleGenerateScript = async () => {
  try {
    currentState.value = "loading";
    showModal.value = false;
    const { data } = await $fetch<{
      data: { script: string; search: string[] };
    }>(`${API_URL}/api/script`, {
      method: "POST",
      body: {
        videoSubject: video.value.videoSubject,
        aiModel: globalSettings.value.aiModel,
        extraPrompt: video.value.extraPrompt,
      },
    });

    video.value.script = data.script;
    console.log({ data });

    video.value.search = data.search.join(",");
    currentState.value = "script";
  } catch (error) {
    console.log({ error });
    currentState.value = "Error";
  }
};

const HandleGenerateVideo = async () => {
  try {
    currentState.value = "loading";
    showModal.value = false;
    const { data } = await $fetch<{
      data: {
        finalAudio: string;
        subtitles: string;
        finalVideo: string;
      };
    }>(`${API_URL}/api/search-and-download`, {
      method: "POST",
      body: {
        script: video.value.script,
        voice: video.value.voice || globalSettings.value.voice,
        search: video.value.search.split(","),
        aiModel: video.value.aiModel || globalSettings.value.aiModel,
        selectedVideoUrls: video.value.selectedVideoUrls,
      },
    });
    video.value.finalVideoUrl = data.finalVideo;
    currentState.value = "script";
  } catch (error) {
    console.log({ error });
    currentState.value = "Error";
  }
};

const settingsModal = ref<"ALL" | "VOICE" | "SUBTITLE" | "MUSIC" | "IDLE">(
  "IDLE"
);
const settingsModalState = computed(() => {
  return settingsModal.value !== "IDLE";
});
const HandleUpdateSettings = async (
  type: "ALL" | "VOICE" | "SUBTITLE" | "MUSIC"
) => {
  settingsModal.value = type;
};

const HandleAddAudio = async () => {
  try {
    currentState.value = "loading";
    const { data } = await $fetch<{ data: { finalVideo: string } }>(
      `${API_URL}/api/addAudio`,
      {
        method: "POST",
        body: {
          finalVideo: video.value.finalVideoUrl,
          songPath: video.value.selectedAudio,
          aiModel: video.value.aiModel || globalSettings.value.aiModel,
        },
      }
    );
    video.value.finalVideoUrl = data.finalVideo;
  } catch (error) {
    console.log({ error });
  } finally {
    currentState.value = "script";
  }
};

const HandleClearAndGoToVideos = () => {
  video.value = {
    finalVideoUrl: "",
    selectedAudio: "",
    script: "",
    search: "",
    voice: "",
    aiModel: "",
    extraPrompt: "",
    videoSubject: "",
    selectedVideoUrls: [],
  };
  settingsModal.value = "IDLE";
  showModal.value = true;
  router.push("/videos");
};

const SearchModal = ref(false);
const HandleOpenSearchVideo = () => {
  SearchModal.value = !SearchModal.value;
};
</script>

<template>
  <n-modal v-model:show="showModal" :mask-closable="false">
    <div
      class="bg-slate-100 dark:bg-gray-950 p-10 py-16 dark:text-slate-100 rounded-2xl min-w-2xl"
    >
      <h1 class="text-3xl font-extrabold">
        {{ $t("video.generate.step.one.title") }}
      </h1>

      <n-form-item :show-label="false" class="mt-10">
        <n-input
          v-model:value="video.videoSubject"
          :placeholder="$t('video.generate.step.one.videoSubject.placeholder')"
          type="textarea"
          show-count
          clearable
          :autosize="{
            minRows: 10,
            maxRows: 20,
          }"
          class="p-5 h-full dark:bg-slate-800 bg-slate-100 rounded-xl border-none"
        />
      </n-form-item>
      <n-form-item label="Extra Prompt:">
        <div class="w-full">
          <n-switch v-model:value="extraPrompt"> </n-switch>
          <n-collapse-transition :show="extraPrompt">
            <n-form-item :show-label="false" class="mt-10">
              <n-input
                v-model:value="video.extraPrompt"
                :placeholder="
                  $t('video.generate.step.one.extraPrompt.placeholder')
                "
                type="textarea"
                show-count
                clearable
                :autosize="{
                  minRows: 5,
                  maxRows: 8,
                }"
                class="p-5 w-full dark:bg-slate-800 bg-slate-100 rounded-xl border-none"
              />
            </n-form-item>
          </n-collapse-transition>
        </div>
      </n-form-item>

      <section class="flex justify-end gap-5">
        <n-button type="tertiary" @click="$router.push('/videos')" size="large">
          {{ $t("video.generate.step.one.cancel") }}
        </n-button>
        <n-button type="success" @click="HandleGenerateScript" size="large">
          {{ $t("video.generate.step.one.generate") }}
        </n-button>
      </section>
    </div>
  </n-modal>
  <n-spin :show="currentState === 'loading'">
    <div>
      <main class="grid grid-cols-5 gap-5 pr-10 relative">
        <!-- Header -->
        <section class="grid grid-cols-2 gap-10 col-span-3">
          <section class="input col-span-2 rounded-lg min-h-96">
            <n-form-item :show-label="false" path="script">
              <n-input
                v-model:value="video.script"
                :placeholder="$t('video.generate.step.two.script.placeholder')"
                type="textarea"
                show-count
                clearable
                :autosize="{
                  minRows: 18,
                  maxRows: 25,
                }"
                class="p-5 h-full dark:bg-slate-800 bg-slate-100 rounded-xl border-none"
              />
            </n-form-item>
          </section>
          <section
            class="setting dark:bg-slate-800 bg-slate-100 rounded-lg min-h-40 p-5"
          >
            <header class="flex items-center">
              <Icon name="material-symbols:settings" size="24" />
              <span class="text-lg ml-2">
                {{ $t("view.generate.setting.label") }}
              </span>
              <div class="ml-auto">
                <n-button ghost text @click="HandleUpdateSettings('ALL')">
                  <template #icon>
                    <Icon name="pepicons:dots-x" />
                  </template>
                </n-button>
              </div>
            </header>
            <article class="mt-5 opacity-60 flex flex-col">
              <span class="font-bold"> Search:</span>
              <span class="text-sm mt-2 truncate"> {{ video.search }}</span>
            </article>
            <n-button
              ghost
              type="primary"
              class="mt-5"
              @click="HandleOpenSearchVideo"
            >
              Search and select videos
            </n-button>
          </section>
          <section
            class="voice dark:bg-slate-800 bg-slate-100 rounded-lg min-h-40 p-5"
          >
            <header class="flex items-center">
              <Icon name="icon-park-outline:voice" size="24" />
              <span class="text-lg ml-2">
                {{ $t("view.generate.voice.label") }}
              </span>
              <div class="ml-auto">
                <n-button ghost text @click="HandleUpdateSettings('VOICE')">
                  <template #icon>
                    <Icon name="pepicons:dots-x" />
                  </template>
                </n-button>
              </div>
            </header>
            <article
              class="mt-8 opacity-80 text-center flex items-center justify-center"
            >
              <Icon name="material-symbols:person" size="36" />
              <span class="ml-2 font-black text-lg">
                {{ video.voice || globalSettings.voice }}
              </span>
            </article>
          </section>
          <section
            class="music dark:bg-slate-800 bg-slate-100 rounded-lg min-h-40 p-5"
          >
            <header class="flex items-center">
              <Icon name="icon-park-outline:music" size="24" />
              <span class="text-lg ml-2">
                {{ $t("view.generate.music.label") }}
              </span>
              <div class="ml-auto">
                <n-button ghost text @click="HandleUpdateSettings('MUSIC')">
                  <template #icon>
                    <Icon name="pepicons:dots-x" />
                  </template>
                </n-button>
              </div>
            </header>
            <article class="mt-8 opacity-80 flex items-center">
              <section class="w-10 h-10 bg-slate-950 rounded-md"></section>
              <section class="ml-2 flex flex-col text-sm">
                <span>{{ video.selectedAudio || "No music selected" }}</span>
                <span class="opacity-60">Sombreros Musical</span>
              </section>
            </article>
          </section>
          <section
            class="subtitle dark:bg-slate-800 bg-slate-100 rounded-lg min-h-40 p-5"
          >
            <header class="flex items-center">
              <Icon name="material-symbols:subtitles" size="26" />
              <span class="text-lg ml-2">
                {{ $t("view.generate.subtitles.label") }}
              </span>
              <div class="ml-auto">
                <n-button ghost text @click="HandleUpdateSettings('SUBTITLE')">
                  <template #icon>
                    <Icon name="ph:dots-nine-thin" />
                  </template>
                </n-button>
              </div>
            </header>
            <article
              class="mt-8 opacity-80 text-center flex items-center justify-center"
            >
              <span
                class="font-black text-lg"
                :style="{ color: globalSettings.color }"
              >
                Subtitle here
              </span>
            </article>
          </section>
        </section>
        <section class="col-span-2">
          <header
            class="col-span-5 flex justify-end gap-4 mb-5"
            v-if="video.finalVideoUrl"
          >
            <n-button
              type="tertiary"
              dashed
              size="large"
              @click="HandleGenerateVideo"
              >Regenerate</n-button
            >
            <n-button
              type="success"
              dashed
              size="large"
              @click="HandleAddAudio"
              :disabled="!video.selectedAudio"
            >
              Add Music
            </n-button>
            <n-button
              type="default"
              dashed
              size="large"
              @click="HandleClearAndGoToVideos"
            >
              Videos
            </n-button>
          </header>
          <section class="grid place-content-center">
            <div
              class="phone bg-slate-700 bg-opacity-10 p-1 rounded-3xl shadow"
            >
              <section
                v-if="!video.finalVideoUrl"
                class="aspect-[9/16] max-w-sm rounded-3xl w-full h-[750px] px-10 grid place-content-center"
              >
                <n-button
                  round
                  type="success"
                  size="large"
                  @click="HandleGenerateVideo"
                >
                  <span class="text-lg px-10"> Generate </span>
                </n-button>
              </section>
              <!-- Video placeholder -->
              <video
                v-else
                class="aspect-[9/16] max-w-sm rounded-3xl"
                :src="`http://localhost:8080/${video.finalVideoUrl}`"
                controls
              ></video>
            </div>
          </section>
        </section>
        <section class="col-span-5">Footer</section>
      </main>
    </div>
    <template #description>
      <p>Generating video | script ...</p>
    </template>
  </n-spin>

  <n-modal
    v-model:show="settingsModalState"
    :mask-closable="false"
    closable
    @close="settingsModal = 'IDLE'"
    preset="card"
    class="max-w-3xl"
    :content-class="'dark:bg-gray-950 p-10 py-16 dark:text-slate-100'"
    :header-class="'dark:bg-gray-950 p-10 py-16 dark:text-slate-100'"
  >
    <div class="p-10" v-if="settingsModal !== 'IDLE'">
      <GenerateScript :active-tab="settingsModal" />
    </div>
  </n-modal>

  <n-modal
    v-model:show="SearchModal"
    :mask-closable="false"
    closable
    @close="SearchModal = false"
    preset="card"
    class="max-w-3xl"
    :content-class="'dark:bg-gray-950 p-10 py-16 dark:text-slate-100'"
    :header-class="'dark:bg-gray-950 p-10 py-16 dark:text-slate-100'"
  >
    <div class="p-10">
      <n-tabs type="line" animated>
        <n-tab-pane name="VIDEO_SEARCH" tab="Search and select" active>
          <VideoSearch />
        </n-tab-pane>
        <n-tab-pane name="VIDEO_SELECTED" tab="Selected Videos">
          <VideoSelected />
        </n-tab-pane>
      </n-tabs>
    </div>
  </n-modal>
</template>
<style scoped></style>
