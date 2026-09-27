import { useClipperStore } from "~/stores/ClipperStore";

/**
 * Composable: useClipper
 *
 * Provides a clean API surface around the ClipperStore for the CLIPPER
 * workspace pages and components. Encapsulates API calls, SSE progress
 * streaming, and clip selection state.
 */
export function useClipper() {
  const store = useClipperStore();

  const isProcessing = computed(() => store.processing);
  const hasProgress = computed(() => store.progress !== null);
  const progress = computed(() => store.progress);
  const currentProject = computed(() => store.currentProject);
  const clips = computed(() => store.sortedClips);
  const selectedClips = computed(() => store.selectedClipsList);
  const hasSelected = computed(() => store.selectedClips.length > 0);
  const canExport = computed(
    () => store.currentProject !== null && store.selectedClips.length > 0
  );

  const refreshClips = async () => {
    if (store.currentProject) {
      await store.fetchProjectClips(store.currentProject.id);
    }
  };

  const streamProgress = (projectId: string) => {
    const API_URL = useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080";
    const eventSource = new EventSource(`${API_URL}/api/clipper/pipeline/stream?project_id=${projectId}`);

    eventSource.onmessage = (event) => {
      const progress = JSON.parse(event.data);
      store.updateProgress(progress);
    };

    eventSource.onerror = (err) => {
      console.error("SSE stream error", err);
      eventSource.close();
    };

    return eventSource;
  };

  return {
    store,
    isProcessing,
    hasProgress,
    progress,
    currentProject,
    clips,
    selectedClips,
    hasSelected,
    canExport,
    refreshClips,
    streamProgress,
  };
}
