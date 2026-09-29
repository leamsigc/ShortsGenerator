<script lang="ts" setup>
/**
 * VoiceSettings — Generate view's VOICE tab content.
 * Full TTS settings (engine, voices, Qwen3 characters/design/clone,
 * audition preview). The chosen voice binds to the per-video setting.
 */
const { video } = useVideoSettings();
</script>

<template>
  <TtsSettingsPanel v-model="video.voice" />
</template>
<style scoped></style>
