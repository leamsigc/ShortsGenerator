<script lang="ts" setup>
/**
 * Facebook Upload Dialog Component
 *
 * @author Leamsigc
 * @version 0.0.1
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

const props = defineProps<{
  show: boolean;
  videos: VideoObject[];
}>();

const emit = defineEmits<{
  'update:show': [value: boolean];
  upload: [data: UploadData];
}>();

const API_URL = "http://localhost:8080";

const isBulkMode = ref(false);
const selectedVideos = ref<VideoObject[]>([]);
const scheduleFrom = ref('');
const scheduleTo = ref('');
const scheduleTime = ref('09:00');
const videosPerDay = ref(1);

// Watch for prop changes and update selectedVideos
watch(() => props.videos, (newVideos) => {
  if (newVideos && newVideos.length > 0) {
    selectedVideos.value = [...newVideos];
  } else {
    selectedVideos.value = [];
  }
}, { immediate: true });

// Watch for show prop to reset state when modal opens
watch(() => props.show, (newVal) => {
  if (newVal && props.videos && props.videos.length > 0) {
    selectedVideos.value = [...props.videos];
  } else if (!newVal) {
    // Reset state when modal closes
    selectedVideos.value = [];
    scheduleFrom.value = '';
    scheduleTo.value = '';
    scheduleTime.value = '09:00';
    videosPerDay.value = 1;
    isBulkMode.value = false;
  }
});

// Handle component unmount to prevent memory leaks
onUnmounted(() => {
  selectedVideos.value = [];
});

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
  try {
    const response = await $fetch(`${API_URL}/api/facebook/bulk-upload`, {
      method: 'POST',
      body: uploadData.value
    });

    if (response.status === 'success') {
      message.success('Videos scheduled for upload successfully!');
      emit('update:show', false);
      emit('upload', uploadData.value);
    } else {
      message.error(response.message || 'Upload failed');
    }
  } catch (error) {
    console.error('Upload error:', error);
    message.error('Failed to upload videos');
  }
};

const handleSingleUpload = async () => {
  if (selectedVideos.value.length !== 1) {
    message.error('Please select exactly one video for single upload');
    return;
  }

  const video = selectedVideos.value[0];

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
      message.success(`Video ${video.name} uploaded successfully!`);
      emit('update:show', false);
    } else {
      message.error(response.message || 'Upload failed');
    }
  } catch (error) {
    console.error('Upload error:', error);
    message.error(`Failed to upload ${video.name}`);
  }
};


</script>

<template>
  <n-modal
    v-if="show"
    :show="show"
    @update:show="$emit('update:show', $event)"
    preset="card"
    title="Upload to Facebook"
    class="max-w-4xl"
    :segmented="false"
  >
    <div class="p-6">
      <n-space vertical size="large">
        <!-- Mode Selection -->
        <n-card title="Upload Mode">
          <n-radio-group v-model:value="isBulkMode" name="upload-mode">
            <n-space>
              <n-radio :value="false">Single Video</n-radio>
              <n-radio :value="true">Bulk Upload</n-radio>
            </n-space>
          </n-radio-group>
        </n-card>

        <!-- Video Selection -->
        <n-card title="Select Videos">
            <n-checkbox-group v-model:value="selectedVideos">
              <n-space vertical>
                <n-checkbox
                  v-for="video in videos"
                  :key="video.name"
                  :value="video"
                  :label="`${video.name} (${video.type})`"
                />
              </n-space>
            </n-checkbox-group>
        </n-card>

        <!-- Scheduling Options -->
        <n-card title="Scheduling Options">
          <n-space vertical size="medium">
            <n-form-item label="Schedule Date">
              <n-date-picker
                v-model:value="scheduleFrom"
                type="date"
                clearable
                :placeholder="isBulkMode ? 'From date' : 'Schedule date'"
              />
            </n-form-item>

            <template v-if="isBulkMode">
              <n-form-item label="To Date">
                <n-date-picker
                  v-model:value="scheduleTo"
                  type="date"
                  clearable
                  placeholder="To date"
                />
              </n-form-item>

              <n-form-item label="Videos per Day">
                <n-input-number
                  v-model:value="videosPerDay"
                  :min="1"
                  :max="10"
                  placeholder="Videos per day"
                />
              </n-form-item>
            </template>

            <n-form-item label="Time">
              <n-time-picker
                v-model:value="scheduleTime"
                format="HH:mm"
                placeholder="Select time"
              />
            </n-form-item>
          </n-space>
        </n-card>

        <!-- Action Buttons -->
        <n-space justify="end">
          <n-button @click="$emit('update:show', false)">
            Cancel
          </n-button>

          <n-button
            v-if="!isBulkMode"
            type="primary"
            @click="handleSingleUpload"
            :disabled="selectedVideos.length !== 1"
          >
            Upload Single Video
          </n-button>

          <n-button
            v-else
            type="primary"
            @click="handleUpload"
            :disabled="selectedVideos.length === 0"
          >
            Schedule Bulk Upload
          </n-button>
        </n-space>
      </n-space>
    </div>
  </n-modal>
</template>

<style scoped>
/* Add any custom styles here */
</style>