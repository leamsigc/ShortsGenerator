<script lang="ts" setup>
/**
 * TtsSettingsPanel — full TTS settings (engine + per-engine options +
 * Qwen3 characters/design/clone + audition preview). Used in the Generate
 * view's Voice modal; the selected voice is exposed via v-model so callers
 * bind it to per-video (video.voice) or global state.
 */
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

import type { CustomVoice } from "~/composables/useCustomVoices";

const props = withDefaults(defineProps<{
  modelValue: string;
  showPreview?: boolean;
}>(), {
  modelValue: "",
  showPreview: true,
});
const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const { API_SETTINGS } = useApiSettings();
const API_URL = API_SETTINGS.value.URL;
const { list: listCustomVoices, save: saveCustomVoice, remove: removeCustomVoice, toQwenParams } =
  useCustomVoices();

const ttsEngineOptions = [
  { label: "Supertonic TTS (Local)", value: "supertonic" },
  { label: "TikTok TTS (Cloud)", value: "tiktok" },
  { label: "Qwen3 TTS (Local, Design/Clone)", value: "qwen3" },
];

const engine = ref("supertonic");
const voiceOptions = ref<{ label: string; value: string; description?: string }[]>([]);
const voicesLoading = ref(false);
const voiceStyles = ref<Record<string, VoiceStyle>>({});
const languageOptions = ref<LanguageOption[]>([]);
const qualityPresets = ref<QualityPreset[]>([]);
const ttsStatus = ref<{ supertonic: string; qwen3: string }>({
  supertonic: "unavailable",
  qwen3: "unavailable",
});

// Supertonic
const stVoice = ref("M3");
const stLang = ref("en");
const stQuality = ref(8);
const stSpeed = ref(1.05);

// Qwen3
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
const customVoices = ref<CustomVoice[]>([]);
const customVoiceName = ref("");
const customSaveLoading = ref(false);
const customSaveMsg = ref("");
const customSaveOk = ref(false);

const currentCharacter = computed(() =>
  qwenCharacters.value.find((c) => c.value === props.modelValue)
);

const currentCustom = computed(() =>
  customVoices.value.find((c) => c.name === props.modelValue) || null
);

const allVoiceOptions = computed(() => [
  ...voiceOptions.value,
  ...(engine.value === "qwen3"
    ? customVoices.value.map((c) => ({
        label: `★ ${c.name} (my ${c.origin === "design" ? "design" : "clone"})`,
        value: c.name,
        description: customDescription(c),
      }))
    : []),
]);

function customDescription(c: CustomVoice): string {
  if (c.origin === "design") return `My designed voice · ${c.language} · "${c.design_prompt.slice(0, 80)}…"`;
  return `My cloned voice · ${c.language} · ref: ${(c.refAudioPath || "").split("/").pop()}`;
}

function voiceDescription(value: string): string {
  if (!value) return "";
  const styled = voiceStyles.value[value]?.description;
  if (styled) return styled;
  const custom = customVoices.value.find((c) => c.name === value);
  if (custom) return customDescription(custom);
  return "";
}

const steeringSummary = computed(() => {
  if (qwenMode.value === "design")
    return qwenDesignPrompt.value ? ` · "${qwenDesignPrompt.value.slice(0, 60)}…"` : "";
  if (qwenMode.value === "custom")
    return qwenInstruct.value ? ` · "${qwenInstruct.value.slice(0, 60)}…"` : " · neutral";
  return " · from reference clip";
});

function voiceLabel(v: string): { label: string; value: string; description?: string } {
  const s = voiceStyles.value[v];
  const prefix = s?.kind === "character" ? "🐶 " : "";
  return {
    label: `${prefix}${v} - ${s?.name || v}${s?.gender ? ` (${s.gender})` : ""}`,
    value: v,
    description: s?.description,
  };
}

