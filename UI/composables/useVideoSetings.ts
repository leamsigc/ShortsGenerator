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
  const video = useLocalStorage<{
    script: string;
    voice: string;
    videoSubject: string;
    extraPrompt: string;
    search: string;
    aiModel: string;
    finalVideoUrl: string;
    selectedAudio: string;
    selectedVideoUrls: VideoResultFormat[];
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
    selectedVideoUrls: [],
  });


  return { video }
}