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
  kind?: string;
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
  preferred_tts: "supertonic" | "tiktok" | "qwen3";
  tts_voice: string;
  tts_lang: string;
  tts_quality: number;
  tts_speed: number;
  qwen_mode?: string;
  qwen_speaker?: string;
  qwen_lang?: string;
  qwen_instruct?: string;
  qwen_design_prompt?: string;
  qwen_clone_ref?: string;
  qwen_clone_text?: string;
  qwen_model?: string;
}
interface QwenMode {
  value: string;
  label: string;
  description: string;
}
interface QwenPreset {
  value: string;
  label: string;
}
interface QwenCharacter {
  value: string;
  label: string;
  mode: string;
  language: string;
  design_prompt: string;
  instruct: string;
  description: string;
}

import { useStorage } from "@vueuse/core";
import { useClipperStore } from "~/stores/ClipperStore";
import type { G4fProviderInfo } from "~/stores/ClipperStore";
import type { CustomVoice } from "~/composables/useCustomVoices";

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
  { label: "Qwen3 TTS (Local, Design/Clone)", value: "qwen3" },
];

const ttsStatus = ref<{ supertonic: string; tiktok: string; qwen3: string }>({
  supertonic: "unavailable",
  tiktok: "available",
  qwen3: "unavailable",
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

// Qwen3-TTS state (custom / design / clone)
const qwenModes = ref<QwenMode[]>([]);
const qwenModels = ref<Record<string, string>>({});
const qwenInstructPresets = ref<QwenPreset[]>([]);
const qwenDesignPresets = ref<QwenPreset[]>([]);
const qwenCharacters = ref<QwenCharacter[]>([]);
const qwenMode = ref("custom");
const qwenSpeaker = ref("Ryan");
const qwenLang = ref("English");
const qwenInstruct = ref("");
const qwenDesignPrompt = ref("");
const qwenModel = ref("");
const qwenCloneRef = ref("");
const qwenCloneText = ref("");
const qwenCloning = ref(false);
const qwenCloneError = ref("");
const qwenRefInput = ref<HTMLInputElement | null>(null);
const previewText = ref("Hey! This is my new voice for viral Shorts. Follow for more!");
const previewLoading = ref(false);
const previewUrl = ref("");
const previewError = ref("");

// My voices (IndexedDB, browser-side preset list)
const { list: listCustomVoices, save: saveCustomVoice, remove: removeCustomVoice, toQwenParams } =
  useCustomVoices();
const customVoices = ref<CustomVoice[]>([]);
const customVoiceName = ref("");
const customSaveLoading = ref(false);
const customSaveMsg = ref("");
const customSaveOk = ref(false);

async function loadVoices(engine: string) {
  voicesLoading.value = true;
  try {
    const res = await $fetch<{
      data: {
        voices: string[];
        voiceStyles?: Record<string, VoiceStyle>;
        languages?: LanguageOption[];
        qualityPresets?: QualityPreset[];
        modes?: QwenMode[];
        models?: Record<string, string>;
        presets?: { instructs: QwenPreset[]; designs: QwenPreset[]; characters?: QwenCharacter[] };
      };
    }>(`${API_URL}/api/tts/voices?engine=${engine}`);
    const data = res.data;
    if (data.voiceStyles) {
      voiceStyles.value = data.voiceStyles;
      voiceOptions.value = data.voices.map((v) => ({
        label: `${data.voiceStyles?.[v]?.kind === "character" ? "🐶 " : ""}${v} - ${data.voiceStyles?.[v]?.name || v} (${data.voiceStyles?.[v]?.gender || ""})`,
        value: v,
        description: data.voiceStyles?.[v]?.description,
      }));
    } else {
      voiceOptions.value = data.voices.map((v) => ({ label: v, value: v }));
    }
    if (data.languages) languageOptions.value = data.languages;
    if (data.qualityPresets) qualityPresets.value = data.qualityPresets;
    if (data.modes) qwenModes.value = data.modes;
    if (data.models) qwenModels.value = data.models;
    if (data.presets) {
      qwenInstructPresets.value = data.presets.instructs || [];
      qwenDesignPresets.value = data.presets.designs || [];
      qwenCharacters.value = data.presets.characters || [];
    }
    mergeCustomVoicesIntoOptions(engine);
  } catch (error) {
    console.error("Failed to load voices:", error);
  } finally {
    voicesLoading.value = false;
  }
}

async function loadTtsStatus() {
  try {
    const { data } = await $fetch<{
      data: { supertonic: string; tiktok: string; qwen3: string };
    }>(`${API_URL}/api/tts/status`);
    ttsStatus.value = {
      supertonic: data.supertonic || "unavailable",
      tiktok: data.tiktok || "available",
      qwen3: (data as Record<string, string>).qwen3 || "unavailable",
    };
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
qwenMode.value = mainSettings?.ttsSettings?.qwen_mode || "custom";
qwenSpeaker.value = mainSettings?.ttsSettings?.qwen_speaker || "Ryan";
qwenLang.value = mainSettings?.ttsSettings?.qwen_lang || "English";
qwenInstruct.value = mainSettings?.ttsSettings?.qwen_instruct || "";
qwenDesignPrompt.value = mainSettings?.ttsSettings?.qwen_design_prompt || "";
qwenModel.value = mainSettings?.ttsSettings?.qwen_model || "";
qwenCloneRef.value = mainSettings?.ttsSettings?.qwen_clone_ref || "";
qwenCloneText.value = mainSettings?.ttsSettings?.qwen_clone_text || "";

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
await reloadCustomVoices();

// g4f cookie toggle (same backend setting as Clipper → Settings → AI Model Provider)
const clipperStore = useClipperStore();
const g4fUseCookies = ref(true);
const g4fSaving = ref(false);
const g4fSaveError = ref("");
const cookieStatus = ref<{ ok: boolean; reason: string; detail: string; renew_steps: string[] } | null>(null);
const cookieChecking = ref(false);
// Full AI provider form (canonical home — was in Clipper settings)
const llmProvider = ref("gemini");
const llmProvidersList = ref<string[]>(["gemini", "g4f", "openai", "ollama", "qwen"]);
const llmBaseUrl = ref("");
const llmApiKey = ref("");
const llmMaskedKey = ref("");
const llmModel = ref("");
const llmOutline = ref(true);
const llmSaving = ref(false);
const llmTesting = ref(false);
const llmTestAbort = ref<AbortController | null>(null);
const llmTestResult = ref<{ ok: boolean; detail: string } | null>(null);
const showLlmBaseUrl = computed(() => ["openai", "ollama", "qwen"].includes(llmProvider.value || ""));
// g4f provider + model selection (populated from installed g4f release)
const g4fProvidersList = ref<G4fProviderInfo[]>([]);
const g4fProviderSel = ref("DeepAI");
const g4fModelSel = ref("gemini-2.5-flash-lite");
const g4fModels = computed(() => {
  const entry = g4fProvidersList.value.find(p => p.id === g4fProviderSel.value);
  const models = entry?.models?.length ? entry.models : (g4fModelSel.value ? [g4fModelSel.value] : []);
  if (g4fModelSel.value && !models.includes(g4fModelSel.value)) return [g4fModelSel.value, ...models];
  return models;
});
function onG4fProviderChange(id: string) {
  const entry = g4fProvidersList.value.find(p => p.id === id);
  if (entry && entry.default_model) g4fModelSel.value = entry.default_model;
}

// Backup model: used only when the selected model fails and the toggle is ON
const fallbackEnabled = ref(false);
const fallbackProviderSel = ref(""); // "" = built-in backup chain
const fallbackModelSel = ref("");
const backupProviderModels = computed(() => {
  if (!fallbackProviderSel.value) return [] as string[];
  const entry = g4fProvidersList.value.find(p => p.id === fallbackProviderSel.value);
  const models = entry?.models?.length ? [...entry.models] : [];
  if (fallbackModelSel.value && !models.includes(fallbackModelSel.value)) {
    return [fallbackModelSel.value, ...models];
  }
  return models;
});
function onBackupProviderChange(id: string) {
  const entry = g4fProvidersList.value.find(p => p.id === id);
  fallbackModelSel.value = entry && entry.default_model ? entry.default_model : "";
}
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
async function refreshCookies() {
  cookieChecking.value = true;
  try {
    const res = await clipperStore.refreshG4fCookies();
    if (res) cookieStatus.value = res.status;
  } catch (e) {
    console.error("Failed to refresh cookies:", e);
  } finally {
    cookieChecking.value = false;
  }
}

function llmPayload() {
  const payload: Record<string, any> = {
    provider: llmProvider.value,
    base_url: llmBaseUrl.value || "",
    model: llmModel.value || "",
    outline_enabled: !!llmOutline.value,
    g4f_use_cookies: llmProvider.value === "g4f" ? g4fUseCookies.value : true,
    fallback_enabled: !!fallbackEnabled.value,
    // Empty provider = built-in backup chain, so always send both fields
    // (clearing them when the backup provider is set back to Automatic).
    fallback_provider: fallbackProviderSel.value || "",
    fallback_model: fallbackProviderSel.value ? (fallbackModelSel.value || "") : "",
  };
  if (llmProvider.value === "g4f") {
    payload.g4f_provider = g4fProviderSel.value;
    payload.g4f_model = g4fModelSel.value || "";
  }
  if (llmApiKey.value) payload.api_key = llmApiKey.value;
  return payload;
}

async function handleSaveLlm() {
  llmSaving.value = true;
  g4fSaveError.value = "";
  try {
    const settings = await clipperStore.updateLlmSettings(llmPayload());
    if (settings) {
      llmMaskedKey.value = settings.api_key;
      llmApiKey.value = "";
      llmProvider.value = settings.provider;
      llmBaseUrl.value = settings.base_url || "";
      llmModel.value = settings.model || "";
      llmOutline.value = settings.outline_enabled !== false;
      g4fUseCookies.value = (settings as any).g4f_use_cookies !== false;
      if ((settings as any).g4f_provider) g4fProviderSel.value = (settings as any).g4f_provider;
      g4fModelSel.value = (settings as any).g4f_model || "";
      fallbackEnabled.value = (settings as any).fallback_enabled === true;
      fallbackProviderSel.value = (settings as any).fallback_provider || "";
      fallbackModelSel.value = (settings as any).fallback_model || "";
    }
  } catch (e: any) {
    g4fSaveError.value = e?.data?.message || e?.message || "Could not save — is the backend running?";
    console.error("Failed to save AI provider:", e);
  } finally {
    llmSaving.value = false;
  }
}

async function handleTestLlm() {
  llmTesting.value = true;
  llmTestResult.value = null;
  llmTestAbort.value?.abort();
  const controller = new AbortController();
  llmTestAbort.value = controller;
  try {
    const r = await clipperStore.testLlmConnection(llmPayload(), controller.signal);
    llmTestResult.value = { ok: r.ok, detail: r.detail };
  } catch (e: any) {
    if (controller.signal.aborted) {
      llmTestResult.value = { ok: false, detail: "Test cancelled. The backend request may still finish in the background." };
    } else {
      const msg = e?.data?.data?.detail || e?.message || "Connection failed";
      llmTestResult.value = {
        ok: false,
        detail: /timeout|aborted/i.test(String(msg)) || e?.name === "TimeoutError"
          ? `${msg} — the provider hung. Try a different g4f provider/model, or turn OFF 'Use browser cookies'.`
          : msg,
      };
    }
  } finally {
    if (llmTestAbort.value === controller) llmTestAbort.value = null;
    llmTesting.value = false;
  }
}

function cancelTestLlm() {
  llmTestAbort.value?.abort();
}
try {
  const llmData = await clipperStore.fetchLlmSettings();
  if (llmData) {
    g4fUseCookies.value = llmData.settings.g4f_use_cookies !== false;
    llmProvider.value = llmData.settings.provider || "gemini";
    llmProvidersList.value = llmData.providers?.length ? llmData.providers : llmProvidersList.value;
    llmBaseUrl.value = llmData.settings.base_url || "";
    llmModel.value = llmData.settings.model || "";
    llmOutline.value = llmData.settings.outline_enabled !== false;
    llmMaskedKey.value = llmData.settings.api_key || "";
    g4fProviderSel.value = llmData.settings.g4f_provider || "DeepAI";
    g4fModelSel.value = llmData.settings.g4f_model || "gemini-2.5-flash-lite";
    fallbackEnabled.value = llmData.settings.fallback_enabled === true;
    fallbackProviderSel.value = llmData.settings.fallback_provider || "";
    fallbackModelSel.value = llmData.settings.fallback_model || "";
    clipperStore.fetchG4fProviders().then(list => { if (list) g4fProvidersList.value = list; });
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
  if (ttsEngine.value === "qwen3") {
    // tts_voice mirrors the Qwen speaker so /generate voice select stays compatible
    settings.tts_voice = qwenSpeaker.value;
    settings.qwen_mode = qwenMode.value;
    settings.qwen_speaker = qwenSpeaker.value;
    settings.qwen_lang = qwenLang.value;
    settings.qwen_instruct = qwenInstruct.value;
    settings.qwen_design_prompt = qwenDesignPrompt.value;
    settings.qwen_clone_ref = qwenCloneRef.value;
    settings.qwen_clone_text = qwenCloneText.value;
    settings.qwen_model = qwenModel.value;
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

function applyQwenCharacter(ch: QwenCharacter) {
  qwenMode.value = ch.mode || "custom";
  qwenLang.value = ch.language || qwenLang.value;
  qwenDesignPrompt.value = ch.design_prompt || "";
  qwenInstruct.value = ch.instruct || "";
  qwenSpeaker.value = ch.value;
  saveTtsSettings();
}

function customVoiceDescription(c: CustomVoice): string {
  if (c.origin === "design") return `My designed voice · ${c.language} · "${c.design_prompt.slice(0, 80)}…"`;
  return `My cloned voice · ${c.language} · ref: ${(c.refAudioPath || "").split("/").pop()}`;
}

function mergeCustomVoicesIntoOptions(target?: string) {
  voiceOptions.value = voiceOptions.value.filter((o) => !customVoices.value.some((c) => c.name === o.value));
  if (target && target !== "qwen3") return;
  if (!target && ttsEngine.value !== "qwen3") return;
  for (const c of customVoices.value) {
    voiceOptions.value.push({
      label: `★ ${c.name} (my ${c.origin === "design" ? "design" : "clone"})`,
      value: c.name,
      description: customVoiceDescription(c),
    });
  }
}

/** Fill the form from a saved (IndexedDB) voice. */
function applyCustomVoice(c: CustomVoice) {
  qwenMode.value = c.origin === "design" ? "design" : "clone";
  qwenLang.value = c.language || qwenLang.value;
  qwenDesignPrompt.value = c.origin === "design" ? c.design_prompt : "";
  qwenInstruct.value = "";
  if (c.origin === "clone") {
    qwenCloneRef.value = c.refAudioPath;
    qwenCloneText.value = c.ref_text;
  }
  qwenSpeaker.value = c.name;
  saveTtsSettings();
}

function onQwenSpeakerChange(v: string) {
  const custom = customVoices.value.find((c) => c.name === v);
  if (custom) applyCustomVoice(custom);
  else saveTtsSettings();
}

async function reloadCustomVoices() {
  customVoices.value = await listCustomVoices();
  mergeCustomVoicesIntoOptions();
}

async function saveCurrentAsCustom() {
  customSaveLoading.value = true;
  customSaveMsg.value = "";
  customSaveOk.value = false;
  const origin = qwenMode.value === "design" ? "design" : "clone";
  const res = await saveCustomVoice({
    name: customVoiceName.value.trim(),
    origin,
    language: qwenLang.value,
    design_prompt: origin === "design" ? qwenDesignPrompt.value.trim() : "",
    ref_text: origin === "clone" ? qwenCloneText.value : "",
    refAudioPath: origin === "clone" ? qwenCloneRef.value : "",
  });
  if (res.ok) {
    const savedName = customVoiceName.value.trim();
    customSaveOk.value = true;
    customSaveMsg.value = res.updated ? `Updated "${savedName}"` : `Saved "${savedName}"`;
    customVoiceName.value = "";
    await reloadCustomVoices();
    onQwenSpeakerChange(savedName);
  } else {
    customSaveMsg.value = res.error || "Could not save voice";
  }
  customSaveLoading.value = false;
}

async function deleteCustomVoice(name: string) {
  if (!(await removeCustomVoice(name))) return;
  await reloadCustomVoices();
  if (qwenSpeaker.value === name) {
    qwenSpeaker.value = "Ryan";
    saveTtsSettings();
  }
}
async function previewQwenVoice() {
  previewLoading.value = true;
  previewError.value = "";
  previewUrl.value = "";
  // A saved custom voice is the source of truth: send its stored config so
  // the audition matches generation exactly.
  const custom = customVoices.value.find((c) => c.name === qwenSpeaker.value) || null;
  const params = custom
    ? toQwenParams(custom)
    : {
        qwen_mode: qwenMode.value,
        qwen_lang: qwenLang.value,
        qwen_instruct: qwenInstruct.value,
        qwen_design_prompt: qwenDesignPrompt.value,
        qwen_clone_ref: qwenCloneRef.value,
        qwen_clone_text: qwenCloneText.value,
      };
  try {
    await saveTtsSettings();
    const res = await $fetch<{ status: string; data: { url: string }; message?: string }>(
      `${API_URL}/api/tts/qwen/preview`,
      {
        method: "POST",
        body: {
          text: previewText.value,
          mode: params.qwen_mode,
          speaker: qwenSpeaker.value,
          language: params.qwen_lang,
          instruct: params.qwen_instruct,
          design_prompt: params.qwen_design_prompt,
          ref_audio: params.qwen_clone_ref,
          ref_text: params.qwen_clone_text,
        },
      }
    );
    if (res.status === "success") {
      previewUrl.value = `${API_URL}${res.data.url}`;
    } else {
      previewError.value = res.message || "Preview failed";
    }
  } catch (e: any) {
    previewError.value = e?.data?.message || e?.message || "Preview failed — is the backend running?";
  } finally {
    previewLoading.value = false;
  }
}

async function uploadQwenCloneRef(event: Event) {
  const input = event.target as HTMLInputElement;
  if (!input.files || input.files.length === 0) return;
  qwenCloning.value = true;
  qwenCloneError.value = "";
  try {
    const formData = new FormData();
    formData.append("file", input.files[0]);
    const res = await $fetch<{ status: string; data: { path: string }; message?: string }>(
      `${API_URL}/api/tts/qwen/clone-reference`,
      { method: "POST", body: formData }
    );
    if (res.status === "success") {
      qwenCloneRef.value = res.data.path;
      await saveTtsSettings();
    } else {
      qwenCloneError.value = res.message || "Upload failed";
    }
  } catch (e: any) {
    qwenCloneError.value = e?.data?.message || e?.message || "Upload failed";
  } finally {
    qwenCloning.value = false;
    input.value = "";
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
        <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">Configure AI provider, TTS, fonts, subtitles and integrations</p>
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

      <n-divider>AI Model Provider</n-divider>

      <div class="max-w-screen-md w-full bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 p-5 rounded-xl mb-4 space-y-3">
        <p class="text-xs text-clipper-ink/60 dark:text-white/60">Global LLM used for script writing, ranking, hook titles and outline generation. Gemini (official API) is the default — paste a free key from makersuite.google.com/app/apikey.</p>
        <n-form-item label="Provider:" path="llmProvider">
          <n-select
            v-model:value="llmProvider"
            :options="llmProvidersList.map(p => ({ label: p === 'gemini' ? 'gemini (Default)' : p === 'g4f' ? 'g4f (Free, needs browser cookies)' : p, value: p }))"
            class="w-full"
          />
        </n-form-item>

        <div v-if="llmProvider === 'g4f'" class="rounded-lg border p-3 space-y-3"
          :class="g4fUseCookies && cookieStatus && !cookieStatus.ok
            ? 'border-red-500/40 bg-red-500/10'
            : 'border-clipper-ink/12 dark:border-white/10 bg-clipper-ink/[0.03] dark:bg-white/[0.03]'">
          <n-form-item label="g4f Provider:" path="g4fProvider">
            <n-select
              v-model:value="g4fProviderSel"
              :options="g4fProvidersList.map(p => ({ label: p.needs_cookies ? `${p.id} (needs cookies)` : (p.label && p.label !== p.id ? `${p.id} — ${p.label}` : p.id), value: p.id }))"
              class="w-full"
              filterable
              @update:value="onG4fProviderChange"
            />
          </n-form-item>
          <n-form-item label="g4f Model:" path="g4fModel">
            <n-select
              v-model:value="g4fModelSel"
              :options="g4fModels.map(m => ({ label: m, value: m }))"
              class="w-full"
              filterable
              tag
            />
          </n-form-item>
          <n-checkbox :checked="g4fUseCookies" :disabled="g4fSaving" @update:checked="onG4fCookiesChange">
            <span class="text-sm font-medium text-clipper-ink dark:text-white">Use browser cookies</span>
          </n-checkbox>
          <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-1 ml-6">
            g4f reads your Firefox Google cookies for Gemini. Turn OFF to use cookie-free
            providers instead — no login, no API key. {{ g4fSaving ? "Saving…" : "" }}
          </p>
          <div v-if="g4fUseCookies">
            <div v-if="cookieChecking" class="text-xs text-clipper-ink/60 dark:text-white/60 mt-2 ml-6">Checking browser cookies…</div>
            <div v-else-if="cookieStatus && !cookieStatus.ok" class="mt-2 ml-6">
              <p class="text-xs font-semibold text-red-500">Browser cookies are outdated</p>
              <p class="text-xs text-clipper-ink/70 dark:text-white/70 mt-1">{{ cookieStatus.detail }}</p>
              <ol class="text-xs text-clipper-ink/70 dark:text-white/70 list-decimal ml-4 mt-2 space-y-1">
                <li v-for="(step, i) in cookieStatus.renew_steps" :key="i">{{ step }}</li>
              </ol>
            </div>
            <p v-else-if="cookieStatus && cookieStatus.ok" class="text-xs text-green-600 dark:text-green-400 mt-2 ml-6">
              Cookies look fresh — {{ cookieStatus.detail }}
            </p>
            <div class="ml-6 mt-2 flex gap-3">
              <button class="text-xs font-medium underline" @click="checkCookies()">Check cookies</button>
              <button class="text-xs font-semibold underline" @click="refreshCookies()">Nuke &amp; re-import cookies</button>
            </div>
          </div>
          <details class="mt-2 ml-6 text-xs text-clipper-ink/70 dark:text-white/70">
            <summary class="cursor-pointer font-medium underline">How to check your cookies are working</summary>
            <ol class="list-decimal ml-4 mt-2 space-y-1">
              <li>The backend reads cookies from browsers on the PC that runs the backend — log in on that PC, not your phone.</li>
              <li>In Firefox (or Chrome) open gemini.google.com and log in — no private/incognito window.</li>
              <li>Send one message on the Gemini website. If it answers, the session is alive.</li>
              <li>Press “Check cookies” above — it must say fresh. Then “Test connection” and watch backend.log (project folder, next to system.sh): expect <code>cookies OK (… missing: none)</code> then <code>first token after …s</code>.</li>
              <li><code>MISSING SAPISID</code> or “No .google.com cookies” means the session expired: log out/in again in the same browser and re-test. No backend restart needed.</li>
              <li>Stuck on <code>waiting for first token</code> until it times out means Google is throttling this session: wait, log out/in again — or switch Provider to <code>gemini</code> + API key.</li>
            </ol>
          </details>
        </div>

        <n-form-item v-if="showLlmBaseUrl" label="Base URL:" path="llmBaseUrl">
          <n-input v-model:value="llmBaseUrl" :placeholder="llmProvider === 'ollama' ? 'http://localhost:11434/v1' : 'https://api.openai.com/v1'" class="w-full" />
        </n-form-item>

        <n-form-item label="API Key:" path="llmApiKey">
          <n-input v-model:value="llmApiKey" type="password" :placeholder="llmMaskedKey ? llmMaskedKey : 'Not set'" class="w-full" />
        </n-form-item>
        <p class="text-[11px] text-clipper-ink/40 dark:text-white/40 -mt-2">Leave empty to keep the existing key.</p>

        <n-form-item label="Model:" path="llmModel">
          <n-input v-model:value="llmModel" placeholder="e.g. gemini-3.5-flash, gemini-2.5-flash, gpt-4o-mini (empty = provider default)" class="w-full" />
        </n-form-item>

        <n-checkbox v-model:checked="fallbackEnabled">
          <span class="text-sm font-medium text-clipper-ink dark:text-white">Use backup if the selected model fails</span>
        </n-checkbox>
        <p class="text-xs text-clipper-ink/60 dark:text-white/60 mt-1 ml-6">
          OFF (default): generation stops with a clear 'model not available' error.
          ON: the backup below runs before failing.
        </p>
        <div
          v-if="fallbackEnabled"
          class="rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-clipper-ink/[0.03] dark:bg-white/[0.03] p-3 space-y-3 mt-2"
        >
          <n-form-item label="Backup provider:" path="fallbackProvider">
            <n-select
              v-model:value="fallbackProviderSel"
              :options="[
                { label: 'Automatic (built-in backup chain)', value: '' },
                ...g4fProvidersList.map(p => ({
                  label: p.needs_cookies ? `${p.id} (needs cookies)` : (p.label && p.label !== p.id ? `${p.id} — ${p.label}` : p.id),
                  value: p.id,
                })),
              ]"
              class="w-full"
              filterable
              @update:value="onBackupProviderChange"
            />
          </n-form-item>
          <n-form-item v-if="fallbackProviderSel" label="Backup model:" path="fallbackModel">
            <n-select
              v-model:value="fallbackModelSel"
              :options="backupProviderModels.map(m => ({ label: m, value: m }))"
              class="w-full"
              filterable
              tag
            />
          </n-form-item>
          <p class="text-xs text-clipper-ink/60 dark:text-white/60 -mt-1 ml-1">
            Automatic tries the cookie-free backup chain (no login, no API key), then your
            Gemini cookies and the official API key — in that order.
          </p>
        </div>

        <n-checkbox v-model:checked="llmOutline">
          <span class="text-sm font-medium text-clipper-ink dark:text-white">Outline generation</span>
          <span class="text-xs text-clipper-ink/40 dark:text-white/40">— generate topic timeline per transcript</span>
        </n-checkbox>

        <div v-if="llmTestResult" class="text-sm" :class="llmTestResult.ok ? 'text-clipper-green' : 'text-red-500'">
          {{ llmTestResult.ok ? 'Connection OK' : 'Connection failed' }} — {{ llmTestResult.detail }}
        </div>
        <p v-if="g4fSaveError" class="text-xs text-red-500">{{ g4fSaveError }}</p>

        <div class="flex gap-2 pt-1">
          <button
            class="h-10 px-4 rounded-lg border border-clipper-ink/12 dark:border-white/10 bg-white dark:bg-neutral-800 text-sm font-medium text-clipper-ink dark:text-white disabled:opacity-50"
            :disabled="llmTesting"
            @click="handleTestLlm"
          >
            {{ llmTesting ? 'Testing…' : 'Test connection' }}
          </button>
          <button
            v-if="llmTesting"
            class="h-10 px-4 rounded-lg border border-red-500/40 text-red-500 text-sm font-semibold hover:bg-red-500/10"
            @click="cancelTestLlm"
          >
            Cancel
          </button>
          <button
            class="h-10 px-4 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 disabled:opacity-50"
            :disabled="llmSaving"
            @click="handleSaveLlm"
          >
            {{ llmSaving ? 'Saving…' : 'Save' }}
          </button>
        </div>
        <p class="text-xs text-clipper-ink/50 dark:text-white/45 pt-2">
          “Test connection” only checks the fields above — it never saves them. Press Save to apply your changes.
        </p>
      </div>

      <n-divider>TTS Settings</n-divider>

      <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 p-5 rounded-xl mb-4">
        <n-form-item label="TTS Engine:" path="ttsEngine">
          <div class="flex items-center gap-3 w-full">
            <n-select v-model:value="ttsEngine" :options="ttsEngineOptions" class="flex-1" @update:value="onTtsEngineChange" />
            <n-tag :type="ttsStatus.supertonic === 'healthy' ? 'success' : 'warning'" size="small">
              {{ ttsStatus.supertonic === 'healthy' ? "Supertonic OK" : "Supertonic Down" }}
            </n-tag>
            <n-tag :type="ttsStatus.qwen3 === 'healthy' || ttsStatus.qwen3 === 'available' ? 'success' : 'warning'" size="small">
              {{ ttsStatus.qwen3 === 'healthy' ? "Qwen3 OK" : ttsStatus.qwen3 === 'available' ? "Qwen3 Ready" : "Qwen3 Down" }}
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

        <template v-else-if="ttsEngine === 'tiktok'">
          <n-form-item label="Voice:" path="voice">
            <n-select
              v-model:value="globalSettings.voice"
              :options="voiceOptions"
              :loading="voicesLoading"
              class="w-full md:w-auto"
            />
          </n-form-item>
        </template>

        <template v-else-if="ttsEngine === 'qwen3'">
          <div v-if="qwenCharacters.length" class="flex flex-wrap items-center gap-2 mb-3">
            <span class="text-xs font-semibold text-gray-500">Characters:</span>
            <n-button
              v-for="c in qwenCharacters" :key="c.value" size="small" ghost
              :type="qwenSpeaker === c.value ? 'primary' : 'default'"
              @click="applyQwenCharacter(c)"
            >
              🐶 {{ c.label }}
            </n-button>
          </div>
          <p v-if="qwenSpeaker && qwenCharacters.find(c => c.value === qwenSpeaker)" class="text-xs text-gray-500 dark:text-gray-400 -mt-2 mb-3 px-1">
            {{ qwenCharacters.find(c => c.value === qwenSpeaker)?.description }}
          </p>
          <div class="border border-dashed border-gray-300 dark:border-white/15 rounded-lg p-3 space-y-2 mb-3">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs font-semibold text-gray-500">My voices:</span>
              <n-input
                v-model:value="customVoiceName" placeholder="Name this voice…" maxlength="40"
                size="small" class="!w-40"
              />
              <n-button
                size="small" type="primary" ghost
                :loading="customSaveLoading"
                :disabled="qwenMode === 'clone' ? !qwenCloneRef : (qwenMode === 'design' ? !qwenDesignPrompt.trim() : true)"
                @click="saveCurrentAsCustom"
              >
                {{ qwenMode === 'design' ? 'Save design' : 'Save voice' }}
              </n-button>
            </div>
            <p class="text-[11px] text-gray-400 px-1">
              {{ qwenMode === 'design'
                ? 'Saves the description as a reusable voice (first save builds it, may take a few minutes). Same name overwrites = update.'
                : qwenMode === 'clone'
                  ? 'Saves the uploaded clip + transcript as a reusable voice. Same name overwrites = update.'
                  : 'Switch to Voice Design or Voice Clone mode to save the current setup as a reusable voice.' }}
            </p>
            <p
              v-if="customSaveMsg" class="text-xs px-1"
              :class="customSaveOk ? 'text-green-600 dark:text-green-400' : 'text-red-500'"
            >
              {{ customSaveMsg }}
            </p>
            <div v-if="customVoices.length" class="flex flex-wrap items-center gap-2">
              <template v-for="c in customVoices" :key="c.name">
                <n-button
                  size="small" ghost
                  :type="qwenSpeaker === c.name ? 'primary' : 'default'"
                  @click="onQwenSpeakerChange(c.name)"
                >
                  ★ {{ c.name }}
                </n-button>
                <n-button
                  size="tiny" quaternary title="Delete saved voice"
                  @click="deleteCustomVoice(c.name)"
                >
                  <template #icon><Icon name="mdi:delete" /></template>
                </n-button>
              </template>
            </div>
          </div>
          <n-form-item label="Mode:" path="qwenMode">
            <n-radio-group v-model:value="qwenMode" name="qwenMode" size="medium" class="flex flex-wrap gap-2" @update:value="saveTtsSettings">
              <n-radio-button v-for="m in qwenModes.length ? qwenModes : [{ value: 'custom', label: 'Preset Voice + Instruct' }, { value: 'design', label: 'Voice Design' }, { value: 'clone', label: 'Voice Clone' }]" :key="m.value" :value="m.value">
                <span>{{ m.label }}</span>
              </n-radio-button>
            </n-radio-group>
          </n-form-item>
          <p class="text-xs text-gray-500 dark:text-gray-400 -mt-2 mb-3 px-1">
            {{ (qwenModes.find(m => m.value === qwenMode) || {}).description || "" }}
          </p>

          <template v-if="qwenMode === 'custom'">
            <n-form-item label="Preset Voice:" path="qwenSpeaker">
              <n-select
                v-model:value="qwenSpeaker"
                :options="voiceOptions"
                :loading="voicesLoading"
                class="w-full"
                @update:value="onQwenSpeakerChange"
              />
            </n-form-item>
            <div v-if="qwenSpeaker && voiceStyles[qwenSpeaker]" class="text-xs text-gray-500 dark:text-gray-400 -mt-3 mb-3 px-1">
              {{ voiceStyles[qwenSpeaker]?.description }}
            </div>
          </template>

          <template v-if="qwenMode === 'design'">
            <n-form-item label="Voice Description:" path="qwenDesignPrompt">
              <n-input
                v-model:value="qwenDesignPrompt"
                type="textarea"
                :rows="3"
                placeholder="Describe the voice, e.g. A dynamic young male narrator with strong rhythmic drive, energetic Shorts-style delivery."
                class="w-full"
                @update:value="saveTtsSettings"
              />
            </n-form-item>
            <div v-if="qwenDesignPresets.length" class="flex flex-wrap gap-2 -mt-2 mb-3">
              <n-button
                v-for="p in qwenDesignPresets" :key="p.label" size="tiny" ghost
                @click="qwenDesignPrompt = p.value; saveTtsSettings()"
              >
                {{ p.label }}
              </n-button>
            </div>
          </template>

          <template v-if="qwenMode === 'clone'">
            <p class="text-[11px] text-gray-400 px-1 mb-1">
              Clone copies your reference clip — emotion and pace come from the clip itself, not from steering text.
            </p>
            <n-form-item label="Reference Clip (~3s+ clear speech):" path="qwenCloneRef">
              <div class="flex items-center gap-2 w-full">
                <n-button size="small" :loading="qwenCloning" @click="qwenRefInput?.click()">
                  {{ qwenCloneRef ? "Replace clip" : "Upload clip" }}
                </n-button>
                <input ref="qwenRefInput" type="file" accept=".mp3,.wav,.m4a,.aac,.ogg,.flac,.wma" class="hidden" @change="uploadQwenCloneRef" />
                <span class="text-xs text-gray-500 truncate">{{ qwenCloneRef ? qwenCloneRef.split('/').pop() : "No clip uploaded" }}</span>
              </div>
            </n-form-item>
            <p v-if="qwenCloneError" class="text-xs text-red-500 -mt-2 mb-2">{{ qwenCloneError }}</p>
            <n-form-item label="Reference Transcript:" path="qwenCloneText">
              <n-input
                v-model:value="qwenCloneText"
                type="textarea"
                :rows="2"
                placeholder="Exact words spoken in the reference clip (empty = timbre-only clone)"
                class="w-full"
                @update:value="saveTtsSettings"
              />
            </n-form-item>
          </template>

          <n-form-item label="Language:" path="qwenLang">
            <n-select
              v-model:value="qwenLang"
              :options="languageOptions.map(l => ({ label: l.label, value: l.code }))"
              class="w-full"
              @update:value="saveTtsSettings"
            />
          </n-form-item>

          <n-form-item v-if="qwenMode === 'custom'" label="Steer the voice (instruct):" path="qwenInstruct">
            <n-input
              v-model:value="qwenInstruct"
              type="textarea"
              :rows="2"
              placeholder="e.g. Speak cheerfully and energetically, fast-paced like a viral Shorts narrator. Empty = neutral."
              class="w-full"
              @update:value="saveTtsSettings"
            />
          </n-form-item>
          <div v-if="qwenMode === 'custom' && qwenInstructPresets.length" class="flex flex-wrap gap-2 -mt-2 mb-3">
            <n-button
              v-for="p in qwenInstructPresets" :key="p.label" size="tiny" ghost
              @click="qwenInstruct = p.value; saveTtsSettings()"
            >
              {{ p.label }}
            </n-button>
          </div>

          <n-form-item label="Model:" path="qwenModel">
            <n-select
              v-model:value="qwenModel"
              :options="[{ label: 'Auto (per-mode default, 1.7B)', value: '' }, ...Object.entries(qwenModels).map(([k, v]) => ({ label: `${k} — ${v}`, value: v }))]"
              placeholder="Auto (per-mode default, 1.7B)"
              class="w-full"
              @update:value="saveTtsSettings"
            />
          </n-form-item>

          <n-divider class="my-3">Audition</n-divider>
          <n-form-item label="Preview text:" path="qwenPreview">
            <n-input v-model:value="previewText" type="textarea" :rows="2" class="w-full" />
          </n-form-item>
          <div class="flex items-center gap-2 mb-2">
            <n-button size="small" type="primary" ghost :loading="previewLoading" @click="previewQwenVoice">
              Generate preview
            </n-button>
            <span class="text-[11px] text-gray-400">First run downloads the model (~3GB), then it's instant.</span>
          </div>
          <p v-if="previewError" class="text-xs text-red-500 mb-2">{{ previewError }}</p>
          <audio v-if="previewUrl" :src="previewUrl" controls class="w-full h-8 mb-2"></audio>
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