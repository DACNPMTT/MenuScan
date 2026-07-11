import { useEffect, useRef, useState, type DragEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  AlertCircle,
  AlertTriangle,
  Camera,
  Check,
  FileText,
  ImageIcon,
  Loader2,
  Upload,
  X,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useAuth } from '@/app/providers/AuthProvider'
import {
  ALLOWED_EXTENSIONS,
  MAX_FILE_SIZE_BYTES,
  type ScanData,
  type SelectedFile,
} from '@/features/menu-scan/types'
import {
  assessImageFile,
  QUALITY_REASON_I18N_KEY,
  type QualityResult,
} from '@/features/menu-scan/imageQuality'
import { cn } from '@/shared/lib/cn'

const ACCEPT_ATTR = ALLOWED_EXTENSIONS.map((ext) =>
  ext === 'pdf' ? 'application/pdf' : `image/${ext}`,
).join(',')

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function validateFile(
  file: File,
  t: (key: string) => string,
): SelectedFile['error'] {
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { code: 'FILE_TOO_LARGE', message: t('scan.errors.fileTooLarge') }
  }
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  const isPdf = file.type === 'application/pdf' || ext === 'pdf'
  const isImage =
    file.type.startsWith('image/') && ALLOWED_EXTENSIONS.includes(ext as never)
  if (!isPdf && !isImage) {
    return { code: 'UNSUPPORTED_TYPE', message: t('scan.errors.unsupportedType') }
  }
  return null
}

// The scan can translate to any language the model supports; this is just the
// curated pick-list. The backend accepts any well-formed tag, so adding a row
// here (or a future free-text entry) needs no backend/DB change.
const TARGET_LANGUAGES = [
  { code: 'vi', label: '🇻🇳 Tiếng Việt' },
  { code: 'en', label: '🇺🇸 English' },
  { code: 'zh', label: '🇨🇳 中文' },
  { code: 'ja', label: '🇯🇵 日本語' },
  { code: 'ko', label: '🇰🇷 한국어' },
  { code: 'fr', label: '🇫🇷 Français' },
  { code: 'th', label: '🇹🇭 ภาษาไทย' },
  { code: 'es', label: '🇪🇸 Español' },
  { code: 'de', label: '🇩🇪 Deutsch' },
  { code: 'it', label: '🇮🇹 Italiano' },
  { code: 'pt', label: '🇵🇹 Português' },
  { code: 'ru', label: '🇷🇺 Русский' },
  { code: 'id', label: '🇮🇩 Bahasa Indonesia' },
  { code: 'ms', label: '🇲🇾 Bahasa Melayu' },
  { code: 'hi', label: '🇮🇳 हिन्दी' },
  { code: 'ar', label: '🇸🇦 العربية' },
] as const

