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
import { useStorage } from "@vueuse/core";

interface Step {
  text: string; // Display text for the step
  afterText?: string; // Text to show after step completion
  async?: boolean; // If true, waits for external trigger to proceed
  duration?: number; // Duration in ms before proceeding (default: 2000)
  action?: () => void; // Function to execute when step is active
}
const router = useRouter();
const API_URL = "http://localhost:8080";

interface MagicSyncAccount {
  platform: string
  accountName: string
  isActive: boolean
}

interface MagicSyncBusiness {
  id: string
  name: string
  url: string
  apiToken: string
  videoBaseUrl: string
}

const { globalSettings } = useGlobalSettings();
const { video, defaults: videoDefaults } = useVideoSettings();
const { get: getCustomVoiceByName, toQwenParams } = useCustomVoices();

/**
 * If the selected voice is a saved custom voice (IndexedDB "My voices"),
 * attach its full stored config so the backend needs no prior global state
 * (works even after a backend restart wiped in-memory TTS settings).
 */
const customVoiceParams = async () => {
  try {
    const custom = await getCustomVoiceByName(video.value.voice);
    return custom ? toQwenParams(custom) : {};
  } catch {
    return {};
  }
};

// Load subtitle templates from API
let settingsData: any = null;
let settingsLoadError: string | null = null;
try {
  const settingsResponse = await $fetch<{ data: any }>(`${API_URL}/api/settings`);
  settingsData = settingsResponse.data;
} catch (e: any) {
  settingsLoadError = e?.message || "Backend unreachable";
  console.error("Failed to load settings (is the backend running on " + API_URL + "?):", e);
}
const subtitleTemplateOptions = computed(() => {
  return settingsData?.subtitleTemplates?.options?.map((t: any) => ({
    label: t.label,
    value: t.value,
  })) || [
    { label: 'Classic Yellow', value: 'classic' },
    { label: 'Modern Glow', value: 'modern_glow' },
    { label: 'Bold Outline', value: 'bold_outline' },
    { label: 'Minimal', value: 'minimal' },
    { label: 'Cinematic', value: 'cinematic' },
  ];
});

const scriptTemplateOptions = computed(() => {
  return settingsData?.scriptTemplates?.options?.map((t: any) => ({
    label: t.label,
    value: t.value,
    description: t.description,
  })) || [
    { label: 'Viral Shorts', value: 'viral_shorts' },
  ];
});

// Add video segment function
let imagePickerId = 0
const imageInputs = ref<Record<number, HTMLInputElement>>({})

const handleImageUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  const formData = new FormData()
  for (const file of Array.from(input.files)) {
    formData.append("file", file)
  }

  try {
    const res = await $fetch<{ status: string; data: { paths: string[] }; message?: string }>(
      `${API_URL}/api/upload-image`,
      { method: "POST", body: formData }
    )
    if (res.status === "success") {
      for (let i = 0; i < input.files.length; i++) {
        video.value.images.push({
          path: res.data.paths[i],
          name: input.files[i].name,
          duration: video.value.imageDuration || 5,
        })
      }
    }
  } catch (e: any) {
    console.error("Image upload failed", e)
  }

  input.value = ""
}

const removeImage = (idx: number) => {
  video.value.images.splice(idx, 1)
}

const triggerImagePicker = () => {
  const id = ++imagePickerId
  const input = document.createElement("input")
  input.type = "file"
  input.accept = ".png,.jpg,.jpeg,.webp,.bmp,.gif"
  input.multiple = true
  input.style.display = "none"
  input.addEventListener("change", handleImageUpload)
  document.body.appendChild(input)
  imageInputs.value[id] = input
  input.click()
}

const addVideoSegment = () => {
  if (video.value.selectedVideoUrls.length > 0) {
    video.value.videoSegments.push({
      url: video.value.selectedVideoUrls[0].url,
      startTime: 0,
      endTime: 10,
    });
  }
};

const showModal = ref(!video.value.script);
const extraPrompt = ref(false);

const scriptLengthOptions = [
  { label: "Short (~30s, ~80 words)", value: "short" },
  { label: "Standard (~60s, ~120 words)", value: "standard" },
  { label: "Long (~2 min, ~220 words)", value: "long" },
  { label: "Extended (~3 min, ~350 words)", value: "extended" },
  { label: "Epic (~4+ min, ~500 words)", value: "epic" },
];

const currentState = ref<"script" | "loading" | "Error">("script");
const scriptError = ref<string | null>(null);

const HandleGenerateScript = async () => {
  try {
    currentState.value = "loading";
    scriptError.value = null;
    showModal.value = false;
    const { data } = await $fetch<{
      data: { script: string; search: string[] };
    }>(`${API_URL}/api/script`, {
      method: "POST",
      // 5 min: script = 2 LLM calls; abort instead of spinning forever.
      timeout: 300000,
      body: {
        videoSubject: video.value.videoSubject,
        aiModel: globalSettings.value.aiModel,
        extraPrompt: video.value.extraPrompt,
        scriptTemplate: video.value.scriptTemplate,
        scriptLength: video.value.scriptLength || "standard",
      },
    });

    video.value.script = data.script;
    console.log({ data });

    video.value.search = data.search.join(",");
    currentState.value = "script";
  } catch (error: any) {
    console.log({ error });
    currentState.value = "Error";
    scriptError.value =
      error?.name === "TimeoutError" || /timeout|aborted/i.test(error?.message || "")
        ? "Script generation timed out after 5 minutes. The AI provider is likely stalled — check Settings → AI Model Provider (cookies status) or try again."
        : (error?.data?.message || error?.message || "Script generation failed. Try again.");
  }
};
// State management — now duration-based so steps auto-progress while backend works
const loaderStates = reactive({
  isGeneratingVideo: false,
  isCombiningVideos: false,
  isAddingSubtitles: false,
});
const uiState = reactive({
  isSimpleLoading: false,
  isAfterTextLoading: false,
  closeSimple: () => {
    uiState.isSimpleLoading = false;
  },
  closeAsync: () => {
    uiState.isAfterTextLoading = false;
  },
});
// Video generation steps — tracked via backend progress (duration simulates while API is pending)
const asyncLoadingSteps = computed<Step[]>(() => [
  {
    text: "Generating Voice",
    duration: 1800,
    afterText: "Voice Generated",
  },
  {
    text: "Downloading & Cutting Videos",
    duration: 2500,
    afterText: "Videos Ready",
  },
  {
    text: "Combining Audio and Video",
    duration: 2200,
    afterText: "Video Generated",
  },
  {
    text: "Adding Subtitles",
    duration: 1800,
    afterText: "Subtitles Added",
  },
  {
    text: "Saving final video",
    duration: 800,
    action: handleAsyncLoadingComplete,
  },
]);
function handleAsyncLoadingComplete() {
  uiState.isAfterTextLoading = false;
}

