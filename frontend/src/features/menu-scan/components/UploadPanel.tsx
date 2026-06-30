import { useRef, useState } from 'react'
import type { MenuScanStatus } from '@/features/menu-scan/types'
import { CameraCapture } from '@/features/menu-scan/components/CameraCapture'
import { Alert } from '@/shared/components/Alert'
import { Button } from '@/shared/components/Button'
import { Card } from '@/shared/components/Card'
import { Spinner } from '@/shared/components/Spinner'
import { apiRequest } from '@/shared/lib/api'

// ── Constants ────────────────────────────────────────────────────────────────

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
const MAX_SIZE_BYTES = 10 * 1024 * 1024 // 10 MB (matches backend)
const ALLOWED_LABEL = 'JPG, PNG, WEBP, PDF'

type InputMode = 'upload' | 'camera'

// ── Upload logic ─────────────────────────────────────────────────────────────

interface ScanCreatedData {
  id: string
  status: string
}

async function uploadFile(file: File): Promise<ScanCreatedData> {
  const body = new FormData()
  body.append('file', file)

  return apiRequest<ScanCreatedData>('/api/v1/scans', {
    method: 'POST',
    body,
  })
}

// ── Validation ───────────────────────────────────────────────────────────────

function validateFile(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return `Unsupported file type. Please use ${ALLOWED_LABEL}.`
  }
  if (file.size > MAX_SIZE_BYTES) {
    return 'File exceeds the 10 MB limit. Please choose a smaller file.'
  }
  return null
}

// ── Component ────────────────────────────────────────────────────────────────

export function UploadPanel() {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [mode, setMode] = useState<InputMode>('upload')
  const [scanStatus, setScanStatus] = useState<MenuScanStatus>('ready')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [scanId, setScanId] = useState<string | null>(null)

  // ── Shared submission path ─────────────────────────────────────────────────

  async function submitFile(file: File) {
    const error = validateFile(file)
    if (error) {
      setValidationError(error)
      return
    }

    setValidationError(null)
    setUploadError(null)
    setScanStatus('uploading')

    try {
      const data = await uploadFile(file)
      setScanId(data.id)
      setScanStatus('processing')
      // TODO: poll GET /api/v1/scans/:id until COMPLETED/FAILED (S1-16)
    } catch {
      setUploadError('Upload failed. Please check your connection and try again.')
      setScanStatus('ready')
    }
  }

  // ── File input handler ─────────────────────────────────────────────────────

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    void submitFile(file)
    // Reset the input so the same file can be re-selected after an error
    event.target.value = ''
  }

  // ── Camera handlers ───────────────────────────────────────────────────────

  function handleCameraCapture(file: File) {
    setMode('upload') // switch UI back to upload view before submitting
    void submitFile(file)
  }

  function handleCameraFallback() {
    setMode('upload')
  }

  // ── Success state ─────────────────────────────────────────────────────────

  if (scanStatus === 'processing' || scanStatus === 'complete') {
    return (
      <Card className="upload-panel" aria-labelledby="upload-title">
        <div>
          <p className="eyebrow">Scan workflow</p>
          <h2 id="upload-title">Scan submitted</h2>
        </div>

        {scanStatus === 'processing' ? (
          <div className="upload-panel__processing">
            <Spinner label="Processing menu…" />
            <p>Processing your menu… This usually takes a few seconds.</p>
          </div>
        ) : (
          <Alert title="Scan complete" variant="success">
            Your menu has been processed successfully.{' '}
            {scanId && <span>Scan ID: {scanId}</span>}
          </Alert>
        )}

        <div className="upload-panel__footer">
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setScanStatus('ready')
              setScanId(null)
            }}
          >
            Scan another menu
          </Button>
        </div>
      </Card>
    )
  }

  // ── Camera mode ───────────────────────────────────────────────────────────
  // Rendered standalone (no Card wrapper) — CameraCapture owns its own
  // full-screen layout with header, matching the Figma "Scan Menu" frame.

  if (mode === 'camera') {
    return (
      <>
        {validationError && (
          <div className="upload-panel__camera-error">
            <Alert title="Invalid image" variant="error">
              {validationError}
            </Alert>
          </div>
        )}

        <CameraCapture
          onCapture={handleCameraCapture}
          onFallback={handleCameraFallback}
        />
      </>
    )
  }

  // ── File-upload mode (default) ────────────────────────────────────────────

  const isSubmitting = scanStatus === 'uploading'

  return (
    <Card className="upload-panel" aria-labelledby="upload-title">
      <div>
        <p className="eyebrow">Scan workflow</p>
        <h2 id="upload-title">Upload a menu</h2>
        <p>
          Drop in a menu image or PDF, or use your camera to capture one
          directly.
        </p>
      </div>

      {validationError && (
        <Alert title="Invalid file" variant="error">
          {validationError}
        </Alert>
      )}

      {uploadError && (
        <Alert title="Upload error" variant="error">
          {uploadError}
        </Alert>
      )}

      {isSubmitting ? (
        <div className="upload-panel__dropzone upload-panel__dropzone--loading">
          <Spinner label="Uploading…" />
          <p>Uploading…</p>
        </div>
      ) : (
        <div
          className="upload-panel__dropzone"
          role="button"
          tabIndex={0}
          aria-label="Choose a file to upload"
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              fileInputRef.current?.click()
            }
          }}
        >
          <span className="upload-panel__icon" aria-hidden="true">
            +
          </span>
          <div>
            <strong>Choose file</strong>
            <span>{ALLOWED_LABEL} up to 10 MB</span>
          </div>
        </div>
      )}

      {/* Hidden file input — the visible dropzone triggers it */}
      <input
        ref={fileInputRef}
        type="file"
        accept={ALLOWED_TYPES.join(',')}
        aria-label="Menu file"
        className="visually-hidden"
        onChange={handleFileChange}
        disabled={isSubmitting}
      />

      <div className="upload-panel__footer">
        <span>Status: {scanStatus}</span>
        <div className="upload-panel__footer-actions">
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setValidationError(null)
              setUploadError(null)
              setMode('camera')
            }}
            disabled={isSubmitting}
            aria-label="Use camera to capture menu"
          >
            📷 Use camera
          </Button>

          <Button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isSubmitting}
          >
            Start scan
          </Button>
        </div>
      </div>
    </Card>
  )
}