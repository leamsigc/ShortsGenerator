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

export const useVideoSettings = () => {
  const video = useStorage<{
    script: string;
    voice: string;
    videoSubject: string;
    extraPrompt: string;
    search: string;
    aiModel: string;
    finalVideoUrl: string;
    selectedAudio: string;
    customTtsAudio: File | null;
    customTtsAudioUrl: string;
    selectedVideoUrls: VideoResultFormat[];
    // Personalization settings
    textSettings: Record<string, any>;
    aspectRatio: string;
  }>('VideoSettings', {
    script: "",
    voice: "en_us_001",
    videoSubject: "",
    extraPrompt: "",
    search: "",

    aiModel: "g4f",

    finalVideoUrl: "",
    //   Audio related

    selectedAudio: "",
    customTtsAudio: null,
    customTtsAudioUrl: "",
    selectedVideoUrls: [],

    // Personalization settings
    textSettings: {},
    aspectRatio: "9:16",
  });


  return { video }
}