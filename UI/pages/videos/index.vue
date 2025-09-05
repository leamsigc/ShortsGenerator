<script lang="ts" setup>
/**
 *
 * All generated videos
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */
const videos = ref<{ name: string; type: string }[]>([]);
const selectedVideos = ref<{ name: string; type: string }[]>([]);
const router = useRouter();

let videosData: { videos: string[]; instagram: string[] } = { videos: [], instagram: [] };

try {
  const { data } = await $fetch<{ data: { videos: string[]; instagram: string[] } }>(
    "http://localhost:8080/api/getVideos"
  );
  videosData = data;
} catch (error) {
  console.error('Failed to load videos:', error);
  // Show error message to user
  console.warn('Could not load videos from server');
}

videos.value = [
  ...videosData.videos.map(video => ({ name: video, type: 'generated' })),
  ...videosData.instagram.map(video => ({ name: video, type: 'instagram' }))
];

const toggleVideoSelection = (video: { name: string; type: string }) => {
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

const previewVideo = (video: string) => {
  if (process.client) {
    window.open(`http://localhost:8080/static/generated_videos/${video}`, '_blank');
  }
};

const handleUploadToFacebook = (video: { name: string; type: string }) => {
  const videosToUpload = [video];
  const videosQuery = encodeURIComponent(JSON.stringify(videosToUpload));
  router.push(`/facebook?videos=${videosQuery}`);
};

const handleBulkUploadToFacebook = () => {
  if (selectedVideos.value.length === 0) {
    return;
  }
  const videosQuery = encodeURIComponent(JSON.stringify(selectedVideos.value));
  router.push(`/facebook?videos=${videosQuery}`);
};


</script>

<template>
  <div class="py-28 px-10">
    <div class="flex justify-between items-center mb-10">
      <h1 class="text-3xl leading-10 font-bold">Generated videos</h1>
      <n-space>
        <n-button type="primary" @click="handleBulkUploadToFacebook" :disabled="selectedVideos.length === 0">
          <template #icon>
            <Icon name="material-symbols:upload" />
          </template>
          Upload to Facebook ({{ selectedVideos.length }})
        </n-button>
      </n-space>
    </div>

    <n-card class="mb-4">
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
    </n-card>

    <n-table :bordered="true" :single-line="true">
      <thead>
        <tr>
          <th width="50">
            <n-checkbox :checked="selectedVideos.length === videos.length && videos.length > 0"
              :indeterminate="selectedVideos.length > 0 && selectedVideos.length < videos.length"
              @update:checked="selectAllVideos" />
          </th>
          <th>ID</th>
          <th>Name</th>
          <th>Type</th>
          <th>Size</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(video, index) in videos" :key="video.name">
          <td>
            <n-checkbox :checked="selectedVideos.some(v => v.name === video.name)"
              @update:checked="toggleVideoSelection(video)" />
          </td>
          <td>{{ index + 1 }}</td>
          <td>{{ video.name }}</td>
          <td>
            <n-tag :type="video.type === 'instagram' ? 'info' : 'success'">
              {{ video.type === 'instagram' ? 'Instagram' : 'Generated' }}
            </n-tag>
          </td>
          <td>~5MB</td>
          <td>
            <n-space>
              <n-button text type="primary" @click="previewVideo(video.name)">
                <template #icon>
                  <Icon name="material-symbols:play-circle" />
                </template>
                Preview
              </n-button>
              <n-button text type="success" @click="handleUploadToFacebook(video)">
                <template #icon>
                  <Icon name="material-symbols:upload" />
                </template>
                Upload to Facebook
              </n-button>
            </n-space>
          </td>
        </tr>
      </tbody>
    </n-table>
  </div>
</template>
<style scoped></style>
