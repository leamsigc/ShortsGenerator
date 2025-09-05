<script lang="ts" setup>
/**
 * Facebook Upload Page
 *
 * Handles uploading videos to Facebook
 *
 * @author Leamsigc
 * @version 1.0.0
 */

interface VideoItem {
  path: string;
  title?: string;
  description?: string;
  schedule_time?: string;
}

interface UploadData {
  videos: VideoItem[];
  schedule_from?: string;
  schedule_to?: string;
  schedule_time?: string;
  videos_per_day?: number;
}

interface VideoObject {
  name: string;
  type: string;
}

const route = useRoute();
const router = useRouter();

// Get videos from query params
const videosQuery = route.query.videos as string;
const videos = ref<VideoObject[]>([]);

if (videosQuery) {
  try {
    videos.value = JSON.parse(decodeURIComponent(videosQuery));
  } catch (error) {
    console.error('Failed to parse videos from query:', error);
    router.push('/videos');
  }
}

// If no videos in query, redirect to videos page
if (videos.value.length === 0) {
  await router.push('/videos');
}

const API_URL = "http://localhost:8080";

const isBulkMode = ref(false);
const selectedVideos = ref<VideoObject[]>([...videos.value]);
const scheduleFrom = ref('');
const scheduleTo = ref('');
const scheduleTime = ref('09:00');
const videosPerDay = ref(1);
const isUploading = ref(false);

const uploadData = computed(() => {
  const videos: VideoItem[] = selectedVideos.value.map(video => ({
    path: video.type === 'instagram' ? `static/generated_videos/instagram/${video.name}` : `static/generated_videos/${video.name}`,
    title: `Video: ${video.name}`,
    description: 'Auto-generated video'
  }));

  return {
    videos,
    schedule_from: scheduleFrom.value || undefined,
    schedule_to: scheduleTo.value || undefined,
    schedule_time: scheduleTime.value,
    videos_per_day: videosPerDay.value
  };
});

const handleUpload = async () => {
  if (selectedVideos.value.length === 0) {
    return;
  }

  isUploading.value = true;

  try {
    const response = await $fetch(`${API_URL}/api/facebook/bulk-upload`, {
      method: 'POST',
      body: uploadData.value
    });

    if (response.status === 'success') {
      router.push('/videos');
    } else {
    }
  } catch (error) {
    console.error('Upload error:', error);
  } finally {
    isUploading.value = false;
  }
};

const handleSingleUpload = async (video: VideoObject) => {
  isUploading.value = true;

  try {
    const response = await $fetch(`${API_URL}/api/facebook/upload`, {
      method: 'POST',
      body: {
        video_path: video.type === 'instagram' ? `static/generated_videos/instagram/${video.name}` : `static/generated_videos/${video.name}`,
        title: `Video: ${video.name}`,
        description: 'Auto-generated video',
        schedule_time: scheduleFrom.value ? `${scheduleFrom.value}T${scheduleTime.value}:00Z` : undefined
      }
    });

    if (response.status === 'success') {
      router.push('/videos');
    } else {
    }
  } catch (error) {
    console.error('Upload error:', error);
  } finally {
    isUploading.value = false;
  }
};

const toggleVideoSelection = (video: VideoObject) => {
  const index = selectedVideos.value.findIndex(v => v.name === video.name);
  if (index > -1) {
    selectedVideos.value.splice(index, 1);
  } else {
    selectedVideos.value.push(video);
  }
};

const selectAllVideos = () => {
  if (selectedVideos.value.length === videos.value.length) {
    selectedVideos.value = [];
  } else {
    selectedVideos.value = [...videos.value];
  }
};

const goBack = () => {
  router.push('/videos');
};
</script>

<template>
  <div class="py-28 px-10">
    <div class="flex items-center mb-10">
      <n-button @click="goBack" type="default" class="mr-4">
        <template #icon>
          <Icon name="material-symbols:arrow-back" />
        </template>
        Back to Videos
      </n-button>
      <h1 class="text-3xl leading-10 font-bold">Upload to Facebook</h1>
      <n-tag type="info" class="ml-4">
        {{ selectedVideos.length }} video{{ selectedVideos.length !== 1 ? 's' : '' }} selected
      </n-tag>
    </div>

    <n-card class="mb-6">
      <n-space vertical size="large">
        <!-- Mode Selection -->
        <n-card title="Upload Mode">
          <n-radio-group :mode-value="isBulkMode" name="upload-mode">
            <n-space>
              <n-radio :value="false">Single Video</n-radio>
              <n-radio :value="true">Bulk Upload</n-radio>
            </n-space>
          </n-radio-group>
        </n-card>

        <!-- Video Selection -->
        <n-card title="Select Videos to Upload">
          <n-space vertical size="medium">
            <n-space>
              <n-checkbox :checked="selectedVideos.length === videos.length && videos.length > 0"
                :indeterminate="selectedVideos.length > 0 && selectedVideos.length < videos.length"
                @update:checked="selectAllVideos">
                Select All
              </n-checkbox>
              <n-text depth="3">
                {{ selectedVideos.length }} of {{ videos.length }} selected
              </n-text>
            </n-space>

            <n-checkbox-group :mode-value="selectedVideos">
              <n-space vertical>
                <n-checkbox v-for="video in videos" :key="video.name" :value="video.name"
                  :label="`${video.name} (${video.type})`" />
              </n-space>
            </n-checkbox-group>
          </n-space>
        </n-card>

        <!-- Scheduling Options -->
        <n-card title="Scheduling Options">
          <n-space vertical size="medium">
            <n-form-item label="Schedule Date">
              <n-date-picker :mode-value="scheduleFrom" type="date" clearable
                :placeholder="isBulkMode ? 'From date' : 'Schedule date'" />
            </n-form-item>

            <template v-if="isBulkMode">
              <n-form-item label="To Date">
                <n-date-picker :mode-value="scheduleTo" type="date" clearable placeholder="To date" />
              </n-form-item>

              <n-form-item label="Videos per Day">
                <n-input-number :mode-value="videosPerDay" :min="1" :max="10" placeholder="Videos per day" />
              </n-form-item>
            </template>

            <n-form-item label="Time">
              <n-time-picker :mode-value="scheduleTime" format="HH:mm" placeholder="Select time" />
            </n-form-item>
          </n-space>
        </n-card>

        <!-- Action Buttons -->
        <n-space justify="end">
          <n-button @click="goBack">
            Cancel
          </n-button>

          <n-button v-if="!isBulkMode" type="primary" @click="handleSingleUpload(selectedVideos[0])"
            :disabled="selectedVideos.length !== 1 || isUploading" :loading="isUploading">
            Upload Single Video
          </n-button>

          <n-button v-else type="primary" @click="handleUpload" :disabled="selectedVideos.length === 0 || isUploading"
            :loading="isUploading">
            Schedule Bulk Upload
          </n-button>
        </n-space>
      </n-space>
    </n-card>
  </div>
</template>

<style scoped>
/* Add any custom styles here */
</style>