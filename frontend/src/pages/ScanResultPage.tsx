import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  Bookmark,
  BookmarkCheck,
  Check,
  ListChecks,
  Loader2,
  RefreshCw,
  XCircle,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useExchangeRates } from '@/shared/hooks/useExchangeRates'
import { CurrencySelect } from '@/shared/components/CurrencySelect'
import { formatConvertedAmount, type ExchangeRates } from '@/shared/lib/currency'
import type {
  MenuItemResult,
  MenuDetail,
  MenuSavedState,
  ScanDetail,
  ScanError,
  ScanResult,
} from '@/features/menu-scan/types'

const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

function resolveUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`
}

const POLL_INTERVAL_MS = 1500
const MAX_POLL_MS = 180_000 // 3 min cap; the pipeline finishes well under this.

const LANGUAGE_MAP: Record<string, string> = {
  vi: '🇻🇳 Tiếng Việt',
  en: '🇺🇸 English',
  zh: '🇨🇳 中文',
  ja: '🇯🇵 日本語',
  ko: '🇰🇷 한국어',
  fr: '🇫🇷 Français',
  th: '🇹🇭 ภาษาไทย',
}

export function ScanResultPage() {
  const { scanId } = useParams<{ scanId: string }>()
  const { accessToken } = useAuth()
  const { t } = useTranslation()
  useDocumentTitle(`${t('scanResult.title')} | MenuScan`)

  const [detail, setDetail] = useState<ScanDetail | null>(null)
  const [result, setResult] = useState<ScanResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const startedAt = useRef(0)

  useEffect(() => {
    if (!scanId) return
    startedAt.current = Date.now()
    let cancelled = false
    let timer = 0

    const poll = async () => {
      try {
        const current = await apiRequest<ScanDetail>(
          `/api/v1/scans/${scanId}`,
          { method: 'GET', token: accessToken ?? undefined },
        )
        if (cancelled) return
        setDetail(current)

        if (current.status === 'COMPLETED') {
          try {
            const res = await apiRequest<ScanResult>(
              `/api/v1/scans/${scanId}/result`,
              { method: 'GET', token: accessToken ?? undefined },
            )
            if (!cancelled) setResult(res)
          } catch (err) {
            if (!cancelled) {
              setError(
                err instanceof ApiError
                  ? err.message
                  : t('scanResult.errors.resultLoadFailed'),
              )
            }
          }
          return
        }

        if (current.status === 'FAILED') {
          if (!cancelled) {
            const err = current.error
            const msg =
              err == null
                ? t('scanResult.errors.scanFailed')
                : typeof err === 'string'
                  ? err
                  : (err as ScanError).message || t('scanResult.errors.scanFailed')
            setError(msg)
          }
          return
        }

        if (Date.now() - startedAt.current < MAX_POLL_MS) {
          timer = window.setTimeout(poll, POLL_INTERVAL_MS)
        } else {
          setError(t('scanResult.errors.tookTooLong'))
        }
      } catch (err) {
        if (cancelled) return
        setError(
          err instanceof ApiError ? err.message : t('scanResult.errors.statusFailed'),
        )
      }
    }

    timer = window.setTimeout(poll, 0)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [scanId, accessToken, t])

  const status = detail?.status
  const handleSavedChange = (isSaved: boolean) => {
    setResult((current) =>
      current?.menu
        ? { ...current, menu: { ...current.menu, is_saved: isSaved } }
        : current,
    )
  }
  const handleConfirmed = (menu: MenuDetail) => {
    setResult((current) =>
      current?.menu
        ? {
            ...current,
            menu: {
              ...current.menu,
              status: menu.status,
              is_saved: menu.is_saved,
              title: menu.title,
              default_currency: menu.default_currency,
              items: menu.items,
            },
          }
        : current,
    )
  }

  return (
    <div className="mx-auto w-full max-w-[900px] px-[30px] py-[40px] sm:px-[50px]">
      <Link
        to="/app"
        className="mb-6 flex w-fit items-center gap-2 text-[14px] text-ink-variant transition-colors hover:text-primary-dark"
      >
        <ArrowLeft className="size-4" aria-hidden />
        {t('common.backToDashboard')}
      </Link>

      {error && (
        <div
          role="alert"
          className="flex flex-col gap-4 rounded-[12px] border border-destructive/30 bg-destructive/5 px-5 py-4"
        >
          <div className="flex items-start gap-3 text-[14px] text-destructive">
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
          <Link
            to="/app/scan"
            className="flex w-fit items-center gap-2 rounded-[8px] border border-destructive/30 px-4 py-2 text-[14px] font-medium text-destructive transition-colors hover:bg-destructive/10"
          >
            <RefreshCw className="size-4" aria-hidden />
            {t('scanResult.retryScan')}
          </Link>
        </div>
      )}

      {!error && status !== 'COMPLETED' && <ProcessingView detail={detail} />}

      {status === 'COMPLETED' && result && (
        <ResultView
          result={result}
          accessToken={accessToken}
          onSavedChange={handleSavedChange}
          onConfirmed={handleConfirmed}
        />
      )}
    </div>
  )
}

function ProcessingView({ detail }: { detail: ScanDetail | null }) {
  const { t } = useTranslation()
  const progress = detail?.progress ?? 0
  const fallbackStage = t('scanResult.processing.default')
  const stageLabel = detail?.stage
    ? t(`scanResult.stages.${detail.stage}`, { defaultValue: fallbackStage })
    : fallbackStage
  return (
    <div className="flex flex-col gap-6 rounded-[12px] border border-hairline bg-canvas p-[30px]">
      <div className="flex items-center gap-3">
        <Loader2 className="size-6 animate-spin text-primary-dark" aria-hidden />
        <div className="flex flex-col">
          <h1 className="text-[24px] font-bold leading-[30px] text-primary-dark">
            {t('scanResult.processing.title')}
          </h1>
          <p className="text-[14px] text-ink-variant">{stageLabel}</p>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <div className="h-2 w-full overflow-hidden rounded-full bg-surface-muted">
          <div
            className="h-full rounded-full bg-primary-dark transition-all duration-500"
            style={{ width: `${Math.max(5, progress)}%` }}
          />
        </div>
        <span className="text-right text-[13px] text-ink-variant">{progress}%</span>
      </div>
    </div>
  )
}

function ResultView({
  result,
  accessToken,
  onSavedChange,
  onConfirmed,
}: {
  result: ScanResult
  accessToken: string | null
  onSavedChange: (isSaved: boolean) => void
  onConfirmed: (menu: MenuDetail) => void
}) {
  const { t } = useTranslation()
  const items = result.menu?.items ?? []
  const toast = useToast()
  const source = result.scan.source
  const baseCurrency = result.menu?.default_currency ?? 'VND'
  const [displayCurrency, setDisplayCurrency] = useState(baseCurrency)
  const { rates } = useExchangeRates(baseCurrency)
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [confirmError, setConfirmError] = useState<string | null>(null)

  const handleToggleSaved = async () => {
    if (!result.menu || saving) return
    const nextSaved = !result.menu.is_saved
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await apiRequest<MenuSavedState>(
        `/api/v1/menus/${result.menu.id}`,
        {
          method: 'PATCH',
          token: accessToken ?? undefined,
          body: JSON.stringify({ is_saved: nextSaved }),
        },
      )
      onSavedChange(updated.is_saved)
      toast.show({
        variant: 'success',
        title: nextSaved ? t('scanResult.toast.saved') : t('scanResult.toast.unsaved'),
      })
    } catch (err) {
      setSaveError(
        err instanceof ApiError
          ? err.message
          : t('scanResult.errors.saveFailed'),
      )
    } finally {
      setSaving(false)
    }
  }

  const handleConfirm = async () => {
    if (!result.menu || confirming) return
    setConfirming(true)
    setConfirmError(null)
    try {
      const confirmed = await apiRequest<MenuDetail>(
        `/api/v1/menus/${result.menu.id}/confirm`,
        {
          method: 'POST',
          token: accessToken ?? undefined,
        },
      )
      onConfirmed(confirmed)
      toast.show({ variant: 'success', title: t('scanResult.toast.confirmed') })
    } catch (err) {
      setConfirmError(
        err instanceof ApiError
          ? err.message
          : t('scanResult.errors.confirmFailed'),
      )
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-full bg-primary-dark">
            <Check className="size-5 text-white" aria-hidden />
          </span>
          <div className="flex flex-col">
            <h1 className="text-[28px] font-bold leading-[34px] text-primary-dark">
              {result.menu?.title || t('scanResult.title')}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <span className="text-[14px] text-ink-variant">
                {t('scanResult.dishCount', { count: items.length })} · {source.file_name}
              </span>
              <span className="hidden text-[14px] text-ink-variant sm:inline">•</span>
              {result.scan.detected_language && (
                <span className="rounded-full bg-secondary px-2.5 py-0.5 text-[12px] font-medium text-ink-variant">
                  {t('scanResult.detected')} {LANGUAGE_MAP[result.scan.detected_language] || result.scan.detected_language.toUpperCase()}
                </span>
              )}
              <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[12px] font-medium text-primary-dark">
                {t('scanResult.translatedTo')} {LANGUAGE_MAP[result.scan.target_language] || result.scan.target_language.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
        {result.menu && (
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <Link
              to={`/app/menus/${result.menu.id}`}
              className="flex min-h-10 items-center gap-2 rounded-[8px] bg-primary-dark px-4 py-2 text-[14px] font-bold text-white transition-opacity hover:opacity-90"
            >
              <ListChecks className="size-4" aria-hidden />
              {t('scanResult.chooseAndSplit')}
            </Link>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={confirming}
              className="flex min-h-10 items-center gap-2 rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {confirming ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Check className="size-4" aria-hidden />
              )}
              {result.menu.status === 'CONFIRMED' ? t('scanResult.confirmed') : t('scanResult.confirmMenu')}
            </button>
            <button
              type="button"
              onClick={handleToggleSaved}
              disabled={saving}
              className="flex min-h-10 items-center gap-2 rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
              aria-pressed={result.menu.is_saved}
            >
              {saving ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : result.menu.is_saved ? (
                <BookmarkCheck className="size-4" aria-hidden />
              ) : (
                <Bookmark className="size-4" aria-hidden />
              )}
              {result.menu.is_saved ? t('scanResult.saved') : t('scanResult.saveMenu')}
            </button>
            {saveError && (
              <span role="alert" className="text-[13px] text-destructive">
                {saveError}
              </span>
            )}
            {confirmError && (
              <span role="alert" className="text-[13px] text-destructive">
                {confirmError}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-[30px] lg:grid-cols-[300px_minmax(0,1fr)]">
        <SourcePreview source={source} accessToken={accessToken} />
        <ItemsList
          items={items}
          baseCurrency={baseCurrency}
          displayCurrency={displayCurrency}
          rates={rates}
          onCurrencyChange={setDisplayCurrency}
        />
      </div>
    </div>
  )
}

/** Fetch the source bytes and render an object URL. Auth is optional because
 * guest scans can read their source by scan id. */
function SourcePreview({
  source,
  accessToken,
}: {
  source: ScanResult['scan']['source']
  accessToken: string | null
}) {
  const { t } = useTranslation()
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const isImage = source.mime_type.startsWith('image/')

  useEffect(() => {
    if (!isImage) return
    let url: string | null = null
    let active = true
    const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined
    fetch(resolveUrl(source.preview_url), { headers, credentials: 'include' })
      .then((res) => (res.ok ? res.blob() : Promise.reject(new Error(`${res.status}`))))
      .then((blob) => {
        if (!active) return
        url = URL.createObjectURL(blob)
        setObjectUrl(url)
      })
      .catch(() => active && setObjectUrl(null))
    return () => {
      active = false
      if (url) URL.revokeObjectURL(url)
    }
  }, [source.preview_url, accessToken, isImage])

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[14px] font-medium uppercase tracking-[0.7px] text-ink-variant">
        {t('scanResult.sourceFile')}
      </p>
      <div className="overflow-hidden rounded-[12px] border border-hairline bg-surface-muted">
        {isImage ? (
          objectUrl ? (
            <img
              src={objectUrl}
              alt={source.file_name}
              className="h-auto w-full object-contain"
            />
          ) : (
            <div className="flex aspect-square items-center justify-center">
              <Loader2 className="size-6 animate-spin text-ink-variant" aria-hidden />
            </div>
          )
        ) : (
          <div className="flex items-center gap-3 p-4">
            <AlertCircle className="size-5 text-primary-dark" aria-hidden />
            <span className="text-[14px] text-ink-variant">
              {source.file_name} (PDF)
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

function ItemsList({
  items,
  baseCurrency,
  displayCurrency,
  rates,
  onCurrencyChange,
}: {
  items: MenuItemResult[]
  baseCurrency: string
  displayCurrency: string
  rates: ExchangeRates | null
  onCurrencyChange: (currency: string) => void
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[14px] font-medium uppercase tracking-[0.7px] text-ink-variant">
          {t('scanResult.extractedItems')}
        </p>
        {items.length > 0 && (
          <CurrencySelect value={displayCurrency} onChange={onCurrencyChange} />
        )}
      </div>
      {items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-[12px] border border-dashed border-hairline bg-canvas px-4 py-[40px] text-center">
          <XCircle className="size-8 text-ink-variant" aria-hidden />
          <div className="flex flex-col gap-1">
            <p className="text-[15px] font-medium text-ink">
              {t('scanResult.noItems.title')}
            </p>
            <p className="max-w-[340px] text-[14px] text-ink-variant">
              {t('scanResult.noItems.body')}
            </p>
          </div>
          <Link
            to="/app/scan"
            className="mt-1 rounded-[8px] bg-primary-dark px-[20px] py-[10px] text-[15px] font-bold text-white transition-opacity hover:opacity-90"
          >
            {t('scanResult.scanAnother')}
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-2 rounded-[12px] border border-hairline bg-canvas p-4 transition-colors hover:border-primary/30 hover:bg-surface-muted/50"
            >
              {item.category && (
                <span className="w-fit rounded-[4px] bg-secondary px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.5px] text-ink-variant">
                  {item.category}
                </span>
              )}
              <div className="flex items-start justify-between gap-3">
                <span className="text-[16px] font-bold leading-tight text-ink">
                  {item.original_name}
                </span>
                <span className="shrink-0 text-[15px] font-semibold text-primary-dark">
                  {item.price
                    ? formatConvertedAmount(
                        Number(item.price),
                        item.currency ?? baseCurrency,
                        displayCurrency,
                        rates,
                      )
                    : '—'}
                </span>
              </div>
              {item.translated_name && item.translated_name !== item.original_name && (
                <span className="text-[14px] font-medium text-ink-variant">
                  {item.translated_name}
                </span>
              )}
              {(item.original_description || item.translated_description) && (
                <div className="mt-1 flex flex-col gap-1.5 border-t border-hairline pt-2.5">
                  {item.original_description && (
                    <span className="text-[13px] italic text-ink-variant">
                      {item.original_description}
                    </span>
                  )}
                  {item.translated_description && item.translated_description !== item.original_description && (
                    <span className="text-[13px] text-ink-variant">
                      {item.translated_description}
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}