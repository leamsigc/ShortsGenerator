<script lang="ts" setup>
/**
 * TracePanel — floating dropdown card toggling @elah/core trace channels.
 * enableChannels/getEnabledChannels are not re-exported from the package
 * index, so this uses the window.__trace console API installed by
 * installTraceGlobal() (idempotent). Falls back to visual-only state with
 * a console hint if the global is unavailable.
 */
import { installTraceGlobal } from "@elah/core"

type TraceChannel =
  | "SET_PLAYHEAD"
  | "PLAYHEAD"
  | "SEEK_GATE"
  | "FEED"
  | "DECODE"
  | "CACHE_PUT"
  | "CACHE_GET"
  | "UPLOAD"
  | "DRAW"
  | "AUDIO"
  | "EXPORT"
  | "EXPORT_ASSETS"
  | "EXPORT_AUDIO"
  | "EXPORT_MUX"
  | "EXPORT_FRAMES"

interface TraceConsoleApi {
  on(...channels: TraceChannel[]): TraceChannel[]
  off(...channels: TraceChannel[]): TraceChannel[]
  all(): TraceChannel[]
  none(): TraceChannel[]
  status(): TraceChannel[]
  channels: TraceChannel[]
}

defineProps<{ show: boolean }>()
const emit = defineEmits<{ "update:show": [value: boolean] }>()

// Curated display subset — the full channel list lives on window.__trace.channels.
const DISPLAY_CHANNELS: TraceChannel[] = [
  "PLAYHEAD",
  "DECODE",
  "CACHE_PUT",
  "AUDIO",
  "DRAW",
  "EXPORT",
  "EXPORT_FRAMES",
  "FEED",
]

const enabled = ref<Set<TraceChannel>>(new Set())

const trace = (): TraceConsoleApi | undefined => window.__trace

const syncFromTrace = () => {
  try {
    const t = trace()
    enabled.value = new Set(t?.status() ?? t?.channels ?? [])
  } catch {
    enabled.value = new Set()
  }
}

onMounted(() => {
  try {
    installTraceGlobal()
  } catch {
    // best-effort — idempotent installer, never fatal for the panel
  }
  syncFromTrace()
})

const setChannel = (channel: TraceChannel, checked: boolean) => {
  const t = trace()
  if (!t) {
    const next = new Set(enabled.value)
    if (checked) next.add(channel)
    else next.delete(channel)
    enabled.value = next
    console.log(`[TracePanel] window.__trace unavailable — "${channel}" toggled visually only. installTraceGlobal() did not expose the console API.`)
    return
  }
  if (checked) t.on(channel)
  else t.off(channel)
  syncFromTrace()
}

const enableAll = () => {
  const t = trace()
  if (!t) {
    enabled.value = new Set(DISPLAY_CHANNELS)
    console.log("[TracePanel] window.__trace unavailable — 'All' applied visually only.")
    return
  }
  t.all()
  syncFromTrace()
}

const disableAll = () => {
  const t = trace()
  if (!t) {
    enabled.value = new Set()
    console.log("[TracePanel] window.__trace unavailable — 'None' applied visually only.")
    return
  }
  t.none()
  syncFromTrace()
}

const close = () => emit("update:show", false)
</script>

<template>
  <div v-if="show" class="relative">
    <div class="fixed inset-0 z-40" @click="close" />
    <div class="relative z-50">
      <div class="w-64 space-y-2 rounded-lg border border-clipper-ink/10 dark:border-white/10 bg-white dark:bg-neutral-800 shadow-lg p-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-clipper-ink dark:text-white">Trace channels</span>
          <div class="flex items-center gap-1">
            <n-button size="tiny" quaternary @click="enableAll">All</n-button>
            <n-button size="tiny" quaternary @click="disableAll">None</n-button>
          </div>
        </div>

        <div class="space-y-0.5">
          <n-checkbox
            v-for="channel in DISPLAY_CHANNELS"
            :key="channel"
            :checked="enabled.has(channel)"
            @update:checked="setChannel(channel, $event)"
          >
            <span
              class="font-mono text-[11px]"
              :class="enabled.has(channel)
                ? 'text-clipper-green'
                : 'text-clipper-ink/50 dark:text-white/50'"
            >{{ channel }}</span>
          </n-checkbox>
        </div>
      </div>
    </div>
  </div>
</template>
