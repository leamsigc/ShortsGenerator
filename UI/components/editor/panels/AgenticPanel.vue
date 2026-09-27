<script lang="ts" setup>
/**
 * AgenticPanel — prompt → AI topic options (POST /api/clipper/ai/topics) →
 * one-click project composition: stock videos per videotag (max 3), a title
 * text clip on the top elements track and background music from the song
 * library. All clip additions are applied in a single undoable engine batch.
 *
 * States: idle → thinking (topics request) → choosing (pick a direction)
 * → composing (overlay while building the timeline) → idle.
 *
 * Contract (frozen by the editor shell):
 *   props:  { elah }
 *   emits: { composed: [] }
 */
import { secondsToFrames } from "@elah/core"
import type { ElahEditor } from "~/composables/useElahEditor"

const props = defineProps<{ elah: ElahEditor }>()
const emit = defineEmits<{ composed: [] }>()

const API = useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080"
const message = useMessage()
const fps = computed(() => props.elah.project.value.fps)

type PanelState = "idle" | "thinking" | "choosing" | "composing"

const state = ref<PanelState>("idle")
const prompt = ref("")
const askedPrompt = ref("")
const error = ref("")

const SAMPLE_PROMPTS = [
  "Serene mountain sunrise",
  "Product launch ad",
  "Brand story reel",
  "Ocean waves at golden hour",
]

interface TopicOption {
  name: string
  description?: string
  videotags: string[]
  imagetags?: string[]
  musicQuery?: string
}

interface StockVideo {
  id?: number | string
  url: string
  thumbnail?: string
  duration?: number | null
  user?: string
}

const options = ref<TopicOption[]>([])
const thinking = computed(() => state.value === "thinking")
const busy = computed(() => state.value !== "idle")

const pickSample = (sample: string) => {
  if (busy.value) return
  prompt.value = sample
}

// =====================================================================
// Step 1 — prompt → topic options
// =====================================================================
const submit = async () => {
  const trimmed = prompt.value.trim()
  if (!trimmed || state.value !== "idle") return
  askedPrompt.value = trimmed
  prompt.value = ""
  error.value = ""
  state.value = "thinking"
  try {
    const res = await $fetch<{ status?: string; data?: { options?: TopicOption[] } }>(
      `${API}/api/clipper/ai/topics`,
      { method: "POST", body: { prompt: trimmed } },
    )
    const opts = res.data?.options ?? []
    if (!opts.length) {
      error.value = "The AI returned no options — try rephrasing your prompt."
      state.value = "idle"
      return
    }
    options.value = opts
    state.value = "choosing"
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Request failed."
    state.value = "idle"
  }
}

// =====================================================================
// Step 2 — compose the chosen direction onto the timeline
// =====================================================================
/** Probe an audio file's duration (seconds; 0 when unavailable). */
const probeAudioDuration = (url: string): Promise<number> =>
  new Promise((resolve) => {
    const el = document.createElement("audio")
    el.preload = "metadata"
    el.onloadedmetadata = () =>
      resolve(Number.isFinite(el.duration) && el.duration > 0 ? el.duration : 0)
    el.onerror = () => resolve(0)
    el.src = url
  })

const compose = async (option: TopicOption) => {
  const elah = props.elah
  state.value = "composing"
  error.value = ""
  try {
    const videoTrackId = elah.trackByKind("video")
    const elementsTrackId = elah.topElementsTrackId()
    const audioTrackId = elah.trackByKind("audio")
    if (!videoTrackId || !elementsTrackId) throw new Error("The timeline is missing a video or elements track.")

    // Stock video per videotag (max 3) — first result each.
    const picks: { url: string; name: string; durationSec: number }[] = []
    for (const tag of (option.videotags ?? []).slice(0, 3)) {
      const res = await $fetch<{ status?: string; data?: StockVideo[] }>(`${API}/api/stock/videos`, {
        query: { query: tag, per_page: 2 },
      })
      const hit = res.data?.[0]
      if (hit?.url) {
        picks.push({ url: hit.url, name: hit.user || tag, durationSec: Math.min(hit.duration || 8, 15) })
      }
    }

    // Background music — first song matching musicQuery, else the first song.
    let songUrl = ""
    let songName = ""
    let songDuration = 0
    if (audioTrackId) {
      const songsRes = await $fetch<{ data?: { songs?: string[] } }>(`${API}/api/getSongs`)
      const songs = (songsRes.data?.songs ?? []).filter(s => !s.startsWith("."))
      const query = (option.musicQuery ?? "").trim().toLowerCase()
      const song = (query && songs.find(s => s.toLowerCase().includes(query))) || songs[0]
      if (song) {
        songName = song
        songUrl = `${API}/static/assets/music/${encodeURIComponent(song)}`
        songDuration = await probeAudioDuration(songUrl)
      }
    }

    // Compose after the seeded source video (if any), else from frame 0.
    const seeded = elah.clipsByTrack.value[elah.trackByKind("video")]?.[0]
    const composeStart = seeded ? seeded.startFrame + seeded.durationFrames : 0

    elah.engine.batch(() => {
      let cursor = composeStart
      for (const pick of picks) {
        const durationFrames = Math.max(1, secondsToFrames(pick.durationSec, fps.value))
        elah.addClip({
          trackId: videoTrackId,
          type: "video",
          src: pick.url,
          name: pick.name,
          startFrame: cursor,
          durationFrames,
        })
        cursor += durationFrames
      }
      // Title at the start of the composed section (shifted right if occupied).
      elah.addClipFree({
        trackId: elementsTrackId,
        type: "text",
        name: option.name,
        startFrame: composeStart,
        durationFrames: Math.max(1, secondsToFrames(3, fps.value)),
        text: {
          content: option.name,
          fontSize: 72,
          color: "#FFFFFF",
          fontFamily: "Poppins",
          fontWeight: "bold",
          textAlign: "center",
        },
        transform: { x: 0.5, y: 0.15, scale: 1, rotation: 0, anchor: { x: 0.5, y: 0.5 } },
      })
      if (songUrl && audioTrackId) {
        const fallbackSec = elah.totalFrames.value / fps.value || 60
        elah.addClip({
          trackId: audioTrackId,
          type: "audio",
          src: songUrl,
          name: songName,
          startFrame: 0,
          durationFrames: Math.max(1, secondsToFrames(songDuration || fallbackSec, fps.value)),
          volume: 0.4,
        })
      }
    }, "Compose AI project")

    message.success(`Composed "${option.name}"`)
    emit("composed")
  } catch (e) {
    const text = e instanceof Error ? e.message : "Could not compose the project."
    error.value = text
    message.error(text)
  } finally {
    options.value = []
    state.value = "idle"
  }
}
</script>

