import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  Clock3,
  FileText,
  FileUp,
  Loader2,
  RefreshCw,
  ScanLine,
  Sparkles,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { ApiError, apiRequestWithMeta } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import type {
  PaginationMeta,
  ScanHistoryItem,
  ScanStatus,
} from '@/features/menu-scan/types'

const PAGE_SIZE = 20
const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

const STATUS_STYLES: Record<ScanStatus, string> = {
  PENDING: 'bg-secondary text-ink-variant',
  PROCESSING: 'bg-primary/15 text-primary-dark',
  COMPLETED: 'bg-[#e4f4df] text-[#256b2b]',
  FAILED: 'bg-destructive/10 text-destructive',
}

function resolveUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`
}

function formatScanTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function DashboardPage() {
  const { t } = useTranslation()
  useDocumentTitle('Dashboard | MenuScan')
  const { user, accessToken } = useAuth()
  const displayName = user?.display_name || user?.email?.split('@')[0] || t('dashboard.fallbackName')
  const [scans, setScans] = useState<ScanHistoryItem[]>([])
  const [meta, setMeta] = useState<PaginationMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadScans = async (page: number) => {
    if (page === 1) {
      setLoading(true)
    } else {
      setLoadingMore(true)
    }
    setError(null)
    try {
      const result = await apiRequestWithMeta<ScanHistoryItem[], PaginationMeta>(
        `/api/v1/scans?page=${page}&page_size=${PAGE_SIZE}`,
        { method: 'GET', token: accessToken ?? undefined },
      )
      setScans((current) =>
        page === 1 ? result.data : [...current, ...result.data],
      )
      setMeta(result.meta)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t('dashboard.historyError'),
      )
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  useEffect(() => {
    void Promise.resolve().then(() => loadScans(1))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const canLoadMore = meta ? meta.page < meta.total_pages : false
  const totalScans = meta?.total ?? scans.length
  const loadedItemCount = scans.reduce(
    (sum, scan) => sum + (scan.menu?.item_count ?? 0),
    0,
  )

  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
      <div className="flex flex-col gap-2">
        <h1 className="text-[32px] font-bold leading-[40px] text-primary-dark sm:text-[44px] sm:leading-[52px]">
          {t('dashboard.welcome', { name: displayName })}
        </h1>
        <p className="flex items-center gap-2 text-[14px] text-ink-variant">
          <Sparkles className="size-4 text-primary-dark" aria-hidden />
          {t('dashboard.systemStatus')}
        </p>
      </div>

      <div className="mt-[30px] grid grid-cols-1 gap-[20px] sm:grid-cols-2">
        <Link
          to="/app/scan"
          className="group flex min-h-[160px] flex-col items-center justify-center gap-4 rounded-[12px] border border-hairline bg-canvas p-[30px] text-center transition-colors hover:bg-surface-muted"
        >
          <span className="flex size-12 items-center justify-center rounded-full bg-primary-dark">
            <FileUp className="size-6 text-white" aria-hidden />
          </span>
          <span className="flex flex-col gap-1.5">
            <span className="text-[20px] leading-[28px] text-primary-dark">
              {t('dashboard.upload.title')}
            </span>
            <span className="text-[14px] text-ink-variant">
              {t('dashboard.upload.desc')}
            </span>
          </span>
        </Link>
        <Link
          to="/app/scan/camera"
          className="group flex min-h-[160px] flex-col items-center justify-center gap-4 rounded-[12px] border border-primary-dark bg-primary-dark p-[30px] text-center transition-opacity hover:opacity-90"
        >
          <span className="flex size-12 items-center justify-center rounded-full bg-white">
            <Camera className="size-6 text-primary-dark" aria-hidden />
          </span>
          <span className="flex flex-col gap-1.5">
            <span className="text-[20px] leading-[28px] text-white">
              {t('dashboard.camera.title')}
            </span>
            <span className="text-[14px] text-[#e0e4d6]">
              {t('dashboard.camera.desc')}
            </span>
          </span>
        </Link>
      </div>

      <div className="mt-[25px] grid grid-cols-1 gap-[20px] sm:grid-cols-3">
        <MetricCard label={t('dashboard.metrics.scanned')} value={String(totalScans)} />
        <MetricCard label={t('dashboard.metrics.itemsLoaded')} value={String(loadedItemCount)} />
        <MetricCard
          label={t('dashboard.metrics.historyPage')}
          value={meta ? `${meta.page}/${Math.max(meta.total_pages, 1)}` : '1/1'}
        />
      </div>

      <section className="mt-[30px] overflow-hidden rounded-[12px] border border-hairline bg-canvas">
        <header className="flex flex-col gap-1 border-b border-hairline bg-app-bg px-[20px] py-[16px] sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-[20px] leading-[28px] text-primary-dark">
            {t('dashboard.recent')}
          </h2>
          {meta && (
            <span className="text-[13px] text-ink-variant">
              {t('dashboard.sessionCount', { count: meta.total })}
            </span>
          )}
        </header>

        {loading ? (
          <HistoryMessage icon={<Loader2 className="size-7 animate-spin" />}>
            {t('dashboard.loadingHistory')}
          </HistoryMessage>
        ) : error ? (
          <HistoryError message={error} onRetry={() => void loadScans(1)} />
        ) : scans.length === 0 ? (
          <EmptyHistory />
        ) : (
          <div className="divide-y divide-hairline">
            {scans.map((scan) => (
              <ScanHistoryRow
                key={scan.id}
                scan={scan}
                accessToken={accessToken}
              />
            ))}
            {canLoadMore && (
              <div className="flex justify-center px-[20px] py-[18px]">
                <button
                  type="button"
                  onClick={() => meta && void loadScans(meta.page + 1)}
                  disabled={loadingMore}
                  className="flex min-h-10 items-center gap-2 rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loadingMore ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <RefreshCw className="size-4" aria-hidden />
                  )}
                  {t('dashboard.loadMore')}
                </button>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[12px] border border-hairline bg-canvas px-[21px] py-[20px]">
      <p className="pb-1.5 text-[14px] text-ink-variant">{label}</p>
      <p className="text-[30px] font-bold leading-[34px] text-primary-dark">{value}</p>
    </div>
  )
}

function ScanHistoryRow({
  scan,
  accessToken,
}: {
  scan: ScanHistoryItem
  accessToken: string | null
}) {
  const { t } = useTranslation()
  const itemCount = scan.menu?.item_count ?? 0
  return (
    <Link
      to={`/app/scans/${scan.id}`}
      className="grid grid-cols-[72px_minmax(0,1fr)] gap-4 px-[20px] py-[16px] transition-colors hover:bg-surface-muted/60 sm:grid-cols-[88px_minmax(0,1fr)_auto]"
    >
      <ScanThumbnail scan={scan} accessToken={accessToken} />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate text-[16px] font-bold leading-[22px] text-ink">
            {scan.source.file_name}
          </h3>
          <span
            className={`rounded-full px-2.5 py-0.5 text-[12px] font-bold ${STATUS_STYLES[scan.status]}`}
          >
            {t(`dashboard.status.${scan.status}`)}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-ink-variant">
          <span className="flex items-center gap-1.5">
            <ScanLine className="size-3.5" aria-hidden />
            {t('dashboard.dishCount', { count: itemCount })}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock3 className="size-3.5" aria-hidden />
            {formatScanTime(scan.created_at)}
          </span>
          {scan.menu?.is_saved && (
            <span className="flex items-center gap-1.5 text-primary-dark">
              <CheckCircle2 className="size-3.5" aria-hidden />
              {t('dashboard.saved')}
            </span>
          )}
        </div>
      </div>
      <div className="hidden items-center text-[13px] font-medium text-ink-variant sm:flex">
        {t('dashboard.viewResult')}
      </div>
    </Link>
  )
}

function ScanThumbnail({
  scan,
  accessToken,
}: {
  scan: ScanHistoryItem
  accessToken: string | null
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const isImage = scan.source.mime_type.startsWith('image/')

  useEffect(() => {
    if (!isImage) return
    let active = true
    let url: string | null = null
    const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined
    fetch(resolveUrl(scan.source.preview_url), { headers, credentials: 'include' })
      .then((response) =>
        response.ok ? response.blob() : Promise.reject(new Error(`${response.status}`)),
      )
      .then((blob) => {
        if (!active) return
        url = URL.createObjectURL(blob)
        setObjectUrl(url)
      })
      .catch(() => {
        if (active) setObjectUrl(null)
      })
    return () => {
      active = false
      if (url) URL.revokeObjectURL(url)
    }
  }, [accessToken, isImage, scan.source.preview_url])

  return (
    <div className="flex aspect-square size-[72px] items-center justify-center overflow-hidden rounded-[8px] border border-hairline bg-surface-muted sm:size-[88px]">
      {isImage && objectUrl ? (
        <img
          src={objectUrl}
          alt={scan.source.file_name}
          className="h-full w-full object-cover"
        />
      ) : isImage ? (
        <Loader2 className="size-5 animate-spin text-ink-variant" aria-hidden />
      ) : (
        <FileText className="size-7 text-primary-dark" aria-hidden />
      )}
    </div>
  )
}

function HistoryMessage({
  icon,
  children,
}: {
  icon: ReactNode
  children: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-4 px-[20px] py-[50px] text-center text-ink-variant">
      <span className="flex size-14 items-center justify-center rounded-full bg-surface-muted text-primary-dark">
        {icon}
      </span>
      <p className="text-[15px]">{children}</p>
    </div>
  )
}

function HistoryError({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col items-center gap-4 px-[20px] py-[50px] text-center">
      <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10">
        <AlertCircle className="size-7 text-destructive" aria-hidden />
      </span>
      <p role="alert" className="max-w-[360px] text-[14px] text-destructive">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="flex min-h-10 items-center gap-2 rounded-[8px] border border-destructive/30 px-4 py-2 text-[14px] font-medium text-destructive transition-colors hover:bg-destructive/10"
      >
        <RefreshCw className="size-4" aria-hidden />
        {t('common.retry')}
      </button>
    </div>
  )
}

function EmptyHistory() {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col items-center gap-4 px-[20px] py-[50px] text-center">
      <span className="flex size-14 items-center justify-center rounded-full bg-surface-muted">
        <ScanLine className="size-7 text-primary-dark" aria-hidden />
      </span>
      <div className="flex flex-col gap-1.5">
        <p className="text-[16px] font-medium text-ink">{t('dashboard.empty.title')}</p>
        <p className="max-w-[320px] text-[14px] text-ink-variant">
          {t('dashboard.empty.body')}
        </p>
      </div>
      <Link
        to="/app/scan"
        className="mt-1 rounded-[8px] bg-primary-dark px-[24px] py-[10px] text-[15px] font-bold text-white transition-opacity hover:opacity-90"
      >
        {t('dashboard.empty.scanNow')}
      </Link>
    </div>
  )
}
