<script lang="ts" setup>
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
interface VoiceStyle {
  name: string;
  description: string;
  gender: string;
}
interface LanguageOption {
  code: string;
  label: string;
}
interface QualityPreset {
  value: number;
  label: string;
}
interface AspectRatioOption {
  value: string;
  label: string;
  width: number;
  height: number;
}
interface AspectRatioSettings {
  current: string;
  options: AspectRatioOption[];
}
interface TitleColorOption {
  value: string;
  label: string;
  sample: string;
}
interface TitleColorSettings {
  current: string;
  options: TitleColorOption[];
}
interface FontOption {
  value: string;
  label: string;
}
interface FontOptions {
  current: string;
  options: FontOption[];
}
interface SubtitleTemplateOption {
  value: string;
  label: string;
  description: string;
  color: string;
  stroke_color: string;
  stroke_width: number;
  fontsize: number;
  position: string;
}
interface SubtitleTemplates {
  current: string;
  options: SubtitleTemplateOption[];
}
interface GlobalSettings {
  fontSettings: FontSettings;
  scriptSettings: ScriptSettings;
  ttsSettings: TTSSettings;
  aspectRatioSettings: AspectRatioSettings;
  titleColorSettings: TitleColorSettings;
  fontOptions: FontOptions;
  subtitleTemplates: SubtitleTemplates;
}
interface TTSSettings {
  preferred_tts: "supertonic" | "tiktok";
  tts_voice: string;
  tts_lang: string;
  tts_quality: number;
  tts_speed: number;
}

import { useStorage } from "@vueuse/core";
import { useClipperStore } from "~/stores/ClipperStore";

interface MagicSyncBusiness {
  id: string
  name: string
  url: string
  apiToken: string
  videoBaseUrl: string
}

const isLoading = ref(false);
const API_URL = "http://localhost:8080";

// MagicSync multi-business config
const magicsyncBusinesses = useStorage<MagicSyncBusiness[]>("MAGICSYNC_BUSINESSES", [])

// Migrate old single-entry config
const oldUrl = useStorage("MAGICSYNC_URL", "")
const oldApiToken = useStorage("MAGICSYNC_API_TOKEN", "")
const oldVideoBaseUrl = useStorage("VIDEO_BASE_URL", "http://localhost:8080")
if (oldUrl.value && oldApiToken.value) {
  const exists = magicsyncBusinesses.value.some(b => b.apiToken === oldApiToken.value)
  if (!exists) {
    magicsyncBusinesses.value.push({
      id: crypto.randomUUID(),
      name: "Default Business",
      url: oldUrl.value,
      apiToken: oldApiToken.value,
      videoBaseUrl: oldVideoBaseUrl.value,
    })
  }
  oldUrl.value = ""
  oldApiToken.value = ""
}

const showBusinessModal = ref(false)
const editingBusiness = ref<MagicSyncBusiness | null>(null)
const businessForm = ref<MagicSyncBusiness>({ id: "", name: "", url: "http://localhost:3000", apiToken: "", videoBaseUrl: "http://localhost:8080" })
const testingBizId = ref<string | null>(null)
const testResults = ref<Record<string, { connected: boolean; accounts: any[]; error: string }>>({})

function openAddBusiness() {
  editingBusiness.value = null
  businessForm.value = { id: crypto.randomUUID(), name: "", url: "http://localhost:3000", apiToken: "", videoBaseUrl: "http://localhost:8080" }
  showBusinessModal.value = true
}

function openEditBusiness(biz: MagicSyncBusiness) {
  editingBusiness.value = biz
  businessForm.value = { ...biz }
  showBusinessModal.value = true
}

function saveBusiness() {
  if (!businessForm.value.name || !businessForm.value.apiToken) return
  if (editingBusiness.value) {
    const idx = magicsyncBusinesses.value.findIndex(b => b.id === editingBusiness.value!.id)
    if (idx >= 0) magicsyncBusinesses.value[idx] = { ...businessForm.value }
  } else {
    magicsyncBusinesses.value.push({ ...businessForm.value })
  }
  showBusinessModal.value = false
}

