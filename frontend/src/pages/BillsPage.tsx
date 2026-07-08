import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, Loader2, ReceiptText, RefreshCw, Trash2, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { ApiError, apiRequest } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { formatMoney } from '@/features/menu-scan/lib'
import { cn } from '@/shared/lib/cn'
import type { BillStatus, BillSummary } from '@/features/billing/types'

type StatusFilter = 'ALL' | BillStatus

const STATUS_FILTERS: StatusFilter[] = ['ALL', 'DRAFT', 'FINALIZED']

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

/** Bill history: every receipt the signed-in diner has created, with
 * status/date filtering and per-row deletion. */
export function BillsPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('bills.title')} | MenuScan`)
  const { accessToken } = useAuth()
  const toast = useToast()

  const [bills, setBills] = useState<BillSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiRequest<BillSummary[]>('/api/v1/bills', {
        method: 'GET',
        token: accessToken ?? undefined,
      })
      setBills(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('bills.errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [accessToken, t])

  useEffect(() => {
    void Promise.resolve().then(load)
  }, [load])

  const handleDelete = async (billId: string) => {
    if (deletingId) return
    setDeletingId(billId)
    setError(null)
    try {
      await apiRequest(`/api/v1/bills/${billId}`, {
        method: 'DELETE',
        token: accessToken ?? undefined,
      })
      setBills((current) => current.filter((bill) => bill.id !== billId))
      toast.show({ variant: 'success', title: t('bills.toast.deleted') })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('bills.errors.deleteFailed'))
    } finally {
      setDeletingId(null)
    }
  }

  const hasFilter = statusFilter !== 'ALL' || Boolean(fromDate) || Boolean(toDate)

  const filtered = useMemo(
    () =>
      bills.filter((bill) => {
        if (statusFilter !== 'ALL' && bill.status !== statusFilter) return false
        const created = new Date(bill.created_at)
        if (fromDate && created < new Date(`${fromDate}T00:00:00`)) return false
        if (toDate && created > new Date(`${toDate}T23:59:59.999`)) return false
        return true
      }),
    [bills, statusFilter, fromDate, toDate],
  )

  const clearFilters = () => {
    setStatusFilter('ALL')
    setFromDate('')
    setToDate('')
  }

  const dateInputClass =
    'h-9 rounded-[8px] border border-hairline bg-canvas px-3 text-[14px] text-ink outline-none focus:border-primary-dark'

  return (
    <div className="mx-auto w-full max-w-[1100px] px-4 py-[30px] sm:px-[50px] sm:py-[50px]">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[32px] font-bold leading-[38px] text-primary-dark">
            {t('bills.title')}
          </h1>
          <p className="mb-0 mt-1 text-[14px] text-ink-variant">{t('bills.subtitle')}</p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="flex h-10 items-center gap-2 rounded-[8px] border border-hairline bg-canvas px-3 text-[14px] font-medium text-ink-variant transition-colors hover:bg-surface-muted disabled:opacity-50"
        >
          <RefreshCw className="size-4" aria-hidden />
          {t('common.retry')}
        </button>
      </div>

      {/* Filters — status chips + a created-at range, applied client-side. */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2">
          {STATUS_FILTERS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setStatusFilter(value)}
              aria-pressed={statusFilter === value}
              className={cn(
                'h-9 rounded-full px-4 text-[13px] font-medium transition-colors',
                statusFilter === value
                  ? 'bg-primary-dark text-white'
                  : 'border border-hairline bg-canvas text-primary-dark hover:bg-surface-muted',
              )}
            >
              {value === 'ALL' ? t('bills.filterAll') : t(`bills.status.${value}`)}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-[13px] text-ink-variant">
          {t('bills.from')}
          <input
            type="date"
            value={fromDate}
            max={toDate || undefined}
            onChange={(event) => setFromDate(event.target.value)}
            className={dateInputClass}
          />
        </label>
        <label className="flex items-center gap-2 text-[13px] text-ink-variant">
          {t('bills.to')}
          <input
            type="date"
            value={toDate}
            min={fromDate || undefined}
            onChange={(event) => setToDate(event.target.value)}
            className={dateInputClass}
          />
        </label>
        {hasFilter && (
          <button
            type="button"
            onClick={clearFilters}
            className="flex h-9 items-center gap-1.5 rounded-full border border-hairline bg-canvas px-3 text-[13px] font-medium text-ink-variant transition-colors hover:bg-surface-muted hover:text-ink"
          >
            <X className="size-3.5" aria-hidden />
            {t('bills.clearFilters')}
          </button>
        )}
      </div>

      {error && (
        <p
          role="alert"
          className="mb-4 flex items-center gap-2 rounded-[8px] border border-destructive/30 bg-destructive/5 px-3 py-2 text-[14px] text-destructive"
        >
          <AlertCircle className="size-4 shrink-0" aria-hidden />
          {error}
        </p>
      )}

      {loading && (
        <p className="flex items-center gap-2 text-[14px] text-ink-variant">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          {t('bills.loading')}
        </p>
      )}

      {!loading && !error && bills.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-[12px] border border-dashed border-hairline bg-secondary px-6 py-14 text-center">
          <ReceiptText className="size-8 text-primary-dark" aria-hidden />
          <p className="mb-0 text-[15px] text-ink-variant">{t('bills.empty')}</p>
          <Link
            to="/app/menus"
            className="rounded-[8px] bg-primary-dark px-4 py-2 text-[14px] font-bold text-white transition-opacity hover:opacity-90"
          >
            {t('bills.goToMenus')}
          </Link>
        </div>
      )}

      {!loading && bills.length > 0 && filtered.length === 0 && (
        <p className="rounded-[12px] border border-dashed border-hairline bg-secondary px-6 py-10 text-center text-[14px] text-ink-variant">
          {t('bills.noMatch')}
        </p>
      )}

      {!loading && filtered.length > 0 && (
        <ul className="flex flex-col gap-3">
          {filtered.map((bill) => (
            <li
              key={bill.id}
              className="flex items-center gap-2 rounded-[12px] border border-hairline bg-canvas pr-3 transition-colors hover:border-primary/40"
            >
              <Link
                to={`/app/bills/${bill.id}`}
                className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-4 rounded-[12px] px-5 py-4 transition-colors hover:bg-surface-muted"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-[8px] bg-surface-muted text-primary-dark">
                    <ReceiptText className="size-5" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <p className="mb-0 truncate text-[15px] font-bold text-ink">
                      {formatDate(bill.created_at)}
                    </p>
                    <p className="mb-0 text-[13px] text-ink-variant">
                      {t('bills.dishCount', { count: bill.item_count })}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span
                    className={
                      bill.status === 'FINALIZED'
                        ? 'rounded-full bg-[#2e6b00]/10 px-3 py-1 text-[12px] font-bold text-[#2e6b00]'
                        : 'rounded-full bg-surface-muted px-3 py-1 text-[12px] font-bold text-ink-variant'
                    }
                  >
                    {t(`bills.status.${bill.status}`)}
                  </span>
                  <strong className="text-[17px] text-primary-dark">
                    {formatMoney(Number(bill.total_amount), bill.currency)}
                  </strong>
                </div>
              </Link>
              <button
                type="button"
                onClick={() => void handleDelete(bill.id)}
                disabled={deletingId !== null}
                aria-label={t('bills.deleteAria', { date: formatDate(bill.created_at) })}
                className="flex size-10 shrink-0 items-center justify-center rounded-[8px] text-ink-variant transition-colors hover:bg-destructive/10 hover:text-destructive disabled:cursor-not-allowed disabled:opacity-50"
              >
                {deletingId === bill.id ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Trash2 className="size-4" aria-hidden />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
