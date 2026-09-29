import { defineStore } from "pinia"

const getApiUrl = (): string => {
  try {
    return useApiSettings().API_SETTINGS.value.URL || "http://localhost:8080"
  } catch {
    return "http://localhost:8080"
  }
}

export interface WordTimestamp {
  word: string
  start: number
  end: number
  confidence: number
}

export interface SentenceTimestamp {
  text: string
  start: number
  end: number
}

export interface OutlineItem {
  topic: string
  start: number
  end: number
  summary: string
}

export interface Transcript {
  video_url: string
  duration: number
  words: WordTimestamp[]
  sentences: SentenceTimestamp[]
  topics: string[]
  i_words: number
  engagement_signals: Record<string, any>
  outline?: OutlineItem[]
  language?: string
  language_probability?: number
}

export interface LlmSettings {
  provider: string
  base_url: string
  api_key: string
  model: string
  outline_enabled: boolean
  g4f_use_cookies: boolean
  g4f_provider: string
  g4f_model: string
}

export interface G4fProviderInfo {
  id: string
  label: string
  url: string
  default_model: string
  models: string[]
  needs_cookies: boolean
}

export interface PublishRecord {
  id: string
  clip_id: string
  clip_hook_title: string
  platforms: string[]
  scheduled_at: string
  visibility: string
  title: string
  video_url: string
  status: string
  response: string
  created_at: string
}

export interface ExportResultItem {
  clip_id: string
  status: string
  output_url: string
}

export const EXPORT_FORMATS = ["tiktok", "reels", "shorts", "douyin", "xiaohongshu", "bilibili", "youtube"] as const
export const EXPORT_QUALITIES = ["high", "medium", "low"] as const

export interface ViralityScores {
  hook_score: number
  engagement_score: number
  value_score: number
  shareability_score: number
  overall_score: number
  pause_count: number
  excitement_markers: number
  question_marks: number
  has_cta: boolean
}

export interface ClipSegment {
  id: string
  project_id: string
  source_id: string
  index: number
  start_time: number
  end_time: number
  duration: number
  transcript: string
  scores: ViralityScores
  hook_title: string
  thumbnail_url: string
  status: string
  face_x?: number
  face_y?: number
  title?: string
  description?: string
  tags?: string[]
  post_content?: string
  suggested_schedule?: string
  is_compilation?: boolean
  source_clip_ids?: string[]
}

export interface ClipTemplate {
  subtitle_template: string
  font: string
  font_size: number
  color: string
  stroke_color: string
  stroke_width: number
  hook_position: string
  hook_animation: string
  broll_enabled: boolean
  broll_keyword: string
  transition_type: string
  transition_duration: number
}

export interface ClipperProject {
  id: string
  name: string
  description: string
  source_urls: string[]
  training_data: string
  template: ClipTemplate
  target_platform: string
  created_at: string
  updated_at: string
  status: string
  source_ids: string[]
  golden_urls?: string[]
  extra_resources?: string[]
}

export interface PipelineProgress {
  stage: string
  progress: number
  message: string
  current_clip: number
  total_clips: number
  preview_url?: string
  updated_at?: string
}

interface ClipperState {
  projects: ClipperProject[]
  currentProject: ClipperProject | null
  clips: ClipSegment[]
  selectedClips: string[]
  processing: boolean
  progress: PipelineProgress | null
  transcripts: Record<string, Transcript>
  activeView: "clips" | "sources" | "transcript" | "publish" | "settings"
  activeClipId: string | null
  llmSettings: LlmSettings | null
  llmProviders: string[]
  publishRecords: PublishRecord[]
}

