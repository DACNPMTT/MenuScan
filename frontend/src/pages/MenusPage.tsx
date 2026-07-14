import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  RefreshCw,
  ScanLine,
  Trash2,
  Utensils,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { ApiError, apiRequest, apiRequestWithMeta } from '@/shared/lib/api'
import { getAccessToken, refreshAccessToken } from '@/shared/lib/auth-token'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { Button } from '@/shared/components/ui/button'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Reveal } from '@/shared/components/motion/Reveal'
import { SectionCard } from '@/shared/components/SectionCard'
import { EmptyState } from '@/shared/components/EmptyState'
import { Spinner } from '@/shared/components/Spinner'
import { Pagination } from '@/shared/components/ui/pagination'
import { API_BASE_URL } from '@/features/menu-scan/lib'
import type {
  MenuSource,
  MenuSummary,
  PaginationMeta,
} from '@/features/menu-scan/types'

const PAGE_SIZE = 5

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function MenusPage() {
  const { t } = useTranslation()
  useDocumentTitle('Menus | MenuScan')
  const toast = useToast()
  const { accessToken } = useAuth()
  const [menus, setMenus] = useState<MenuSummary[]>([])
  const [meta, setMeta] = useState<PaginationMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadMenus = useCallback(
    async (page: number) => {
      setLoading(true)
      setError(null)
      try {
        const result = await apiRequestWithMeta<MenuSummary[], PaginationMeta>(
          `/api/v1/menus?page=${page}&page_size=${PAGE_SIZE}`,
          { method: 'GET', token: accessToken ?? undefined },
        )
        setMenus(result.data)
        setMeta(result.meta)
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : t('menus.errors.loadFailed'),
        )
      } finally {
        setLoading(false)
      }
    },
    [accessToken, t],
  )

  useEffect(() => {
    void Promise.resolve().then(() => loadMenus(1))
  }, [loadMenus])

  const handleDelete = async (menuId: string) => {
    if (deletingId) return
    setDeletingId(menuId)
    setError(null)
    try {
      await apiRequest(`/api/v1/menus/${menuId}`, {
        method: 'DELETE',
        token: accessToken ?? undefined,
      })
      setMenus((current) => current.filter((menu) => menu.id !== menuId))
      setMeta((current) =>
        current ? { ...current, total: Math.max(0, current.total - 1) } : current,
      )
      toast.show({ variant: 'success', title: t('menus.toast.deleted') })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('menus.errors.deleteFailed'))
    } finally {
      setDeletingId(null)
    }
  }



  return (
    <PageTransition className="mx-auto w-full max-w-[1200px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-2">
          <p className="text-[13px] font-bold uppercase tracking-[0.7px] text-ink-variant">
            {t('menus.savedMenus')}
          </p>
          <h1 className="text-[32px] font-bold leading-[40px] text-primary-dark sm:text-[44px] sm:leading-[52px]">
            {t('menus.title')}
          </h1>
        </div>
        <Button asChild size="lg">
          <Link to="/app/scan">
            <ScanLine aria-hidden />
            {t('menus.scanNew')}
          </Link>
        </Button>
      </header>

      {error && (
        <div
          role="alert"
          className="mt-5 flex flex-col gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex items-center gap-3 text-[14px] text-destructive">
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void loadMenus(1)}
            className="border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            <RefreshCw aria-hidden />
            {t('common.retry')}
          </Button>
        </div>
      )}

      <SectionCard
        className="mt-[25px]"
        title={t('menus.finalReview')}
        action={
          meta ? (
            <span className="text-[13px] text-ink-variant">
              {t('menus.menuCount', { count: meta.total })}
            </span>
          ) : null
        }
        bodyClassName="flex flex-col gap-3"
      >
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-hairline bg-surface py-[60px] text-ink-variant shadow-1">
            <Spinner label={t('menus.loading')} />
          </div>
        ) : menus.length === 0 ? (
          <EmptyState
            icon={Utensils}
            title={t('menus.empty')}
            action={
              <Button asChild size="lg">
                <Link to="/app/scan">
                  <ScanLine aria-hidden />
                  {t('menus.scanNew')}
                </Link>
              </Button>
            }
          />
        ) : (
          <>
            {menus.map((menu, index) => (
              <Reveal key={menu.id} delay={Math.min((index % 8) * 0.05, 0.35)}>
                <MenuRow
                  menu={menu}
                  accessToken={accessToken}
                  deleting={deletingId === menu.id}
                  onDelete={handleDelete}
                />
              </Reveal>
            ))}
            {meta && meta.total_pages > 1 && (
              <Pagination
                currentPage={meta.page}
                totalPages={meta.total_pages}
                onPageChange={(page) => void loadMenus(page)}
              />
            )}
          </>
        )}
      </SectionCard>
    </PageTransition>
  )
}