function deleteBusiness(id: string) {
  magicsyncBusinesses.value = magicsyncBusinesses.value.filter(b => b.id !== id)
  delete testResults.value[id]
}

async function testBusinessConnection(biz: MagicSyncBusiness) {
  testingBizId.value = biz.id
  testResults.value[biz.id] = { connected: false, accounts: [], error: "" }
  try {
    const res = await $fetch<{ status: string; data: { accounts: any[] }; message?: string }>(
      `${API_URL}/api/magicsync/accounts`,
      { method: "POST", body: { url: biz.url, apiToken: biz.apiToken } }
    )
    if (res.status === "success") {
      testResults.value[biz.id] = { connected: true, accounts: res.data.accounts, error: "" }
    } else {
      testResults.value[biz.id] = { connected: false, accounts: [], error: res.message || "Connection failed" }
    }
  } catch (e: any) {
    testResults.value[biz.id] = { connected: false, accounts: [], error: e?.data?.message || e?.message || "Connection failed" }
  } finally {
    testingBizId.value = null
  }
}

const voiceOptions = ref<{ label: string; value: string; description?: string }[]>([]);
const voicesLoading = ref(false);
const voiceStyles = ref<Record<string, VoiceStyle>>({});
const languageOptions = ref<LanguageOption[]>([]);
const qualityPresets = ref<QualityPreset[]>([]);

const { globalSettings } = useGlobalSettings();

const ttsEngineOptions = [
  { label: "Supertonic TTS (Local)", value: "supertonic" },
  { label: "TikTok TTS (Cloud)", value: "tiktok" },
];

const ttsStatus = ref<{ supertonic: string; tiktok: string }>({
  supertonic: "unavailable",
  tiktok: "available",
});

const aiModelOptions = [
  { label: "FREE", value: "g4f" },
  { label: "GPT 4", value: "gpt4" },
  { label: "GPT 3.5 Turbo", value: "gpt3.5-turbo" },
];

const settingsRule = {
  font: { required: true, trigger: ["input", "blur"] },
  fontColor: { required: true, trigger: ["input", "blur"] },
  subtitlePosition: { required: true, trigger: ["input", "blur"] },
  aiModel: { required: true, trigger: ["change", "blur"] },
};

const subtitlePositionOptions = [
  "center,top", "center,bottom", "center,center",
  "left,center", "left,bottom", "right,center", "right,bottom",
];

const selectedVoice = ref("");
const selectedLang = ref("en");
const selectedQuality = ref(8);
const selectedSpeed = ref(1.05);

async function loadVoices(engine: string) {
  voicesLoading.value = true;
  try {
    const res = await $fetch<{
      data: {
        voices: string[];
        voiceStyles?: Record<string, VoiceStyle>;
        languages?: LanguageOption[];
        qualityPresets?: QualityPreset[];
      };
    }>(`${API_URL}/api/tts/voices?engine=${engine}`);
    const data = res.data;
    if (data.voiceStyles) {
      voiceStyles.value = data.voiceStyles;
      voiceOptions.value = data.voices.map((v) => ({
        label: `${v} - ${data.voiceStyles?.[v]?.name || v} (${data.voiceStyles?.[v]?.gender || ""})`,
        value: v,
        description: data.voiceStyles?.[v]?.description,
      }));
    } else {
      voiceOptions.value = data.voices.map((v) => ({ label: v, value: v }));
    }
    if (data.languages) languageOptions.value = data.languages;
    if (data.qualityPresets) qualityPresets.value = data.qualityPresets;
  } catch (error) {
    console.error("Failed to load voices:", error);
  } finally {
    voicesLoading.value = false;
  }
}

