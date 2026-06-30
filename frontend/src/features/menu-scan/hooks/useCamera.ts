import { useCallback, useEffect, useRef, useState } from 'react'

export type FacingMode = 'environment' | 'user'

export type CameraStatus =
  | 'idle'
  | 'requesting'
  | 'active'
  | 'permission-denied'
  | 'unavailable'
  | 'error'

export interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>
  status: CameraStatus
  facingMode: FacingMode
  canFlip: boolean
  startCamera: (facing?: FacingMode) => Promise<void>
  stopCamera: () => void
  flipCamera: () => void
  capture: () => File | null
}

/**
 * Manages the MediaStream lifecycle and exposes a `capture()` method
 * that draws the current video frame onto a canvas and returns a File.
 *
 * The hook cleans up the stream on unmount automatically.
 */
export function useCamera(): UseCameraReturn {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  const [status, setStatus] = useState<CameraStatus>('idle')
  const [facingMode, setFacingMode] = useState<FacingMode>('environment')
  const [canFlip, setCanFlip] = useState(false)

  // Lazy-create an off-screen canvas once
  const getCanvas = useCallback(() => {
    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas')
    }
    return canvasRef.current
  }, [])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      for (const track of streamRef.current.getTracks()) {
        track.stop()
      }
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setStatus('idle')
  }, [])

  const startCamera = useCallback(
    async (facing: FacingMode = 'environment') => {
      // Tear down any existing stream first
      if (streamRef.current) {
        for (const track of streamRef.current.getTracks()) {
          track.stop()
        }
        streamRef.current = null
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        setStatus('unavailable')
        return
      }

      setStatus('requesting')

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: facing } },
          audio: false,
        })

        streamRef.current = stream

        if (videoRef.current) {
          videoRef.current.srcObject = stream
          // Play may be blocked until user gesture; we ignore the promise
          // here since playback starts automatically after srcObject is set.
          videoRef.current.play().catch(() => undefined)
        }

        setFacingMode(facing)
        setStatus('active')

        // Detect whether the device has more than one video input
        // so we know whether the flip button is useful.
        navigator.mediaDevices
          .enumerateDevices()
          .then((devices) => {
            const videoInputs = devices.filter((d) => d.kind === 'videoinput')
            setCanFlip(videoInputs.length > 1)
          })
          .catch(() => {
            setCanFlip(false)
          })
      } catch (err) {
        if (
          err instanceof DOMException &&
          (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')
        ) {
          setStatus('permission-denied')
        } else if (
          err instanceof DOMException &&
          (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError')
        ) {
          setStatus('unavailable')
        } else {
          setStatus('error')
        }
      }
    },
    [],
  )

  const flipCamera = useCallback(() => {
    const next: FacingMode = facingMode === 'environment' ? 'user' : 'environment'
    void startCamera(next)
  }, [facingMode, startCamera])

  /**
   * Captures the current video frame and returns it as a PNG File,
   * or null if the video element isn't ready.
   */
  const capture = useCallback((): File | null => {
    const video = videoRef.current
    if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      return null
    }

    const canvas = getCanvas()
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    // canvas.toBlob is async; we use toDataURL for synchronous access
    // and convert to a Blob manually so we can hand back a File.
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
    const base64 = dataUrl.split(',')[1]
    if (!base64) return null

    const bytes = atob(base64)
    const arr = new Uint8Array(bytes.length)
    for (let i = 0; i < bytes.length; i++) {
      arr[i] = bytes.charCodeAt(i)
    }

    const blob = new Blob([arr], { type: 'image/jpeg' })
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    return new File([blob], `menu-capture-${timestamp}.jpg`, {
      type: 'image/jpeg',
    })
  }, [getCanvas])

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        for (const track of streamRef.current.getTracks()) {
          track.stop()
        }
      }
    }
  }, [])

  return {
    videoRef,
    status,
    facingMode,
    canFlip,
    startCamera,
    stopCamera,
    flipCamera,
    capture,
  }
}