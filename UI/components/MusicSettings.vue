<script lang="ts" setup>
/**
 *
 * MusicSettings — music library with named song cards, per-song preview,
 * music volume slider, and sound-effect picker with per-effect start time.
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.2
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

interface SfxEntry {
  path: string;
  startTime: number;
}

const { API_SETTINGS } = useApiSettings();
const availableSongs = ref<string[]>([]);
const availableSfx = ref<string[]>([]);
const { video } = useVideoSettings();

const uploadLoading = ref(false)
const uploadResult = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const downloadUrl = ref('')
const downloadLoading = ref(false)
const downloadResult = ref<string | null>(null)
const previewingSong = ref<string | null>(null)
const previewAudio = ref<HTMLAudioElement | null>(null)
const sfxPick = ref<string | null>(null)

const API_BASE = API_SETTINGS.value.URL

/** Pretty display name: strips "Video by ..." prefixes and file extensions */
function songLabel(song: string): string {
  const base = song.replace(/\.[^.]+$/, "")
  return base.replace(/^Video by\s*/i, "").trim() || song
}

async function loadSongs() {
  try {
    const { data: songsResponse } = await $fetch<{ data: { songs: string[] } }>(
      `${API_BASE}/api/getSongs`
    );
    availableSongs.value = (songsResponse.songs || []).filter((s) => !s.startsWith("."));
  } catch (e) {
    console.error("Failed to load songs", e)
  }
}

async function loadSfx() {
  try {
    const { data: sfxResponse } = await $fetch<{ data: { sfx: string[] } }>(
      `${API_BASE}/api/getSfx`
    );
    availableSfx.value = (sfxResponse.sfx || []).filter((s) => !s.startsWith("."));
  } catch (e) {
    console.error("Failed to load sound effects", e)
  }
}

function selectSong(song: string) {
  video.value.selectedAudio = song
  // Don't auto-preview on select — user must click Preview
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  uploadLoading.value = true
  uploadResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', input.files[0])
    await $fetch(`${API_BASE}/api/upload-music`, {
      method: 'POST',
      body: formData,
    })
    uploadResult.value = 'Uploaded successfully!'
    input.value = ''
    await loadSongs()
  } catch (e: any) {
    uploadResult.value = e?.data?.message || e?.message || 'Upload failed'
  } finally {
    uploadLoading.value = false
  }
}

async function handleDownloadUrl() {
  if (!downloadUrl.value.trim()) return
  downloadLoading.value = true
  downloadResult.value = null
  try {
    await $fetch(`${API_BASE}/api/download-music-url`, {
      method: 'POST',
      body: { url: downloadUrl.value.trim() },
    })
    downloadResult.value = 'Downloaded successfully!'
    downloadUrl.value = ''
    await loadSongs()
  } catch (e: any) {
    downloadResult.value = e?.data?.message || e?.message || 'Download failed'
  } finally {
    downloadLoading.value = false
  }
}

/** Toggle preview of a single song — stops any other preview */
function togglePreview(song: string) {
  if (previewingSong.value === song) {
    // Stop current preview
    if (previewAudio.value) {
      previewAudio.value.pause()
      previewAudio.value.currentTime = 0
    }
    previewingSong.value = null
    return
  }
  // Stop previous if any
  if (previewAudio.value) {
    previewAudio.value.pause()
    previewAudio.value.currentTime = 0
  }
  previewingSong.value = song
}

watch(previewingSong, async (song) => {
  await nextTick()
  if (song && previewAudio.value) {
    previewAudio.value.src = `${API_BASE}/static/assets/music/${encodeURIComponent(song)}`
    try { await previewAudio.value.play() } catch {}
  } else if (previewAudio.value) {
    previewAudio.value.pause()
  }
})

function stopPreview() {
  if (previewAudio.value) {
    previewAudio.value.pause()
    previewAudio.value.currentTime = 0
  }
  previewingSong.value = null
}

function onSfxAdd(name: string | null) {
  if (!name) return
  const list = video.value.soundEffects ?? []
  if (!list.some((s) => s.path === name)) {
    list.push({ path: name, startTime: 0 })
  }
}

function onSfxRemove(idx: number) {
  video.value.soundEffects?.splice(idx, 1)
}

onMounted(() => {
  loadSongs()
  loadSfx()
})

onUnmounted(() => {
  if (previewAudio.value) {
    previewAudio.value.pause()
  }
  previewingSong.value = null
})
</script>