async function loadTtsStatus() {
  try {
    const { data } = await $fetch<{
      data: { supertonic: string; tiktok: string };
    }>(`${API_URL}/api/tts/status`);
    ttsStatus.value = data;
  } catch (error) {
    console.error("Failed to load TTS status:", error);
  }
}

let mainSettings: GlobalSettings | undefined;
let settingsLoadError: string | null = null;
try {
  const res = await $fetch<{ data: GlobalSettings }>(`${API_URL}/api/settings`);
  mainSettings = res.data;
} catch (e: any) {
  settingsLoadError = e?.message || "Backend unreachable";
  console.error("Failed to load settings (is the backend running on " + API_URL + "?):", e);
}

if (mainSettings?.fontSettings) {
  globalSettings.value.font = mainSettings.fontSettings.font;
  globalSettings.value.color = mainSettings.fontSettings.color;
  globalSettings.value.fontsize = mainSettings.fontSettings.fontsize;
  globalSettings.value.stroke_color = mainSettings.fontSettings.stroke_color;
  globalSettings.value.stroke_width = mainSettings.fontSettings.stroke_width;
  globalSettings.value.subtitles_position = mainSettings.fontSettings.subtitles_position;
}

const ttsEngine = ref(mainSettings?.ttsSettings?.preferred_tts || "supertonic");
selectedVoice.value = mainSettings?.ttsSettings?.tts_voice || "M3";
selectedLang.value = mainSettings?.ttsSettings?.tts_lang || "en";
selectedQuality.value = mainSettings?.ttsSettings?.tts_quality || 8;
selectedSpeed.value = mainSettings?.ttsSettings?.tts_speed || 1.05;

const aspectRatio = ref(mainSettings?.aspectRatioSettings?.current || "9:16");
const aspectRatioOptions = ref(mainSettings?.aspectRatioSettings?.options || []);
const titleColor = ref(mainSettings?.titleColorSettings?.current || "#FFFF00");
const titleColorOptions = ref(mainSettings?.titleColorSettings?.options || []);
const selectedFont = ref(mainSettings?.fontOptions?.current || "bold_font.ttf");
const fontOptionsList = ref(mainSettings?.fontOptions?.options || []);
const subtitleTemplate = ref(mainSettings?.subtitleTemplates?.current || "classic");
const subtitleTemplateOptions = ref(mainSettings?.subtitleTemplates?.options || []);

await loadVoices(ttsEngine.value);
await loadTtsStatus();

// g4f cookie toggle (same backend setting as Clipper → Settings → AI Model Provider)
const clipperStore = useClipperStore();
const g4fUseCookies = ref(true);
const g4fSaving = ref(false);
const g4fSaveError = ref("");
const cookieStatus = ref<{ ok: boolean; reason: string; detail: string; renew_steps: string[] } | null>(null);
const cookieChecking = ref(false);
async function checkCookies() {
  cookieChecking.value = true;
  try {
    cookieStatus.value = await clipperStore.fetchG4fCookieStatus();
  } catch (e) {
    console.error("Failed to check cookie status:", e);
  } finally {
    cookieChecking.value = false;
  }
}
try {
  const llmData = await clipperStore.fetchLlmSettings();
  if (llmData) {
    g4fUseCookies.value = llmData.settings.g4f_use_cookies !== false;
    if (g4fUseCookies.value) checkCookies();
  }
} catch (e) {
  console.error("Failed to load LLM settings:", e);
}

async function onG4fCookiesChange(value: boolean) {
  const previous = g4fUseCookies.value;
  g4fUseCookies.value = value;
  g4fSaving.value = true;
  g4fSaveError.value = "";
  try {
    await clipperStore.updateLlmSettings({ g4f_use_cookies: value });
    if (value) checkCookies();
    else cookieStatus.value = null;
  } catch (e: any) {
    g4fUseCookies.value = previous;
    g4fSaveError.value = e?.data?.message || e?.message || "Could not save — is the backend running?";
    console.error("Failed to save cookie setting:", e);
  } finally {
    g4fSaving.value = false;
  }
}

