<script lang="ts" setup>
const loading = ref(true)
const instagramVideos = ref<string[]>([])
const { video } = useVideoSettings()
const URL = useApiSettings().API_SETTINGS.value.URL;
// Fetch Instagram videos
const fetchInstagramVideos = async () => {
    try {
        const response = await fetch(`${URL}/api/getVideos`)
        const data = await response.json()

        if (data.status === 'success') {
            instagramVideos.value = data.data.instagram || []
        }
    } catch (error) {
        console.error('Error fetching Instagram videos:', error)
    } finally {
        loading.value = false
    }
}

// Check if video is already selected
const isVideoSelected = (videoName: string) => {
    return video.value.selectedVideoUrls?.some(
        (v) => v.url === `static/generated_videos/instagram/${videoName}`
    )
}

// Handle video selection
const handleSelectVideo = (videoName: string) => {
    if (!video.value.selectedVideoUrls) {
        video.value.selectedVideoUrls = []
    }
    if (isVideoSelected(videoName)) {
        return;
    }

    video.value.selectedVideoUrls.push({
        url: `static/generated_videos/instagram/${videoName}`,
        image: `${URL}/static/generated_videos/instagram/${videoName}`,
        videoUrl: { fileType: 'mp4', link: `${URL}/static/generated_videos/instagram/${videoName}`, quality: 'hd' },
        type: 'local'
    });
}

// Handle video deletion
const handleDeleteVideo = async (videoName: string) => {
    video.value.selectedVideoUrls =
        video.value.selectedVideoUrls
            .filter((v) => v.url !== `static/generated_videos/instagram/${videoName}`)
}

// Watch for changes in selected videos
watch(() => video.value.selectedVideoUrls, () => {
    // You can add any additional logic here when selected videos change
}, { deep: true })

// Fetch videos on component mount
onMounted(() => {
    fetchInstagramVideos()
})
</script>

<template>
    <div class="instagram-videos">
        <div v-if="loading" class="flex justify-center items-center min-h-[200px]">
            <n-spin size="large" />
        </div>
        <div v-else>
            <!-- Video Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div v-for="video in instagramVideos" :key="video" class="video-card">
                    <div class="relative bg-slate-800 rounded-lg overflow-hidden group">
                        <!-- Video Preview -->
                        <video class="w-full aspect-[9/16] object-cover"
                            :src="`${URL}/static/generated_videos/instagram/${video}`" controls></video>

                        <!-- Overlay with Actions -->
                        <div
                            class="absolute inset-0 bottom-10 bg-black bg-opacity-50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <div class="space-y-2">
                                <!-- Select Button -->
                                <n-button type="primary" size="small" class="mx-2" :disabled="isVideoSelected(video)"
                                    @click="handleSelectVideo(video)">
                                    {{ isVideoSelected(video) ? 'Selected' : 'Select' }}
                                </n-button>

                                <!-- Delete Button -->
                                <n-button type="error" size="small" class="mx-2" @click="handleDeleteVideo(video)">
                                    Unselect
                                </n-button>
                            </div>
                        </div>
                    </div>

                    <!-- Video Name -->
                    <div class="mt-2 px-2">
                        <p class="text-sm text-gray-500 dark:text-gray-400 truncate">
                            {{ video }}
                        </p>
                    </div>
                </div>
            </div>

            <!-- No Videos Message -->
            <div v-if="instagramVideos.length === 0" class="text-center py-10">
                <p class="text-gray-500 dark:text-gray-400">
                    No Instagram videos available. Download some videos first.
                </p>
            </div>
        </div>
    </div>
</template>


<style scoped>
.video-card {
    @apply transition-transform duration-200;
}

.video-card:hover {
    @apply transform scale-[1.02];
}
</style>