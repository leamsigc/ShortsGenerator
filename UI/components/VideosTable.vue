<script lang="ts" setup>
/**
 *
 * Component Description:Desc
 *
 * @author Reflect-Media <Leamsigc>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

import "tabulator-tables/dist/css/tabulator.min.css";
import {
  TabulatorFull as Tabulator,
  type ColumnDefinition,
} from "tabulator-tables";
const table = ref(null); //reference to your table element
const tabulator = ref<Tabulator | null>(null); //variable to hold your table

const columns = ref<ColumnDefinition[]>([
  { title: "Name", field: "name", width: 180 },
  { title: "Title", field: "title", width: 220 },
  { title: "Path", field: "path", width: 200 },
  { title: "Type", field: "type", width: 80 },
  {
    title: "Created At", field: "created_at", width: 140, formatter: (cell: any) => {
      const date = new Date(cell.getValue());
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
  },
  {
    title: "Actions",
    field: "actions",
    width: 100,
    formatter: () => '<button class="preview-btn bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600 text-sm">Preview</button>',
    cellClick: (e: any, cell: any) => {
      const videoData = cell.getRow().getData();
      showVideoModal(videoData);
    }
  },
]);
const data = ref<Record<string, any>[]>([]);
const showModal = ref(false);
const selectedVideo = ref<Record<string, any> | null>(null);

// Function to show video modal
const showVideoModal = (videoData: Record<string, any>) => {
  selectedVideo.value = videoData;
  showModal.value = true;
};

// Function to load videos from API
const loadVideos = async () => {
  try {
    const response = await fetch('/api/getVideos');
    const result = await response.json();
    if (result.status === 'success') {
      // Load metadata for each video
      const videosWithMetadata = await Promise.all(
        result.data.videos.map(async (videoName: string) => {
          try {
            const metadataResponse = await fetch(`/static/generated_videos/${videoName.replace('.mp4', '_metadata.json')}`);
            const metadata = await metadataResponse.json();
            return {
              id: videoName,
              name: videoName,
              ...metadata
            };
          } catch (error) {
            // Fallback if metadata file doesn't exist
            return {
              id: videoName,
              name: videoName,
              title: videoName,
              type: 'video',
              created_at: new Date().toISOString()
            };
          }
        })
      );
      data.value = videosWithMetadata;
    }
  } catch (error) {
    console.error('Error loading videos:', error);
  }
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

onMounted(async () => {
  if (!table.value) return;

  // Load videos first
  await loadVideos();

  tabulator.value = new Tabulator(table.value, {
    data: data.value, //link data to table
    reactiveData: true, //enable data reactivity
    columns: columns.value, //define table columns
    layout: "fitDataStretch",
    responsiveLayout: "collapse",
    pagination: false,
    paginationSize: 10,
    paginationSizeSelector: [5, 10, 25, 50],
  });
});
</script>

<template>
  <div class="max-w-screen-xl w-full">
    <h3>Generated Videos</h3>
    <div ref="table"></div>

    <!-- Video Details Modal -->
    <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-2xl font-bold">Video Details</h2>
          <button @click="showModal = false" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>

        <div v-if="selectedVideo" class="space-y-4">
          <!-- Video Preview -->
          <div class="mb-4">
            <video :src="`/static${selectedVideo.path}`" controls class="w-full max-h-96 rounded-lg"></video>
          </div>

          <!-- Basic Info -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <h3 class="font-semibold text-lg mb-2">Basic Information</h3>
              <p><strong>Name:</strong> {{ selectedVideo.name }}</p>
              <p><strong>Title:</strong> {{ selectedVideo.title }}</p>
              <p><strong>Type:</strong> {{ selectedVideo.type }}</p>
              <p><strong>Created At:</strong> {{ new Date(selectedVideo.created_at).toLocaleString() }}</p>
              <p><strong>Video Subject:</strong> {{ selectedVideo.video_subject }}</p>
              <p><strong>AI Model:</strong> {{ selectedVideo.ai_model }}</p>
            </div>

            <div>
              <h3 class="font-semibold text-lg mb-2">Path Information</h3>
              <p><strong>Path:</strong> {{ selectedVideo.path }}</p>
              <p><strong>Full Path:</strong> /static{{ selectedVideo.path }}</p>
            </div>
          </div>

          <!-- Script -->
          <div>
            <h3 class="font-semibold text-lg mb-2">Script</h3>
            <div class="bg-gray-100 p-4 rounded-lg max-h-40 overflow-y-auto">
              <p class="whitespace-pre-wrap">{{ selectedVideo.script }}</p>
            </div>
          </div>

          <!-- Metadata -->
          <div>
            <h3 class="font-semibold text-lg mb-2">Metadata</h3>
            <div class="bg-gray-100 p-4 rounded-lg">
              <p><strong>Title:</strong> {{ selectedVideo.metadata?.title }}</p>
              <p><strong>Description:</strong> {{ selectedVideo.metadata?.description }}</p>
              <p><strong>Tags:</strong> {{ selectedVideo.metadata?.tags?.join(', ') }}</p>
            </div>
          </div>

          <!-- Formatted Metadata for Copy-Paste -->
          <div>
            <h3 class="font-semibold text-lg mb-2">Copy-Paste Format</h3>
            <div class="bg-gray-100 p-4 rounded-lg">
              <pre class="whitespace-pre-wrap text-sm">{{ selectedVideo.metadata?.formatted_metadata }}</pre>
            </div>
            <button @click="copyToClipboard(selectedVideo.metadata?.formatted_metadata)"
              class="mt-2 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
              Copy Metadata
            </button>
          </div>

          <!-- Search Terms -->
          <div>
            <h3 class="font-semibold text-lg mb-2">Search Terms Used</h3>
            <div class="flex flex-wrap gap-2">
              <span v-for="term in selectedVideo.search_terms" :key="term"
                class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                {{ term }}
              </span>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="mt-6 pt-4 border-t border-gray-200">
            <h3 class="font-semibold text-lg mb-2">Quick Actions</h3>
            <div class="flex gap-2">
              <a :href="`/static${selectedVideo.path}`" download
                class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 text-sm">
                Download Video
              </a>
              <button @click="copyToClipboard(selectedVideo.path)"
                class="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600 text-sm">
                Copy Path
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped></style>
