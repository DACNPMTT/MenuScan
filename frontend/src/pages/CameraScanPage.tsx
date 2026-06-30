import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertCircle, ArrowLeft, Camera, Loader2, RefreshCw } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import type { ScanData } from '@/features/menu-scan/types'

type CameraState = 'starting' | 'live' | 'captured' | 'submitting' | 'error'

export function CameraScanPage() {
  useDocumentTitle('Quét bằng camera | MenuScan')
  const navigate = useNavigate()
  const { accessToken } = useAuth()

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [state, setState] = useState<CameraState>('starting')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [capturedUrl, setCapturedUrl] = useState<string | null>(null)
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
          ? 'Truy cập camera bị từ chối. Hãy cấp quyền camera trong trình duyệt.'
          : name === 'NotFoundError'
            ? 'Không tìm thấy camera trên thiết bị.'
            : 'Không mở được camera. Vui lòng thử lại.',
      )
      setState('error')
    }
  }, [stopStream])

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
    capturedBlob.current = null
    void startCamera()
  }

  const handleSubmit = async () => {
    const blob = capturedBlob.current
    if (!blob || !accessToken) return
    setState('submitting')
    const file = new File([blob], `camera-scan-${Date.now()}.jpg`, {
      type: 'image/jpeg',
    })
    const formData = new FormData()
    formData.append('file', file)
    try {
      const scan = await apiRequest<ScanData>('/api/v1/scans', {
        method: 'POST',
        token: accessToken,
        body: formData,
      })
      navigate(`/app/scans/${scan.id}`)
    } catch (error) {
      setState('captured')
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : 'Không thể tải ảnh lên. Vui lòng thử lại.',
      )
    }
  }

  return (
    <div className="mx-auto w-full max-w-[800px] px-[30px] py-[40px] sm:px-[50px]">
      <Link
        to="/app/scan"
        className="mb-6 flex w-fit items-center gap-2 text-[14px] text-ink-variant transition-colors hover:text-primary-dark"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Về trang upload
      </Link>

      <h1 className="mb-6 text-[32px] font-bold leading-[38px] text-primary-dark">
        Quét bằng camera
      </h1>

      {errorMessage && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-3 rounded-[12px] border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Viewfinder */}
      <div className="relative aspect-[3/4] w-full overflow-hidden rounded-[12px] border border-hairline bg-ink sm:aspect-video">
        {capturedUrl ? (
          <img
            src={capturedUrl}
            alt="Ảnh đã chụp"
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

        {/* Overlay framing corners (matches Figma camera viewfinder intent). */}
        {state === 'live' && (
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute left-4 top-4 size-12 rounded-tl-[2px] border-l-[3px] border-t-[3px] border-[#2e6b00]" />
            <div className="absolute right-4 top-4 size-12 rounded-tr-[2px] border-r-[3px] border-t-[3px] border-[#2e6b00]" />
            <div className="absolute bottom-4 left-4 size-12 rounded-bl-[2px] border-b-[3px] border-l-[3px] border-[#2e6b00]" />
            <div className="absolute bottom-4 right-4 size-12 rounded-br-[2px] border-b-[3px] border-r-[3px] border-[#2e6b00]" />
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
              Camera không khả dụng.
            </p>
            <button
              type="button"
              onClick={() => void startCamera()}
              className="rounded-[8px] bg-white px-4 py-2 text-[14px] font-bold text-primary-dark"
            >
              Thử lại
            </button>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        {state === 'live' && (
          <button
            type="button"
            onClick={handleCapture}
            className="flex items-center gap-2 rounded-full border-4 border-hairline bg-canvas px-6 py-3 text-[15px] font-bold text-primary-dark transition-colors hover:bg-surface-muted"
          >
            <Camera className="size-5" aria-hidden />
            Chụp ảnh
          </button>
        )}
        {state === 'captured' && (
          <>
            <button
              type="button"
              onClick={handleRetake}
              className="flex items-center gap-2 rounded-[8px] border border-hairline bg-canvas px-5 py-3 text-[15px] font-bold text-ink-variant transition-colors hover:bg-surface-muted"
            >
              <RefreshCw className="size-5" aria-hidden />
              Chụp lại
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              className="rounded-[8px] bg-primary-dark px-6 py-3 text-[15px] font-bold text-white transition-opacity hover:opacity-90"
            >
              Dùng ảnh này
            </button>
          </>
        )}
      </div>

      <p className="mt-4 text-center text-[13px] text-ink-variant">
        Đặt menu trong khung, đảm bảo đủ sáng và không bị mờ.
      </p>
    </div>
  )
}
