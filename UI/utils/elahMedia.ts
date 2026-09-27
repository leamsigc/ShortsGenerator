/**
 * elahMedia — media probing + waveform helpers for the editor panels.
 *
 * Probing uses temporary HTMLMediaElement / HTMLImageElement instances so no
 * elah internals are needed. The URL is NOT revoked here — the caller owns the
 * lifecycle (blob URLs stay alive because clips keep using them as `src`).
 *
 * Extracted from the former ElahAssetPanel so the new stock / audio panels
 * share one implementation.
 */

export interface MediaProbeResult {
  durationSec: number
  width: number
  height: number
}

/** Probe duration (+ dimensions for video/image) of a media URL. Never throws. */
export const probeMedia = (url: string, kind: "video" | "audio" | "image"): Promise<MediaProbeResult> =>
  new Promise((resolve) => {
    const done = (durationSec: number, width = 0, height = 0) =>
      resolve({
        durationSec: Number.isFinite(durationSec) && durationSec > 0 ? durationSec : 0,
        width,
        height,
      })

    if (kind === "image") {
      const img = new Image()
      img.onload = () => done(5, img.naturalWidth, img.naturalHeight)
      img.onerror = () => done(5)
      img.src = url
      return
    }
    const el = document.createElement(kind === "audio" ? "audio" : "video")
    el.preload = "metadata"
    el.crossOrigin = "anonymous"
    el.src = url
    el.onloadedmetadata = () =>
      done(
        el.duration,
        kind === "video" ? (el as HTMLVideoElement).videoWidth : 0,
        kind === "video" ? (el as HTMLVideoElement).videoHeight : 0,
      )
    el.onerror = () => done(0)
  })

/** Audio duration only — convenience wrapper. */
export const probeAudioDuration = async (url: string): Promise<number> =>
  (await probeMedia(url, "audio")).durationSec

/** Deterministic pseudo-waveform (seeded PRNG from the seed string). */
export const waveformBars = (seed: string, count = 28): number[] => {
  let h = 2166136261
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  const out: number[] = []
  for (let i = 0; i < count; i++) {
    h ^= h << 13
    h ^= h >>> 17
    h ^= h << 5
    out.push(0.25 + ((Math.abs(h) % 1000) / 1000) * 0.75)
  }
  return out
}

/** "mm:ss" for a duration in seconds. */
export const fmtDuration = (sec: number | undefined | null): string => {
  if (!sec || !Number.isFinite(sec)) return ""
  const total = Math.round(sec)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}