export const useClipperStore = defineStore("clipper", {
  state: (): ClipperState => ({
    projects: [],
    currentProject: null,
    clips: [],
    selectedClips: [],
    processing: false,
    progress: null,
    transcripts: {},
    activeView: "clips",
    activeClipId: null,
    llmSettings: null,
    llmProviders: ["gemini", "g4f", "openai", "ollama", "qwen"],
    publishRecords: [],
  }),

  getters: {
    activeClip: (state) => {
      return state.clips.find(c => c.id === state.activeClipId) || state.clips[0] || null
    },
    sortedClips: (state) => {
      return [...state.clips].sort((a, b) => b.scores.overall_score - a.scores.overall_score)
    },
    selectedClipsList: (state) => {
      return state.clips.filter(c => state.selectedClips.includes(c.id))
    },
    projectById: (state) => (id: string) => {
      return state.projects.find(p => p.id === id)
    },
    clipById: (state) => (id: string) => {
      return state.clips.find(c => c.id === id)
    },
  },

  actions: {
    updateProgress(progress: Partial<PipelineProgress>) {
      this.progress = { ...this.progress, ...progress } as PipelineProgress | null
    },

    async fetchProjects() {
      try {
        const res = await $fetch<{ status: string; data: ClipperProject[] }>(
          `${getApiUrl()}/api/clipper/projects`
        )
        if (res.status === "success") {
          this.projects = res.data
        }
      } catch (e) {
        console.error("Failed to fetch projects", e)
      }
    },

    async fetchProject(projectId: string): Promise<ClipperProject | null> {
      try {
        const res = await $fetch<{ status: string; data: ClipperProject }>(
          `${getApiUrl()}/api/clipper/projects/${projectId}`
        )
        if (res.status === "success") {
          const idx = this.projects.findIndex(p => p.id === projectId)
          if (idx !== -1) this.projects[idx] = res.data
          else this.projects.push(res.data)
          return res.data
        }
        return null
      } catch (e) {
        console.error("Failed to fetch project", e)
        return null
      }
    },

    async createProject(data: Partial<ClipperProject>) {
      try {
        const res = await $fetch<{ status: string; data: ClipperProject }>(
          `${getApiUrl()}/api/clipper/projects`,
          {
            method: "POST",
            body: data,
          }
        )
        if (res.status === "success") {
          this.projects.unshift(res.data)
          return res.data
        }
      } catch (e) {
        console.error("Failed to create project", e)
        throw e
      }
    },

    async updateProject(projectId: string, data: Partial<ClipperProject>) {
      try {
        const res = await $fetch<{ status: string; data: ClipperProject }>(
          `${getApiUrl()}/api/clipper/projects/${projectId}`,
          {
            method: "PUT",
            body: data,
          }
        )
        if (res.status === "success") {
          const idx = this.projects.findIndex(p => p.id === projectId)
          if (idx !== -1) {
            this.projects[idx] = res.data
          }
          if (this.currentProject?.id === projectId) {
            this.currentProject = res.data
          }
          return res.data
        }
      } catch (e) {
        console.error("Failed to update project", e)
        throw e
      }
    },

    async addSource(projectId: string, url: string) {
      try {
        const res = await $fetch<{ status: string; data: { source_id: string; url: string } }>(
          `${getApiUrl()}/api/clipper/projects/${projectId}/sources`,
          {
            method: "POST",
            body: { url },
          }
        )
        if (res.status === "success") {
          const project = this.projects.find(p => p.id === projectId)
          if (project) {
            project.source_urls.push(res.data.url)
            project.source_ids.push(res.data.source_id)
          }
          if (this.currentProject?.id === projectId) {
            this.currentProject = { ...this.currentProject }
          }
          return res.data
        }
      } catch (e) {
        console.error("Failed to add source", e)
        throw e
      }
    },

    async removeSource(projectId: string, sourceId: string) {
      try {
        await $fetch(`${getApiUrl()}/api/clipper/projects/${projectId}/sources/${sourceId}`, {
          method: "DELETE",
        })
        await this.fetchProjects()
        if (this.currentProject?.id === projectId) {
          const refreshed = this.projects.find(p => p.id === projectId)
          if (refreshed) this.currentProject = refreshed
        }
      } catch (e) {
        console.error("Failed to remove source", e)
        throw e
      }
    },

    async deleteProject(projectId: string) {
      try {
        await $fetch(`${getApiUrl()}/api/clipper/projects/${projectId}`, {
          method: "DELETE",
        })
        this.projects = this.projects.filter(p => p.id !== projectId)
        if (this.currentProject?.id === projectId) {
          this.currentProject = null
        }
      } catch (e) {
        console.error("Failed to delete project", e)
        throw e
      }
    },

    async uploadLocalSource(projectId: string, file: File, srtFile?: File | null) {
      const formData = new FormData()
      formData.append("video", file)
      if (srtFile) formData.append("srt", srtFile)
      try {
        const res = await $fetch<{ status: string; data: { source_id: string; url: string; filename: string; srt: boolean } }>(
          `${getApiUrl()}/api/clipper/projects/${projectId}/upload`,
          { method: "POST", body: formData }
        )
        if (res.status === "success") {
          const project = this.projects.find(p => p.id === projectId)
          if (project) {
            project.source_urls.push(res.data.url)
            project.source_ids.push(res.data.source_id)
          }
          if (this.currentProject?.id === projectId) {
            this.currentProject = { ...this.currentProject }
          }
          return res.data
        }
      } catch (e) {
        console.error("Failed to upload source", e)
        throw e
      }
    },

    async cancelProcessing(projectId?: string) {
      try {
        const res = await $fetch<{ status: string }>(
          `${getApiUrl()}/api/clipper/cancel`,
          {
            method: "POST",
            body: projectId ? { project_id: projectId } : { project_id: "*" },
          }
        )
        return res
      } catch (e) {
        console.error("Failed to cancel processing", e)
        throw e
      }
    },

    async fetchLlmSettings() {
      try {
        const res = await $fetch<{ status: string; data: { settings: LlmSettings; providers: string[] } }>(
          `${getApiUrl()}/api/clipper/llm/settings`
        )
        if (res.status === "success") {
          this.llmSettings = res.data.settings
          this.llmProviders = res.data.providers
          return res.data
        }
        return null
      } catch (e) {
        console.error("Failed to fetch LLM settings", e)
        return null
      }
    },

    async updateLlmSettings(data: Partial<LlmSettings>) {
      try {
        const res = await $fetch<{ status: string; data: { settings: LlmSettings } }>(
          `${getApiUrl()}/api/clipper/llm/settings`,
          { method: "POST", body: data }
        )
        if (res.status === "success") {
          this.llmSettings = res.data.settings
          return res.data.settings
        }
        return null
      } catch (e) {
        console.error("Failed to update LLM settings", e)
        throw e
      }
    },

    async testLlmConnection(settings?: Partial<LlmSettings>, signal?: AbortSignal) {
      try {
        const res = await $fetch<{ status: string; data: { ok: boolean; detail: string; provider: string } }>(
          `${getApiUrl()}/api/clipper/llm/test`,
          { method: "POST", body: settings ? { settings } : {}, signal }
        )
        return res.data
      } catch (e: any) {
        if (e?.data?.data) return e.data.data
        console.error("Failed to test LLM connection", e)
        throw e
      }
    },

    async fetchG4fCookieStatus() {
      try {
        const res = await $fetch<{ status: string; data: { ok: boolean; reason: string; detail: string; renew_steps: string[] } }>(
          `${getApiUrl()}/api/clipper/llm/cookie-status`
        )
        if (res.status === "success") return res.data
        return null
      } catch (e) {
        console.error("Failed to check cookie status", e)
        return null
      }
    },

    async refreshG4fCookies() {
      try {
        const res = await $fetch<{ status: string; data: { cleared: string[]; cookies_found: number; status: { ok: boolean; reason: string; detail: string; renew_steps: string[] } } }>(
          `${getApiUrl()}/api/clipper/llm/cookies/refresh`,
          { method: "POST" }
        )
        if (res.status === "success") return res.data
        return null
      } catch (e) {
        console.error("Failed to refresh cookies", e)
        return null
      }
    },

    async fetchG4fProviders() {
      try {
        const res = await $fetch<{ status: string; data: { providers: G4fProviderInfo[] } }>(
          `${getApiUrl()}/api/clipper/llm/g4f-providers`
        )
        if (res.status === "success") return res.data.providers
        return null
      } catch (e) {
        console.error("Failed to fetch g4f providers", e)
        return null
      }
    },

    async fetchPublishRecords(projectId: string) {
      try {
        const res = await $fetch<{ status: string; data: PublishRecord[] }>(
          `${getApiUrl()}/api/clipper/projects/${projectId}/publish-records`
        )
        if (res.status === "success") {
          this.publishRecords = res.data
        }
      } catch (e) {
        console.error("Failed to fetch publish records", e)
      }
    },

    async deletePublishRecord(projectId: string, recordId: string) {
      try {
        await $fetch(`${getApiUrl()}/api/clipper/projects/${projectId}/publish-records/${recordId}`, {
          method: "DELETE",
        })
        this.publishRecords = this.publishRecords.filter(r => r.id !== recordId)
      } catch (e) {
        console.error("Failed to delete publish record", e)
        throw e
      }
    },

    async generateCover(clipId: string): Promise<string | null> {
      try {
        const res = await $fetch<{ status: string; data: { cover_url: string } }>(
          `${getApiUrl()}/api/clipper/clip/${clipId}/cover`,
          { method: "POST" }
        )
        if (res.status === "success") {
          const idx = this.clips.findIndex(c => c.id === clipId)
          if (idx !== -1) {
            this.clips[idx] = { ...this.clips[idx], thumbnail_url: res.data.cover_url }
          }
          return res.data.cover_url
        }
        return null
      } catch (e) {
        console.error("Failed to generate cover", e)
        return null
      }
    },

    async exportClips(projectId: string, clipIds: string[] | null, format: string, quality: string, burnSubtitles: boolean) {
      try {
        const res = await $fetch<{ status: string; data: { results: ExportResultItem[]; preset: { format: string; aspect: string; crf: number; preset: string } } }>(
          `${getApiUrl()}/api/clipper/export`,
          {
            method: "POST",
            body: {
              project_id: projectId,
              ...(clipIds?.length ? { clip_ids: clipIds } : {}),
              format,
              quality,
              burn_subtitles: burnSubtitles,
            },
          }
        )
        if (res.status === "cancelled") {
          return null
        }
        if (res.status === "success") {
          return res.data
        }
        return null
      } catch (e) {
        console.error("Failed to export clips", e)
        throw e
      }
    },

    async setCurrentProject(projectId: string) {
      const project = this.projects.find(p => p.id === projectId)
      if (project) {
        this.currentProject = project
      }
    },

    async processProject(projectId: string, language: string | null = "auto", opts: { autoSelect?: boolean; modelSize?: string } = {}) {
      this.processing = true
      this.progress = { stage: "downloading", progress: 0, message: "Starting...", current_clip: 0, total_clips: 0 }

      const eventSource = new EventSource(`${getApiUrl()}/api/clipper/pipeline/stream?project_id=${projectId}`)

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.progress = data
      }

      try {
        const res = await $fetch<{ status: string; data: { project: ClipperProject; sources: any[]; clips: ClipSegment[] } }>(
          `${getApiUrl()}/api/clipper/process`,
          {
            method: "POST",
            body: {
              project_id: projectId,
              language,
              auto_select: opts.autoSelect ?? true,
              ...(opts.modelSize ? { model_size: opts.modelSize } : {}),
            },
          }
        )
        if (res.status === "cancelled") {
          return null
        }
        if (res.status === "success") {
          await this.fetchProjects()
          const refreshed = this.projects.find(p => p.id === projectId)
          if (refreshed) this.currentProject = refreshed
          if (res.data.clips?.length) {
            this.clips = res.data.clips
            this.activeClipId = res.data.clips[0].id
            this.activeView = "clips"
          } else {
            await this.fetchProjectClips(projectId)
          }
          this.loadTranscripts(projectId)
          return res.data
        }
        return null
      } catch (e) {
        console.error("Failed to process project", e)
        throw e
      } finally {
        this.processing = false
        eventSource.close()
        this.progress = null
      }
    },

    async loadTranscripts(projectId: string) {
      const project = this.projects.find(p => p.id === projectId) || this.currentProject
      if (!project?.source_ids?.length) return
      for (const sourceId of project.source_ids) {
        await this.fetchTranscript(projectId, sourceId)
      }
    },

    sourceVideoUrl(projectId: string, sourceId: string): string {
      return `${getApiUrl()}/api/clipper/projects/${projectId}/sources/${sourceId}/video`
    },

    async selectClips(projectId: string, options: { max_clips?: number; ai_model?: string; min_duration?: number; max_duration?: number; model_size?: string } = {}) {
      this.processing = true
      this.progress = { stage: "scoring", progress: 0, message: "Scoring segments...", current_clip: 0, total_clips: 0 }

      const eventSource = new EventSource(`${getApiUrl()}/api/clipper/pipeline/stream?project_id=${projectId}`)
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.progress = data
      }

      try {
        const res = await $fetch<{ status: string; data: { clips: ClipSegment[] } }>(
          `${getApiUrl()}/api/clipper/select`,
          {
            method: "POST",
            body: { project_id: projectId, ...options },
          }
        )
        if (res.status === "cancelled") {
          return null
        }
        if (res.status === "success") {
          this.clips = res.data.clips
          this.selectedClips = res.data.clips.map(c => c.id)
          return res.data.clips
        }
        return null
      } catch (e) {
        console.error("Failed to select clips", e)
        throw e
      } finally {
        this.processing = false
        eventSource.close()
        this.progress = null
      }
    },

    async fetchProjectClips(projectId: string, minScore = 0) {
      try {
        const res = await $fetch<{ status: string; data: ClipSegment[] }>(
          `${getApiUrl()}/api/clipper/projects/${projectId}/clips?min_score=${minScore}`
        )
        if (res.status === "success") {
          this.clips = res.data
        }
      } catch (e) {
        console.error("Failed to fetch clips", e)
      }
    },

    async fetchClip(clipId: string): Promise<ClipSegment | null> {
      try {
        const res = await $fetch<{ status: string; data: ClipSegment }>(
          `${getApiUrl()}/api/clipper/clip/${clipId}`
        )
        if (res.status === "success") {
          const idx = this.clips.findIndex(c => c.id === clipId)
          if (idx !== -1) {
            this.clips[idx] = res.data
          } else {
            this.clips.push(res.data)
          }
          return res.data
        }
        return null
      } catch (e) {
        console.error("Failed to fetch clip", e)
        return null
      }
    },

    async generatePreview(clipId: string, width = 480): Promise<string | null> {
      try {
        const res = await $fetch<{ status: string; data: { preview_url: string } }>(
          `${getApiUrl()}/api/clipper/clip/${clipId}/preview`,
          { method: "POST", body: { width } }
        )
        if (res.status === "success") {
          const idx = this.clips.findIndex(c => c.id === clipId)
          if (idx !== -1) {
            this.clips[idx] = { ...this.clips[idx], thumbnail_url: res.data.preview_url }
          }
          return res.data.preview_url
        }
        return null
      } catch (e) {
        console.error("Failed to generate preview", e)
        return null
      }
    },

    clipVideoUrl(clipId: string): string {
      return `${getApiUrl()}/api/clipper/clip/${clipId}/video`
    },

    async renderClip(clipId: string, faceX = 0.5, faceY = 0.35, opts: { format?: string; quality?: string; burnSubtitles?: boolean; aspect?: string } = {}) {
      try {
        const res = await $fetch<{ status: string; data: { clip: ClipSegment; output_url: string } }>(
          `${getApiUrl()}/api/clipper/clip/${clipId}/render`,
          {
            method: "POST",
            body: {
              face_x: faceX,
              face_y: faceY,
              ...(opts.format ? { format: opts.format } : {}),
              ...(opts.quality ? { quality: opts.quality } : {}),
              ...(opts.burnSubtitles !== undefined ? { burn_subtitles: opts.burnSubtitles } : {}),
              ...(opts.aspect ? { aspect: opts.aspect } : {}),
            },
          }
        )
        if (res.status === "success") {
          const idx = this.clips.findIndex(c => c.id === clipId)
          if (idx !== -1) {
            this.clips[idx] = res.data.clip
          }
          return res.data
        }
      } catch (e) {
        console.error("Failed to render clip", e)
        throw e
      }
    },

    async trimClip(clipId: string, startTime?: number, endTime?: number) {
      try {
        const res = await $fetch<{ status: string; data: ClipSegment }>(
          `${getApiUrl()}/api/clipper/clip/${clipId}/trim`,
          {
            method: "POST",
            body: { start_time: startTime, end_time: endTime },
          }
        )
        if (res.status === "success") {
          const idx = this.clips.findIndex(c => c.id === clipId)
          if (idx !== -1) {
            this.clips[idx] = res.data
          }
          return res.data
        }
      } catch (e) {
        console.error("Failed to trim clip", e)
        throw e
      }
    },

    async splitClip(clipId: string, splitTime: number) {
      try {
        const res = await $fetch<{ status: string; data: { clip1: ClipSegment; clip2: ClipSegment } }>(
          `${getApiUrl()}/api/clipper/clip/${clipId}/split`,
          {
            method: "POST",
            body: { split_time: splitTime },
          }
        )
        if (res.status === "success") {
          const idx = this.clips.findIndex(c => c.id === clipId)
          if (idx !== -1) {
            this.clips[idx] = res.data.clip1
          }
          this.clips.push(res.data.clip2)
          return res.data
        }
      } catch (e) {
        console.error("Failed to split clip", e)
        throw e
      }
    },

    async mergeClips(clipIds: string[], outputName = "merged") {
      try {
        const res = await $fetch<{ status: string; data: ClipSegment }>(
          `${getApiUrl()}/api/clipper/merge`,
          {
            method: "POST",
            body: { clip_ids: clipIds, output_name: outputName, render: true },
          }
        )
        if (res.status === "success") {
          this.clips.push(res.data)
          return res.data
        }
      } catch (e) {
        console.error("Failed to merge clips", e)
        throw e
      }
    },

    async fetchTranscript(projectId: string, sourceId: string) {
      try {
        const res = await $fetch<{ status: string; data: Transcript }>(
          `${getApiUrl()}/api/clipper/transcript/${projectId}/${sourceId}`
        )
        if (res.status === "success") {
          this.transcripts[`${projectId}/${sourceId}`] = res.data
          return res.data
        }
      } catch (e) {
        console.error("Failed to fetch transcript", e)
        return null
      }
    },

    async generateClipMetadata(clipId: string, aiModel = "llm") {
      try {
        const res = await $fetch<{ status: string; data: { title: string; description: string; tags: string[]; post_content: string; suggested_schedule: string } }>(
          `${getApiUrl()}/api/clipper/clip/${clipId}/metadata`,
          { method: "POST", body: { ai_model: aiModel } }
        )
        if (res.status === "success") {
          const idx = this.clips.findIndex(c => c.id === clipId)
          if (idx !== -1) {
            this.clips[idx] = { ...this.clips[idx], ...res.data }
          }
          return res.data
        }
      } catch (e) {
        console.error("Failed to generate metadata", e)
        throw e
      }
    },

    async scheduleClip(clipId: string, payload: { scheduledAt: string; content: string; title: string; description: string; platforms: string[]; url: string; apiToken: string; videoBaseUrl: string; visibility?: string }) {
      try {
        const res = await $fetch<{ status: string; data: any }>(
          `${getApiUrl()}/api/clipper/clip/${clipId}/schedule`,
          { method: "POST", body: payload }
        )
        return res
      } catch (e) {
        console.error("Failed to schedule clip", e)
        throw e
      }
    },

    toggleClipSelection(clipId: string) {
      const idx = this.selectedClips.indexOf(clipId)
      if (idx === -1) {
        this.selectedClips.push(clipId)
      } else {
        this.selectedClips.splice(idx, 1)
      }
    },

    clearSelection() {
      this.selectedClips = []
    },
  },
})