async function loadVoices(target: string) {
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
    }>(`${API_URL}/api/tts/voices?engine=${target}`);
    const data = res.data;
    voiceStyles.value = data.voiceStyles || {};
    voiceOptions.value = (data.voices || []).map(voiceLabel);
    if (data.languages) languageOptions.value = data.languages;
    if (data.qualityPresets) qualityPresets.value = data.qualityPresets;
    if (data.modes) qwenModes.value = data.modes;
    if (data.models) qwenModels.value = data.models;
    if (data.presets) {
      qwenInstructPresets.value = data.presets.instructs || [];
      qwenDesignPresets.value = data.presets.designs || [];
      qwenCharacters.value = data.presets.characters || [];
    }
  } catch (e) {
    console.error("Failed to load voices:", e);
  } finally {
    voicesLoading.value = false;
  }
}

async function loadStatus() {
  try {
    const { data } = await $fetch<{ data: { supertonic: string; qwen3: string } }>(
      `${API_URL}/api/tts/status`
    );
    ttsStatus.value = {
      supertonic: data.supertonic || "unavailable",
      qwen3: (data as Record<string, string>).qwen3 || "unavailable",
    };
  } catch (e) {
    console.error("Failed to load TTS status:", e);
  }
}

async function saveAll() {
  const settings: Record<string, unknown> = {
    preferred_tts: engine.value,
    tts_voice: engine.value === "qwen3" ? qwenSpeaker.value : stVoice.value,
    tts_lang: stLang.value,
    tts_quality: stQuality.value,
    tts_speed: stSpeed.value,
    qwen_mode: qwenMode.value,
    qwen_speaker: qwenSpeaker.value,
    qwen_lang: qwenLang.value,
    qwen_instruct: qwenInstruct.value,
    qwen_design_prompt: qwenDesignPrompt.value,
    qwen_clone_ref: qwenCloneRef.value,
    qwen_clone_text: qwenCloneText.value,
    qwen_model: qwenModel.value,
  };
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: { type: "TTS", settings },
    });
  } catch (e) {
    console.error("Failed to save TTS settings:", e);
  }
}

async function onEngineChange(value: string) {
  engine.value = value;
  await loadVoices(value);
  await saveAll();
}

function selectVoice(value: string) {
  emit("update:modelValue", value);
  if (engine.value === "supertonic") {
    stVoice.value = value;
    saveAll();
  } else if (engine.value === "qwen3") {
    const ch = qwenCharacters.value.find((c) => c.value === value);
    if (ch) applyCharacter(ch);
    else {
      const custom = customVoices.value.find((c) => c.name === value);
      if (custom) applyCustomVoice(custom, false);
      else {
        qwenSpeaker.value = value;
        saveAll();
      }
    }
  }
}

/** Fill the form from a saved (IndexedDB) voice. Emits unless told otherwise. */
function applyCustomVoice(c: CustomVoice, emitVoice = true) {
  qwenMode.value = c.origin === "design" ? "design" : "clone";
  qwenLang.value = c.language || qwenLang.value;
  qwenDesignPrompt.value = c.origin === "design" ? c.design_prompt : "";
  qwenInstruct.value = "";
  qwenCloneRef.value = c.origin === "clone" ? c.refAudioPath : qwenCloneRef.value;
  qwenCloneText.value = c.origin === "clone" ? c.ref_text : "";
  if (emitVoice) emit("update:modelValue", c.name);
  saveAll();
}

async function reloadCustomVoices() {
  customVoices.value = await listCustomVoices();
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
    customSaveMsg.value = res.updated ? `Updated "${savedName}"` : `Saved "${savedName}" — select it to use it`;
    customVoiceName.value = "";
    await reloadCustomVoices();
    selectVoice(savedName);
  } else {
    customSaveMsg.value = res.error || "Could not save voice";
  }
  customSaveLoading.value = false;
}

async function deleteCustomVoice(name: string) {
  if (!(await removeCustomVoice(name))) return;
  await reloadCustomVoices();
  if (props.modelValue === name) {
    qwenSpeaker.value = "Ryan";
    emit("update:modelValue", "Ryan");
    saveAll();
  }
}

function applyCharacter(ch: QwenCharacter, emitVoice = true) {
  qwenMode.value = ch.mode || "custom";
  qwenLang.value = ch.language || qwenLang.value;
  qwenDesignPrompt.value = ch.design_prompt || "";
  qwenInstruct.value = ch.instruct || "";
  qwenSpeaker.value = ch.value;
  if (emitVoice) emit("update:modelValue", ch.value);
  saveAll();
}

