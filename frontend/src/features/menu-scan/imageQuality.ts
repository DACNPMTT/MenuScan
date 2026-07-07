// Client-side image quality gate for the "Ảnh đạt? nét · sáng" step.
//
// Runs entirely in the browser on a downscaled copy of the captured frame — no
// upload, no API, instant feedback. It answers "is this frame sharp and well
// lit enough to OCR?" so we can prompt a retake before spending a scan.
//
// It does NOT decide "is this a menu?" — that needs OCR text and is checked on
// the backend after OCR. See the scan pipeline's text-validity stage.

export type QualityReason = 'BLURRY' | 'TOO_DARK' | 'TOO_BRIGHT'

/** Maps a quality failure to its i18n message key under `camera.quality`. */
export const QUALITY_REASON_I18N_KEY: Record<QualityReason, string> = {
  BLURRY: 'blurry',
  TOO_DARK: 'dark',
  TOO_BRIGHT: 'bright',
}

export interface QualityResult {
  ok: boolean
  /** Variance of the Laplacian on 0..255 grayscale. Higher = sharper. */
  sharpness: number
  /** Mean luminance 0..255. */
  brightness: number
  reasons: QualityReason[]
}

// Thresholds are a starting point calibrated against synthetic samples; tune on
// real menu photos (a handful of sharp/blurry/dark shots) before trusting them.
// Kept together so they are easy to adjust in one place.
export const QUALITY_THRESHOLDS = {
  minSharpness: 60,
  minBrightness: 40,
  maxBrightness: 225,
} as const

// Downscale target for the working canvas. Small enough to be instant, large
// enough that the Laplacian still sees real edges.
const WORK_MAX_DIMENSION = 256

/**
 * Assess sharpness + brightness of raw RGBA pixels. Pure and deterministic so it
 * can be unit-tested without a DOM.
 */
export function assessImageData(image: ImageData): QualityResult {
  const { data, width, height } = image
  const gray = new Float32Array(width * height)

  let brightnessSum = 0
  for (let i = 0, p = 0; i < data.length; i += 4, p += 1) {
    // Rec. 601 luma.
    const luma = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
    gray[p] = luma
    brightnessSum += luma
  }
  const brightness = brightnessSum / (width * height)

  // Variance of the Laplacian over interior pixels — the standard focus measure.
  let lapSum = 0
  let lapSqSum = 0
  let count = 0
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const c = y * width + x
      const lap =
        4 * gray[c] - gray[c - 1] - gray[c + 1] - gray[c - width] - gray[c + width]
      lapSum += lap
      lapSqSum += lap * lap
      count += 1
    }
  }
  const mean = count > 0 ? lapSum / count : 0
  const sharpness = count > 0 ? lapSqSum / count - mean * mean : 0

  const reasons: QualityReason[] = []
  if (sharpness < QUALITY_THRESHOLDS.minSharpness) reasons.push('BLURRY')
  if (brightness < QUALITY_THRESHOLDS.minBrightness) reasons.push('TOO_DARK')
  if (brightness > QUALITY_THRESHOLDS.maxBrightness) reasons.push('TOO_BRIGHT')

  return { ok: reasons.length === 0, sharpness, brightness, reasons }
}

/** Downscale any drawable into a small working canvas and assess it. */
function assessDrawable(
  source: CanvasImageSource,
  srcW: number,
  srcH: number,
): QualityResult | null {
  if (!srcW || !srcH) return null

  const scale = Math.min(1, WORK_MAX_DIMENSION / Math.max(srcW, srcH))
  const w = Math.max(1, Math.round(srcW * scale))
  const h = Math.max(1, Math.round(srcH * scale))

  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return null

  ctx.drawImage(source, 0, 0, w, h)
  return assessImageData(ctx.getImageData(0, 0, w, h))
}

/**
 * Assess a live captured frame (video or canvas). Returns null when a 2D
 * context can't be obtained.
 */
export function assessFrame(
  source: HTMLCanvasElement | HTMLVideoElement,
): QualityResult | null {
  const srcW =
    source instanceof HTMLVideoElement ? source.videoWidth : source.width
  const srcH =
    source instanceof HTMLVideoElement ? source.videoHeight : source.height
  return assessDrawable(source, srcW, srcH)
}

/**
 * Assess an uploaded image file (gallery / drag-drop). Decodes the file, then
 * assesses a downscaled copy. Returns null for non-images (e.g. PDF) or when the
 * image can't be decoded.
 */
export async function assessImageFile(file: File): Promise<QualityResult | null> {
  if (!file.type.startsWith('image/')) return null
  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file)
  } catch {
    return null
  }
  try {
    return assessDrawable(bitmap, bitmap.width, bitmap.height)
  } finally {
    bitmap.close()
  }
}
