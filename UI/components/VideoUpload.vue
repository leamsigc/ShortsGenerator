<script setup>
const { video } = useVideoSettings()
const URL = useApiSettings().API_SETTINGS.value.URL;
const fileInput = ref(null)
const selectedFiles = ref([])
const isUploading = ref(false)
const uploadStatus = ref([])
const handleFileSelect = (event) => {
  const input = event.target
  if (input.files) {
    selectedFiles.value = Array.from(input.files)
  }
}

const uploadFiles = async () => {
  if (selectedFiles.value.length === 0) return
  isUploading.value = true
  uploadStatus.value = []

  try {
    const formData = new FormData()
    for (const file of selectedFiles.value) {
      formData.append('file', file)
    }

    const response = await fetch(`${URL}/api/upload-video`, {
      method: 'POST',
      body: formData,
    })

    const data = await response.json()

    if (data.status === 'success') {
      for (const filename of data.data.filenames) {
        if (!video.value.selectedVideoUrls) {
          video.value.selectedVideoUrls = []
        }
        video.value.selectedVideoUrls.push({
          url: `static/generated_videos/instagram/${filename}`,
          image: `${URL}/static/generated_videos/instagram/${filename}`,
          videoUrl: { fileType: 'mp4', link: `${URL}/static/generated_videos/instagram/${filename}`, quality: 'hd' },
          type: 'local'
        })
      }
      uploadStatus.value.push({
        type: 'success',
        message: `Uploaded ${data.data.filenames.length} video(s) and added to selection`,
      })
      selectedFiles.value = []
    } else {
      throw new Error(data.message || 'Upload failed')
    }
  } catch (error) {
    uploadStatus.value.push({
      type: 'error',
      message: `Upload failed: ${error.message}`,
    })
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-clipper-ink dark:text-white">Upload Videos</h1>
      <p class="text-sm text-clipper-ink/60 dark:text-white/60 mt-1">Add local video files as sources</p>
    </div>

    <div class="bg-white dark:bg-neutral-800 border border-clipper-ink/08 dark:border-white/08 rounded-xl p-6">
      <div class="space-y-4">
        <div
          class="border-2 border-dashed border-clipper-ink/12 dark:border-white/10 rounded-xl p-8 text-center cursor-pointer hover:border-clipper-green transition-colors bg-neutral-100 dark:bg-neutral-800"
          @click="fileInput?.click()"
        >
          <Icon name="ph:upload-simple" size="40" class="text-clipper-ink/35 dark:text-white/40 mb-2 mx-auto" />
          <p class="text-sm font-medium text-clipper-ink dark:text-white">Click to select videos or drag them here</p>
          <p class="text-xs text-clipper-ink/35 dark:text-white/40 mt-1">MP4, MOV, AVI, MKV, WebM</p>
          <input
            ref="fileInput"
            type="file"
            multiple
            accept=".mp4,.mov,.avi,.mkv,.webm,.flv,.wmv"
            class="hidden"
            @change="handleFileSelect"
          />
        </div>

        <div v-if="selectedFiles.length > 0" class="mt-4">
          <h3 class="text-sm font-semibold text-clipper-ink dark:text-white mb-2">Selected files ({{ selectedFiles.length }}):</h3>
          <ul class="space-y-1">
            <li v-for="(file, idx) in selectedFiles" :key="idx" class="text-sm text-clipper-ink/70 dark:text-white/70 flex items-center gap-2">
              <Icon name="ph:file-video" size="16" class="text-clipper-ink/40 dark:text-white/40" />
              {{ file.name }} ({{ (file.size / 1024 / 1024).toFixed(1) }} MB)
            </li>
          </ul>
        </div>

        <div class="flex justify-end mt-6">
          <button
            @click="uploadFiles"
            :disabled="selectedFiles.length === 0 || isUploading"
            class="h-10 px-6 rounded-lg bg-clipper-green text-clipper-ink font-semibold text-sm hover:opacity-90 disabled:opacity-50"
          >
            <span v-if="isUploading">Uploading...</span>
            <span v-else>Upload Videos</span>
          </button>
        </div>
      </div>

      <div class="mt-6 space-y-2">
        <div
          v-for="(status, index) in uploadStatus"
          :key="index"
          :class="[
            'p-4 rounded-lg border text-sm',
            status.type === 'success' ? 'bg-clipper-green/10 border-clipper-green/20 text-clipper-ink' : 'bg-neutral-100 dark:bg-neutral-800 border-clipper-ink/08 dark:border-white/08 text-clipper-ink/70 dark:text-white/70'
          ]"
        >
          {{ status.message }}
        </div>
      </div>
    </div>
  </div>
</template>