async function onTtsEngineChange(engine: string) {
  await loadVoices(engine);
  await saveTtsSettings();
}

async function saveTtsSettings() {
  const settings: Record<string, unknown> = {
    preferred_tts: ttsEngine.value,
  };
  if (ttsEngine.value === "supertonic") {
    settings.tts_voice = selectedVoice.value;
    settings.tts_lang = selectedLang.value;
    settings.tts_quality = selectedQuality.value;
    settings.tts_speed = selectedSpeed.value;
  }
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: { type: "TTS", settings },
    });
  } catch (error) {
    console.error("Failed to save TTS settings:", error);
  }
}

async function saveAspectRatio() {
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: { type: "ASPECT", settings: { current: aspectRatio.value } },
    });
  } catch (error) {
    console.error("Failed to save aspect ratio:", error);
  }
}

async function saveFontSettings() {
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: { type: "FONT", settings: { font: `static/assets/fonts/${selectedFont.value}` } },
    });
  } catch (error) {
    console.error("Failed to save font settings:", error);
  }
}

async function saveTitleColor() {
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: { type: "FONT", settings: { color: titleColor.value } },
    });
  } catch (error) {
    console.error("Failed to save title color:", error);
  }
}

async function saveSubtitleTemplate() {
  const template = subtitleTemplateOptions.value.find(t => t.value === subtitleTemplate.value);
  if (!template) return;
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: {
        type: "FONT",
        settings: {
          color: template.color, stroke_color: template.stroke_color,
          stroke_width: template.stroke_width, fontsize: template.fontsize,
          subtitles_position: template.position,
        },
      },
    });
  } catch (error) {
    console.error("Failed to save subtitle template:", error);
  }
}

