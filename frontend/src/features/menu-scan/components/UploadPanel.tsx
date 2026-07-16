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
import { Reveal } from '@/shared/components/motion/Reveal'
import { SectionCard } from '@/shared/components/SectionCard'
import { IconBadge } from '@/shared/components/IconBadge'
import { Button } from '@/shared/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select'

interface SimpleDiningSession {
  id: string
  name: string | null
  status: string
}

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


interface LocalSelectedFile extends SelectedFile {
  id: string
  quality?: QualityResult | null
}

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

  const [selectedFiles, setSelectedFiles] = useState<LocalSelectedFile[]>([])
  
  const [diningSessions, setDiningSessions] = useState<SimpleDiningSession[]>([])
  const [selectedDiningSessionId, setSelectedDiningSessionId] = useState<string>('')

  // Load dining sessions of the host
  useEffect(() => {
    if (!user) return
    const loadDiningSessions = async () => {
      try {
        const data = await apiRequest<SimpleDiningSession[]>('/api/v1/dining/sessions', {
          method: 'GET',
          token: accessToken ?? undefined,
        })
        setDiningSessions(data.filter((s: SimpleDiningSession) => s.status === 'COLLECTING'))
      } catch (err) {
        console.error('Failed to load dining sessions:', err)
      }
    }
    void loadDiningSessions()
  }, [accessToken, user])

  // Pre-select if passed in query param
  useEffect(() => {
    if (diningSessionQueryParam) {
      let active = true
      Promise.resolve().then(() => {
        if (active) {
          setSelectedDiningSessionId(diningSessionQueryParam)
        }
      })
      return () => {
        active = false
      }
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

  // Revoke object URLs so we don't leak them on unmount.
  useEffect(() => {
    return () => {
      selectedFiles.forEach(f => {
        if (f.previewUrl) URL.revokeObjectURL(f.previewUrl)
      })
    }
  }, [selectedFiles])

  const acceptFiles = (files: FileList | null | undefined) => {
    if (!files || files.length === 0) return
    const maxFiles = user ? 8 : 2
    if (selectedFiles.length + files.length > maxFiles) {
      setSubmitError(t('scan.errors.genericPrefix') + `Bạn chỉ được tải lên tối đa ${maxFiles} file.`)
      return
    }

    const newFiles: LocalSelectedFile[] = Array.from(files).map((file) => {
      const isImage = file.type.startsWith('image/')
      const validationError = validateFile(file, t)
      const newFile: LocalSelectedFile = {
        id: Math.random().toString(36).substring(7),
        file,
        previewUrl: isImage ? URL.createObjectURL(file) : null,
        error: validationError,
        quality: null,
      }
      if (isImage && !validationError) {
        void assessImageFile(file).then((result) => {
          setSelectedFiles((prev) => prev.map((p) => p.id === newFile.id ? { ...p, quality: result } : p))
        })
      }
      return newFile
    })
    
    setSelectedFiles((prev) => [...prev, ...newFiles])
    setSubmitError(null)
  }

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    acceptFiles(event.target.files)
    event.target.value = ''
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    acceptFiles(event.dataTransfer.files)
  }

  const handleRemove = (id: string) => {
    setSelectedFiles((prev) => {
      const file = prev.find(p => p.id === id)
      if (file?.previewUrl) URL.revokeObjectURL(file.previewUrl)
      return prev.filter(p => p.id !== id)
    })
    setSubmitError(null)
  }

  const handleSubmit = async () => {
    if (selectedFiles.length === 0 || selectedFiles.some(f => f.error)) return
    setIsSubmitting(true)
    setSubmitError(null)
    const formData = new FormData()
    selectedFiles.forEach(f => formData.append('files', f.file))
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
      let message: string
      if (error instanceof ApiError && error.status === 429) {
        // Throttled: called AI again too soon. Friendly, localized message.
        message = t('scan.errors.rateLimited')
      } else if (error instanceof ApiError) {
        message = error.message
      } else {
        message = `${t('scan.errors.genericPrefix')}${error instanceof Error ? error.message : String(error)}`
      }
      setSubmitError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const canSubmit = Boolean(selectedFiles.length > 0 && selectedFiles.every(f => !f.error) && !isSubmitting)
  const fileReady = Boolean(selectedFiles.length > 0 && selectedFiles.every(f => !f.error))
  // Stepper: no file = step 1 current (awaiting upload); valid file attached
  // = step 1 complete (uploaded), step 2 current (next).
  const completedSteps = fileReady ? 1 : 0

  return (
    <div className="grid grid-cols-1 gap-[40px] lg:grid-cols-[minmax(0,1fr)_360px]">
      {/* LEFT COLUMN: input choice + dropzone + file list */}
      <Reveal className="flex flex-col gap-[30px]">
        {/* Input choice cards */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {/* Upload (active) */}
          <div className="relative flex min-h-[92px] items-center gap-5 rounded-2xl border-2 border-primary bg-primary/5 p-5 shadow-2">
            <IconBadge icon={Upload} solid size="md" />
            <div className="flex flex-col gap-0.5">
              <span className="text-[18px] leading-[26px] text-primary-dark">
                {t('scan.uploadCard.title')}
              </span>
              <span className="text-[13px] text-ink-variant">
                {t('scan.uploadCard.desc')}
              </span>
            </div>
            <span className="absolute right-2 top-2 flex size-5 items-center justify-center rounded-full bg-primary">
              <Check className="size-3 text-white" aria-hidden />
            </span>
          </div>
          {/* Camera (link) */}
          <Link
            to="/app/scan/camera"
            className="group flex min-h-[92px] items-center gap-5 rounded-2xl border border-border bg-surface p-5 shadow-1 transition-all duration-200 ease-[var(--ease-out-quint)] hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-2"
          >
            <IconBadge
              icon={Camera}
              size="md"
              className="transition-transform duration-200 group-hover:scale-110"
            />
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
            'flex h-[256px] cursor-pointer flex-col items-center justify-center gap-5 rounded-3xl border-2 border-dashed bg-surface p-8 text-center transition-all duration-200',
            isDragging
              ? 'scale-[1.01] border-primary bg-panel'
              : 'border-border hover:border-primary/40 hover:bg-panel',
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT_ATTR}
            multiple
            onChange={handleInputChange}
            className="hidden"
          />
          <IconBadge icon={Upload} solid size="lg" />
          <div className="flex flex-col items-center gap-1.5">
            <p className="text-[20px] font-bold leading-[30px] text-ink">
              {t('scan.dropzone.title')}
            </p>
            <p className="text-[14px] leading-[20px] text-ink-variant">
              {t('scan.dropzone.hint')}
            </p>
          </div>
        </div>

        {/* Selected files + preview */}
        {selectedFiles.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-[14px] font-medium uppercase tracking-[0.7px] text-ink-variant">
              {t('scan.selectedFile')} ({selectedFiles.length}/{user ? 8 : 2})
            </p>
            <div className="flex flex-col gap-3">
              {selectedFiles.map((selected) => {
                const isPdf = selected.file.type === 'application/pdf'
                return (
                  <div key={selected.id} className="flex flex-col gap-2">
                    <div className="flex items-center gap-5 rounded-2xl border border-border bg-surface p-3 shadow-1">
                      {isPdf ? (
                        <IconBadge icon={FileText} tone="primary" size="sm" />
                      ) : (
                        <div className="size-10 shrink-0 overflow-hidden rounded-xl bg-panel">
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
                        onClick={() => handleRemove(selected.id)}
                        className="flex items-center gap-1.5 rounded-full p-2 text-[14px] text-ink-variant transition-all duration-200 ease-[var(--ease-out-quint)] hover:bg-destructive/10 hover:text-destructive"
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
                    {!selected.error && selected.quality && !selected.quality.ok && (
                      <div
                        role="status"
                        className="flex items-start gap-3 rounded-2xl border border-amber/40 bg-amber/10 px-3 py-2.5 text-[14px] text-amber"
                      >
                        <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
                        <div className="flex flex-col gap-0.5">
                          <span className="font-bold">{t('camera.quality.warnTitle')}</span>
                          <ul className="flex flex-col gap-0.5">
                            {selected.quality.reasons.map((reason) => (
                              <li key={reason}>
                                • {t(`camera.quality.${QUALITY_REASON_I18N_KEY[reason]}`)}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {submitError && (
          <p
            role="alert"
            className="flex items-center gap-2 rounded-2xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-[14px] text-destructive"
          >
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            {submitError}
          </p>
        )}
      </Reveal>

      {/* RIGHT COLUMN: processing status stepper + selects + CTA */}
      <Reveal delay={0.08} className="flex flex-col gap-[30px]">
        <SectionCard title={t('scan.statusTitle')}>
          <ol className="flex flex-col">
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
                      <span className="flex size-6 items-center justify-center rounded-full bg-primary">
                        <Check className="size-3.5 text-white" aria-hidden />
                      </span>
                    )}
                    {state === 'current' && (
                      <span className="flex size-6 items-center justify-center rounded-full border-2 border-primary bg-surface">
                        <span className="size-2 rounded-full bg-primary" />
                      </span>
                    )}
                    {state === 'pending' && (
                      <span className="size-6 rounded-full border border-border bg-surface" />
                    )}
                    {!isLast && (
                      <span
                        className={cn(
                          'mt-1 w-[2px] flex-1',
                          state === 'complete' ? 'bg-primary' : 'bg-border',
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
        </SectionCard>

        {/* Ngôn ngữ đích */}
        <SectionCard>
          <div className="flex flex-col gap-2">
            <label
              htmlFor="targetLanguage"
              className="text-[15px] font-bold text-primary-dark"
            >
              {t('scan.translateTo')}
            </label>
            <Select
              value={targetLanguage}
              onValueChange={setTargetLanguage}
              disabled={isSubmitting}
            >
              <SelectTrigger
                id="targetLanguage"
                className="h-[44px] w-full rounded-xl border border-border bg-surface px-3 text-[15px] text-ink"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TARGET_LANGUAGES.map((lang) => (
                  <SelectItem key={lang.code} value={lang.code}>
                    {lang.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </SectionCard>

        {user && (diningSessions.length > 0 || diningSessionQueryParam) && (
          <SectionCard>
            <div className="flex flex-col gap-2">
              <label
                htmlFor="diningSessionSelect"
                className="text-[15px] font-bold text-primary-dark"
              >
                Liên kết phiên ăn uống (Tùy chọn)
              </label>
              <Select
                value={selectedDiningSessionId || 'none'}
                onValueChange={(v) => setSelectedDiningSessionId(v === 'none' ? '' : v)}
                disabled={isSubmitting}
              >
                <SelectTrigger
                  id="diningSessionSelect"
                  className="h-[44px] w-full rounded-xl border border-border bg-surface px-3 text-[15px] text-ink"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">-- Không liên kết --</SelectItem>
                  {diningSessionQueryParam && !diningSessions.some(s => s.id === diningSessionQueryParam) && (
                    <SelectItem value={diningSessionQueryParam}>
                      Phiên ăn {diningSessionQueryParam.slice(0, 8)} (Đang liên kết)
                    </SelectItem>
                  )}
                  {diningSessions.map((session: SimpleDiningSession) => (
                    <SelectItem key={session.id} value={session.id}>
                      {session.name || `Phiên ăn ${session.id.slice(0, 8)}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </SectionCard>
        )}

        <Button
          type="button"
          size="lg"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="h-[56px] w-full text-[17px]"
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
        </Button>
      </Reveal>
    </div>
  )
}
