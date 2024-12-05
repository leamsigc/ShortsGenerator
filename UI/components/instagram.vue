<script setup>
const instagramUrls = ref([''])
const isDownloading = ref(false)
const downloadStatus = ref([])

// Add new URL input
const addUrl = () => {
  instagramUrls.value.push('')
}

// Remove URL input
const removeUrl = (index) => {
  instagramUrls.value.splice(index, 1)
}

// Download videos
const downloadVideos = async () => {
  isDownloading.value = true
  downloadStatus.value = []

  try {
    // Filter out empty URLs
    const urls = instagramUrls.value.filter(url => url.trim() !== '').map(url => {
      return url.replaceAll('/share/', '')
    })

    // Process each URL
    for (const url of urls) {
      try {
        const response = await fetch('http://localhost:8080/api/instagram/download', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ url: url.trim() }),
        })

        const data = await response.json()

        if (data.status === 'success') {
          downloadStatus.value.push({
            type: 'success',
            message: `Successfully downloaded video from: ${url}`,
          })
        } else {
          throw new Error(data.message || 'Failed to download video')
        }
      } catch (error) {
        downloadStatus.value.push({
          type: 'error',
          message: `Failed to download from ${url}: ${error.message}`,
        })
      }
    }
  } catch (error) {
    downloadStatus.value.push({
      type: 'error',
      message: `An error occurred: ${error.message}`,
    })
  } finally {
    isDownloading.value = false
  }
}
</script>


<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">Instagram Video Downloader</h1>

    <div class="bg-white rounded-lg shadow p-6">
      <form @submit.prevent="downloadVideos" class="space-y-4">
        <!-- URL Inputs -->
        <div v-for="(url, index) in instagramUrls" :key="index" class="flex gap-2">
          <div class="flex-1">
            <input v-model="instagramUrls[index]" type="text" :placeholder="'Enter Instagram URL ' + (index + 1)"
              class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required />
          </div>
          <!-- Remove URL button -->
          <button v-if="instagramUrls.length > 1" @click="removeUrl(index)" type="button"
            class="px-3 py-2 text-red-600 hover:bg-red-100 rounded-lg transition-colors" title="Remove URL">
            <span class="text-xl">×</span>
          </button>
        </div>

        <!-- Add More URLs button -->
        <div class="flex justify-start">
          <button @click="addUrl" type="button"
            class="flex items-center px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
            <span class="mr-1">+</span> Add another URL
          </button>
        </div>

        <!-- Download button -->
        <div class="flex justify-end mt-6">
          <button type="submit"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="isDownloading">
            <span v-if="isDownloading">Downloading...</span>
            <span v-else>Download Videos</span>
          </button>
        </div>
      </form>

      <!-- Status Messages -->
      <div class="mt-6 space-y-2">
        <div v-for="(status, index) in downloadStatus" :key="index" :class="[
          'p-4 rounded-lg',
          status.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        ]">
          {{ status.message }}
        </div>
      </div>
    </div>
  </div>
</template>


<style scoped>
/* Add any additional styling here */
</style>
