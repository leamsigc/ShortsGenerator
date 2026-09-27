import {
  TimelineEngine,
  PlaybackEngine,
  GpuRenderer,
  createDefaultDemuxerFactory,
  AudioPlaybackController,
  resolveTimeline,
  framesToTimecode,
  secondsToFrames,
  getTotalFrames,
  serializeProject,
  deserializeProject,
  clipsOverlap,
} from "@elah/core"
import type {
  Project,
  Clip,
  Track,
  CreateClipOptions,
  Transform,
  TrackKind,
  ShapeVariant,
  InitialTrackConfig,
  Transition,
  TransitionKind,
  TransitionEasing,
} from "@elah/core"

/**
 * Default lane seeding — mirrors the elah Production playground: one video
 * track, four elements (text/shape) lanes stacked on top, then two audio lanes
 * (a main, full-volume track plus a secondary one).
 * Order is top→bottom in the UI (lower order = higher zIndex, renders on top).
 */
export const DEFAULT_EL_TRACKS: InitialTrackConfig[] = [
  { kind: "video", name: "Video" },
  { kind: "elements", name: "Elements" },
  { kind: "elements", name: "Elements 2" },
  { kind: "elements", name: "Elements 3" },
  { kind: "elements", name: "Elements 4" },
  { kind: "audio", name: "Audio (Main)" },
  { kind: "audio", name: "Audio 2" },
]

/**
 * useElahEditor — Vue binding for the @elah/core browser video engine.
 *
 * Owns the TimelineEngine (mutations/undo), PlaybackEngine (RAF clock),
 * GpuRenderer (WebGL2 preview) and AudioPlaybackController, and mirrors
 * everything into Vue refs so templates/components stay reactive.
 * All mutations funnel through the engine — never mutate projectRef directly.
 *
 * Rendered frames are deterministic: resolveTimeline(frame, project) is
 * pure, so preview and export produce identical pixels.
 */