async function previewQwenVoice() {
  previewLoading.value = true;
  previewError.value = "";
  previewUrl.value = "";
  // A saved custom voice is the source of truth: send its stored config so
  // the audition matches generation exactly (generation does the same).
  const custom = customVoices.value.find((c) => c.name === props.modelValue) || null;
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
    await saveAll();
    const res = await $fetch<{ status: string; data: { url: string }; message?: string }>(
      `${API_URL}/api/tts/qwen/preview`,
      {
        method: "POST",
        body: {
          text: previewText.value,
          mode: params.qwen_mode,
          // Audition exactly what generation would use: the voice shown in
          // the dropdown wins, saved speaker is the fallback.
          speaker: props.modelValue || qwenSpeaker.value,
          language: params.qwen_lang,
          instruct: params.qwen_instruct,
          design_prompt: params.qwen_design_prompt,
          ref_audio: params.qwen_clone_ref,
          ref_text: params.qwen_clone_text,
        },
      }
    );
    if (res.status === "success") previewUrl.value = `${API_URL}${res.data.url}`;
    else previewError.value = res.message || "Preview failed";
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
      await saveAll();
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

// Init: global engine + saved per-engine values, then voices + status.
try {
  const res = await $fetch<{ data: { ttsSettings?: Record<string, any> } }>(
    `${API_URL}/api/settings`
  );
  const t = res.data?.ttsSettings;
  if (t) {
    engine.value = t.preferred_tts || "supertonic";
    stVoice.value = t.tts_voice || "M3";
    stLang.value = t.tts_lang || "en";
    stQuality.value = t.tts_quality ?? 8;
    stSpeed.value = t.tts_speed ?? 1.05;
    qwenMode.value = t.qwen_mode || "custom";
    qwenSpeaker.value = t.qwen_speaker || "Ryan";
    qwenLang.value = t.qwen_lang || "English";
    qwenInstruct.value = t.qwen_instruct || "";
    qwenDesignPrompt.value = t.qwen_design_prompt || "";
    qwenModel.value = t.qwen_model || "";
    qwenCloneRef.value = t.qwen_clone_ref || "";
    qwenCloneText.value = t.qwen_clone_text || "";
  }
} catch (e) {
  console.error("Failed to load TTS settings (is the backend running?):", e);
}
await loadVoices(engine.value);
await loadStatus();
await reloadCustomVoices();
</script>

<template>
  <div class="space-y-4">
    <n-form-item label="TTS Engine:">
      <div class="flex items-center gap-2 w-full flex-wrap">
        <n-select
          :value="engine"
          :options="ttsEngineOptions"
          class="flex-1 min-w-40"
          @update:value="onEngineChange"
        />
        <n-tag :type="ttsStatus.supertonic === 'healthy' ? 'success' : 'warning'" size="small">
          {{ ttsStatus.supertonic === 'healthy' ? "Supertonic OK" : "Supertonic Down" }}
        </n-tag>
        <n-tag
          :type="ttsStatus.qwen3 === 'healthy' || ttsStatus.qwen3 === 'available' ? 'success' : 'warning'"
          size="small"
        >
          {{ ttsStatus.qwen3 === 'healthy' ? "Qwen3 OK" : ttsStatus.qwen3 === 'available' ? "Qwen3 Ready" : "Qwen3 Down" }}
        </n-tag>
      </div>
    </n-form-item>

    <n-form-item label="Voice:">
      <n-select
        :value="modelValue"
        :options="allVoiceOptions"
        :loading="voicesLoading"
        placeholder="Select a voice"
        class="w-full"
        @update:value="selectVoice"
      />
    </n-form-item>
    <div
      v-if="modelValue && voiceDescription(modelValue)"
      class="text-xs text-gray-500 dark:text-gray-400 -mt-3 px-1"
    >
      {{ voiceDescription(modelValue) }}
    </div>

    <!-- Supertonic options -->
    <template v-if="engine === 'supertonic'">
      <n-form-item label="Language:">
        <n-select
          v-model:value="stLang"
          :options="languageOptions.map((l) => ({ label: l.label, value: l.code }))"
          class="w-full"
          @update:value="saveAll"
        />
      </n-form-item>
      <n-form-item label="Quality:">
        <div class="w-full">
          <n-slider
            v-model:value="stQuality" :min="5" :max="12" :step="1"
            :marks="{ 5: 'Fast', 8: 'Standard', 12: 'Best' }"
            class="w-full" @update:value="saveAll"
          />
          <div class="text-xs text-gray-500 mt-1">
            {{ qualityPresets.find((q) => q.value === stQuality)?.label || `${stQuality} steps` }}
          </div>
        </div>
      </n-form-item>
      <n-form-item label="Speed:">
        <div class="w-full">
          <n-slider
            v-model:value="stSpeed" :min="0.7" :max="2.0" :step="0.05"
            :marks="{ 0.7: 'Slow', 1.0: 'Normal', 1.5: 'Fast', 2.0: 'Max' }"
            class="w-full" @update:value="saveAll"
          />
          <div class="text-xs text-gray-500 mt-1">{{ stSpeed.toFixed(2) }}x speed</div>
        </div>
      </n-form-item>
    </template>

    <!-- Qwen3 options -->
    <template v-else-if="engine === 'qwen3'">
      <div v-if="qwenCharacters.length" class="flex flex-wrap items-center gap-2">
        <span class="text-xs font-semibold text-gray-500">Characters:</span>
        <n-button
          v-for="c in qwenCharacters" :key="c.value" size="small" ghost
          :type="modelValue === c.value ? 'primary' : 'default'"
          @click="applyCharacter(c)"
        >
          🐶 {{ c.label }}
        </n-button>
      </div>
      <p v-if="currentCharacter" class="text-xs text-gray-500 dark:text-gray-400 px-1">
        {{ currentCharacter.description }}
      </p>

      <div class="border border-dashed border-gray-300 dark:border-white/15 rounded-lg p-3 space-y-2">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-xs font-semibold text-gray-500">My voices:</span>
          <n-input
            v-model:value="customVoiceName" placeholder="Name this voice…" maxlength="40"
            size="small" class="flex-1 min-w-32"
          />
          <n-button
            size="small" type="primary" ghost
            :loading="customSaveLoading"
            :disabled="qwenMode === 'clone' ? !qwenCloneRef : !qwenDesignPrompt.trim()"
            @click="saveCurrentAsCustom"
          >
            {{ qwenMode === 'design' ? 'Save design' : 'Save voice' }}
          </n-button>
        </div>
        <p class="text-[11px] text-gray-400 px-1">
          {{ qwenMode === 'design'
            ? 'Saves the description above as a reusable voice (first save builds it, may take a few minutes). Same name overwrites = update.'
            : 'Saves the uploaded clip + transcript above as a reusable voice. Same name overwrites = update.' }}
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
              :type="modelValue === c.name ? 'primary' : 'default'"
              @click="selectVoice(c.name)"
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

      <n-form-item label="Mode:">
        <n-radio-group
          v-model:value="qwenMode" name="qwenModePanel" size="small"
          class="flex flex-wrap gap-2" @update:value="saveAll"
        >
          <n-radio-button
            v-for="m in qwenModes.length ? qwenModes : [{ value: 'custom', label: 'Preset + Instruct' }, { value: 'design', label: 'Voice Design' }, { value: 'clone', label: 'Voice Clone' }]"
            :key="m.value" :value="m.value"
          >
            <span>{{ m.label }}</span>
          </n-radio-button>
        </n-radio-group>
      </n-form-item>
      <p class="text-xs text-gray-500 dark:text-gray-400 -mt-2 px-1">
        {{ (qwenModes.find((m) => m.value === qwenMode) || {} as QwenMode).description || "" }}
      </p>

      <template v-if="qwenMode === 'design'">
        <n-form-item label="Voice Description:">
          <n-input
            v-model:value="qwenDesignPrompt" type="textarea" :rows="3"
            placeholder="Describe the voice…"
            class="w-full" @update:value="saveAll"
          />
        </n-form-item>
        <div v-if="qwenDesignPresets.length" class="flex flex-wrap gap-2 -mt-2">
          <n-button
            v-for="p in qwenDesignPresets" :key="p.label" size="tiny" ghost
            @click="qwenDesignPrompt = p.value; saveAll()"
          >
            {{ p.label }}
          </n-button>
        </div>
      </template>

      <template v-if="qwenMode === 'clone'">
        <p class="text-[11px] text-gray-400 px-1 -mt-2 mb-1">
          Clone copies your reference clip — emotion and pace come from the clip itself, not from steering text.
        </p>
        <n-form-item label="Reference Clip (~3s+ clear speech):">
          <div class="flex items-center gap-2 w-full">
            <n-button size="small" :loading="qwenCloning" @click="qwenRefInput?.click()">
              {{ qwenCloneRef ? "Replace clip" : "Upload clip" }}
            </n-button>
            <input
              ref="qwenRefInput" type="file" accept=".mp3,.wav,.m4a,.aac,.ogg,.flac,.wma"
              class="hidden" @change="uploadQwenCloneRef"
            />
            <span class="text-xs text-gray-500 truncate">
              {{ qwenCloneRef ? qwenCloneRef.split('/').pop() : "No clip uploaded" }}
            </span>
          </div>
        </n-form-item>
        <p v-if="qwenCloneError" class="text-xs text-red-500 -mt-2">{{ qwenCloneError }}</p>
        <n-form-item label="Reference Transcript:">
          <n-input
            v-model:value="qwenCloneText" type="textarea" :rows="2"
            placeholder="Exact words in the clip (empty = timbre-only clone)"
            class="w-full" @update:value="saveAll"
          />
        </n-form-item>
      </template>

      <n-form-item label="Language:">
        <n-select
          v-model:value="qwenLang"
          :options="languageOptions.map((l) => ({ label: l.label, value: l.code }))"
          class="w-full" @update:value="saveAll"
        />
      </n-form-item>
      <p class="text-[11px] text-gray-400 px-1 -mt-2">
        Active: {{ qwenMode }} · {{ qwenLang }} · {{ modelValue || qwenSpeaker }}{{ steeringSummary }}
      </p>

      <template v-if="qwenMode === 'custom'">
        <n-form-item label="Steer the voice (instruct):">
          <n-input
            v-model:value="qwenInstruct" type="textarea" :rows="2"
            placeholder="e.g. Speak cheerfully and energetically… Empty = neutral."
            class="w-full" @update:value="saveAll"
          />
        </n-form-item>
        <div v-if="qwenInstructPresets.length" class="flex flex-wrap gap-2 -mt-2">
          <n-button
            v-for="p in qwenInstructPresets" :key="p.label" size="tiny" ghost
            @click="qwenInstruct = p.value; saveAll()"
          >
            {{ p.label }}
          </n-button>
        </div>
      </template>

      <n-form-item label="Model:">
        <n-select
          v-model:value="qwenModel"
          :options="[{ label: 'Auto (per-mode default, 1.7B)', value: '' }, ...Object.entries(qwenModels).map(([k, v]) => ({ label: `${k} — ${v}`, value: v }))]"
          placeholder="Auto (per-mode default, 1.7B)"
          class="w-full" @update:value="saveAll"
        />
      </n-form-item>

      <template v-if="showPreview">
        <n-divider class="my-3">Audition</n-divider>
        <n-form-item label="Preview text:">
          <n-input v-model:value="previewText" type="textarea" :rows="2" class="w-full" />
        </n-form-item>
        <div class="flex items-center gap-2 mb-2 flex-wrap">
          <n-button size="small" type="primary" ghost :loading="previewLoading" @click="previewQwenVoice">
            Generate preview
          </n-button>
          <span class="text-[11px] text-gray-400">First run downloads the model (~3GB), then it's instant.</span>
        </div>
        <p v-if="previewError" class="text-xs text-red-500 mb-2">{{ previewError }}</p>
        <audio v-if="previewUrl" :src="previewUrl" controls class="w-full h-8 mb-2"></audio>
      </template>
    </template>

    <template v-else-if="engine === 'tiktok'">
      <p class="text-xs text-gray-500 dark:text-gray-400 px-1">
        Cloud voices — the voice selected above is used per video.
      </p>
    </template>
  </div>
</template>
<style scoped></style>
