import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Camera,
  CheckCircle2,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import type { ScanData } from '@/features/menu-scan/types'
import {
  assessFrame,
  QUALITY_REASON_I18N_KEY,
  type QualityResult,
} from '@/features/menu-scan/imageQuality'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Reveal } from '@/shared/components/motion/Reveal'
import { Button } from '@/shared/components/ui/button'

type CameraState = 'starting' | 'live' | 'captured' | 'submitting' | 'error'

export function CameraScanPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('camera.title')} | MenuScan`)
  const navigate = useNavigate()

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [state, setState] = useState<CameraState>('starting')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [capturedUrl, setCapturedUrl] = useState<string | null>(null)
  const [quality, setQuality] = useState<QualityResult | null>(null)
  const capturedBlob = useRef<Blob | null>(null)

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  const startCamera = useCallback(async () => {
    setState('starting')
    setErrorMessage(null)
    try {
      // Stop any prior stream before requesting a new one.
      stopStream()
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play().catch(() => undefined)
      }
      setState('live')
    } catch (err) {
      const name = (err as DOMException)?.name
      setErrorMessage(
        name === 'NotAllowedError'
          ? t('camera.errors.denied')
          : name === 'NotFoundError'
            ? t('camera.errors.notFound')
            : t('camera.errors.openFailed'),
      )
      setState('error')
    }
  }, [stopStream, t])

  useEffect(() => {
    // Defer to a microtask so the setState inside startCamera doesn't run
    // synchronously during the effect body (react-hooks/set-state-in-effect).
    let active = true
    Promise.resolve().then(() => {
      if (active) void startCamera()
    })
    return () => {
      active = false
      stopStream()
      if (capturedUrl) URL.revokeObjectURL(capturedUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCapture = () => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    // Assess the captured frame (sharpness + brightness) before we commit to it.
    setQuality(assessFrame(canvas))
    canvas.toBlob((blob) => {
      if (!blob) return
      if (capturedUrl) URL.revokeObjectURL(capturedUrl)
      capturedBlob.current = blob
      setCapturedUrl(URL.createObjectURL(blob))
      setState('captured')
      // Freeze the live feed once a frame is chosen.
      stopStream()
    }, 'image/jpeg', 0.9)
  }

  const handleRetake = () => {
    if (capturedUrl) URL.revokeObjectURL(capturedUrl)
    setCapturedUrl(null)
    setQuality(null)
    capturedBlob.current = null
    void startCamera()
  }

  const handleSubmit = async () => {
    const blob = capturedBlob.current
    if (!blob) return
    setState('submitting')
    const file = new File([blob], `camera-scan-${Date.now()}.jpg`, {
      type: 'image/jpeg',
    })
    const formData = new FormData()
    formData.append('file', file)
    try {
      const scan = await apiRequest<ScanData>('/api/v1/scans', {
        method: 'POST',
        body: formData,
      })
      navigate(`/app/scans/${scan.id}`)
    } catch (error) {
      setState('captured')
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : t('camera.errors.uploadFailed'),
      )
    }
  }

  return (
    <PageTransition className="mx-auto w-full max-w-[800px] px-[30px] py-[40px] sm:px-[50px]">
      <Button variant="ghost" size="sm" asChild className="mb-6 w-fit">
        <Link to="/app/scan">
          <ArrowLeft className="size-4" aria-hidden />
          {t('camera.backToUpload')}
        </Link>
      </Button>

      <h1 className="mb-6 text-[32px] font-bold leading-[38px] text-ink">
        {t('camera.title')}
      </h1>

      {errorMessage && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Viewfinder */}
      <Reveal>
        <div className="relative aspect-[3/4] w-full overflow-hidden rounded-3xl border border-border bg-ink shadow-3 sm:aspect-video">
          {capturedUrl ? (
            <img
              src={capturedUrl}
              alt={t('camera.capturedAlt')}
              className="h-full w-full object-contain"
            />
          ) : (
            <video
              ref={videoRef}
              playsInline
              muted
              className="h-full w-full object-cover"
            />
          )}

          {/* Overlay framing corners (matches the camera viewfinder intent). */}
          {state === 'live' && (
            <div className="pointer-events-none absolute inset-0">
              <div className="absolute left-4 top-4 size-12 rounded-tl-[2px] border-l-[3px] border-t-[3px] border-primary" />
              <div className="absolute right-4 top-4 size-12 rounded-tr-[2px] border-r-[3px] border-t-[3px] border-primary" />
              <div className="absolute bottom-4 left-4 size-12 rounded-bl-[2px] border-b-[3px] border-l-[3px] border-primary" />
              <div className="absolute bottom-4 right-4 size-12 rounded-br-[2px] border-b-[3px] border-r-[3px] border-primary" />
            </div>
          )}

          {(state === 'starting' || state === 'submitting') && (
            <div className="absolute inset-0 flex items-center justify-center bg-ink/60">
              <Loader2 className="size-8 animate-spin text-white" aria-hidden />
            </div>
          )}

          {state === 'error' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center">
              <Camera className="size-8 text-white/80" aria-hidden />
              <p className="text-[14px] text-white/80">
                {t('camera.unavailable')}
              </p>
              <Button
                type="button"
                onClick={() => void startCamera()}
              >
                {t('common.retry')}
              </Button>
            </div>
          )}
        </div>
      </Reveal>

      {/* Quality gate feedback (soft block — user may still use the photo). */}
      {state === 'captured' && quality && (
        quality.ok ? (
          <div className="mt-4 flex items-center gap-2 rounded-2xl border border-primary/30 bg-primary/5 px-4 py-2.5 text-[14px] text-primary">
            <CheckCircle2 className="size-4 shrink-0" aria-hidden />
            <span>{t('camera.quality.ok')}</span>
          </div>
        ) : (
          <div
            role="status"
            className="mt-4 flex items-start gap-3 rounded-2xl border border-amber/40 bg-amber/10 px-4 py-3 text-[14px] text-amber"
          >
            <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
            <div className="flex flex-col gap-1">
              <span className="font-bold">{t('camera.quality.warnTitle')}</span>
              <ul className="flex flex-col gap-0.5">
                {quality.reasons.map((reason) => (
                  <li key={reason}>
                    • {t(`camera.quality.${QUALITY_REASON_I18N_KEY[reason]}`)}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )
      )}

      {/* Controls */}
      <Reveal delay={0.08}>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {state === 'live' && (
            <Button type="button" size="lg" onClick={handleCapture}>
              <Camera className="size-5" aria-hidden />
              {t('camera.capture')}
            </Button>
          )}
          {state === 'captured' && (
            <>
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={handleRetake}
              >
                <RefreshCw className="size-5" aria-hidden />
                {t('camera.retake')}
              </Button>
              <Button type="button" size="lg" onClick={handleSubmit}>
                {t('camera.useThis')}
              </Button>
            </>
          )}
        </div>
      </Reveal>

      <p className="mt-4 text-center text-[13px] text-ink-variant">
        {t('camera.hint')}
      </p>
    </PageTransition>
  )
}
