<script lang="ts" setup>
/**
 *
 * Component Description: Voice Settings with Custom Audio Support
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

const { API_SETTINGS } = useApiSettings();
const voiceOptions = ref<{ label: string; value: string }[]>([]);
const isRecording = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const recordedChunks = ref<Blob[]>([]);

const { video } = useVideoSettings();

const { data } = await $fetch<{ data: { voices: string[] } }>(
  `${API_SETTINGS.value.URL}/api/models`
);
voiceOptions.value = data.voices.map((voice) => {
  return { label: voice, value: voice };
});

// Audio recording functions
const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.value = new MediaRecorder(stream);
    recordedChunks.value = [];

    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunks.value.push(event.data);
      }
    };

    mediaRecorder.value.onstop = () => {
      const blob = new Blob(recordedChunks.value, { type: 'audio/wav' });
      const file = new File([blob], 'recorded-tts.wav', { type: 'audio/wav' });
      video.value.customTtsAudio = file;
      video.value.customTtsAudioUrl = URL.createObjectURL(blob);
      stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorder.value.start();
    isRecording.value = true;
  } catch (error) {
    console.error('Error starting recording:', error);
  }
};

const stopRecording = () => {
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop();
    isRecording.value = false;
  }
};

// File upload handling
const handleFileDrop = (event: DragEvent) => {
  event.preventDefault();
  const files = event.dataTransfer?.files;
  if (files && files.length > 0) {
    handleFileSelect(files[0]);
  }
};

const handleFileSelect = (file: File) => {
  if (file.type.startsWith('audio/')) {
    video.value.customTtsAudio = file;
    video.value.customTtsAudioUrl = URL.createObjectURL(file);
  } else {
    alert('Please select an audio file');
  }
};

const clearCustomAudio = () => {
  video.value.customTtsAudio = null;
  video.value.customTtsAudioUrl = '';
};

const triggerFileInput = () => {
  const input = document.getElementById('audio-file-input') as HTMLInputElement;
  input?.click();
};
</script>

<template>
  <div class="space-y-4">
    <n-form-item label="Voice:" path="voice">
      <n-select v-model:value="video.voice" :options="voiceOptions" />
    </n-form-item>

    <n-divider title="Custom TTS Audio" />

    <div class="space-y-3">
      <!-- Record Button -->
      <div class="flex gap-2">
        <n-button
          v-if="!isRecording"
          type="primary"
          @click="startRecording"
          :disabled="!!video.customTtsAudio"
        >
          <template #icon>
            <Icon name="material-symbols:mic" />
          </template>
          Record Audio
        </n-button>

        <n-button
          v-else
          type="error"
          @click="stopRecording"
        >
          <template #icon>
            <Icon name="material-symbols:stop" />
          </template>
          Stop Recording
        </n-button>

        <n-button
          type="tertiary"
          @click="triggerFileInput"
          :disabled="!!video.customTtsAudio"
        >
          <template #icon>
            <Icon name="material-symbols:upload" />
          </template>
          Upload Audio
        </n-button>
      </div>

      <!-- Hidden file input -->
      <input
        id="audio-file-input"
        type="file"
        accept="audio/*"
        class="hidden"
        @change="(e) => handleFileSelect((e.target as HTMLInputElement).files![0])"
      />

      <!-- Drop zone -->
      <div
        v-if="!video.customTtsAudio"
        class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors"
        @dragover.prevent
        @drop="handleFileDrop"
        @click="triggerFileInput"
      >
        <Icon name="material-symbols:cloud-upload" size="48" class="mx-auto mb-2 text-gray-400" />
        <p class="text-sm text-gray-600 dark:text-gray-400">
          Drag & drop an audio file here, or click to browse
        </p>
        <p class="text-xs text-gray-500 mt-1">
          Supports WAV, MP3, M4A, and other audio formats
        </p>
      </div>

      <!-- Custom audio preview -->
      <div v-if="video.customTtsAudio" class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <Icon name="material-symbols:audio-file" size="24" />
        <div class="flex-1">
          <p class="font-medium">{{ video.customTtsAudio.name }}</p>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            {{ (video.customTtsAudio.size / 1024 / 1024).toFixed(2) }} MB
          </p>
        </div>
        <audio controls class="flex-1 max-w-xs">
          <source :src="video.customTtsAudioUrl" />
        </audio>
        <n-button text type="error" @click="clearCustomAudio">
          <template #icon>
            <Icon name="material-symbols:delete" />
          </template>
        </n-button>
      </div>

      <!-- Recording indicator -->
      <div v-if="isRecording" class="flex items-center gap-2 text-red-500">
        <div class="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
        <span class="text-sm font-medium">Recording...</span>
      </div>
    </div>
  </div>
</template>
<style scoped></style>
