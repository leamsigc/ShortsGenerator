export const useVideoSettings = () => {
    const video = useLocalStorage('VideoSettings',{
        script: "",
        voice: "en_us_001",
        videoSubject: "",
        extraPrompt: "",
        search: "",

        aiModel: "g4f",

        finalVideoUrl: "",
        //   Audio related 

        selectedAudio: ""
    });


    return { video }
}