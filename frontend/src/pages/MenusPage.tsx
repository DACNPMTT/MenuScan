import { useCallback, useEffect, useState, type ReactNode } from 'react'
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
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { ApiError, apiRequest, apiRequestWithMeta } from '@/shared/lib/api'
import { getAccessToken, refreshAccessToken } from '@/shared/lib/auth-token'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { API_BASE_URL } from '@/features/menu-scan/lib'
import type {
  MenuSource,
  MenuSummary,
  PaginationMeta,
} from '@/features/menu-scan/types'

const PAGE_SIZE = 20

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function MenusPage() {
  useDocumentTitle('Menus | MenuScan')
  const toast = useToast()
  const { accessToken } = useAuth()
  const [menus, setMenus] = useState<MenuSummary[]>([])
  const [meta, setMeta] = useState<PaginationMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadMenus = useCallback(
    async (page: number) => {
      if (page === 1) setLoading(true)
      else setLoadingMore(true)
      setError(null)
      try {
        const result = await apiRequestWithMeta<MenuSummary[], PaginationMeta>(
          `/api/v1/menus?page=${page}&page_size=${PAGE_SIZE}`,
          { method: 'GET', token: accessToken ?? undefined },
        )
        setMenus((current) =>
          page === 1 ? result.data : [...current, ...result.data],
        )
        setMeta(result.meta)
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : 'Không thể tải danh sách menu.',
        )
      } finally {
        setLoading(false)
        setLoadingMore(false)
      }
    },
    [accessToken],
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
      toast.show({ variant: 'success', title: 'Đã xóa menu' })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Không thể xóa menu.')
    } finally {
      setDeletingId(null)
    }
  }

  const canLoadMore = meta ? meta.page < meta.total_pages : false

  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-2">
          <p className="text-[13px] font-bold uppercase tracking-[0.7px] text-ink-variant">
            Menu đã lưu
          </p>
          <h1 className="text-[32px] font-bold leading-[40px] text-primary-dark sm:text-[44px] sm:leading-[52px]">
            Menus
          </h1>
        </div>
        <Link
          to="/app/scan"
          className="flex min-h-10 w-fit items-center gap-2 rounded-[8px] bg-primary-dark px-4 py-2 text-[14px] font-bold text-white transition-opacity hover:opacity-90"
        >
          <ScanLine className="size-4" aria-hidden />
          Quét menu mới
        </Link>
      </header>

      {error && (
        <div
          role="alert"
          className="mt-5 flex flex-col gap-3 rounded-[8px] border border-destructive/30 bg-destructive/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex items-center gap-3 text-[14px] text-destructive">
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => void loadMenus(1)}
            className="flex min-h-9 w-fit items-center gap-2 rounded-[8px] border border-destructive/30 px-3 py-1.5 text-[13px] font-bold text-destructive transition-colors hover:bg-destructive/10"
          >
            <RefreshCw className="size-4" aria-hidden />
            Thử lại
          </button>
        </div>
      )}

      <section className="mt-[25px] overflow-hidden rounded-[12px] border border-hairline bg-canvas">
        <div className="flex items-center justify-between border-b border-hairline bg-app-bg px-[20px] py-[16px]">
          <h2 className="text-[20px] leading-[28px] text-primary-dark">
            Review cuối
          </h2>
          {meta && (
            <span className="text-[13px] text-ink-variant">{meta.total} menu</span>
          )}
        </div>

        {loading ? (
          <MenuMessage icon={<Loader2 className="size-7 animate-spin" />}>
            Đang tải menu...
          </MenuMessage>
        ) : menus.length === 0 ? (
          <>
            <MenuMessage icon={<Utensils className="size-7" />}>
              Chưa có menu nào. Sau khi scan xong, hãy xác nhận review cuối để
              menu xuất hiện ở đây.
            </MenuMessage>
            <div className="flex justify-center px-[20px] pb-[40px]">
              <Link
                to="/app/scan"
                className="flex min-h-10 items-center gap-2 rounded-[8px] bg-primary-dark px-5 text-[14px] font-bold text-white transition-opacity hover:opacity-90"
              >
                <ScanLine className="size-4" aria-hidden />
                Quét menu mới
              </Link>
            </div>
          </>
        ) : (
          <div className="divide-y divide-hairline">
            {menus.map((menu) => (
              <MenuRow
                key={menu.id}
                menu={menu}
                accessToken={accessToken}
                deleting={deletingId === menu.id}
                onDelete={handleDelete}
              />
            ))}
            {canLoadMore && (
              <div className="flex justify-center px-[20px] py-[18px]">
                <button
                  type="button"
                  onClick={() => meta && void loadMenus(meta.page + 1)}
                  disabled={loadingMore}
                  className="flex min-h-10 items-center gap-2 rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loadingMore ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <RefreshCw className="size-4" aria-hidden />
                  )}
                  Tải thêm
                </button>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
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
  return (
    <div className="grid grid-cols-[56px_minmax(0,1fr)] gap-4 px-[20px] py-[16px] sm:grid-cols-[64px_minmax(0,1fr)_auto]">
      <MenuThumbnail source={menu.source} accessToken={accessToken} />
      <Link
        to={`/app/menus/${menu.id}`}
        className="min-w-0 transition-colors hover:text-primary-dark"
      >
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate text-[17px] font-bold leading-[24px] text-ink">
            {menu.title}
          </h3>
          <span className="flex items-center gap-1 rounded-full bg-[#e4f4df] px-2.5 py-0.5 text-[12px] font-bold text-[#256b2b]">
            <CheckCircle2 className="size-3.5" aria-hidden />
            {menu.status === 'CONFIRMED' ? 'Đã xác nhận' : 'Bản nháp'}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-ink-variant">
          <span>{menu.item_count} món</span>
          <span>{menu.source.file_name}</span>
          <span>{formatTime(menu.updated_at)}</span>
        </div>
      </Link>
      <div className="col-span-2 flex items-center justify-end gap-2 sm:col-span-1">
        <Link
          to={`/app/menus/${menu.id}`}
          className="rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10"
        >
          Xem
        </Link>
        <button
          type="button"
          onClick={() => void onDelete(menu.id)}
          disabled={deleting}
          aria-label={`Xóa ${menu.title}`}
          className="flex size-10 items-center justify-center rounded-[8px] border border-destructive/30 text-destructive transition-colors hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {deleting ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <Trash2 className="size-4" aria-hidden />
          )}
        </button>
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
    <div className="flex aspect-square size-14 items-center justify-center overflow-hidden rounded-[8px] border border-hairline bg-surface-muted sm:size-16">
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

function MenuMessage({
  icon,
  children,
}: {
  icon: ReactNode
  children: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-4 px-[20px] py-[54px] text-center text-ink-variant">
      <span className="flex size-14 items-center justify-center rounded-full bg-surface-muted text-primary-dark">
        {icon}
      </span>
      <p className="max-w-[420px] text-[15px]">{children}</p>
    </div>
  )
}
