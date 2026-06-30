import { useEffect, useRef, useState, type DragEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  Camera,
  Check,
  FileText,
  ImageIcon,
  Loader2,
  Upload,
  X,
} from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import {
  ALLOWED_EXTENSIONS,
  MAX_FILE_SIZE_BYTES,
  type ScanData,
  type SelectedFile,
} from '@/features/menu-scan/types'
import { cn } from '@/shared/lib/cn'

const ACCEPT_ATTR = ALLOWED_EXTENSIONS.map((ext) =>
  ext === 'pdf' ? 'application/pdf' : `image/${ext}`,
).join(',')

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function validateFile(file: File): SelectedFile['error'] {
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      code: 'FILE_TOO_LARGE',
      message: 'File quá lớn. Dung lượng tối đa là 10 MB.',
    }
  }
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  const isPdf = file.type === 'application/pdf' || ext === 'pdf'
  const isImage =
    file.type.startsWith('image/') && ALLOWED_EXTENSIONS.includes(ext as never)
  if (!isPdf && !isImage) {
    return {
      code: 'UNSUPPORTED_TYPE',
      message: 'Định dạng không được hỗ trợ. Chỉ chấp nhận JPG, PNG, WEBP, PDF.',
    }
  }
  return null
}

const STEPS = [
  { title: 'Tải lên', desc: 'File đã được đính kèm.' },
  { title: 'Phân tích AI', desc: 'Nhận dạng & phân tích menu.' },
  { title: 'Trích xuất', desc: 'Lấy món và giá.' },
  { title: 'Kết quả', desc: 'Hiển thị danh sách món.' },
] as const