// Music adding steps — shown in same style modal when adding music
const musicUiState = reactive({ loading: false })
const musicSteps = computed<Step[]>(() => [
  { text: "Preparing audio", duration: 1200, afterText: "Audio prepared" },
  { text: "Mixing music & SFX", duration: 1800, afterText: "Music mixed" },
  { text: "Finalizing video", duration: 1000, action: () => { musicUiState.loading = false } },
])


const HandleGenerateVideo = async () => {
  try {
    // Show stepped loader that auto-progresses while backend works (tracks backend via keep-open)
    uiState.isAfterTextLoading = true;
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
        videoOrderMode: (video.value as any).videoOrderMode || "random",
        subtitlesPosition: video.value.subtitlePosition
          ? `center,${video.value.subtitlePosition}`
          : "",
        subtitleTemplate: video.value.subtitleTemplate || "classic",
        aspectRatio: video.value.aspectRatio || "9:16",
        customSubtitle: video.value.customSubtitle || "",
        scriptTemplate: video.value.scriptTemplate || "",
        customAudioPath: video.value.useCustomAudio ? video.value.customAudioPath : "",
        audioStartTime: video.value.audioStartTime || 0,
        audioEndTime: video.value.audioEndTime || 0,
        images: (video.value.images || []).map((img: any) => img.path),
        imageDurations: (video.value.images || []).map((img: any) => img.duration),
        imageDuration: video.value.imageDuration || 5,
        clipDuration: video.value.clipDuration || 10,
        ...(await customVoiceParams()),
      },
    });
    video.value.finalVideoUrl = data.finalVideo;
    video.value.lastMetadata = data.metadata;
    currentState.value = "script";

  } catch (error) {
    console.log({ error });
    currentState.value = "Error";
  } finally {
    uiState.isAfterTextLoading = false;
  }
};

// Re-render audio + video only — no AI calls (no script/search/metadata regeneration).
// Reuses the current script, selected videos and settings, and re-attaches lastMetadata.
const HandleRegenerateVideoOnly = async () => {
  try {
    uiState.isAfterTextLoading = true;
    currentState.value = "loading";
    showModal.value = false;
    const { data } = await $fetch<{
      data: {
        finalAudio: string;
        subtitles: string;
        finalVideo: string;
      };
    }>(`${API_URL}/api/regenerate-video`, {
      method: "POST",
      body: {
        script: video.value.script,
        voice: video.value.voice || globalSettings.value.voice,
        search: video.value.search.split(","),
        aiModel: video.value.aiModel || globalSettings.value.aiModel,
        selectedVideoUrls: video.value.selectedVideoUrls,
        videoOrderMode: (video.value as any).videoOrderMode || "random",
        subtitlesPosition: video.value.subtitlePosition
          ? `center,${video.value.subtitlePosition}`
          : "",
        subtitleTemplate: video.value.subtitleTemplate || "classic",
        aspectRatio: video.value.aspectRatio || "9:16",
        customSubtitle: video.value.customSubtitle || "",
        scriptTemplate: video.value.scriptTemplate || "",
        customAudioPath: video.value.useCustomAudio ? video.value.customAudioPath : "",
        audioStartTime: video.value.audioStartTime || 0,
        audioEndTime: video.value.audioEndTime || 0,
        images: (video.value.images || []).map((img: any) => img.path),
        imageDurations: (video.value.images || []).map((img: any) => img.duration),
        imageDuration: video.value.imageDuration || 5,
        clipDuration: video.value.clipDuration || 10,
        metadata: video.value.lastMetadata || {},
        ...(await customVoiceParams()),
      },
    });
    video.value.finalVideoUrl = data.finalVideo;
    // Keep existing metadata — backend reused it, nothing AI-generated to update.
    currentState.value = "script";

  } catch (error) {
    console.log({ error });
    currentState.value = "Error";
  } finally {
    uiState.isAfterTextLoading = false;
  }
};

const settingsModal = ref<"ALL" | "VOICE" | "SUBTITLE" | "MUSIC" | "IDLE">(
  "IDLE"
);
const settingsModalState = computed({
  get: () => settingsModal.value !== "IDLE",
  set: (val) => { if (!val) settingsModal.value = "IDLE"; }
});
const HandleUpdateSettings = async (
  type: "ALL" | "VOICE" | "SUBTITLE" | "MUSIC"
) => {
  settingsModal.value = type;
};

const HandleAddAudio = async () => {
  try {
    musicUiState.loading = true;
    currentState.value = "loading";
    const musicSource = video.value.musicSource || "library";
    const songPath =
      musicSource === "library" ? video.value.selectedAudio || "" : "";
    const backgroundMusicFromVideo =
      musicSource === "video" ? video.value.backgroundMusicFromVideo || "" : "";
    const hasMusic =
      (musicSource === "library" && !!songPath) ||
      (musicSource === "video" && !!backgroundMusicFromVideo);
    if (!hasMusic) {
      currentState.value = "script";
      return;
    }
    const { data } = await $fetch<{ data: { finalVideo: string } }>(
      `${API_URL}/api/addAudio`,
      {
        method: "POST",
        body: {
          finalVideo: video.value.finalVideoUrl,
          songPath,
          aiModel: video.value.aiModel || globalSettings.value.aiModel,
          musicSource,
          backgroundMusicFromVideo,
          aspectRatio: video.value.aspectRatio || "9:16",
          musicVolume: video.value.musicVolume ?? 0.1,
          sfxVolume: video.value.sfxVolume ?? 0.9,
          soundEffects: (video.value.soundEffects || []).map((s: any) =>
            typeof s === "string" ? { path: s, startTime: 0 } : s,
          ),
        },
      }
    );
    video.value.finalVideoUrl = data.finalVideo;
  } catch (error) {
    console.log({ error });
  } finally {
    musicUiState.loading = false;
    currentState.value = "script";
  }
};
const HandleClear = () => {
  // Reset from the store's defaults (single source of truth — can never drift)
  video.value = JSON.parse(JSON.stringify(videoDefaults));
  settingsModal.value = "IDLE";
  showModal.value = true;
}

const HandleClearAndGoToVideos = () => {
  HandleClear();
  router.push("/videos");
};