const HandleSaveSettings = async () => {};
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-[30px] font-bold leading-tight text-clipper-ink dark:text-white tracking-tight">Global Settings</h1>
      <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">Configure TTS, fonts, subtitles and integrations</p>
    </div>

    <div v-if="settingsLoadError" class="max-w-screen-md w-full bg-white dark:bg-neutral-800 border border-clipper-ink/12 dark:border-white/10 rounded-lg p-4">
      <p class="text-sm font-semibold text-clipper-ink dark:text-white">Backend unreachable ({{ API_URL }})</p>
      <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-1">
        Settings could not be loaded — start the backend (Flask on port 8080), then reload this page. Showing defaults meanwhile.
      </p>
    </div>

    <n-form
      ref="formRef"
      class="max-w-screen-md w-full"
      :model="globalSettings"
      :rules="settingsRule"
      size="large"
      :disabled="isLoading"
    >
      <n-form-item label="AI Model:" path="aiModel">
        <n-select v-model:value="globalSettings.aiModel" :options="aiModelOptions" class="w-full md:w-auto" />
      </n-form-item>

      <div v-if="globalSettings.aiModel === 'g4f'" class="max-w-screen-md w-full bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 p-4 rounded-xl mb-4">
        <n-checkbox
          :checked="g4fUseCookies"
          :disabled="g4fSaving"
          @update:checked="onG4fCookiesChange"
        >
          <span class="text-sm font-medium text-clipper-ink dark:text-white">Use browser cookies</span>
        </n-checkbox>
        <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-1 ml-6">
          g4f reads your Firefox Google cookies for Gemini. Turn OFF to use cookie-free
          providers instead — no login, no API key. {{ g4fSaving ? "Saving…" : "" }}
        </p>
        <div v-if="cookieChecking" class="text-xs text-clipper-ink/60 dark:text-white/60 mt-2 ml-6">Checking browser cookies…</div>
        <div v-else-if="cookieStatus && !cookieStatus.ok" class="mt-2 ml-6 rounded-lg border border-red-500/40 bg-red-500/10 p-3">
          <p class="text-xs font-semibold text-red-500">Browser cookies are outdated</p>
          <p class="text-xs text-clipper-ink/70 dark:text-white/70 mt-1">{{ cookieStatus.detail }}</p>
          <ol class="text-xs text-clipper-ink/70 dark:text-white/70 list-decimal ml-4 mt-2 space-y-1">
            <li v-for="(step, i) in cookieStatus.renew_steps" :key="i">{{ step }}</li>
          </ol>
          <button class="mt-2 text-xs font-medium underline" @click="checkCookies()">Check again</button>
        </div>
        <p v-else-if="cookieStatus && cookieStatus.ok" class="text-xs text-green-600 dark:text-green-400 mt-2 ml-6">
          Cookies look fresh — {{ cookieStatus.detail }}
        </p>
        <p v-if="g4fSaveError" class="text-xs text-red-500 mt-1 ml-6">{{ g4fSaveError }}</p>
      </div>

      <n-divider>TTS Settings</n-divider>

      <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 p-5 rounded-xl mb-4">
        <n-form-item label="TTS Engine:" path="ttsEngine">
          <div class="flex items-center gap-3 w-full">
            <n-select v-model:value="ttsEngine" :options="ttsEngineOptions" class="flex-1" @update:value="onTtsEngineChange" />
            <n-tag :type="ttsStatus.supertonic === 'healthy' ? 'success' : 'warning'" size="small">
              {{ ttsStatus.supertonic === 'healthy' ? "Supertonic OK" : "Supertonic Down" }}
            </n-tag>
          </div>
        </n-form-item>

        <template v-if="ttsEngine === 'supertonic'">
          <n-form-item label="Voice Style:" path="supertonicVoice">
            <n-select
              v-model:value="selectedVoice"
              :options="voiceOptions"
              :loading="voicesLoading"
              class="w-full"
              @update:value="saveTtsSettings"
            />
          </n-form-item>

          <div v-if="selectedVoice && voiceStyles[selectedVoice]" class="text-xs text-gray-500 dark:text-gray-400 -mt-3 mb-3 px-1">
            {{ voiceStyles[selectedVoice]?.description }}
          </div>

          <n-form-item label="Language:" path="supertonicLang">
            <n-select
              v-model:value="selectedLang"
              :options="languageOptions.map(l => ({ label: l.label, value: l.code }))"
              class="w-full"
              @update:value="saveTtsSettings"
            />
          </n-form-item>

          <n-form-item label="Quality:" path="supertonicQuality">
            <n-slider
              v-model:value="selectedQuality"
              :min="5"
              :max="12"
              :step="1"
              :marks="{
                5: 'Fast',
                8: 'Standard',
                12: 'Best'
              }"
              class="w-full"
              @update:value="saveTtsSettings"
            />
            <div class="text-xs text-gray-500 mt-1">
              {{ qualityPresets.find(q => q.value === selectedQuality)?.label || `${selectedQuality} steps` }}
            </div>
          </n-form-item>

          <n-form-item label="Speed:" path="supertonicSpeed">
            <n-slider
              v-model:value="selectedSpeed"
              :min="0.7"
              :max="2.0"
              :step="0.05"
              :marks="{
                0.7: 'Slow',
                1.0: 'Normal',
                1.5: 'Fast',
                2.0: 'Max'
              }"
              class="w-full"
              @update:value="saveTtsSettings"
            />
            <div class="text-xs text-gray-500 mt-1">
              {{ selectedSpeed.toFixed(2) }}x speed
            </div>
          </n-form-item>
        </template>

        <template v-else>
          <n-form-item label="Voice:" path="voice">
            <n-select
              v-model:value="globalSettings.voice"
              :options="voiceOptions"
              :loading="voicesLoading"
              class="w-full md:w-auto"
            />
          </n-form-item>
        </template>
      </div>

      <n-divider />

      <n-form-item label="Font:" path="font">
        <n-input v-model:value="globalSettings.font" placeholder="Font for the subtitle" show-count clearable class="w-full" />
      </n-form-item>
      <n-form-item label="Color(#18A058)" path="fontcolor">
        <n-color-picker v-model:value="globalSettings.color" :show-alpha="false" class="w-full md:w-auto" />
      </n-form-item>
      <n-form-item label="Subtitle position:" path="subtitlePosition">
        <n-radio-group v-model:value="globalSettings.subtitles_position" name="subtitlePosition" size="medium" class="flex flex-wrap gap-2">
          <n-radio-button v-for="position in subtitlePositionOptions" :key="position" :value="position">
            <span class="capitalize">{{ position }}</span>
          </n-radio-button>
        </n-radio-group>
      </n-form-item>
      <n-form-item label="Font size:">
        <n-input-number v-model:value="globalSettings.fontsize" placeholder="Font for the subtitle" class="w-full" />
      </n-form-item>

      <n-form-item label="Stroke color(#18A058)">
        <n-color-picker v-model:value="globalSettings.stroke_color" class="w-full md:w-auto" />
      </n-form-item>
      <n-form-item label="Stroke width:">
        <n-input-number v-model:value="globalSettings.stroke_width" placeholder="Font for the subtitle" class="w-full" />
      </n-form-item>

      <n-divider>Video Settings</n-divider>

      <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 p-5 rounded-xl mb-4">
        <n-form-item label="Aspect Ratio:">
          <n-select v-model:value="aspectRatio" :options="aspectRatioOptions.map(o => ({ label: o.label, value: o.value }))" class="w-full" @update:value="saveAspectRatio" />
        </n-form-item>
      </div>

      <n-divider>Subtitle Templates</n-divider>

      <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 p-5 rounded-xl mb-4">
        <n-form-item label="Template:">
          <n-select v-model:value="subtitleTemplate" :options="subtitleTemplateOptions.map(t => ({ label: t.label, value: t.value, description: t.description }))" class="w-full" @update:value="saveSubtitleTemplate" />
        </n-form-item>
        <div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {{ subtitleTemplateOptions.find(t => t.value === subtitleTemplate)?.description }}
        </div>
      </div>

      <n-divider>Title Color & Font</n-divider>

      <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 p-5 rounded-xl mb-4">
        <n-form-item label="Title Color:">
          <div class="flex flex-wrap gap-2">
            <n-button
              v-for="color in titleColorOptions" :key="color.value" size="small"
              :type="titleColor === color.value ? 'primary' : 'default'"
              :style="{ backgroundColor: color.value, borderColor: titleColor === color.value ? '#fff' : color.value }"
              @click="titleColor = color.value; saveTitleColor()"
            >
              <span :style="{ color: color.value === '#000000' ? '#fff' : color.value }">★</span>
            </n-button>
          </div>
        </n-form-item>

        <n-form-item label="Font:">
          <n-select v-model:value="selectedFont" :options="fontOptionsList.map(f => ({ label: f.label, value: f.value }))" class="w-full" @update:value="saveFontSettings" />
        </n-form-item>
      </div>

      <n-divider>MagicSync Integration</n-divider>

      <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 p-5 rounded-xl mb-4">
        <p class="text-sm text-clipper-ink/60 dark:text-white/60 mb-4">
          Add API keys for each business you want to schedule videos to via MagicSync.
        </p>

        <div v-if="magicsyncBusinesses.length === 0" class="text-sm text-clipper-ink/35 dark:text-white/40 border border-dashed border-clipper-ink/12 dark:border-white/10 rounded-lg p-3 mb-4">
          No businesses configured yet. Add one to start scheduling videos.
        </div>

        <div v-for="biz in magicsyncBusinesses" :key="biz.id" class="bg-white dark:bg-neutral-800 rounded-lg p-4 mb-3 border border-clipper-ink/08 dark:border-white/08">
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1 min-w-0">
              <h4 class="font-semibold text-sm text-clipper-ink dark:text-white">{{ biz.name }}</h4>
              <p class="text-xs text-clipper-ink/60 dark:text-white/60 truncate">URL: {{ biz.url }}</p>
              <p class="text-xs text-clipper-ink/60 dark:text-white/60 truncate">Base URL: {{ biz.videoBaseUrl }}</p>
              <p class="text-xs text-clipper-ink/35 dark:text-white/40 truncate">Token: {{ biz.apiToken ? '••••••••' : 'Not set' }}</p>
            </div>
            <div class="flex items-center gap-1 shrink-0 ml-2">
              <n-button size="tiny" quaternary @click="openEditBusiness(biz)">
                <template #icon><Icon name="mdi:pencil" /></template>
              </n-button>
              <n-button size="tiny" quaternary @click="deleteBusiness(biz.id)">
                <template #icon><Icon name="mdi:delete" /></template>
              </n-button>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <n-button
              size="tiny"
              :loading="testingBizId === biz.id"
              @click="testBusinessConnection(biz)"
            >
              <template #icon><Icon name="mdi:connection" /></template>
              Test Connection
            </n-button>

            <div v-if="testResults[biz.id]" class="text-xs">
              <div v-if="testResults[biz.id].connected" class="text-clipper-ink dark:text-white">
                <span class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-clipper-green inline-block"></span> Connected — {{ testResults[biz.id].accounts.length }} account(s)</span>
                <div v-if="testResults[biz.id].accounts.length > 0" class="mt-1 space-y-0.5">
                  <div v-for="acc in testResults[biz.id].accounts" :key="acc.platform + acc.accountName" class="flex items-center gap-1 text-clipper-ink/70 dark:text-white/70">
                    <Icon name="ph:check-circle" class="text-clipper-green text-xs" />
                    <span>{{ acc.platform }} — {{ acc.accountName }}</span>
                    <span v-if="!acc.isActive" class="text-[11px] px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08">inactive</span>
                  </div>
                </div>
              </div>
              <div v-else class="text-clipper-ink/60 dark:text-white/60">{{ testResults[biz.id].error }}</div>
            </div>
          </div>
        </div>

        <n-button type="primary" ghost @click="openAddBusiness">
          <template #icon><Icon name="mdi:plus" /></template>
          Add Business
        </n-button>
      </div>

      <n-modal
        v-model:show="showBusinessModal"
        preset="card"
        title="Business Configuration"
        style="max-width: 520px"
        :mask-closable="false"
      >
        <div class="space-y-4">
          <n-form-item label="Business Name:">
            <n-input v-model:value="businessForm.name" placeholder="My Business" class="w-full" />
          </n-form-item>
          <n-form-item label="MagicSync URL:">
            <n-input v-model:value="businessForm.url" placeholder="http://localhost:3000" class="w-full" />
          </n-form-item>
          <n-form-item label="API Token:">
            <n-input
              v-model:value="businessForm.apiToken"
              type="password"
              show-password-on="click"
              placeholder="Enter MagicSync API token"
              class="w-full"
            />
          </n-form-item>
          <n-form-item label="Video Asset Base URL:">
            <n-input v-model:value="businessForm.videoBaseUrl" placeholder="http://localhost:8080" class="w-full" />
            <template #feedback>
              Base URL for video assets served by the Python backend (must be publicly accessible)
            </template>
          </n-form-item>
          <div class="flex gap-3 pt-2 justify-end">
            <n-button @click="showBusinessModal = false">Cancel</n-button>
            <n-button type="primary" @click="saveBusiness" :disabled="!businessForm.name || !businessForm.apiToken">
              Save
            </n-button>
          </div>
        </div>
      </n-modal>

      <n-form-item>
        <button class="h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 disabled:opacity-50" @click="HandleSaveSettings" :disabled="isLoading">
          Save settings
        </button>
      </n-form-item>
    </n-form>
  </div>
</template>
<style scoped></style>