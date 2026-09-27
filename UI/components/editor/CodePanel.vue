<script lang="ts" setup>
/**
 * CodePanel — "Render spec" drawer for the elah editor: pretty-printed
 * serializeProject() JSON of the current project, refreshed whenever the
 * engine emits a change (project ref is swapped), with copy + download.
 */
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ show: boolean; elah: ElahEditor }>()
const emit = defineEmits<{ "update:show": [value: boolean] }>()

const message = useMessage()

// Recomputes on project change (engine 'change' events swap the project ref)
// and each time the drawer re-opens, so the spec is always fresh.
const jsonText = computed(() => {
  void props.show
  void props.elah.project.value
  try {
    return JSON.stringify(JSON.parse(props.elah.saveProject()), null, 2)
  } catch {
    return props.elah.saveProject()
  }
})

const copyJson = async () => {
  try {
    await navigator.clipboard.writeText(jsonText.value)
    message.success("Copied")
  } catch {
    message.error("Copy failed")
  }
}

const downloadJson = () => {
  const blob = new Blob([jsonText.value], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = "project-spec.json"
  anchor.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <n-drawer
    :show="show"
    placement="right"
    :width="480"
    @update:show="emit('update:show', $event)"
  >
    <n-drawer-content closable>
      <template #header>
        <div class="flex flex-col gap-0.5">
          <span class="text-sm font-semibold text-clipper-ink dark:text-white">Render spec</span>
          <span class="text-xs text-clipper-ink/50 dark:text-white/50">Current project — serializeProject() JSON</span>
        </div>
      </template>

      <pre
        class="overflow-auto text-[11px] leading-relaxed font-mono whitespace-pre-wrap break-all p-3 rounded-lg bg-neutral-100 dark:bg-neutral-800 text-clipper-ink dark:text-white/80"
        :style="{ maxHeight: 'calc(100% - 56px)' }"
      >{{ jsonText }}</pre>

      <template #footer>
        <div class="flex items-center gap-2">
          <n-button size="small" @click="copyJson">
            <template #icon><Icon name="ph:copy" size="14" /></template>
            Copy
          </n-button>
          <n-button size="small" @click="downloadJson">
            <template #icon><Icon name="ph:file-arrow-down" size="14" /></template>
            Download JSON
          </n-button>
        </div>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>
