import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Camera,
  X,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { apiRequest } from '@/shared/lib/api'
import { describeError } from '@/shared/lib/errors'
import { useAuth } from '@/app/providers/AuthProvider'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import type { ScanData } from '@/features/menu-scan/types'
import {
  assessFrame,
  type QualityResult,
} from '@/features/menu-scan/imageQuality'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Reveal } from '@/shared/components/motion/Reveal'
import { Button } from '@/shared/components/ui/button'
import { Spinner } from '@/shared/components/Spinner'

type CameraState = 'starting' | 'live' | 'submitting' | 'error'

interface CapturedImage {
  id: string
  url: string
  blob: Blob
  quality?: QualityResult | null
}

export function CameraScanPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('camera.title')} | MenuScan`)
  const navigate = useNavigate()

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const { user } = useAuth()
  const [state, setState] = useState<CameraState>('starting')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [capturedImages, setCapturedImages] = useState<CapturedImage[]>([])

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
      setCapturedImages(prev => {
        prev.forEach(img => URL.revokeObjectURL(img.url))
        return prev
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCapture = () => {
    const maxFiles = user ? 8 : 2
    if (capturedImages.length >= maxFiles) return

    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    
    const qualityResult = assessFrame(canvas)
    
    canvas.toBlob((blob) => {
      if (!blob) return
      const url = URL.createObjectURL(blob)
      const newImage: CapturedImage = {
        id: Math.random().toString(36).substring(7),
        url,
        blob,
        quality: qualityResult
      }
      setCapturedImages(prev => [...prev, newImage])
      // Thêm hiệu ứng chớp tắt nho nhỏ ở video view (tuỳ chọn) bằng css. Không stop stream.
    }, 'image/jpeg', 0.92)
  }

  const handleRemoveImage = (id: string) => {
    setCapturedImages(prev => {
      const img = prev.find(p => p.id === id)
      if (img) URL.revokeObjectURL(img.url)
      return prev.filter(p => p.id !== id)
    })
  }



  const handleSubmit = async () => {
    if (capturedImages.length === 0) return
    setState('submitting')
    
    const formData = new FormData()
    capturedImages.forEach((img, index) => {
      const file = new File([img.blob], `camera-scan-${Date.now()}-${index}.jpg`, {
        type: 'image/jpeg',
      })
      formData.append('files', file)
    })
    try {
      const scan = await apiRequest<ScanData>('/api/v1/scans', {
        method: 'POST',
        body: formData,
      })
      navigate(`/app/scans/${scan.id}`)
    } catch (error) {
      setState('live')
      setErrorMessage(describeError(error, t, 'camera.errors.uploadFailed'))
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
          <video
            ref={videoRef}
            playsInline
            muted
            className="h-full w-full object-cover"
          />

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
              <Spinner label={state === 'starting' ? t('camera.starting') : t('scan.uploading')} />
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

      {/* Captured Thumbnails */}
      {capturedImages.length > 0 && (
        <div className="mt-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-[14px] font-medium uppercase tracking-[0.7px] text-ink-variant">
              Ảnh đã chụp ({capturedImages.length}/{user ? 8 : 2})
            </span>
          </div>
          <div className="flex w-full gap-3 overflow-x-auto pb-2 scrollbar-thin">
            {capturedImages.map((img) => (
              <div key={img.id} className="relative aspect-[3/4] h-[120px] shrink-0 overflow-hidden rounded-xl border border-border shadow-1">
                <img src={img.url} alt="Captured" className="h-full w-full object-cover" />
                <button
                  type="button"
                  onClick={() => handleRemoveImage(img.id)}
                  className="absolute right-1 top-1 flex size-6 items-center justify-center rounded-full bg-ink/70 text-white transition hover:bg-destructive"
                >
                  <X className="size-4" aria-hidden />
                </button>
                {img.quality && !img.quality.ok && (
                  <div className="absolute bottom-1 left-1 flex size-6 items-center justify-center rounded-full bg-amber text-white shadow-1" title={img.quality.reasons.join(', ')}>
                    <AlertTriangle className="size-3.5" aria-hidden />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Controls */}
      <Reveal delay={0.08}>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {state === 'live' && (
            <>
              <Button type="button" size="lg" onClick={handleCapture} disabled={capturedImages.length >= (user ? 8 : 2)}>
                <Camera className="size-5" aria-hidden />
                {t('camera.capture')}
              </Button>
              {capturedImages.length > 0 && (
                <Button type="button" size="lg" onClick={handleSubmit} variant="default" className="bg-green-600 hover:bg-green-700">
                  {t('camera.useThis')} ({capturedImages.length})
                </Button>
              )}
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