const SearchModal = ref(false);
const HandleOpenSearchVideo = () => {
  SearchModal.value = !SearchModal.value;
};

// Sound effects library + picker state
const sfxLibrary = ref<string[]>([]);
const sfxPick = ref<string | null>(null);
const sfxOptions = computed(() => [
  ...sfxLibrary.value.map((name) => ({ label: name, value: name })),
  ...["ding", "buzz", "pop", "whoosh", "chime"]
    .filter((n) => !sfxLibrary.value.some((s) => s.toLowerCase().includes(n)))
    .map((n) => ({ label: `${n} (built-in tone)`, value: `builtin:${n}` })),
]);
const addSfx = () => {
  if (!sfxPick.value) return;
  const list = video.value.soundEffects ?? [];
  const entry = sfxPick.value.startsWith("builtin:")
    ? { path: sfxPick.value, startTime: 0 }
    : { path: `static/assets/sfx/${sfxPick.value}`, startTime: 0 };
  if (!list.some((s) => s.path === entry.path)) {
    video.value.soundEffects = [...list, entry];
  }
  sfxPick.value = null;
};

const loadSfxLibrary = async () => {
  try {
    const res = await $fetch<{ status: string; data: { sfx: string[] } }>(`${API_URL}/api/getSfx`);
    if (res.status === "success") {
      sfxLibrary.value = (res.data.sfx || []).filter((f) => !f.startsWith("."));
    }
  } catch (e) {
    console.error("Failed to load SFX library", e);
  }
};
onMounted(loadSfxLibrary);

// Thumbnail extraction modal
const thumbnailModal = ref(false)
const thumbnailTargetUrl = ref('')
const thumbnailTimestamp = ref(0)
const extractingThumbnail = ref(false)

const openThumbnailModal = () => {
  thumbnailModal.value = true
}

const extractThumbnail = async () => {
  if (!thumbnailTargetUrl.value) return
  const sourceUrl = thumbnailTargetUrl.value

  extractingThumbnail.value = true
  try {
    const { Input, ALL_FORMATS, UrlSource, CanvasSink } = await import('mediabunny')

    const input = new Input({
      source: new UrlSource(sourceUrl),
      formats: ALL_FORMATS,
    })

    const videoTrack = await input.getPrimaryVideoTrack()
    if (!videoTrack) throw new Error('No video track found')

    const displayWidth = await videoTrack.getDisplayWidth()
    const displayHeight = await videoTrack.getDisplayHeight()
    const thumbSize = 400
    const width = displayWidth > displayHeight
      ? thumbSize
      : Math.floor(thumbSize * displayWidth / displayHeight)
    const height = displayHeight > displayWidth
      ? thumbSize
      : Math.floor(thumbSize * displayHeight / displayWidth)

    const sink = new CanvasSink(videoTrack, {
      width: Math.floor(width * window.devicePixelRatio),
      height: Math.floor(height * window.devicePixelRatio),
      fit: 'fill',
    })

    const wrappedCanvas = await sink.canvasAtTimestamp(thumbnailTimestamp.value)
    input.close()

    if (!wrappedCanvas) throw new Error('Could not extract frame')

    const canvas = wrappedCanvas.canvas as HTMLCanvasElement
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(b => b ? resolve(b) : reject(new Error('Canvas toBlob failed')), 'image/jpeg', 0.9)
    })

    const formData = new FormData()
    formData.append('file', blob, `thumbnail_${thumbnailTimestamp.value}s.jpg`)

    const res = await $fetch<{ status: string; data: { paths: string[] } }>(
      `${API_URL}/api/upload-image`,
      { method: 'POST', body: formData }
    )

    if (res.status === 'success') {
      video.value.images.unshift({
        path: res.data.paths[0],
        name: `Thumbnail @${thumbnailTimestamp.value}s`,
        duration: 0.05,
      })
    }
  } catch (e: any) {
    console.error("Thumbnail extraction failed", e)
  } finally {
    extractingThumbnail.value = false
    thumbnailModal.value = false
  }
}

// Schedule Upload state
const scheduleModal = ref(false)
const scheduleDate = ref<number | null>(null)
const scheduleTime = ref<number | null>(null)
const scheduleContent = ref('')
const scheduleTitle = ref('')
const scheduleDescription = ref('')
const scheduling = ref(false)
const scheduleResult = ref<string | null>(null)
const selectedPlatforms = ref<string[]>([])
const magicsyncAccounts = ref<MagicSyncAccount[]>([])
const magicsyncLoading = ref(false)
const magicsyncBusinesses = useStorage<MagicSyncBusiness[]>("MAGICSYNC_BUSINESSES", [])
const selectedBusinessId = ref<string | null>(null)

const openScheduleModal = async () => {
  scheduleDate.value = null
  scheduleTime.value = null
  scheduleResult.value = null
  selectedPlatforms.value = []
  magicsyncAccounts.value = []
  scheduleContent.value = ''
  scheduleTitle.value = ''
  scheduleDescription.value = ''

  // Pre-fill from stored generate metadata
  if (video.value.lastMetadata) {
    scheduleContent.value = video.value.lastMetadata.post_content || video.value.lastMetadata.title || video.value.lastMetadata.description || ''
    scheduleTitle.value = video.value.lastMetadata.title || ''
    scheduleDescription.value = video.value.lastMetadata.description || ''
    if (video.value.lastMetadata.suggested_schedule) {
      const d = new Date(video.value.lastMetadata.suggested_schedule)
      scheduleDate.value = d.getTime()
      scheduleTime.value = d.getTime()
    }
  }

  if (magicsyncBusinesses.value.length > 0) {
    selectedBusinessId.value = magicsyncBusinesses.value[0].id
    await fetchAccountsForBusiness(selectedBusinessId.value)
  } else {
    selectedBusinessId.value = null
  }

  scheduleModal.value = true
}

async function fetchAccountsForBusiness(businessId: string | null) {
  if (!businessId) {
    magicsyncAccounts.value = []
    selectedPlatforms.value = []
    return
  }
  const biz = magicsyncBusinesses.value.find(b => b.id === businessId)
  if (!biz) return
  magicsyncLoading.value = true
  magicsyncAccounts.value = []
  selectedPlatforms.value = []
  try {
    const res = await $fetch<{ status: string; data: { accounts: MagicSyncAccount[] }; message?: string }>(
      `${API_URL}/api/magicsync/accounts`,
      { method: 'POST', body: { url: biz.url, apiToken: biz.apiToken } }
    )
    if (res.status === 'success') {
      magicsyncAccounts.value = res.data.accounts.filter(a => a.isActive)
      selectedPlatforms.value = [...new Set(magicsyncAccounts.value.map(a => a.platform))]
    }
  } catch (e) {
    console.error('Failed to fetch MagicSync accounts', e)
  } finally {
    magicsyncLoading.value = false
  }
}