function MenuRow({
  accessToken,
  menu,
  deleting,
  onDelete,
}: {
  accessToken: string | null
  menu: MenuSummary
  deleting: boolean
  onDelete: (menuId: string) => Promise<void>
}) {
  const { t } = useTranslation()
  return (
    <div className="grid grid-cols-[56px_minmax(0,1fr)] gap-4 rounded-2xl border border-border bg-surface px-5 py-4 shadow-1 transition-all duration-200 ease-[var(--ease-out-quint)] hover:-translate-y-1 hover:shadow-3 sm:grid-cols-[64px_minmax(0,1fr)_auto]">
      <MenuThumbnail source={menu.source} accessToken={accessToken} />
      <Link
        to={`/app/menus/${menu.id}`}
        className="min-w-0 transition-colors hover:text-primary-dark"
      >
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate text-[17px] font-bold leading-[24px] text-ink">
            {menu.title}
          </h3>
          <span className="flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-0.5 text-[12px] font-bold text-primary-dark">
            <CheckCircle2 className="size-3.5" aria-hidden />
            {menu.status === 'CONFIRMED' ? t('menus.confirmed') : t('menus.draft')}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-ink-variant">
          <span>{t('menus.dishCount', { count: menu.item_count })}</span>
          <span>{menu.source.file_name}</span>
          <span>{formatTime(menu.updated_at)}</span>
        </div>
      </Link>
      <div className="col-span-2 flex items-center justify-end gap-2 sm:col-span-1">
        <Button
          asChild
          variant="outline"
          size="sm"
          className="border-primary text-primary hover:bg-primary/10 hover:text-primary"
        >
          <Link to={`/app/menus/${menu.id}`}>{t('menus.view')}</Link>
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={() => void onDelete(menu.id)}
          disabled={deleting}
          aria-label={t('menus.deleteAria', { title: menu.title })}
          className="border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
        >
          {deleting ? (
            <Loader2 className="animate-spin" aria-hidden />
          ) : (
            <Trash2 aria-hidden />
          )}
        </Button>
      </div>
    </div>
  )
}

function MenuThumbnail({
  accessToken,
  source,
}: {
  accessToken: string | null
  source: MenuSource
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState(false)
  const isImage = source.mime_type.startsWith('image/')

  useEffect(() => {
    if (!isImage) {
      return
    }

    let active = true
    let nextObjectUrl: string | null = null

    const previewUrl = source.preview_url.startsWith('http')
      ? source.preview_url
      : `${API_BASE_URL}${source.preview_url}`

    const fetchPreview = async (token: string | null) =>
      fetch(previewUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
      })

    const loadPreview = async () => {
      setPreviewError(false)
      setObjectUrl(null)
      try {
        let response = await fetchPreview(getAccessToken() ?? accessToken)
        if (response.status === 401 || response.status === 403) {
          const freshToken = await refreshAccessToken()
          if (freshToken) response = await fetchPreview(freshToken)
        }
        if (!response.ok) throw new Error('Menu preview request failed')
        const blob = await response.blob()
        nextObjectUrl = URL.createObjectURL(blob)
        if (active) {
          setObjectUrl(nextObjectUrl)
        } else {
          URL.revokeObjectURL(nextObjectUrl)
        }
      } catch {
        if (active) setPreviewError(true)
      }
    }

    void loadPreview()
    return () => {
      active = false
      if (nextObjectUrl) URL.revokeObjectURL(nextObjectUrl)
    }
  }, [accessToken, isImage, source.preview_url])

  return (
    <div className="flex aspect-square size-14 items-center justify-center overflow-hidden rounded-2xl border border-border bg-panel sm:size-16">
      {objectUrl && isImage ? (
        <img
          src={objectUrl}
          alt={source.file_name}
          className="h-full w-full object-cover"
          loading="lazy"
        />
      ) : previewError || !isImage ? (
        <FileText className="size-6 text-primary-dark" aria-hidden />
      ) : (
        <Loader2 className="size-5 animate-spin text-primary-dark" aria-hidden />
      )}
    </div>
  )
}

