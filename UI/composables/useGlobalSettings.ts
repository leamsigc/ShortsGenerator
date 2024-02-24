
export const useApiSettings = () => {
    const API_SETTINGS = useLocalStorage("API_SETTINGS", {
        URL:"http://localhost:8080",
    })
    return {
        API_SETTINGS
    }
}
export const useGlobalSettings = () => {
    const globalSettings = useLocalStorage("globalSettings", {
        font: "Roboto",
        color: "#000",
        subtitles_position: "center,bottom",
        fontsize: 20,
        stroke_color: "#000",
        stroke_width: 5,
        aiModel: "g4f",
        voice: "en_us_001",
    });

    return {
        globalSettings
    };
}