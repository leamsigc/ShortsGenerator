<script lang="ts" setup>
/**
 * EditorHeader — top bar of the elah production editor shell.
 * Left: back + brand. Center: undo/redo. Right: Code / Trace toggles + Export.
 */
import type { ElahEditor } from "~/composables/useElahEditor"

defineProps<{
  elah: ElahEditor
  showCode: boolean
  showTrace: boolean
  isFullscreen: boolean
}>()

const emit = defineEmits<{
  back: []
  "update:showCode": [value: boolean]
  "update:showTrace": [value: boolean]
  export: []
  toggleFullscreen: []
}>()
</script>

<template>
  <header class="shrink-0 h-11 grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-3 border-b border-clipper-ink/08 dark:border-white/08 bg-white dark:bg-neutral-900">
    <!-- Left: back + brand -->
    <div class="flex items-center gap-2 min-w-0">
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button quaternary circle aria-label="Back to clipper" @click="emit('back')">
            <template #icon><Icon name="ph:arrow-left" size="16" /></template>
          </n-button>
        </template>
        Back to clipper
      </n-tooltip>
      <span class="flex items-center gap-2 min-w-0">
        <span class="w-2 h-2 rounded-full bg-clipper-green shrink-0" />
        <span class="font-bold text-sm text-clipper-ink dark:text-white tracking-tight truncate">CLIPPER Studio</span>
        <span class="text-[10px] font-mono text-clipper-ink/50 dark:text-white/50 hidden lg:inline">@elah/core</span>
      </span>
    </div>

    <!-- Center: history -->
    <div class="flex items-center gap-1">
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="small" quaternary :disabled="!elah.canUndo.value" title="Undo (Ctrl/Cmd+Z)" @click="elah.undo()">
            <template #icon><Icon name="ph:arrow-counter-clockwise" size="16" /></template>
          </n-button>
        </template>
        Undo
      </n-tooltip>
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button size="small" quaternary :disabled="!elah.canRedo.value" title="Redo (Ctrl/Cmd+Y)" @click="elah.redo()">
            <template #icon><Icon name="ph:arrow-clockwise" size="16" /></template>
          </n-button>
        </template>
        Redo
      </n-tooltip>
    </div>

    <!-- Right: Fullscreen / Code / Trace / Export -->
    <div class="flex items-center gap-1.5 justify-end">
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-button
            size="small"
            quaternary
            :aria-label="isFullscreen ? 'Exit fullscreen' : 'Fullscreen editor'"
            :title="isFullscreen ? 'Exit fullscreen (Esc)' : 'Fullscreen editor'"
            @click="emit('toggleFullscreen')"
          >
            <template #icon><Icon :name="isFullscreen ? 'ph:arrows-in' : 'ph:arrows-out'" size="15" /></template>
          </n-button>
        </template>
        {{ isFullscreen ? "Exit fullscreen" : "Fullscreen editor" }}
      </n-tooltip>
      <n-button
        size="small"
        quaternary
        :class="{ 'text-clipper-green': showCode }"
        title="Show render code"
        @click="emit('update:showCode', !showCode)"
      >
        <template #icon><Icon name="ph:code" size="15" /></template>
        Code
      </n-button>
      <n-button
        size="small"
        quaternary
        :class="{ 'text-clipper-green': showTrace }"
        title="Toggle trace panel"
        @click="emit('update:showTrace', !showTrace)"
      >
        <template #icon><Icon name="ph:chart-line-up" size="15" /></template>
        Trace
      </n-button>
      <span class="w-px h-4 bg-clipper-ink/08 dark:bg-white/08" />
      <n-button size="small" type="primary" title="Export" @click="emit('export')">
        <template #icon><Icon name="ph:file-arrow-down" size="15" /></template>
        Export
      </n-button>
    </div>
  </header>
</template>