<template>
  <n-form ref="reviewFormRef" class="max-w-screen-md" :model="video" size="large">
    <!-- Music library as named cards -->
    <n-form-item label="Music library:" path="selectedAudio">
      <div class="w-full grid grid-cols-2 sm:grid-cols-3 gap-3">
        <div
          v-for="song in availableSongs"
          :key="song"
          role="button"
          tabindex="0"
          class="relative rounded-lg overflow-hidden border-2 transition-all p-3 text-left cursor-pointer"
          :class="video.selectedAudio === song
            ? 'border-clipper-green bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08'
            : 'border-clipper-ink/08 dark:border-white/08 hover:border-slate-500 bg-neutral-100 dark:bg-neutral-800'"
          @click="selectSong(song)"
          @keydown.enter.prevent="selectSong(song)"
          @keydown.space.prevent="selectSong(song)"
        >
          <div class="flex items-center gap-2 mb-2">
            <Icon name="mdi:music" size="18" class="text-clipper-green shrink-0" />
            <span class="text-xs font-bold text-clipper-ink dark:text-white truncate">{{ songLabel(song) }}</span>
          </div>
          <button
            type="button"
            class="text-xs flex items-center gap-1"
            :class="previewingSong === song ? 'text-red-500 hover:text-red-600' : 'text-clipper-green hover:text-clipper-ink dark:hover:text-white'"
            @click.stop="togglePreview(song)"
          >
            <Icon :name="previewingSong === song ? 'mdi:stop' : 'mdi:play'" size="14" />
            {{ previewingSong === song ? 'Stop' : 'Preview' }}
          </button>
          <div
            v-if="video.selectedAudio === song"
            class="absolute top-1 right-1 w-5 h-5 bg-clipper-green rounded-full flex items-center justify-center"
          >
            <Icon name="mdi:check" size="12" class="text-white" />
          </div>
        </div>
      </div>
      <!-- Single preview player — allows stop and prevents multiple audios -->
      <audio
        ref="previewAudio"
        class="hidden"
        preload="none"
        @ended="previewingSong = null"
      />
      <div v-if="previewingSong" class="mt-3 flex items-center gap-2 p-2 bg-clipper-green/10 dark:bg-neutral-800 border border-clipper-green/20 rounded-lg">
        <Icon name="mdi:music" size="16" class="text-clipper-green shrink-0" />
        <span class="text-xs font-medium truncate flex-1 text-clipper-ink dark:text-white">Playing: {{ songLabel(previewingSong) }}</span>
        <button class="h-7 px-3 rounded-md bg-white dark:bg-neutral-700 border border-clipper-ink/12 dark:border-white/10 text-xs font-medium hover:border-clipper-ink/20 flex items-center gap-1" @click="stopPreview">
          <Icon name="mdi:stop" size="14" /> Stop
        </button>
      </div>
    </n-form-item>

    <!-- Music volume -->
    <n-form-item label="Music volume" :show-feedback="false">
      <div class="w-full">
        <div class="flex items-center justify-between text-xs opacity-70 mb-1">
          <span>Quiet</span>
          <span class="font-mono">{{ Math.round((video.musicVolume ?? 0.15) * 100) }}%</span>
        </div>
        <n-slider v-model:value="video.musicVolume" :min="0" :max="1" :step="0.05" />
      </div>
    </n-form-item>

    <n-divider>Sound Effects</n-divider>
    <n-form-item label="Add effect:" :show-feedback="false">
      <div class="w-full">
        <div class="flex items-center gap-2">
          <n-select
            v-model:value="sfxPick"
            :options="availableSfx.map((s) => ({ label: songLabel(s), value: s }))"
            placeholder="Add effect…"
            size="small"
            clearable
            class="flex-1"
          />
          <n-button size="small" @click="onSfxAdd(sfxPick)" :disabled="!sfxPick">
            <template #icon><Icon name="ph:plus" /></template>
          </n-button>
        </div>

        <div v-if="(video.soundEffects || []).length" class="mt-3 space-y-2">
          <div v-for="(sfx, idx) in video.soundEffects" :key="idx" class="flex items-center gap-2 p-2 bg-neutral-100 dark:bg-neutral-800 rounded">
            <Icon name="mdi:music-note" class="shrink-0 text-amber-400" />
            <span class="text-xs truncate flex-1">{{ songLabel(sfx.path) }}</span>
            <n-input-number v-model:value="sfx.startTime" size="tiny" :min="0" :max="600" class="w-20" />
            <span class="text-xs opacity-50">s</span>
            <n-button size="tiny" quaternary @click="onSfxRemove(idx)">
              <Icon name="ph:trash" class="text-red-400" />
            </n-button>
          </div>
        </div>

        <div class="mt-3 flex items-center justify-between text-xs opacity-70">
          <span>SFX volume</span>
          <span class="font-mono">{{ Math.round((video.sfxVolume ?? 0.9) * 100) }}%</span>
        </div>
        <n-slider v-model:value="video.sfxVolume" :min="0" :max="1" :step="0.05" />
        <p class="text-xs opacity-50 mt-2">Music auto-ducks while an effect plays.</p>
      </div>
    </n-form-item>

    <n-divider>Upload Audio File</n-divider>
    <div class="space-y-3">
      <input ref="fileInput" type="file" accept=".mp3,.wav,.m4a,.aac,.ogg,.flac" class="hidden" @change="handleUpload" />
      <n-button :loading="uploadLoading" type="info" ghost @click="triggerUpload">
        <template #icon><Icon name="mdi:upload" /></template>
        Upload Audio
      </n-button>
      <p v-if="uploadResult" :class="uploadResult === 'Uploaded successfully!' ? 'text-green-400 text-sm' : 'text-red-400 text-sm'">
        {{ uploadResult }}
      </p>
    </div>

    <n-divider>Download from URL</n-divider>
    <div class="space-y-3">
      <div class="flex gap-2">
        <n-input v-model:value="downloadUrl" placeholder="YouTube, SoundCloud, etc. URL" class="flex-1" />
        <n-button :loading="downloadLoading" :disabled="!downloadUrl.trim()" type="info" ghost @click="handleDownloadUrl">
          <template #icon><Icon name="mdi:download" /></template>
          Download
        </n-button>
      </div>
      <p v-if="downloadResult" :class="downloadResult === 'Downloaded successfully!' ? 'text-green-400 text-sm' : 'text-red-400 text-sm'">
        {{ downloadResult }}
      </p>
    </div>
  </n-form>
</template>
<style scoped></style>
