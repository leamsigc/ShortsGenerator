<script lang="ts" setup>
const { globalSettings } = useGlobalSettings();

const previewStyle = computed(() => {
    return {
        color: globalSettings.value.color,
        fontFamily: globalSettings.value.google_font || 'Arial',
        fontSize: `${globalSettings.value.fontsize / 3}px`, // Scaled down for preview
        backgroundColor: globalSettings.value.background_opacity > 0
            ? globalSettings.value.background_color
            : 'transparent',
        opacity: globalSettings.value.background_opacity,
        lineHeight: `${globalSettings.value.line_spacing}em`,
        padding: `${globalSettings.value.padding / 2}px`,
        textAlign: globalSettings.value.text_align as 'left' | 'center' | 'right',
        WebkitTextStroke: `${globalSettings.value.stroke_width / 2}px ${globalSettings.value.stroke_color}`,
        textShadow: globalSettings.value.shadow_enabled
            ? `${globalSettings.value.shadow_offset[0]}px ${globalSettings.value.shadow_offset[1]}px ${globalSettings.value.shadow_color}`
            : 'none',
        maxWidth: '100%',
        wordWrap: globalSettings.value.word_wrap ? 'break-word' : 'normal',
    }
});
</script>

<template>
    <div class="subtitle-preview" :style="previewStyle">
        <slot>Preview Text</slot>
    </div>
</template>