import { useEffect, useRef, useState } from 'react'
import { Alert } from '@/shared/components/Alert'
import { Button } from '@/shared/components/Button'
import { Spinner } from '@/shared/components/Spinner'
import { useCamera } from '@/features/menu-scan/hooks/useCamera'

export interface CameraCaptureProps {
  onCapture: (file: File) => void
  onFallback: () => void
}

export function CameraCapture({ onCapture, onFallback }: CameraCaptureProps) {
  const { videoRef, status, canFlip, startCamera, stopCamera, flipCamera, capture } =
    useCamera()

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    void startCamera('environment')
    return () => { stopCamera() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!preview) { setPreviewUrl(null); return }
    const url = URL.createObjectURL(preview)
    setPreviewUrl(url)
    return () => { URL.revokeObjectURL(url) }
  }, [preview])

  function handleCapture() {
    const file = capture()
    if (file) { setPreview(file); stopCamera() }
  }

  function handleRetake() {
    setPreview(null)
    void startCamera()
  }

  function handleUsePhoto() {
    if (preview) onCapture(preview)
  }

  function handleGalleryChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    stopCamera()
    onCapture(file)
  }

  // ── Permission denied ──────────────────────────────────────────────────────
  if (status === 'permission-denied') {
    return (
      <div className="scan-menu scan-menu--message">
        <Alert title="Không có quyền truy cập camera" variant="warning">
          <p>Vui lòng cho phép truy cập camera trong cài đặt trình duyệt rồi thử lại, hoặc chọn ảnh từ thư viện.</p>
        </Alert>
        <div className="scan-menu__message-actions">
          <Button type="button" onClick={() => void startCamera()}>Thử lại</Button>
          <Button type="button" variant="secondary" onClick={onFallback}>Tải file thay thế</Button>
        </div>
      </div>
    )
  }

  // ── Unavailable / error ────────────────────────────────────────────────────
  if (status === 'unavailable' || status === 'error') {
    return (
      <div className="scan-menu scan-menu--message">
        <Alert title="Không tìm thấy camera" variant="warning">
          <p>Thiết bị không có camera hoặc camera không thể truy cập. Hãy tải ảnh menu lên thay thế.</p>
        </Alert>
        <div className="scan-menu__message-actions">
          <Button type="button" onClick={onFallback}>Tải file thay thế</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="scan-menu">

      {/* Header */}
      <div className="scan-menu__header">
        <button type="button" className="scan-menu__back" onClick={onFallback}>
          <span className="scan-menu__back-icon" aria-hidden="true">‹</span>
          Back
        </button>
        <span className="scan-menu__title">Scan Menu</span>
      </div>

      {/* Viewfinder */}
      <div className="scan-menu__viewfinder">
        {status === 'requesting' && (
          <div className="scan-menu__loading" aria-live="polite">
            <Spinner label="Đang khởi động camera…" />
            <p>Đang khởi động camera…</p>
          </div>
        )}

        {!preview && status !== 'active' && (
          <div className="scan-menu__hint">
            <span className="scan-menu__hint-icon" aria-hidden="true">⊞</span>
            <span>Align menu here</span>
          </div>
        )}

        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video
          ref={videoRef}
          className={
            status === 'active' && !preview
              ? 'scan-menu__video scan-menu__video--visible'
              : 'scan-menu__video'
          }
          playsInline
          autoPlay
          muted
          aria-label="Camera viewfinder"
        />

        {preview && previewUrl && (
          <img
            src={previewUrl}
            alt="Ảnh menu vừa chụp"
            className="scan-menu__preview-img"
          />
        )}

        <CornerBrackets />
      </div>

      {/* Tips bar */}
      <div className="scan-menu__tips" aria-label="Camera tips">
        <span className="scan-menu__tip">
          <TipIcon d="M8 3H3v5M21 3h-5v5M3 16v5h5M16 21h5v-5" /> Keep inside frame
        </span>
        <span className="scan-menu__tip">
          <TipIcon d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" /> Good lighting
        </span>
        <span className="scan-menu__tip">
          <TipIcon d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0M3 12h1M20 12h1M12 3v1M12 20v1" /> Avoid blur
        </span>
      </div>

      {/* Controls: Gallery · Capture · Switch */}
      <div className="scan-menu__controls">
        <button
          type="button"
          className="scan-menu__ctrl-icon"
          onClick={() => fileInputRef.current?.click()}
          aria-label="Chọn ảnh từ gallery"
        >
          <GalleryIcon />
          <span>Gallery</span>
        </button>

        <button
          type="button"
          className="scan-menu__capture-btn"
          onClick={handleCapture}
          disabled={status !== 'active' || !!preview}
          aria-label="Chụp ảnh"
        >
          <span className="scan-menu__capture-inner" aria-hidden="true" />
        </button>

        <button
          type="button"
          className={
            canFlip
              ? 'scan-menu__ctrl-icon'
              : 'scan-menu__ctrl-icon scan-menu__ctrl-icon--dim'
          }
          onClick={flipCamera}
          disabled={!canFlip}
          aria-label="Đổi camera"
        >
          <SwitchIcon />
          <span>Switch</span>
        </button>
      </div>

      {/* Hidden gallery input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="visually-hidden"
        aria-label="Chọn ảnh từ thư viện"
        onChange={handleGalleryChange}
      />

      {/* Divider + POST-CAPTURE STATE label */}
      <div className="scan-menu__divider" aria-hidden="true" />
      <p className="scan-menu__post-label">Post-capture state</p>

      {/* Bottom bar: Retake · Use This Photo */}
      <div className="scan-menu__bottom">
        <button
          type="button"
          className="scan-menu__btn scan-menu__btn--outline"
          onClick={handleRetake}
        >
          <RetakeIcon /> Retake
        </button>
        <button
          type="button"
          className="scan-menu__btn scan-menu__btn--filled"
          onClick={handleUsePhoto}
          disabled={!preview}
        >
          <CheckIcon /> Use This Photo
        </button>
      </div>
    </div>
  )
}

// ── SVG helpers ───────────────────────────────────────────────────────────────

function CornerBrackets() {
  return (
    <svg className="scan-menu__corners" viewBox="0 0 100 100"
      preserveAspectRatio="none" aria-hidden="true">
      <polyline points="15,6 6,6 6,15"    fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      <polyline points="85,6 94,6 94,15"  fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      <polyline points="6,85 6,94 15,94"  fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      <polyline points="94,85 94,94 85,94" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

function TipIcon({ d }: { d: string }) {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  )
}

function GalleryIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <polyline points="21 15 16 10 5 21" />
    </svg>
  )
}

function SwitchIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 7h-9m3-3-3 3 3 3M4 17h9m-3 3 3-3-3-3" />
    </svg>
  )
}

function RetakeIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  )
}