const togglePlatform = (platform: string) => {
  const idx = selectedPlatforms.value.indexOf(platform)
  if (idx >= 0) {
    selectedPlatforms.value.splice(idx, 1)
  } else {
    selectedPlatforms.value.push(platform)
  }
}

const uniquePlatforms = computed(() => {
  const seen = new Set<string>()
  for (const acc of magicsyncAccounts.value) {
    seen.add(acc.platform)
  }
  return [...seen]
})

const handleSchedule = async () => {
  if (!scheduleDate.value || !scheduleTime.value) return
  if (selectedPlatforms.value.length === 0) return
  if (!selectedBusinessId.value) return

  const biz = magicsyncBusinesses.value.find(b => b.id === selectedBusinessId.value)
  if (!biz) return

  scheduling.value = true
  scheduleResult.value = null

  try {
    const date = new Date(scheduleDate.value)
    const time = new Date(scheduleTime.value)
    date.setHours(time.getHours(), time.getMinutes(), 0, 0)
    const scheduledAt = date.toISOString()
    const filename = video.value.finalVideoUrl.split('/').pop()

    await $fetch(`${API_URL}/api/schedule-to-magicsync`, {
      method: 'POST',
      body: {
        videoFilename: filename,
        scheduledAt,
        content: scheduleContent.value,
        title: scheduleTitle.value,
        description: scheduleDescription.value,
        platforms: selectedPlatforms.value,
        url: biz.url,
        apiToken: biz.apiToken,
        videoBaseUrl: biz.videoBaseUrl,
      }
    })

    scheduleResult.value = 'success'
    setTimeout(() => { scheduleModal.value = false }, 2000)
  } catch (e: any) {
    scheduleResult.value = `Error: ${e?.data?.message || e?.message || 'Unknown error'}`
  } finally {
    scheduling.value = false
  }
}

const customAudioInput = ref(null);
const customAudioPlayer = ref<HTMLAudioElement | null>(null);
const isRecording = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const previewUrl = ref('');
const isPreviewLoading = ref(false);

const handleCustomAudioUpload = async (event: any) => {
  const file = event.target?.files?.[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await $fetch<{ data: { path: string } }>(`${API_URL}/api/upload-custom-audio`, {
      method: 'POST',
      body: formData,
    });
    video.value.customAudioPath = res.data.path;
    video.value.audioStartTime = 0;
    video.value.audioEndTime = 0;
    previewUrl.value = '';
  } catch (e) {
    console.error('Upload failed', e);
  }
};

const markAudioStart = () => {
  if (customAudioPlayer.value) {
    video.value.audioStartTime = Math.floor(customAudioPlayer.value.currentTime);
  }
};

const markAudioEnd = () => {
  if (customAudioPlayer.value) {
    video.value.audioEndTime = Math.ceil(customAudioPlayer.value.currentTime);
  }
};

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('file', blob, `recording_${Date.now()}.webm`);
      try {
        const res = await $fetch<{ data: { path: string } }>(`${API_URL}/api/upload-custom-audio`, {
          method: 'POST',
          body: formData,
        });
        video.value.customAudioPath = res.data.path;
        video.value.audioStartTime = 0;
        video.value.audioEndTime = 0;
        previewUrl.value = '';
      } catch (e) {
        console.error('Upload recording failed', e);
      }
      stream.getTracks().forEach(t => t.stop());
    };
    recorder.start();
    mediaRecorder.value = recorder;
    isRecording.value = true;
  } catch (e) {
    console.error('Recording failed', e);
  }
};

const stopRecording = () => {
  if (mediaRecorder.value) {
    mediaRecorder.value.stop();
    isRecording.value = false;
  }
};

const handlePreview = async () => {
  if (!video.value.selectedVideoUrls.length) return;
  isPreviewLoading.value = true;
  previewUrl.value = '';
  try {
    const { Input, ALL_FORMATS, BlobSource, Output, BufferTarget, Mp4OutputFormat, CanvasSource, CanvasSink, AudioBufferSource } = await import('mediabunny');

    const clips = video.value.selectedVideoUrls;
    const canvas = document.createElement('canvas');
    canvas.width = 1080;
    canvas.height = 1920;

    // Determine audio duration
    let audioDuration = 10;
    let audioBuffer: AudioBuffer | null = null;
    if (video.value.customAudioPath) {
      const audioResp = await fetch(`${API_URL}/${video.value.customAudioPath}`);
      const audioBlob = await audioResp.blob();
      const audioCtx = new AudioContext();
      const fullBuffer = await audioCtx.decodeAudioData(await audioBlob.arrayBuffer());
      const start = video.value.audioStartTime || 0;
      const end = video.value.audioEndTime > 0 ? video.value.audioEndTime : fullBuffer.duration;
      audioDuration = end - start;
      const sampleRate = fullBuffer.sampleRate;
      const channels = fullBuffer.numberOfChannels;
      const startSample = Math.floor(start * sampleRate);
      const frameCount = Math.floor((end - start) * sampleRate);
      const segmentBuffer = audioCtx.createBuffer(channels, Math.max(1, frameCount), sampleRate);
      for (let c = 0; c < channels; c++) {
        const src = fullBuffer.getChannelData(c).slice(startSample, startSample + frameCount);
        segmentBuffer.copyToChannel(src, c);
      }
      audioBuffer = segmentBuffer;
      audioCtx.close();
    }

    const output = new Output({
      format: new Mp4OutputFormat(),
      target: new BufferTarget(),
    });

    const videoSource = new CanvasSource(canvas, { codec: 'avc', width: 1080, height: 1920, bitrate: 4000000 });
    output.addVideoTrack(videoSource);

    if (audioBuffer) {
      const source = new AudioBufferSource({ codec: 'aac', bitrate: 128000 });
      output.addAudioTrack(source);
      await output.start();
      await source.add(audioBuffer);
    } else {
      await output.start();
    }

    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, 1080, 1920);

    const durationPerClip = audioDuration / clips.length;

    for (let i = 0; i < clips.length; i++) {
      const clip = clips[i];
      const videoUrl = clip.videoUrl?.link || `${API_URL}/${clip.url}`;
      const resp = await fetch(videoUrl);
      const blob = await resp.blob();
      const input = new Input({ source: new BlobSource(blob), formats: ALL_FORMATS });
      const tracks = await input.getVideoTracks();
      if (!tracks.length) continue;
      const sink = new CanvasSink(tracks[0]);
      const clipStart = i * durationPerClip;

      for await (const wrapped of sink.canvases(0, durationPerClip)) {
        ctx.drawImage(wrapped.canvas, 0, 0, 1080, 1920);
        await videoSource.add(clipStart + wrapped.timestamp, wrapped.duration);
      }
    }

    await output.finish();
    const buffer = output.target.buffer as ArrayBuffer;
    const blob = new Blob([buffer], { type: 'video/mp4' });
    previewUrl.value = URL.createObjectURL(blob);
  } catch (e) {
    console.error('Preview failed', e);
  } finally {
    isPreviewLoading.value = false;
  }
};

