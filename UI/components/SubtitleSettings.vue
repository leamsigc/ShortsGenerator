<script lang="ts" setup>
/**
 *
 * Component Description:Desc
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

const { globalSettings } = useGlobalSettings();
const API_URL = "http://localhost:8080";

const handleSettingChange = (setting: string, value: any) => {
  globalSettings.value[setting] = value;
  // Debounced save to backend
  debouncedSaveSettings();
};

// Create a debounced version of saveSettings
const debouncedSaveSettings = useDebounceFn(async () => {
  try {
    await $fetch(`${API_URL}/api/settings`, {
      method: "POST",
      body: {
        type: "FONT",
        settings: {
          font: globalSettings.value.font,
          fontsize: globalSettings.value.fontsize,
          google_font: globalSettings.value.google_font,
          color: globalSettings.value.color,
          stroke_color: globalSettings.value.stroke_color,
          stroke_width: globalSettings.value.stroke_width,
          background_color: globalSettings.value.background_color,
          background_opacity: globalSettings.value.background_opacity,
          text_align: globalSettings.value.text_align,
          line_spacing: globalSettings.value.line_spacing,
          padding: globalSettings.value.padding,
          word_wrap: globalSettings.value.word_wrap,
          max_lines: globalSettings.value.max_lines,
          shadow_enabled: globalSettings.value.shadow_enabled,
          shadow_color: globalSettings.value.shadow_color,
          shadow_offset: globalSettings.value.shadow_offset,
          subtitles_position: globalSettings.value.subtitles_position,
        }
      }
    });
  } catch (error) {
    console.error('Failed to save settings:', error);
  }
}, 500); // 500ms delay

// Add preview text for testing subtitle appearance
const previewText = ref("This is a preview of how your subtitles will look");
</script>

<template>
  <div class="subtitle-settings">
    <section class="preview-section mb-8">
      <SubtitlePreview>{{ previewText }}</SubtitlePreview>
    </section>

    <n-form label-placement="left" label-width="160">
      <n-form-item label="Font">
        <n-input v-model:value="globalSettings.font" @update:value="v => handleSettingChange('font', v)" />
      </n-form-item>

      <n-form-item label="Google Font">
        <n-input v-model:value="globalSettings.google_font" @update:value="v => handleSettingChange('google_font', v)"
          placeholder="Enter Google Font name" />
      </n-form-item>

      <n-form-item label="Font Size">
        <n-input-number v-model:value="globalSettings.fontsize" @update:value="v => handleSettingChange('fontsize', v)"
          :min="10" :max="200" />
      </n-form-item>

      <n-form-item label="Font Color">
        <n-color-picker v-model:value="globalSettings.color" @update:value="v => handleSettingChange('color', v)" />
      </n-form-item>

      <n-form-item label="Stroke Color">
        <n-color-picker v-model:value="globalSettings.stroke_color"
          @update:value="v => handleSettingChange('stroke_color', v)" />
      </n-form-item>

      <n-form-item label="Stroke Width">
        <n-input-number v-model:value="globalSettings.stroke_width"
          @update:value="v => handleSettingChange('stroke_width', v)" :min="0" :max="20" />
      </n-form-item>

      <n-form-item label="Background Color">
        <n-color-picker v-model:value="globalSettings.background_color"
          @update:value="v => handleSettingChange('background_color', v)" :show-alpha="true" />
      </n-form-item>

      <n-form-item label="Background Opacity">
        <n-slider v-model:value="globalSettings.background_opacity"
          @update:value="v => handleSettingChange('background_opacity', v)" :min="0" :max="1" :step="0.1" />
      </n-form-item>

      <n-form-item label="Line Spacing">
        <n-input-number v-model:value="globalSettings.line_spacing"
          @update:value="v => handleSettingChange('line_spacing', v)" :min="1" :max="3" :step="0.1" />
      </n-form-item>

      <n-form-item label="Text Alignment">
        <n-select v-model:value="globalSettings.text_align" @update:value="v => handleSettingChange('text_align', v)"
          :options="[
            { label: 'Left', value: 'left' },
            { label: 'Center', value: 'center' },
            { label: 'Right', value: 'right' }
          ]" />
      </n-form-item>

      <n-form-item label="Enable Shadow">
        <n-switch v-model:value="globalSettings.shadow_enabled"
          @update:value="v => handleSettingChange('shadow_enabled', v)" />
      </n-form-item>

      <n-form-item label="Shadow Color" v-if="globalSettings.shadow_enabled">
        <n-color-picker v-model:value="globalSettings.shadow_color"
          @update:value="v => handleSettingChange('shadow_color', v)" :show-alpha="true" />
      </n-form-item>

      <n-form-item label="Position">
        <n-select v-model:value="globalSettings.subtitles_position"
          @update:value="v => handleSettingChange('subtitles_position', v)" :options="[
            { label: 'Top', value: 'center,top' },
            { label: 'Bottom', value: 'center,bottom' },
            { label: 'Center', value: 'center,center' }
          ]" />
      </n-form-item>
    </n-form>
  </div>
</template>
<style scoped></style>
