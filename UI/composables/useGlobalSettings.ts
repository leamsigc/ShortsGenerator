import { useStorage } from "@vueuse/core";


export const useApiSettings = () => {
    const API_SETTINGS = useStorage("API_SETTINGS", {
        URL: "http://localhost:8080",
    })
    return {
        API_SETTINGS
    }
}

interface GlobalSettings {
    // Font settings
    font: string;
    fontsize: number;
    google_font: string;

    // Colors and styling
    color: string;
    stroke_color: string;
    stroke_width: number;
    background_color: string;
    background_opacity: number;

    // Text layout
    text_align: 'left' | 'center' | 'right';
    line_spacing: number;
    padding: number;
    word_wrap: boolean;
    max_lines: number;

    // Shadow settings
    shadow_enabled: boolean;
    shadow_color: string;
    shadow_offset: [number, number];

    // Position
    subtitles_position: string;

    // Video settings
    aspect_ratio: '9:16' | '16:9' | '1:1' | '4:5';
    max_clip_duration: number;

    // AI and voice settings
    aiModel: string;
    voice: string;
}

export const useGlobalSettings = () => {
    const globalSettings = useStorage<GlobalSettings>("globalSettings", {
        // Font settings
        font: "static/assets/fonts/bold_font.ttf",
        fontsize: 100,
        google_font: "",

        // Colors and styling
        color: "#FFFF00",
        stroke_color: "black",
        stroke_width: 5,
        background_color: "transparent",
        background_opacity: 1,

        // Text layout
        text_align: "center",
        line_spacing: 1.5,
        padding: 20,
        word_wrap: true,
        max_lines: 2,

        // Shadow settings
        shadow_enabled: false,
        shadow_color: "#000000",
        shadow_offset: [2, 2],

        // Position
        subtitles_position: "center,bottom",

        // Video settings
        aspect_ratio: "9:16",
        max_clip_duration: 15,

        // AI and voice settings
        aiModel: "g4f",
        voice: "en_us_001",
    });

    return {
        globalSettings
    };
}