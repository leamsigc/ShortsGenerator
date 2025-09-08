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

const videos = ref<{ name: string; type: string; metadata?: any }[]>([]);
const selectedVideos = ref<{ name: string; type: string; metadata?: any }[]>([]);
const router = useRouter();
const showModal = ref(false);
const selectedVideo = ref<any>(null);

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

// Load videos with metadata
const loadVideosWithMetadata = async () => {
  const allVideos = [
    ...videosData.videos.map(video => ({ name: video, type: 'generated' })),
    ...videosData.instagram.map(video => ({ name: video, type: 'instagram' }))
  ];

  const videosWithMetadata = await Promise.all(
    allVideos.map(async (video) => {
      if (video.type === 'generated') {
        try {
          const metadataResponse = await $fetch(
            `http://localhost:8080/static/generated_videos/${video.name.replace('.mp4', '_metadata.json')}`
          );
          return { ...video, metadata: metadataResponse };
        } catch (error) {
          // Fallback if metadata file doesn't exist
          return {
            ...video,
            metadata: {
              title: video.name,
              type: 'video',
              created_at: new Date().toISOString()
            }
          };
        }
      }
      return video;
    })
  );

  videos.value = videosWithMetadata;
};

await loadVideosWithMetadata();

// Function to show video modal
const showVideoModal = (video: any) => {
  selectedVideo.value = video;
  showModal.value = true;
};

// Function to copy metadata to clipboard
const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    alert('Metadata copied to clipboard!');
  } catch (error) {
    console.error('Failed to copy:', error);
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    alert('Metadata copied to clipboard!');
  }
};

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
          <th>Title</th>
          <th>Type</th>
          <th>Created At</th>
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
            <span v-if="video.metadata?.title" class="truncate max-w-xs block" :title="video.metadata.title">
              {{ video.metadata.title }}
            </span>
            <span v-else class="text-gray-400">No title</span>
          </td>
          <td>
            <n-tag :type="video.type === 'instagram' ? 'info' : 'success'">
              {{ video.type === 'instagram' ? 'Instagram' : 'Generated' }}
            </n-tag>
          </td>
          <td>
            <span v-if="video.metadata?.created_at">
              {{ new Date(video.metadata.created_at).toLocaleDateString() }}
            </span>
            <span v-else class="text-gray-400">Unknown</span>
          </td>
          <td>
            <n-space>
              <n-button text type="primary" @click="showVideoModal(video)">
                <template #icon>
                  <Icon name="material-symbols:visibility" />
                </template>
                Details
              </n-button>
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

    <!-- Video Details Modal -->
    <n-modal v-model:show="showModal" preset="card" title="Video Details" size="huge" style="width: 90vw;">
      <div v-if="selectedVideo" class="space-y-6">
        <!-- Video Preview -->
        <div v-if="selectedVideo.type === 'generated'">
          <h3 class="text-lg font-semibold mb-2">Video Preview</h3>
          <video
            :src="`http://localhost:8080/${selectedVideo.metadata?.path || '/generated_videos/' + selectedVideo.name}`"
            controls class="w-full max-h-96 rounded-lg border"></video>
        </div>

        <!-- Basic Information -->
        <div class="grid grid-cols-2 gap-6">
          <div>
            <h3 class="text-lg font-semibold mb-3">Basic Information</h3>
            <div class="space-y-2">
              <p><strong>Name:</strong> {{ selectedVideo.name }}</p>
              <p><strong>Title:</strong> {{ selectedVideo.metadata?.title || 'No title' }}</p>
              <p><strong>Type:</strong> {{ selectedVideo.type === 'instagram' ? 'Instagram' : 'Generated' }}</p>
              <p><strong>Created At:</strong> {{ selectedVideo.metadata?.created_at ? new
                Date(selectedVideo.metadata.created_at).toLocaleString() : 'Unknown' }}</p>
              <p v-if="selectedVideo.metadata?.video_subject"><strong>Video Subject:</strong> {{
                selectedVideo.metadata.video_subject }}</p>
              <p v-if="selectedVideo.metadata?.ai_model"><strong>AI Model:</strong> {{ selectedVideo.metadata.ai_model
                }}
              </p>
            </div>
          </div>

          <div>
            <h3 class="text-lg font-semibold mb-3">Path Information</h3>
            <div class="space-y-2">
              <p><strong>Path:</strong> {{ selectedVideo.metadata?.path || `/generated_videos/${selectedVideo.name}` }}
              </p>
              <p><strong>Full Path:</strong> http://localhost:8080/static{{ selectedVideo.metadata?.path ||
                `/generated_videos/${selectedVideo.name}` }}</p>
            </div>
          </div>
        </div>

        <!-- Script (only for generated videos) -->
        <div v-if="selectedVideo.metadata?.script">
          <h3 class="text-lg font-semibold mb-3">Script</h3>
          <div class="bg-gray-50 p-4 rounded-lg max-h-40 overflow-y-auto border">
            <p class="whitespace-pre-wrap text-sm">{{ selectedVideo.metadata.script }}</p>
          </div>
        </div>

        <!-- Metadata -->
        <div v-if="selectedVideo.metadata?.metadata">
          <h3 class="text-lg font-semibold mb-3">Metadata</h3>
          <div class="bg-gray-50 p-4 rounded-lg border">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <p><strong>Title:</strong> {{ selectedVideo.metadata.metadata.title }}</p>
                <p><strong>Description:</strong> {{ selectedVideo.metadata.metadata.description }}</p>
              </div>
              <div>
                <p><strong>Tags:</strong></p>
                <div class="flex flex-wrap gap-1 mt-1">
                  <n-tag v-for="tag in selectedVideo.metadata.metadata.tags" :key="tag" size="small">
                    {{ tag }}
                  </n-tag>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Formatted Metadata for Copy-Paste -->
        <div v-if="selectedVideo.metadata?.metadata?.formatted_metadata">
          <h3 class="text-lg font-semibold mb-3">Copy-Paste Format</h3>
          <div class="bg-gray-50 p-4 rounded-lg border">
            <pre class="whitespace-pre-wrap text-xs">{{ selectedVideo.metadata.metadata.formatted_metadata }}</pre>
          </div>
          <n-button type="primary" @click="copyToClipboard(selectedVideo.metadata.metadata.formatted_metadata)"
            class="mt-2">
            <template #icon>
              <Icon name="material-symbols:content-copy" />
            </template>
            Copy Metadata
          </n-button>
        </div>

        <!-- Search Terms -->
        <div v-if="selectedVideo.metadata?.search_terms">
          <h3 class="text-lg font-semibold mb-3">Search Terms Used</h3>
          <div class="flex flex-wrap gap-2">
            <n-tag v-for="term in selectedVideo.metadata.search_terms" :key="term" type="info">
              {{ term }}
            </n-tag>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="pt-4 border-t">
          <h3 class="text-lg font-semibold mb-3">Quick Actions</h3>
          <n-space>
            <n-button type="primary" @click="previewVideo(selectedVideo.name)">
              <template #icon>
                <Icon name="material-symbols:play-circle" />
              </template>
              Preview Video
            </n-button>
            <n-button type="success" @click="handleUploadToFacebook(selectedVideo)">
              <template #icon>
                <Icon name="material-symbols:upload" />
              </template>
              Upload to Facebook
            </n-button>
            <n-button type="info"
              @click="copyToClipboard(selectedVideo.metadata?.path || `/generated_videos/${selectedVideo.name}`)">
              <template #icon>
                <Icon name="material-symbols:content-copy" />
              </template>
              Copy Path
            </n-button>
          </n-space>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<style scoped>
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