function handleComplete() {
  // Handle Loading Complete
}
// Event handlers
function handleStateChange(state: number) {
  // Handle Loading State Change
}
</script>

<template>
  <n-modal v-model:show="showModal" :mask-closable="false">

    <div class="bg-white dark:bg-neutral-800 p-8 border border-clipper-ink/08 dark:border-white/08 py-16 text-clipper-ink dark:text-white rounded-2xl min-w-2xl">
      <h1 class="text-3xl font-extrabold">
        {{ $t("video.generate.step.one.title") }}
      </h1>

      <n-form-item :show-label="false" class="mt-10">
        <n-input v-model:value="video.videoSubject"
          :placeholder="$t('video.generate.step.one.videoSubject.placeholder')" type="textarea" show-count clearable
          :autosize="{
            minRows: 10,
            maxRows: 20,
          }" class="p-5 h-full bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl border-none" />
      </n-form-item>
      <n-form-item label="Extra Prompt:">
        <div class="w-full">
          <n-switch v-model:value="extraPrompt"> </n-switch>
          <n-collapse-transition :show="extraPrompt">
            <n-form-item :show-label="false" class="mt-10">
              <n-input v-model:value="video.extraPrompt" :placeholder="$t('video.generate.step.one.extraPrompt.placeholder')
                " type="textarea" show-count clearable :autosize="{
                  minRows: 5,
                  maxRows: 8,
                }" class="p-5 w-full bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl border-none" />
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
  <MultiStepLoader :steps="asyncLoadingSteps" :loading="uiState.isAfterTextLoading" @state-change="handleStateChange"
    @complete="handleComplete" @close="uiState.closeAsync" />
  <MultiStepLoader :steps="musicSteps" :loading="musicUiState.loading" @close="musicUiState.loading = false" />
  <n-spin :show="currentState === 'loading'">
    <div>
      <div v-if="settingsLoadError" class="max-w-screen-xl mx-auto mt-4 bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg p-3">
        <p class="text-xs font-semibold text-red-600 dark:text-red-400">Backend unreachable ({{ API_URL }}) — start the Flask backend on port 8080 and reload. Templates below are defaults.</p>
      </div>
      <main class="grid grid-cols-5 gap-5 pr-10 relative">
        <!-- Header -->
        <section class="grid grid-cols-2 gap-10 col-span-3">
          <section class="input col-span-2 rounded-lg min-h-96">
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold opacity-70">Script Template:</span>
                <n-select
                  v-model:value="video.scriptTemplate"
                  :options="scriptTemplateOptions"
                  placeholder="Select template"
                  size="small"
                  class="w-48"
                  clearable
                />
                <span class="text-sm font-semibold opacity-70 ml-2">Length:</span>
                <n-select
                  v-model:value="video.scriptLength"
                  :options="scriptLengthOptions"
                  size="small"
                  class="w-56"
                />
              </div>
              <n-button
                v-if="video.script"
                type="warning"
                dashed
                size="small"
                @click="HandleGenerateScript"
              >
                Regenerate Script
              </n-button>
            </div>
            <div v-if="scriptError" class="mb-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 flex items-start justify-between gap-3">
              <p class="text-xs text-red-600 dark:text-red-400">{{ scriptError }}</p>
              <button class="text-xs font-semibold underline shrink-0" @click="HandleGenerateScript">Retry</button>
            </div>
            <n-form-item :show-label="false" path="script">
              <n-input v-model:value="video.script" :placeholder="$t('video.generate.step.two.script.placeholder')"
                type="textarea" show-count clearable :autosize="{
                  minRows: 18,
                  maxRows: 25,
                }" class="p-5 h-full bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl border-none" />
            </n-form-item>
          </section>
          <section class="setting bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl min-h-40 p-5">
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
            <n-button ghost type="primary" class="mt-5" @click="HandleOpenSearchVideo">
              Search and select videos
            </n-button>
            
            <!-- Video Segment Selection -->
            <div v-if="video.selectedVideoUrls.length > 0" class="mt-4 p-3 bg-slate-200 dark:bg-slate-700 rounded-lg">
              <div class="text-sm font-bold mb-2">Video Segments (from - to):</div>
              <div v-for="(seg, idx) in video.videoSegments" :key="idx" class="flex items-center gap-2 mb-2">
                <span class="text-xs truncate w-20">{{ seg.url.split('/').pop() }}</span>
                <n-input-number
                  v-model:value="seg.startTime"
                  :min="0"
                  :max="seg.endTime"
                  size="small"
                  class="w-16"
                  placeholder="Start"
                />
                <span>-</span>
                <n-input-number
                  v-model:value="seg.endTime"
                  :min="seg.startTime"
                  size="small"
                  class="w-16"
                  placeholder="End"
                />
                <n-button size="small" quaternary @click="video.videoSegments.splice(idx, 1)">
                  <Icon name="ph:trash" />
                </n-button>
              </div>
              <n-button size="small" quaternary @click="addVideoSegment">
                <Icon name="ph:plus" /> Add Segment
              </n-button>
            </div>
          </section>
          <section class="aspect-ratio bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl min-h-40 p-5">
            <header class="flex items-center">
              <Icon name="icon-park-outline:square-small" size="24" />
              <span class="text-lg ml-2">Aspect Ratio</span>
            </header>
            <article class="mt-8 opacity-80">
              <n-radio-group v-model:value="video.aspectRatio" name="aspectRatio" class="flex flex-wrap gap-2">
                <n-radio-button value="9:16">9:16</n-radio-button>
                <n-radio-button value="16:9">16:9</n-radio-button>
                <n-radio-button value="1:1">1:1</n-radio-button>
                <n-radio-button value="4:5">4:5</n-radio-button>
              </n-radio-group>
            </article>
          </section>
          <section class="images bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl min-h-40 p-5">
            <header class="flex items-center">
              <Icon name="material-symbols:image" size="24" />
              <span class="text-lg ml-2">Images</span>
            </header>
            <div class="mt-3 space-y-3">
              <p class="text-xs text-clipper-ink/60 dark:text-white/60">Upload images or extract a frame from a video to use as thumbnail. Images are stitched at the start of the final video.</p>

              <!-- Thumbnail extraction from video -->
              <div v-if="video.selectedVideoUrls.length > 0" class="bg-neutral-100 dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded p-3">
                <p class="text-xs font-medium mb-2">Extract Frame from Video</p>
                <n-button size="small" @click="openThumbnailModal">
                  <template #icon><Icon name="mdi:camera" /></template>
                  Select Video & Extract
                </n-button>
              </div>

              <div class="flex items-center gap-2">
                <n-button size="small" @click="triggerImagePicker">
                  <template #icon><Icon name="mdi:upload" /></template>
                  Upload Images
                </n-button>
                <n-input-number v-if="video.images?.length > 0" v-model:value="video.imageDuration" :min="1" :max="60" size="small" class="w-24">
                  <template #prefix>Sec</template>
                </n-input-number>
              </div>

              <div v-if="video.images?.length > 0" class="space-y-2">
                <div v-for="(img, idx) in video.images" :key="idx" class="flex items-center gap-2 p-2 bg-neutral-100 dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-lg">
                  <Icon name="mdi:image" class="text-clipper-green shrink-0" />
                  <span class="text-xs truncate flex-1">{{ img.name }}</span>
                  <n-input-number v-model:value="img.duration" :min="1" :max="60" size="tiny" class="w-16" />
                  <n-button size="tiny" quaternary @click="removeImage(idx)">
                    <Icon name="ph:trash" class="text-red-400" />
                  </n-button>
                </div>
              </div>
            </div>
          </section>
          <section class="clip-duration bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl min-h-40 p-5">
            <header class="flex items-center">
              <Icon name="material-symbols:timeline" size="24" />
              <span class="text-lg ml-2">Clip Duration</span>
            </header>
            <article class="mt-4 flex items-center gap-3">
              <span class="text-sm text-clipper-ink/60 dark:text-white/60">Max seconds per video clip</span>
              <n-input-number v-model:value="video.clipDuration" :min="1" :max="60" size="small" class="w-24">
                <template #prefix>Sec</template>
              </n-input-number>
            </article>
          </section>
          <section class="voice bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl min-h-40 p-5">
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
            <article class="mt-8 opacity-80 text-center flex items-center justify-center">
              <Icon name="material-symbols:person" size="36" />
              <span class="ml-2 font-black text-lg">
                {{ video.voice || globalSettings.voice }}
              </span>
            </article>
          </section>
          <section class="custom-audio bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl min-h-40 p-5">
            <header class="flex items-center">
              <Icon name="material-symbols:audio-file" size="24" />
              <span class="text-lg ml-2">Custom Audio</span>
            </header>
            <div class="mt-3">
              <n-switch v-model:value="video.useCustomAudio">
                <template #checked> Use own audio file</template>
                <template #unchecked> Use TTS voice</template>
              </n-switch>
            </div>
            <div v-if="video.useCustomAudio" class="mt-4 space-y-3">
              <div class="flex gap-2">
                <div
                  class="border-2 border-dashed border-gray-400 rounded-lg p-3 text-center cursor-pointer hover:border-clipper-green flex-1"
                  @click="customAudioInput?.click()"
                >
                  <p class="text-sm opacity-70" v-if="!video.customAudioPath">Upload audio</p>
                  <p class="text-sm text-green-500 truncate" v-else>{{ video.customAudioPath.split('/').pop() }}</p>
                  <input ref="customAudioInput" type="file" accept=".mp3,.wav,.m4a,.aac,.ogg,.flac,.wma" class="hidden" @change="handleCustomAudioUpload" />
                </div>
                <button
                  v-if="!isRecording"
                  @click="startRecording"
                  class="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm"
                  title="Record audio from microphone"
                >🎤 Record</button>
                <button
                  v-else
                  @click="stopRecording"
                  class="px-3 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 text-sm animate-pulse"
                >⏹ Stop</button>
              </div>

              <div v-if="video.customAudioPath" class="space-y-2">
                <audio
                  ref="customAudioPlayer"
                  :src="`${API_URL}/${video.customAudioPath}`"
                  controls
                  class="w-full h-8"
                ></audio>
                <div class="flex gap-2 items-center">
                  <button @click="markAudioStart" class="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700">Mark Start</button>
                  <span class="text-xs font-mono">{{ video.audioStartTime }}s</span>
                  <span class="text-xs opacity-50">→</span>
                  <span class="text-xs font-mono">{{ video.audioEndTime > 0 ? video.audioEndTime + 's' : 'end' }}</span>
                  <button @click="markAudioEnd" class="px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700">Mark End</button>
                </div>
              </div>

              <div v-if="video.selectedVideoUrls.length" class="mt-2">
                <button
                  @click="handlePreview"
                  :disabled="isPreviewLoading"
                  class="w-full px-3 py-2 bg-clipper-green text-white rounded-lg hover:opacity-90 text-sm disabled:opacity-50"
                >
                  <span v-if="isPreviewLoading">Generating preview...</span>
                  <span v-else>Preview video (browser-side)</span>
                </button>
                <video v-if="previewUrl" :src="previewUrl" controls class="w-full mt-2 rounded-lg aspect-[9/16] max-h-64 object-cover bg-black"></video>
              </div>
            </div>
          </section>
          <section class="music bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl min-h-40 p-5">
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
            
            <!-- Music Source Selection -->
            <div class="mt-4">
              <n-radio-group v-model:value="video.musicSource" name="musicSource" size="small">
                <n-radio-button value="library">From Library</n-radio-button>
                <n-radio-button value="video">From Video</n-radio-button>
              </n-radio-group>
            </div>
            
            <!-- From Video Selection -->
            <div v-if="video.musicSource === 'video'" class="mt-3">
              <n-select
                v-model:value="video.backgroundMusicFromVideo"
                :options="video.selectedVideoUrls.map((v, i) => ({
                  label: v.url.split('/').pop() || `Video ${i + 1}`,
                  value: v.url
                }))"
                placeholder="Select video for audio"
                size="small"
              />
            </div>
            
            <article class="mt-4 opacity-80 flex items-center">
              <section class="w-10 h-10 bg-slate-950 rounded-md"></section>
              <section class="ml-2 flex flex-col text-sm">
                <span v-if="video.backgroundMusicFromVideo">
                  🎵 From video: {{ video.backgroundMusicFromVideo.split('/').pop() }}
                </span>
                <span v-else-if="video.selectedAudio">
                  {{ video.selectedAudio }}
                </span>
                <span v-else class="opacity-60">No music selected</span>
              </section>
            </article>

            <!-- Music Volume -->
            <div class="mt-4">
              <div class="flex items-center justify-between text-xs opacity-70">
                <span>Music volume</span>
                <span>{{ Math.round((video.musicVolume ?? 0.15) * 100) }}%</span>
              </div>
              <n-slider v-model:value="video.musicVolume" :min="0" :max="1" :step="0.05" size="small" />
            </div>

            <!-- Sound Effects -->
            <div class="mt-4">
              <div class="flex items-center justify-between text-xs opacity-70 mb-1">
                <span>Sound effects (music auto-ducks while an effect plays)</span>
              </div>
              <div class="flex items-center gap-2">
                <n-select
                  v-model:value="sfxPick"
                  :options="sfxOptions"
                  placeholder="Add effect…"
                  size="small"
                  clearable
                  class="flex-1"
                />
                <n-button size="small" @click="addSfx" :disabled="!sfxPick">
                  <template #icon><Icon name="ph:plus" /></template>
                </n-button>
              </div>
              <div v-if="(video.soundEffects || []).length" class="mt-2 space-y-1">
                <div v-for="(sfx, idx) in video.soundEffects" :key="idx" class="flex items-center gap-2 text-xs">
                  <Icon name="mdi:music-note" class="shrink-0" />
                  <span class="truncate flex-1">{{ sfx.path.split('/').pop() }}</span>
                  <n-input-number v-model:value="sfx.startTime" size="tiny" :min="0" :max="600" class="w-20" />
                  <span class="opacity-50">s</span>
                  <n-button size="tiny" quaternary @click="video.soundEffects.splice(idx, 1)">
                    <Icon name="ph:trash" class="text-red-400" />
                  </n-button>
                </div>
              </div>
              <div class="mt-2 flex items-center justify-between text-xs opacity-70">
                <span>SFX volume</span>
                <span>{{ Math.round((video.sfxVolume ?? 0.9) * 100) }}%</span>
              </div>
              <n-slider v-model:value="video.sfxVolume" :min="0" :max="1" :step="0.05" size="small" />
            </div>
          </section>
          <section class="subtitle bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl min-h-40 p-5">
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
            
            <!-- Subtitle Template Selection -->
            <div class="mt-4">
              <n-select
                v-model:value="video.subtitleTemplate"
                :options="subtitleTemplateOptions"
                placeholder="Select template"
                size="small"
              />
            </div>
            
            <!-- Custom Subtitle Input -->
            <div class="mt-3">
              <n-collapse>
                <n-collapse-item title="Custom Subtitle" name="custom">
                  <n-input
                    v-model:value="video.customSubtitle"
                    type="textarea"
                    placeholder="Enter custom subtitle text..."
                    :autosize="{ minRows: 2, maxRows: 4 }"
                  />
                </n-collapse-item>
              </n-collapse>
            </div>
            
            <!-- Position Selector -->
            <div class="mt-3">
              <span class="text-sm opacity-70">Position:</span>
              <n-radio-group v-model:value="video.subtitlePosition" class="ml-2">
                <n-radio-button value="top">Top</n-radio-button>
                <n-radio-button value="center">Center</n-radio-button>
                <n-radio-button value="bottom">Bottom</n-radio-button>
              </n-radio-group>
            </div>
            
            <article class="mt-4 opacity-80 text-center flex items-center justify-center">
              <span class="font-black text-lg" :style="{ color: globalSettings.color }">
                {{ video.customSubtitle || 'Preview text' }}
              </span>
            </article>
          </section>
        </section>
        <section class="col-span-2">
          <header class="col-span-5 flex justify-end gap-4 mb-5" v-if="video.finalVideoUrl">
            <n-button type="tertiary" dashed size="tiny" @click="HandleGenerateVideo">Regenerate</n-button>
            <n-button
              type="info"
              dashed
              size="tiny"
              @click="HandleRegenerateVideoOnly"
              title="Re-render audio + video only. Skips AI calls (no script, search or metadata regeneration)."
            >Regenerate Video Only</n-button>
            <n-button type="tertiary" dashed size="tiny" @click="HandleClear">Clear</n-button>

            <n-button
              type="success"
              dashed
              size="tiny"
              @click="HandleAddAudio"
              :disabled="!(video.musicSource === 'video' ? video.backgroundMusicFromVideo : video.selectedAudio)"
            >
              Add Music
            </n-button>
            <n-button type="primary" dashed size="tiny" @click="openScheduleModal">
              <template #icon>
                <Icon name="mdi:calendar-clock" />
              </template>
              Schedule
            </n-button>
            <n-button type="default" dashed size="tiny" @click="HandleClearAndGoToVideos">
              Videos
            </n-button>
          </header>
          <section class="grid place-content-center">
            <div class="phone bg-slate-700 bg-opacity-10 p-1 rounded-3xl shadow">
              <section v-if="!video.finalVideoUrl"
                class="aspect-[9/16] max-w-sm rounded-3xl w-full h-[750px] px-10 grid place-content-center">
                <n-button round type="success" size="large" @click="HandleGenerateVideo">
                  <span class="text-lg px-10"> Generate </span>
                </n-button>
              </section>
              <!-- Video placeholder -->
              <video v-else class="aspect-[9/16] max-w-sm rounded-3xl"
                :src="`/api/video/${video.finalVideoUrl.split('/').pop()}`" controls></video>
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

  <n-modal v-model:show="settingsModalState" :mask-closable="false" closable @close="settingsModal = 'IDLE'"
    preset="card" class="max-w-3xl" :content-class="'bg-white dark:bg-neutral-800 p-6 py-16 text-clipper-ink dark:text-white'"
    :header-class="'bg-white dark:bg-neutral-800 p-6 py-16 text-clipper-ink dark:text-white'">
    <div class="p-10" v-if="settingsModal !== 'IDLE'">
      <GenerateScript :active-tab="settingsModal" />
    </div>
  </n-modal>

  <n-modal v-model:show="SearchModal" :mask-closable="false" closable @close="SearchModal = false" preset="card"
    class="max-w-3xl" :content-class="'bg-white dark:bg-neutral-800 p-6 py-16 text-clipper-ink dark:text-white'"
    :header-class="'bg-white dark:bg-neutral-800 p-6 py-16 text-clipper-ink dark:text-white'">
    <div class="p-10">
      <n-tabs type="line" animated>
        <n-tab-pane name="VIDEO_SEARCH" tab="Search and select" active>
          <VideoSearch />
        </n-tab-pane>
        <n-tab-pane name="VIDEO_SELECTED" tab="Selected Videos">
          <VideoSelected />
        </n-tab-pane>
        <n-tab-pane name="VIDEO_INSTAGRAM" tab="Download from Instagram">
          <Instagram />
        </n-tab-pane>

        <n-tab-pane name="VIDEO_INSTAGRAM_SELECTED" tab="Instagram">
          <InstagramVideos />
        </n-tab-pane>
        <n-tab-pane name="VIDEO_UPLOAD" tab="Upload">
          <VideoUpload />
        </n-tab-pane>
      </n-tabs>
    </div>
  </n-modal>

    <n-modal
      v-model:show="scheduleModal"
      preset="card"
      title="Schedule Upload"
      style="max-width: 520px"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <div v-if="video.finalVideoUrl">
          <p class="text-sm text-clipper-ink/60 dark:text-white/60">
            Video:
            <span class="text-white">{{ video.lastMetadata?.title || video.finalVideoUrl.split('/').pop() }}</span>
          </p>
        </div>

        <div v-if="magicsyncBusinesses.length > 0">
          <label class="block text-sm text-clipper-ink/60 dark:text-white/60 mb-1">Business</label>
          <n-select
            v-model:value="selectedBusinessId"
            :options="magicsyncBusinesses.map(b => ({ label: b.name, value: b.id }))"
            class="w-full"
            @update:value="fetchAccountsForBusiness"
          />
        </div>

        <div>
          <label class="block text-sm text-clipper-ink/60 dark:text-white/60 mb-1">Date</label>
          <n-date-picker v-model:value="scheduleDate" type="date" class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-clipper-ink/60 dark:text-white/60 mb-1">Time</label>
          <n-time-picker v-model:value="scheduleTime" class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-clipper-ink/60 dark:text-white/60 mb-1">Post Content</label>
          <n-input v-model:value="scheduleContent" type="textarea" :rows="3" placeholder="Post text..." class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-clipper-ink/60 dark:text-white/60 mb-1">Title (optional)</label>
          <n-input v-model:value="scheduleTitle" placeholder="Video title" class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-clipper-ink/60 dark:text-white/60 mb-1">Description (optional)</label>
          <n-input v-model:value="scheduleDescription" type="textarea" :rows="2" placeholder="Video description" class="w-full" />
        </div>

        <div>
          <label class="block text-sm text-clipper-ink/60 dark:text-white/60 mb-1">
            Post to
            <span v-if="magicsyncLoading" class="text-xs ml-1">(loading...)</span>
          </label>
          <div v-if="magicsyncLoading" class="flex items-center gap-2 text-sm text-gray-500">
            <n-spin size="small" />
            Fetching connected accounts...
          </div>
          <div v-else-if="magicsyncBusinesses.length === 0" class="text-sm text-clipper-ink/35 dark:text-white/40">
            No MagicSync businesses configured.
            <NuxtLink to="/settings" class="underline">Add one in Settings</NuxtLink>
          </div>
          <div v-else-if="uniquePlatforms.length === 0 && !magicsyncLoading" class="text-sm text-clipper-ink/35 dark:text-white/40">
            No connected accounts for this business.
          </div>
          <div v-else class="space-y-2">
            <div v-for="platform in uniquePlatforms" :key="platform" class="flex items-center gap-2">
              <n-checkbox
                :checked="selectedPlatforms.includes(platform)"
                @update:checked="togglePlatform(platform)"
              >
                <span class="text-sm capitalize">{{ platform }}</span>
              </n-checkbox>
            </div>
          </div>
        </div>

        <div v-if="scheduleResult === 'success'" class="text-green-400 text-sm font-medium">
          Scheduled successfully!
        </div>
        <div v-else-if="scheduleResult" class="text-red-400 text-sm">
          {{ scheduleResult }}
        </div>

        <div class="flex gap-3 pt-2">
          <n-button @click="scheduleModal = false" class="flex-1">Cancel</n-button>
          <n-button
            type="primary"
            class="flex-1"
            :loading="scheduling"
            :disabled="!scheduleDate || !scheduleTime || selectedPlatforms.length === 0"
            @click="handleSchedule"
          >
            Schedule
          </n-button>
        </div>
      </div>
    </n-modal>

    <n-modal
      v-model:show="thumbnailModal"
      preset="card"
      title="Extract Frame from Video"
      style="max-width: 480px"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <div>
          <label class="block text-sm text-clipper-ink/60 dark:text-white/60 mb-1">Select Video</label>
          <n-select
            v-model:value="thumbnailTargetUrl"
            :options="video.selectedVideoUrls.map((v, i) => ({
              label: v.url.split('/').pop() || `Video ${i + 1}`,
              value: v.url
            }))"
            placeholder="Choose a video"
          />
        </div>

        <div>
          <label class="block text-sm text-clipper-ink/60 dark:text-white/60 mb-1">Timestamp (seconds)</label>
          <n-input-number v-model:value="thumbnailTimestamp" :min="0" :max="300" size="large" class="w-full" />
          <div class="flex gap-1 mt-2">
            <n-button size="tiny" @click="thumbnailTimestamp = 0">0s</n-button>
            <n-button size="tiny" @click="thumbnailTimestamp = 1">1s</n-button>
            <n-button size="tiny" @click="thumbnailTimestamp = 2">2s</n-button>
            <n-button size="tiny" @click="thumbnailTimestamp = 5">5s</n-button>
            <n-button size="tiny" @click="thumbnailTimestamp = 10">10s</n-button>
          </div>
        </div>

        <div class="flex gap-3 pt-2">
          <n-button @click="thumbnailModal = false" class="flex-1">Cancel</n-button>
          <n-button
            type="primary"
            class="flex-1"
            :loading="extractingThumbnail"
            :disabled="!thumbnailTargetUrl"
            @click="extractThumbnail"
          >
            Extract & Add (0.05s)
          </n-button>
        </div>
      </div>
    </n-modal>
</template>
<style scoped></style>
