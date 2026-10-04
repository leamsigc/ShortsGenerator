import { useStorage } from '@vueuse/core'


export interface VideoResultFormat {
  url: string;
  image: string;
  videoUrl?: {
    fileType: string;
    link: string;
    quality: string;
  };
  type?: "local" | "remote"
}

export interface VideoSegment {
  url: string;
  startTime: number;
  endTime: number;
}

export interface UploadedImage {
  path: string;
  name: string;
  duration: number;
}

export interface VideoMetadata {
  title: string;
  description: string;
  tags: string[];
  post_content?: string;
  suggested_schedule?: string;
}

export interface SoundEffectEntry {
  path: string;
  startTime: number;
}

export type VideoOrderMode = "random" | "selection" | "custom";

export const useVideoSettings = () => {
  const defaults = {
    script: "",
    voice: "",
    videoSubject: "",
    extraPrompt: "",
    search: "",
    aiModel: "g4f",
    finalVideoUrl: "",
    selectedAudio: "",
    selectedVideoUrls: [] as VideoResultFormat[],
    videoOrderMode: "random" as VideoOrderMode,
    aspectRatio: "9:16",
    subtitleTemplate: "classic",
    subtitleFont: "",
    subtitlePosition: "bottom",
    customSubtitle: "",
    videoSegments: [] as VideoSegment[],
    backgroundMusicFromVideo: "",
    musicSource: "library" as const,
    musicVolume: 0.15,
    sfxVolume: 0.9,
    soundEffects: [] as SoundEffectEntry[],
    scriptLength: "standard" as string,
    scriptTemplate: "viral_shorts",
    useCustomAudio: false,
    customAudioPath: "",
    audioStartTime: 0,
    audioEndTime: 0,
    images: [] as UploadedImage[],
    imageDuration: 5,
    lastMetadata: null as VideoMetadata | null,
  }

  const video = useStorage<typeof defaults>('VideoSettings', { ...defaults })

  // Migrate old stored data: ensure all keys from defaults exist
  for (const key of Object.keys(defaults)) {
    if (!(key in video.value)) {
      ;(video.value as any)[key] = (defaults as any)[key]
    }
  }
  // Guard against stale/invalid order modes from older builds
  const validModes: VideoOrderMode[] = ["random", "selection", "custom"]
  if (!validModes.includes((video.value as any).videoOrderMode)) {
    ;(video.value as any).videoOrderMode = "random"
  }

  return { video, defaults }
}