<template>
  <div class="relative flex h-full min-h-0 flex-col">
    <!-- Header -->
    <div class="flex items-center gap-2 border-b border-clipper-ink/08 dark:border-white/08 px-3 py-2.5">
      <Icon name="ph:sparkle" size="14" class="text-clipper-green" />
      <span class="text-sm font-semibold text-clipper-ink dark:text-white">Agentic AI</span>
    </div>

    <!-- Body -->
    <div class="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
      <n-alert v-if="error" type="error" closable @close="error = ''">
        {{ error }}
      </n-alert>

      <p
        v-if="!askedPrompt"
        class="text-[11px] leading-relaxed text-clipper-ink/50 dark:text-white/50"
      >
        Describe the video you want to build — the AI plans stock footage, a
        title and music, then composes it on the timeline.
      </p>

      <!-- Prompt -->
      <div class="space-y-2">
        <n-input
          v-model:value="prompt"
          type="textarea"
          :autosize="true"
          :disabled="busy"
          placeholder="Describe the video you want to build…"
          @keydown.enter.prevent="submit()"
        />
        <n-button
          type="primary"
          size="small"
          block
          :loading="thinking"
          :disabled="state !== 'idle' || !prompt.trim()"
          @click="submit()"
        >
          <template #icon><Icon name="ph:sparkle" size="14" /></template>
          Generate
        </n-button>
      </div>

      <!-- Sample prompt chips -->
      <div class="flex flex-wrap gap-1.5">
        <n-tag
          v-for="sample in SAMPLE_PROMPTS"
          :key="sample"
          size="small"
          round
          :checkable="false"
          class="cursor-pointer"
          @click="pickSample(sample)"
        >{{ sample }}</n-tag>
      </div>

      <!-- Chosen prompt (muted line once back to idle) -->
      <p
        v-if="askedPrompt && state === 'idle'"
        class="truncate text-[11px] text-clipper-ink/50 dark:text-white/50"
      >“{{ askedPrompt }}”</p>

      <!-- Thinking -->
      <div
        v-if="thinking"
        class="flex items-center gap-2 text-[11px] text-clipper-ink/50 dark:text-white/50"
      >
        <n-spin size="small" />
        <span>Thinking…</span>
      </div>

      <!-- Direction options -->
      <div v-if="state === 'choosing' && options.length > 0" class="space-y-2">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-clipper-ink/50 dark:text-white/50">
          Pick a direction
        </p>
        <button
          v-for="opt in options"
          :key="opt.name"
          type="button"
          class="w-full cursor-pointer space-y-1.5 rounded-lg border border-clipper-ink/10 p-3 text-left transition-colors hover:border-clipper-green dark:border-white/10"
          @click="compose(opt)"
        >
          <p class="text-sm font-semibold text-clipper-ink dark:text-white">{{ opt.name }}</p>
          <p v-if="opt.description" class="text-xs text-clipper-ink/50 dark:text-white/50">{{ opt.description }}</p>
          <div class="flex flex-wrap gap-1">
            <n-tag v-for="tag in opt.videotags" :key="tag" size="tiny" :bordered="false">{{ tag }}</n-tag>
          </div>
        </button>
      </div>
    </div>

    <!-- Composing overlay (solid surface) -->
    <div
      v-if="state === 'composing'"
      class="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-white dark:bg-neutral-900"
    >
      <n-spin size="medium" />
      <span class="text-xs font-medium text-clipper-ink dark:text-white">Composing project…</span>
    </div>
  </div>
</template>