export function UploadPanel() {
  const { t, i18n } = useTranslation()
  useDocumentTitle(`${t('scan.title')} | MenuScan`)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, accessToken } = useAuth()

  const diningSessionQueryParam = searchParams.get('dining_session_id')

  const steps = t('scan.steps', { returnObjects: true }) as Array<{
    title: string
    desc: string
  }>

  const [selected, setSelected] = useState<SelectedFile | null>(null)
  const [quality, setQuality] = useState<QualityResult | null>(null)

  const [diningSessions, setDiningSessions] = useState<any[]>([])
  const [selectedDiningSessionId, setSelectedDiningSessionId] = useState<string>('')

  // Load dining sessions of the host
  useEffect(() => {
    if (!user) return
    const loadDiningSessions = async () => {
      try {
        const data = await apiRequest<any[]>('/api/v1/dining/sessions', {
          method: 'GET',
          token: accessToken ?? undefined,
        })
        setDiningSessions(data.filter((s: any) => s.status === 'COLLECTING'))
      } catch (err) {
        console.error('Failed to load dining sessions:', err)
      }
    }
    void loadDiningSessions()
  }, [accessToken, user])

  // Pre-select if passed in query param
  useEffect(() => {
    if (diningSessionQueryParam) {
      setSelectedDiningSessionId(diningSessionQueryParam)
    }
  }, [diningSessionQueryParam])
  // Default the scan target to the user's interface language (set at login /
  // in the language switcher); they can still override it per scan below.
  const [targetLanguage, setTargetLanguage] = useState(() => {
    const uiLanguage = i18n.resolvedLanguage ?? 'vi'
    return TARGET_LANGUAGES.some((lang) => lang.code === uiLanguage)
      ? uiLanguage
      : 'vi'
  })
  const [isDragging, setIsDragging] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  // Guards the async quality check: a slow decode from a replaced file must not
  // overwrite the current result.
  const currentFileRef = useRef<File | null>(null)

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
    const validationError = validateFile(file, t)
    setSelected({
      file,
      previewUrl: isImage ? URL.createObjectURL(file) : null,
      error: validationError,
    })
    setSubmitError(null)
    // Advisory sharpness/brightness check for valid images (PDF skipped). It
    // never blocks upload — it only surfaces a "retake / choose another" hint.
    currentFileRef.current = file
    setQuality(null)
    if (isImage && !validationError) {
      void assessImageFile(file).then((result) => {
        if (currentFileRef.current === file) setQuality(result)
      })
    }
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
    setQuality(null)
    currentFileRef.current = null
    setSubmitError(null)
  }

  const handleSubmit = async () => {
    if (!selected || selected.error) return
    setIsSubmitting(true)
    setSubmitError(null)
    const formData = new FormData()
    formData.append('file', selected.file)
    formData.append('target_language', targetLanguage)
    if (selectedDiningSessionId) {
      formData.append('dining_session_id', selectedDiningSessionId)
    }
    try {
      const scan = await apiRequest<ScanData>('/api/v1/scans', {
        method: 'POST',
        body: formData,
      })
      // Hand off to the result page, which polls the scan status and renders
      // the extracted menu once the pipeline completes.
      navigate(`/app/scans/${scan.id}`)
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : `${t('scan.errors.genericPrefix')}${error instanceof Error ? error.message : String(error)}`
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
                {t('scan.uploadCard.title')}
              </span>
              <span className="text-[13px] text-ink-variant">
                {t('scan.uploadCard.desc')}
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
                {t('scan.cameraCard.title')}
              </span>
              <span className="text-[13px] text-ink-variant">
                {t('scan.cameraCard.desc')}
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
          aria-label={t('scan.dropzone.aria')}
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
              {t('scan.dropzone.title')}
            </p>
            <p className="text-[14px] leading-[20px] text-ink-variant">
              {t('scan.dropzone.hint')}
            </p>
          </div>
        </div>

        {/* Selected file + preview */}
        {selected && (
          <div className="flex flex-col gap-2">
            <p className="text-[14px] font-medium uppercase tracking-[0.7px] text-ink-variant">
              {t('scan.selectedFile')}
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
                aria-label={t('scan.removeAria', { name: selected.file.name })}
              >
                <X className="size-5" aria-hidden />
                <span className="hidden sm:inline">{t('common.delete')}</span>
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
            {!selected.error && quality && !quality.ok && (
              <div
                role="status"
                className="flex items-start gap-3 rounded-[8px] border border-[#e0a800]/50 bg-[#fff8e1] px-3 py-2.5 text-[14px] text-[#8a6d00]"
              >
                <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
                <div className="flex flex-col gap-0.5">
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
            {t('scan.statusTitle')}
          </h2>
          <ol className="relative mt-4 flex flex-col">
            {steps.map((step, index) => {
              const stepNum = index + 1
              const state =
                stepNum <= completedSteps
                  ? 'complete'
                  : stepNum === completedSteps + 1
                    ? 'current'
                    : 'pending'
              const isLast = index === steps.length - 1
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
                      {state === 'current' ? t('scan.readyToStart') : step.desc}
                    </span>
                  </div>
                </li>
              )
            })}
          </ol>
        </div>

        {/* Ngôn ngữ đích */}
        <div className="flex flex-col gap-2 rounded-[12px] border border-hairline bg-canvas p-[21px]">
          <label
            htmlFor="targetLanguage"
            className="text-[15px] font-bold text-primary-dark"
          >
            {t('scan.translateTo')}
          </label>
          <select
            id="targetLanguage"
            value={targetLanguage}
            onChange={(e) => setTargetLanguage(e.target.value)}
            disabled={isSubmitting}
            className="h-[44px] w-full rounded-[8px] border border-hairline bg-surface-muted px-3 text-[15px] text-ink outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50"
          >
            {TARGET_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>

        {user && (diningSessions.length > 0 || diningSessionQueryParam) && (
          <div className="flex flex-col gap-2 rounded-[12px] border border-hairline bg-canvas p-[21px]">
            <label
              htmlFor="diningSessionSelect"
              className="text-[15px] font-bold text-primary-dark"
            >
              Liên kết phiên ăn uống (Tùy chọn)
            </label>
            <select
              id="diningSessionSelect"
              value={selectedDiningSessionId}
              onChange={(e) => setSelectedDiningSessionId(e.target.value)}
              disabled={isSubmitting}
              className="h-[44px] w-full rounded-[8px] border border-hairline bg-surface-muted px-3 text-[15px] text-ink outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50"
            >
              <option value="">-- Không liên kết --</option>
              {diningSessionQueryParam && !diningSessions.some(s => s.id === diningSessionQueryParam) && (
                <option value={diningSessionQueryParam}>
                  Phiên ăn {diningSessionQueryParam.slice(0, 8)} (Đang liên kết)
                </option>
              )}
              {diningSessions.map((session: any) => (
                <option key={session.id} value={session.id}>
                  Phiên ăn {session.id.slice(0, 8)} ({session.target_language.toUpperCase()})
                </option>
              ))}
            </select>
          </div>
        )}

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
              {t('scan.uploading')}
            </>
          ) : (
            <>
              <Upload className="size-5" aria-hidden />
              {t('scan.start')}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
