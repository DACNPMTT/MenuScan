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
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Reveal } from '@/shared/components/motion/Reveal'
import { Spinner } from '@/shared/components/Spinner'
import { SectionCard } from '@/shared/components/SectionCard'
import { IconBadge } from '@/shared/components/IconBadge'
import { StatTile } from '@/shared/components/StatTile'
import { EmptyState } from '@/shared/components/EmptyState'
import { TiltCard } from '@/shared/components/rb/TiltCard'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Card } from '@/shared/components/ui/card'
import { Pagination } from '@/shared/components/ui/pagination'

const PAGE_SIZE = 5
const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

// Status pill variants, mapped onto the design-system Badge tones.
const STATUS_VARIANTS: Record<
  ScanStatus,
  'primary' | 'accent' | 'success' | 'destructive' | 'secondary'
> = {
  PENDING: 'secondary',
  PROCESSING: 'accent',
  COMPLETED: 'success',
  FAILED: 'destructive',
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
  const [error, setError] = useState<string | null>(null)

  const loadScans = async (page: number) => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiRequestWithMeta<ScanHistoryItem[], PaginationMeta>(
        `/api/v1/scans?page=${page}&page_size=${PAGE_SIZE}`,
        { method: 'GET', token: accessToken ?? undefined },
      )
      setScans(result.data)
      setMeta(result.meta)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t('dashboard.historyError'),
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void Promise.resolve().then(() => loadScans(1))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])


  const totalScans = meta?.total ?? scans.length
  const loadedItemCount = scans.reduce(
    (sum, scan) => sum + (scan.menu?.item_count ?? 0),
    0,
  )

  return (
    <PageTransition>
      <div className="mx-auto w-full max-w-[1200px] px-4 py-8 sm:px-8 lg:py-10">
        <div className="flex flex-col gap-2">
          <h1 className="text-[32px] font-bold leading-[40px] text-ink sm:text-[44px] sm:leading-[52px]">
            {t('dashboard.welcome', { name: displayName })}
          </h1>
          <p className="flex items-center gap-2 text-[14px] text-ink-variant">
            <Sparkles className="size-4 text-amber" aria-hidden />
            {t('dashboard.systemStatus')}
          </p>
        </div>

        {/* Primary CTAs — bento, tilt on hover. */}
        <div className="mt-7 grid grid-cols-1 gap-5 sm:grid-cols-2">
          <TiltCard className="h-full">
            <Link to="/app/scan" className="block h-full">
              <Card className="h-full min-h-[176px] items-center justify-center gap-4 px-6 py-7 text-center shadow-2 transition-all duration-200 hover:-translate-y-1 hover:shadow-3 sm:px-8">
                <IconBadge icon={FileUp} tone="primary" solid size="lg" />
                <span className="flex flex-col gap-1.5">
                  <span className="text-[20px] font-bold leading-[26px] text-ink">
                    {t('dashboard.upload.title')}
                  </span>
                  <span className="text-[14px] text-ink-variant">
                    {t('dashboard.upload.desc')}
                  </span>
                </span>
              </Card>
            </Link>
          </TiltCard>

          <TiltCard className="h-full">
            <Link to="/app/scan/camera" className="block h-full">
              <Card className="h-full min-h-[176px] items-center justify-center gap-4 border-transparent bg-primary px-6 py-7 text-center text-white shadow-3 transition-all duration-200 hover:-translate-y-1 hover:shadow-pop sm:px-8">
                <IconBadge
                  icon={Camera}
                  size="lg"
                  className="bg-white/15 text-white"
                />
                <span className="flex flex-col gap-1.5">
                  <span className="text-[20px] font-bold leading-[26px] text-white">
                    {t('dashboard.camera.title')}
                  </span>
                  <span className="text-[14px] text-white/80">
                    {t('dashboard.camera.desc')}
                  </span>
                </span>
              </Card>
            </Link>
          </TiltCard>
        </div>

        {/* Metrics — animated counters for the numeric ones. */}
        <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-3">
          <StatTile label={t('dashboard.metrics.scanned')} count={totalScans} />
          <StatTile label={t('dashboard.metrics.itemsLoaded')} count={loadedItemCount} />
          <StatTile
            label={t('dashboard.metrics.historyPage')}
            value={meta ? `${meta.page}/${Math.max(meta.total_pages, 1)}` : '1/1'}
          />
        </div>

        {/* Recent scans — elevated panel with staggered rows. */}
        <div className="mt-7">
          <SectionCard
            flush
            title={t('dashboard.recent')}
            action={
              meta ? (
                <span className="text-[13px] text-ink-variant">
                  {t('dashboard.sessionCount', { count: meta.total })}
                </span>
              ) : undefined
            }
          >
            {loading ? (
              <div className="flex flex-col items-center justify-center gap-4 px-6 py-12 text-center text-ink-variant">
                <Spinner label={t('dashboard.loadingHistory')} />
              </div>
            ) : error ? (
              <HistoryError message={error} onRetry={() => void loadScans(1)} />
            ) : scans.length === 0 ? (
              <EmptyHistory />
            ) : (
              <div className="divide-y divide-border">
                {scans.map((scan, index) => (
                  <Reveal key={scan.id} delay={Math.min(index * 0.04, 0.32)}>
                    <ScanHistoryRow scan={scan} accessToken={accessToken} />
                  </Reveal>
                ))}
                {meta && meta.total_pages > 1 && (
                  <Pagination
                    currentPage={meta.page}
                    totalPages={meta.total_pages}
                    onPageChange={(page) => void loadScans(page)}
                  />
                )}
              </div>
            )}
          </SectionCard>
        </div>
      </div>
    </PageTransition>
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
      className="grid grid-cols-[72px_minmax(0,1fr)] gap-4 px-6 py-4 transition-colors hover:bg-panel sm:grid-cols-[88px_minmax(0,1fr)_auto]"
    >
      <ScanThumbnail scan={scan} accessToken={accessToken} />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate text-[16px] font-bold leading-[22px] text-ink">
            {scan.source.file_name}
          </h3>
          <Badge variant={STATUS_VARIANTS[scan.status]}>
            {t(`dashboard.status.${scan.status}`)}
          </Badge>
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
            <span className="flex items-center gap-1.5 text-success">
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
    <div className="flex aspect-square size-[72px] items-center justify-center overflow-hidden rounded-2xl border border-border bg-panel sm:size-[88px]">
      {isImage && objectUrl ? (
        <img
          src={objectUrl}
          alt={scan.source.file_name}
          className="h-full w-full object-cover"
        />
      ) : isImage ? (
        <Loader2 className="size-5 animate-spin text-ink-variant" aria-hidden />
      ) : (
        <FileText className="size-7 text-primary" aria-hidden />
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
    <div className="flex flex-col items-center gap-4 px-6 py-12 text-center text-ink-variant">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-panel text-primary">
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
    <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-destructive/10">
        <AlertCircle className="size-7 text-destructive" aria-hidden />
      </span>
      <p role="alert" className="max-w-[360px] text-[14px] text-destructive">
        {message}
      </p>
      <Button
        variant="outline"
        onClick={onRetry}
        className="border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
      >
        <RefreshCw className="size-4" aria-hidden />
        {t('common.retry')}
      </Button>
    </div>
  )
}

function EmptyHistory() {
  const { t } = useTranslation()
  return (
    <EmptyState
      icon={ScanLine}
      tone="primary"
      title={t('dashboard.empty.title')}
      description={t('dashboard.empty.body')}
      action={
        <Button asChild size="lg">
          <Link to="/app/scan">{t('dashboard.empty.scanNow')}</Link>
        </Button>
      }
    />
  )
}