export function useElahEditor(options: {
  fps?: number
  stage?: { width: number; height: number }
  initialTracks?: { kind: "video" | "audio" | "elements"; name: string }[]
} = {}) {
  const fps = options.fps ?? 30

  const engine = new TimelineEngine({
    fps,
    stage: options.stage ?? { width: 1080, height: 1920 },
    initialTracks: options.initialTracks ?? DEFAULT_EL_TRACKS,
  })

  const playback = new PlaybackEngine({
    fps,
    getTotalFrames: () => engine.getTotalFrames(),
  })

  // ---- Vue-reactive mirrors of engine state ----
  const project = shallowRef<Project>(engine.getProject())
  const currentFrame = ref(0)
  const isPlaying = ref(false)
  const playbackRate = ref(1)
  const loop = ref(false)
  const canUndo = ref(false)
  const canRedo = ref(false)

  const syncProject = () => {
    project.value = engine.getProject()
    canUndo.value = engine.canUndo()
    canRedo.value = engine.canRedo()
  }
  engine.on("change", syncProject)

  const unsubPlayback = playback.subscribe((snap) => {
    currentFrame.value = snap.currentFrame
    isPlaying.value = snap.isPlaying
    playbackRate.value = snap.playbackRate
    loop.value = snap.loop
  })

  // ---- Selection (multi-select capable; primary = last selected) ----
  const selectedClipIds = ref<string[]>([])
  const selectedClipId = computed<string | null>({
    get: () => selectedClipIds.value[selectedClipIds.value.length - 1] ?? null,
    set: (id) => {
      selectedClipIds.value = id ? [id] : []
    },
  })
  const findClip = (clipId: string | null): { clip: Clip; trackId: string } | null =>
    clipId ? engine.findClip(clipId) : null
  const selectedClip = computed<Clip | null>(() => findClip(selectedClipId.value)?.clip ?? null)

  const setSelection = (ids: string[]) => {
    selectedClipIds.value = [...new Set(ids)]
  }
  const toggleSelection = (clipId: string) => {
    const idx = selectedClipIds.value.indexOf(clipId)
    if (idx === -1) selectedClipIds.value.push(clipId)
    else selectedClipIds.value.splice(idx, 1)
  }
  const selectAll = () => {
    selectedClipIds.value = Object.values(project.value.clips).flat().map(c => c.id)
  }
  const selectNone = () => {
    selectedClipIds.value = []
  }

  // ---- Tracks / clips helpers (reactive views) ----
  const tracks = computed<Track[]>(() => project.value.tracks)
  const clipsByTrack = computed<Record<string, Clip[]>>(() => project.value.clips)
  const totalFrames = computed(() => getTotalFrames(project.value.clips))
  const timecode = computed(() => framesToTimecode(currentFrame.value, fps))

  // ---- Mutations (all through the engine — single undo funnel) ----
  const undo = () => { engine.undo() }
  const redo = () => { engine.redo() }

  const addClip = (opts: CreateClipOptions) => {
    const clip = engine.addClip(opts)
    selectedClipId.value = clip.id
    return clip
  }
  /** Add at the requested start if free, else shift right to the next free slot. */
  const addClipFree = (opts: CreateClipOptions) => {
    const start = findFreeStart(opts.trackId, opts.startFrame, opts.durationFrames)
    if (start === null) return null
    return addClip({ ...opts, startFrame: start })
  }
  const removeClip = (clip: Clip) => {
    engine.removeClip(clip.id, clip.trackId)
    if (selectedClipIds.value.includes(clip.id)) {
      selectedClipIds.value = selectedClipIds.value.filter(id => id !== clip.id)
    }
  }
  const removeSelectedClips = () => {
    const ids = [...selectedClipIds.value]
    if (!ids.length) return
    engine.batch(() => {
      for (const id of ids) {
        const found = engine.findClip(id)
        if (found) engine.removeClip(found.clip.id, found.trackId)
      }
    }, "Remove clips")
    selectedClipIds.value = []
  }
  const updateClip = (clipId: string, trackId: string, updates: Partial<Clip>) =>
    engine.updateClip(clipId, trackId, updates)

  // Interaction-session mutations: cheap preview (no history) + single commit on release.
  const previewClip = (clipId: string, trackId: string, updates: Partial<Clip>) =>
    engine.previewClip(clipId, trackId, updates)
  const commitInteraction = (description?: string) => engine.commitInteraction(description)
  const cancelInteraction = () => engine.cancelInteraction()

  const moveClip = (clipId: string, fromTrackId: string, toTrackId: string, startFrame: number) =>
    engine.moveClip(clipId, fromTrackId, toTrackId, Math.max(0, Math.round(startFrame)))

  const trimClip = (clipId: string, trackId: string, startFrame: number, durationFrames: number) =>
    engine.trimClip(clipId, trackId, Math.max(0, Math.round(startFrame)), Math.max(1, Math.round(durationFrames)))

  const splitAtPlayhead = (clipId: string, trackId: string) =>
    engine.splitClip(clipId, trackId, currentFrame.value)

  const setStage = (width: number, height: number) => engine.setStage(width, height)

  const addTrack = (kind: TrackKind, name?: string) =>
    engine.addTrack(kind, name ? { name } : undefined)
  const removeTrack = (trackId: string) => {
    engine.removeTrack(trackId)
    selectedClipIds.value = selectedClipIds.value.filter(id => {
      const found = engine.findClip(id)
      return found !== null
    })
  }
  const updateTrack = (trackId: string, updates: Partial<Track>) =>
    engine.updateTrack(trackId, updates)

  // First track id of a kind (e.g. video / elements / audio) — the panels use
  // this to route inserted stock/text/audio clips.
  const trackByKind = (kind: TrackKind): string =>
    project.value.tracks.find(t => t.kind === kind)?.id ?? ""

  // Duplicate the primary selected clip right after itself (single undo entry)
  const duplicateSelected = (): string | null => {
    const found = findClip(selectedClipId.value)
    if (!found) return null
    const id = engine.cloneClip(
      found.clip.id,
      found.clip.trackId,
      found.clip.startFrame + found.clip.durationFrames,
    )
    if (id) selectedClipId.value = id
    return id
  }

  // Topmost elements track (lowest `order`) — text/shape presets land here.
  const topElementsTrackId = (): string =>
    [...project.value.tracks].filter(t => t.kind === "elements").sort((a, b) => a.order - b.order)[0]?.id ?? trackByKind("elements")

  // ---- Transitions ----
  const addTransition = (opts: {
    fromClipId: string
    toClipId: string
    trackId: string
    kind: TransitionKind
    durationFrames: number
    easing?: TransitionEasing
  }): Transition | null => engine.addTransition(opts)
  const updateTransition = (
    transitionId: string,
    patch: Partial<Pick<Transition, "kind" | "durationFrames" | "easing" | "direction">>,
  ) => engine.updateTransition(transitionId, patch)
  const removeTransition = (transitionId: string) => engine.removeTransition(transitionId)

  // ---- Master volume (project-level; mirrored to the audio output gain) ----
  const masterVolume = computed<number>({
    get: () => project.value.masterVolume ?? 1,
    set: (v) => engine.setMasterVolume(v),
  })

  /** First non-overlapping start >= desiredStart on a track (engine.addClip throws on overlap). */
  const findFreeStart = (trackId: string, desiredStart: number, durationFrames: number): number | null => {
    if (engine.isTrackLocked(trackId)) return null
    const trackClips = project.value.clips[trackId] ?? []
    let start = Math.max(0, Math.round(desiredStart))
    for (let guard = 0; guard < 1000; guard++) {
      const hit = trackClips.find(c => clipsOverlap({ startFrame: start, durationFrames }, c))
      if (!hit) return start
      start = hit.startFrame + hit.durationFrames
    }
    return null
  }

  // ---- Copy / paste (in-memory clipboard, deep-cloned clips) ----
  let clipboard: Clip[] = []

  const copySelectedClips = (): number => {
    const ids = new Set(selectedClipIds.value)
    const clips = Object.values(project.value.clips)
      .flat()
      .filter(c => ids.has(c.id))
      .sort((a, b) => a.startFrame - b.startFrame)
      .map(c => JSON.parse(JSON.stringify(c)) as Clip)
    if (clips.length) clipboard = clips
    return clips.length
  }

  const buildPasteOptions = (raw: Clip, trackId: string, startFrame: number): CreateClipOptions => {
    const base = {
      trackId,
      name: `${raw.name} copy`,
      startFrame: Math.max(0, Math.round(startFrame)),
      durationFrames: raw.durationFrames,
      ...(raw.volume !== undefined ? { volume: raw.volume } : {}),
      ...(raw.opacity !== undefined ? { opacity: raw.opacity } : {}),
      ...(raw.transform ? { transform: JSON.parse(JSON.stringify(raw.transform)) as Transform } : {}),
    }
    switch (raw.type) {
      case "video":
      case "audio":
      case "image":
        return { ...base, type: raw.type, src: raw.src ?? "", ...(raw.assetId ? { assetId: raw.assetId } : {}) }
      case "text":
        return {
          ...base,
          type: "text",
          text: {
            content: raw.content ?? "",
            ...(raw.fontSize !== undefined ? { fontSize: raw.fontSize } : {}),
            ...(raw.color !== undefined ? { color: raw.color } : {}),
            ...(raw.fontFamily !== undefined ? { fontFamily: raw.fontFamily } : {}),
            ...(raw.fontWeight !== undefined ? { fontWeight: raw.fontWeight } : {}),
            ...(raw.textAlign !== undefined ? { textAlign: raw.textAlign } : {}),
          },
        }
      case "shape":
        return {
          ...base,
          type: "shape",
          shape: {
            shapeKind: raw.shapeKind ?? "rect",
            ...(raw.shapeFill !== undefined ? { shapeFill: raw.shapeFill } : {}),
            ...(raw.shapeStroke !== undefined ? { shapeStroke: raw.shapeStroke } : {}),
            ...(raw.shapeStrokeWidth !== undefined ? { shapeStrokeWidth: raw.shapeStrokeWidth } : {}),
          },
        }
      case "freehand":
        return {
          ...base,
          type: "freehand",
          freehand: {
            ...(raw.pathData !== undefined ? { pathData: raw.pathData } : {}),
            ...(raw.strokeColor !== undefined ? { strokeColor: raw.strokeColor } : {}),
            ...(raw.strokeWidth !== undefined ? { strokeWidth: raw.strokeWidth } : {}),
          },
        }
    }
  }

  /** Paste the clipboard at the playhead, preserving relative offsets; returns pasted ids. */
  const pasteClips = (): string[] => {
    if (!clipboard.length) return []
    const anchor = Math.min(...clipboard.map(c => c.startFrame))
    const newIds: string[] = []
    engine.batch(() => {
      for (const raw of clipboard) {
        const trackId = project.value.tracks.some(t => t.id === raw.trackId)
          ? raw.trackId
          : project.value.tracks.find(t => t.kind === project.value.tracks.find(x => x.id === raw.trackId)?.kind)?.id
        if (!trackId || engine.isTrackLocked(trackId)) continue
        const start = findFreeStart(trackId, currentFrame.value + (raw.startFrame - anchor), raw.durationFrames)
        if (start === null) continue
        try {
          const created = engine.addClip(buildPasteOptions(raw, trackId, start))
          engine.updateClip(created.id, created.trackId, {
            sourceStartFrame: raw.sourceStartFrame,
            sourceDurationFrames: raw.sourceDurationFrames,
            ...(raw.textAnimation ? { textAnimation: { ...raw.textAnimation } } : {}),
          })
          newIds.push(created.id)
        } catch (e) {
          console.error("[elah] paste clip failed", e)
        }
      }
    }, "Paste clips")
    if (newIds.length) selectedClipIds.value = newIds
    return newIds
  }

  // ---- Save / load (el'ah project JSON) ----
  const saveProject = (): string => serializeProject(engine)
  const loadProject = (json: string) => {
    deserializeProject(engine, json)
    selectedClipIds.value = []
    seek(0)
  }

  // ---- Per-clip natural media dimensions (probed on import; used by overlays) ----
  const naturalSizes = shallowRef<Map<string, { width: number; height: number }>>(new Map())
  const setNaturalSize = (clipId: string, width: number, height: number) => {
    if (!width || !height) return
    const next = new Map(naturalSizes.value)
    next.set(clipId, { width, height })
    naturalSizes.value = next
  }

  // ---- Playback control ----
  const play = () => playback.play()
  const pause = () => playback.pause()
  const togglePlay = () => { isPlaying.value ? pause() : play() }
  const seek = (frame: number) => {
    const clamped = Math.max(0, Math.min(Math.round(frame), totalFrames.value))
    playback.seek(clamped)
    currentFrame.value = clamped
  }
  const setPlaybackRate = (rate: number) => playback.setPlaybackRate(rate)
  const setLoop = (value: boolean) => playback.setLoop(value)

  // ---- Video audio mirror ----
  // @elah/core keeps scene.audios strictly for clips of type 'audio' —
  // video clips NEVER produce audio on preview or export. Mirror each video
  // clip as an audio clip on the audio track with the same src + timing so
  // the AudioPlaybackController and the export mixer both pick it up.
  // The mirror is derived on the fly, so edits to the video clip (trim/move)
  // automatically carry over to its audio — no pairing bookkeeping needed.
  const withVideoAudio = (project: Project): Project => {
    const mirrors: Clip[] = []
    for (const [trackId, clips] of Object.entries(project.clips)) {
      for (const c of clips) {
        if (c.type === "video" && c.src && !c.disabled && !c.locked) {
          // Keep volume/opacity through the resolver by mirroring the clip
          // onto the audio track, but preserve the ORIGINAL track context for
          // mute/volume lookups (resolver uses clip.trackId).
          mirrors.push({
            ...c,
            id: `${c.id}::video-audio`,
            type: "audio",
          })
        }
      }
    }
    if (!mirrors.length) return project
    // Route mirrors through the audio track so engine-level mute/volume on the
    // audio lane applies to them like regular audio clips.
    const audioTrack = project.tracks.find((t) => t.kind === "audio")
    if (!audioTrack) return project
    return {
      ...project,
      clips: {
        ...project.clips,
        // Mirrors live on the audio track's list; the resolver reads
        // `clips[track.id]` per track, so they must sit under the audio track id.
        [audioTrack.id]: [...(project.clips[audioTrack.id] ?? []), ...mirrors.map((m) => ({
          ...m,
          trackId: audioTrack.id,
        }))],
      },
    }
  }


  let renderer: InstanceType<typeof GpuRenderer> | null = null
  let audioController: AudioPlaybackController | null = null
  let rafId = 0
  let mounted = false

  const demuxerFactory = createDefaultDemuxerFactory()

  const mountPreview = (container: HTMLElement) => {
    renderer = new GpuRenderer({ demuxerFactory })
    renderer.mount(container)
    const { width, height } = project.value.stage
    const rect = container.getBoundingClientRect()
    renderer.resize(rect.width || width, rect.height || height, window.devicePixelRatio)

    audioController = new AudioPlaybackController(playback, () => withVideoAudio(engine.getProject()))
    audioController.start()
    audioController.setMasterGain(project.value.masterVolume ?? 1)

    mounted = true
    const loopFn = () => {
      if (!mounted || !renderer) return
      try {
        const scene = resolveTimeline(playback.currentFrame, engine.getProject())
        renderer.render(scene)
      } catch (e) {
        console.error("[elah] render tick failed", e)
      }
      rafId = requestAnimationFrame(loopFn)
    }
    rafId = requestAnimationFrame(loopFn)
  }

  // Keep the WebAudio master gain in sync with project.masterVolume
  const stopMasterVolumeWatch = watch(
    () => project.value.masterVolume,
    (v) => audioController?.setMasterGain(v ?? 1),
  )

  const resizePreview = (cssWidth: number, cssHeight: number) => {
    renderer?.resize(cssWidth, cssHeight, window.devicePixelRatio)
  }

  const dispose = () => {
    mounted = false
    cancelAnimationFrame(rafId)
    stopMasterVolumeWatch()
    audioController?.destroy()
    renderer?.dispose()
    renderer = null
    unsubPlayback()
  }

  return {
    // engine handles (escape hatch for advanced use)
    engine,
    playback,
    // reactive state
    project,
    tracks,
    clipsByTrack,
    totalFrames,
    currentFrame,
    isPlaying,
    playbackRate,
    loop,
    selectedClipId,
    selectedClipIds,
    selectedClip,
    canUndo,
    canRedo,
    timecode,
    masterVolume,
    naturalSizes,
    // selection
    setSelection, toggleSelection, selectAll, selectNone, findClip,
    // mutations
    undo, redo,
    addClip, addClipFree, removeClip, removeSelectedClips, updateClip, previewClip, commitInteraction, cancelInteraction,
    moveClip, trimClip, splitAtPlayhead, setStage,
    addTrack, removeTrack, updateTrack,
    addTransition, updateTransition, removeTransition,
    // clipboard
    copySelectedClips, pasteClips, findFreeStart,
    // persistence
    saveProject, loadProject,
    // media dims
    setNaturalSize,
    // playback
    play, pause, togglePlay, seek, setPlaybackRate, setLoop,
    // preview lifecycle
    mountPreview, resizePreview, dispose,
    // audio mirroring (video clips produce scene audio via this wrapper)
    withVideoAudio,
    // helpers
    trackByKind, topElementsTrackId, duplicateSelected,
  }
}

export type ElahEditor = ReturnType<typeof useElahEditor>