export function UploadPanel() {
  useDocumentTitle('Thêm menu | MenuScan')
  const navigate = useNavigate()
  const { accessToken } = useAuth()

  const [selected, setSelected] = useState<SelectedFile | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Revoke object URLs so we don't leak them on every replace/remove.
  useEffect(() => {
    return () => {
      if (selected?.previewUrl) URL.revokeObjectURL(selected.previewUrl)
    }
  }, [selected?.previewUrl])

  const acceptFile = (file: File | undefined | null) => {
    if (!file) return
    if (selected?.previewUrl) URL.revokeObjectURL(selected.previewUrl)
    const isImage = file.type.startsWith('image/')
    setSelected({
      file,
      previewUrl: isImage ? URL.createObjectURL(file) : null,
      error: validateFile(file),
    })
    setSubmitError(null)
  }

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    acceptFile(event.target.files?.[0])
    event.target.value = ''
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    acceptFile(event.dataTransfer.files?.[0])
  }

  const handleRemove = () => {
    if (selected?.previewUrl) URL.revokeObjectURL(selected.previewUrl)
    setSelected(null)
    setSubmitError(null)
  }

  const handleSubmit = async () => {
    if (!selected || selected.error || !accessToken) return
    setIsSubmitting(true)
    setSubmitError(null)
    const formData = new FormData()
    formData.append('file', selected.file)
    try {
      const scan = await apiRequest<ScanData>('/api/v1/scans', {
        method: 'POST',
        token: accessToken,
        body: formData,
      })
      // Hand off to the result page, which polls the scan status and renders
      // the extracted menu once the pipeline completes.
      navigate(`/app/scans/${scan.id}`)
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Không thể tải file lên. Vui lòng thử lại.'
      setSubmitError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const canSubmit = Boolean(selected && !selected.error && !isSubmitting)
  const isPdf = selected?.file.type === 'application/pdf'
  const fileReady = Boolean(selected && !selected.error)
  // Stepper: no file = step 1 current (awaiting upload); valid file attached
  // = step 1 complete (uploaded), step 2 current (next).
  const completedSteps = fileReady ? 1 : 0

  return (
    <div className="grid grid-cols-1 gap-[40px] lg:grid-cols-[minmax(0,1fr)_360px]">
      {/* LEFT COLUMN: input choice + dropzone + file list */}
      <div className="flex flex-col gap-[30px]">
        {/* Input choice cards */}
        <div className="grid grid-cols-1 gap-[20px] sm:grid-cols-2">
          {/* Upload (active) */}
          <div className="relative flex min-h-[92px] items-center gap-5 rounded-[12px] border-2 border-primary-dark bg-surface-muted p-[22px]">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary">
              <Upload className="size-6 text-white" aria-hidden />
            </span>
            <div className="flex flex-col gap-0.5">
              <span className="text-[18px] leading-[26px] text-primary-dark">
                Tải ảnh / PDF lên
              </span>
              <span className="text-[13px] text-ink-variant">
                Kéo thả hoặc chọn file
              </span>
            </div>
            <span className="absolute right-2 top-2 flex size-5 items-center justify-center rounded-full bg-primary-dark">
              <Check className="size-3 text-white" aria-hidden />
            </span>
          </div>
          {/* Camera (link) */}
          <Link
            to="/app/scan/camera"
            className="flex min-h-[92px] items-center gap-5 rounded-[12px] border border-hairline bg-canvas p-[21px] transition-colors hover:bg-surface-muted"
          >
            <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-surface-muted">
              <Camera className="size-6 text-primary-dark" aria-hidden />
            </span>
            <div className="flex flex-col gap-0.5">
              <span className="text-[18px] leading-[26px] text-primary-dark">
                Quét bằng camera
              </span>
              <span className="text-[13px] text-ink-variant">
                Chụp menu vật lý
              </span>
            </div>
          </Link>
        </div>

        {/* Dropzone */}
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              inputRef.current?.click()
            }
          }}
          aria-label="Kéo thả file vào đây hoặc nhấn để chọn file"
          className={cn(
            'flex h-[256px] cursor-pointer flex-col items-center justify-center gap-5 rounded-[12px] border border-dashed p-px text-center transition-colors',
            isDragging
              ? 'border-primary-dark bg-secondary'
              : 'border-hairline bg-secondary hover:bg-surface-muted',
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT_ATTR}
            onChange={handleInputChange}
            className="hidden"
          />
          <div className="flex size-16 items-center justify-center rounded-full border border-hairline bg-canvas shadow-sm">
            <Upload className="size-7 text-primary-dark" aria-hidden />
          </div>
          <div className="flex flex-col items-center gap-1.5">
            <p className="text-[20px] leading-[30px] text-primary-dark">
              Kéo thả hoặc nhấn để chọn file
            </p>
            <p className="text-[14px] leading-[20px] text-ink-variant">
              Hỗ trợ JPG, JPEG, PNG, WEBP, PDF — tối đa 10 MB
            </p>
          </div>
        </div>

        {/* Selected file + preview */}
        {selected && (
          <div className="flex flex-col gap-2">
            <p className="text-[14px] font-medium uppercase tracking-[0.7px] text-ink-variant">
              File đã chọn
            </p>
            <div className="flex items-center gap-5 rounded-[8px] border border-hairline bg-canvas p-[9px]">
              {isPdf ? (
                <div className="flex size-10 shrink-0 items-center justify-center rounded-[4px] bg-surface-muted">
                  <FileText className="size-5 text-primary-dark" aria-hidden />
                </div>
              ) : (
                <div className="size-10 shrink-0 overflow-hidden rounded-[4px] bg-surface-muted">
                  {selected.previewUrl ? (
                    <img
                      src={selected.previewUrl}
                      alt={selected.file.name}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <ImageIcon className="m-auto size-5 text-ink-variant" aria-hidden />
                  )}
                </div>
              )}
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-[16px] leading-[22px] text-ink">
                  {selected.file.name}
                </span>
                <span className="text-[14px] leading-[20px] text-ink-variant">
                  {formatBytes(selected.file.size)}
                  {isPdf ? ' · PDF' : ''}
                </span>
              </div>
              <button
                type="button"
                onClick={handleRemove}
                className="flex items-center gap-1.5 rounded-[4px] p-2 text-[14px] text-ink-variant transition-colors hover:bg-secondary hover:text-primary-dark"
                aria-label={`Xóa file ${selected.file.name}`}
              >
                <X className="size-5" aria-hidden />
                <span className="hidden sm:inline">Xóa</span>
              </button>
            </div>
            {selected.error && (
              <p
                role="alert"
                className="flex items-center gap-2 text-[14px] text-destructive"
              >
                <AlertCircle className="size-4 shrink-0" aria-hidden />
                {selected.error.message}
              </p>
            )}
          </div>
        )}

        {submitError && (
          <p
            role="alert"
            className="flex items-center gap-2 rounded-[8px] border border-destructive/30 bg-destructive/5 px-3 py-2 text-[14px] text-destructive"
          >
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            {submitError}
          </p>
        )}
      </div>

      {/* RIGHT COLUMN: processing status stepper + CTA */}
      <div className="flex flex-col gap-[30px]">
        <div className="rounded-[12px] border border-hairline bg-canvas p-[21px]">
          <h2 className="border-b border-hairline pb-[9px] text-[18px] leading-[26px] text-primary-dark">
            Trạng thái xử lý
          </h2>
          <ol className="relative mt-4 flex flex-col">
            {STEPS.map((step, index) => {
              const stepNum = index + 1
              const state =
                stepNum <= completedSteps
                  ? 'complete'
                  : stepNum === completedSteps + 1
                    ? 'current'
                    : 'pending'
              const isLast = index === STEPS.length - 1
              return (
                <li key={step.title} className="flex gap-5">
                  {/* Indicator + connector */}
                  <div className="relative flex flex-col items-center">
                    {state === 'complete' && (
                      <span className="flex size-6 items-center justify-center rounded-full bg-primary-dark">
                        <Check className="size-3.5 text-white" aria-hidden />
                      </span>
                    )}
                    {state === 'current' && (
                      <span className="flex size-6 items-center justify-center rounded-full border-2 border-primary-dark bg-canvas">
                        <span className="size-2 rounded-full bg-primary-dark" />
                      </span>
                    )}
                    {state === 'pending' && (
                      <span className="size-6 rounded-full border border-hairline bg-canvas" />
                    )}
                    {!isLast && (
                      <span
                        className={cn(
                          'mt-1 w-[2px] flex-1',
                          state === 'complete' ? 'bg-primary-dark' : 'bg-hairline',
                        )}
                      />
                    )}
                  </div>
                  {/* Label */}
                  <div className={cn('flex flex-col gap-0.5 pb-7', isLast && 'pb-0')}>
                    <span
                      className={cn(
                        'text-[15px] leading-[22px]',
                        state === 'pending'
                          ? 'font-medium text-ink-variant'
                          : 'font-bold text-primary-dark',
                      )}
                    >
                      {stepNum}. {step.title}
                    </span>
                    <span
                      className={cn(
                        'text-[13px] leading-[18px]',
                        state === 'current'
                          ? 'italic text-ink-variant'
                          : 'text-ink-variant',
                      )}
                    >
                      {state === 'current' ? 'Sẵn sàng để bắt đầu...' : step.desc}
                    </span>
                  </div>
                </li>
              )
            })}
          </ol>
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className={cn(
            'flex h-[56px] w-full items-center justify-center gap-2 rounded-[12px] text-[17px] font-bold transition-colors',
            canSubmit
              ? 'bg-primary-dark text-white hover:opacity-90'
              : 'cursor-not-allowed bg-surface-muted text-ink-variant',
          )}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="size-5 animate-spin" aria-hidden />
              Đang tải lên...
            </>
          ) : (
            <>
              <Upload className="size-5" aria-hidden />
              Bắt đầu quét
            </>
          )}
        </button>
      </div>
    </div>
  )
}