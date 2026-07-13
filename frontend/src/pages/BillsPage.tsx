import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, Loader2, ReceiptText, RefreshCw, Trash2, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { ApiError, apiRequest } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { formatMoney } from '@/features/menu-scan/lib'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Reveal } from '@/shared/components/motion/Reveal'
import { SectionCard } from '@/shared/components/SectionCard'
import { IconBadge } from '@/shared/components/IconBadge'
import { EmptyState } from '@/shared/components/EmptyState'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { DatePicker } from '@/shared/components/ui/date-picker'
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

  return (
    <PageTransition>
      <div className="mx-auto w-full max-w-[1100px] px-4 py-8 sm:px-8 sm:py-12">
        {/* Header */}
        <Reveal>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[32px] font-bold leading-tight text-ink">
                {t('bills.title')}
              </h1>
              <p className="mt-1 text-[14px] text-ink-variant">{t('bills.subtitle')}</p>
            </div>
            <Button variant="outline" onClick={() => void load()} disabled={loading}>
              <RefreshCw className="size-4" aria-hidden />
              {t('common.retry')}
            </Button>
          </div>
        </Reveal>

        {/* Filters — status chips + a created-at range, applied client-side. */}
        <Reveal delay={0.05}>
          <SectionCard className="mb-5">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex flex-wrap gap-2">
                {STATUS_FILTERS.map((value) => (
                  <Button
                    key={value}
                    size="sm"
                    variant={statusFilter === value ? 'default' : 'outline'}
                    aria-pressed={statusFilter === value}
                    onClick={() => setStatusFilter(value)}
                  >
                    {value === 'ALL' ? t('bills.filterAll') : t(`bills.status.${value}`)}
                  </Button>
                ))}
              </div>
              <div className="flex items-center gap-2 text-[13px] text-ink-variant">
                {t('bills.from')}
                <DatePicker
                  value={fromDate}
                  onChange={setFromDate}
                  max={toDate || undefined}
                  aria-label={t('bills.from')}
                />
              </div>
              <div className="flex items-center gap-2 text-[13px] text-ink-variant">
                {t('bills.to')}
                <DatePicker
                  value={toDate}
                  onChange={setToDate}
                  min={fromDate || undefined}
                  aria-label={t('bills.to')}
                />
              </div>
              {hasFilter && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="size-3.5" aria-hidden />
                  {t('bills.clearFilters')}
                </Button>
              )}
            </div>
          </SectionCard>
        </Reveal>

        {error && (
          <p
            role="alert"
            className="mb-4 flex items-center gap-2 rounded-2xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-[14px] text-destructive"
          >
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            {error}
          </p>
        )}

        {loading && (
          <SectionCard>
            <div className="flex items-center justify-center gap-2 py-8 text-[14px] text-ink-variant">
              <Loader2 className="size-4 animate-spin" aria-hidden />
              {t('bills.loading')}
            </div>
          </SectionCard>
        )}

        {!loading && !error && bills.length === 0 && (
          <SectionCard>
            <EmptyState
              icon={ReceiptText}
              title={t('bills.empty')}
              action={
                <Button asChild>
                  <Link to="/app/menus">{t('bills.goToMenus')}</Link>
                </Button>
              }
            />
          </SectionCard>
        )}

        {!loading && bills.length > 0 && filtered.length === 0 && (
          <SectionCard>
            <EmptyState
              icon={ReceiptText}
              tone="muted"
              title={t('bills.noMatch')}
              action={
                <Button variant="outline" onClick={clearFilters}>
                  <X className="size-3.5" aria-hidden />
                  {t('bills.clearFilters')}
                </Button>
              }
            />
          </SectionCard>
        )}

        {!loading && filtered.length > 0 && (
          <div className="flex flex-col gap-3">
            {filtered.map((bill, index) => (
              <Reveal key={bill.id} delay={Math.min(index * 0.04, 0.24)}>
                <div className="flex items-center gap-2 overflow-hidden rounded-2xl border border-border bg-surface pr-2 shadow-2 transition-all duration-200 ease-[var(--ease-out-quint)] hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-3">
                  <Link
                    to={`/app/bills/${bill.id}`}
                    className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-4 rounded-2xl px-5 py-4 transition-colors hover:bg-panel"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <IconBadge icon={ReceiptText} size="sm" />
                      <div className="min-w-0">
                        <p className="truncate text-[15px] font-bold text-ink">
                          {formatDate(bill.created_at)}
                        </p>
                        <p className="text-[13px] text-ink-variant">
                          {t('bills.dishCount', { count: bill.item_count })}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Badge variant={bill.status === 'FINALIZED' ? 'primary' : 'outline'}>
                        {t(`bills.status.${bill.status}`)}
                      </Badge>
                      <strong className="text-[17px] text-primary-dark">
                        {formatMoney(Number(bill.total_amount), bill.currency)}
                      </strong>
                    </div>
                  </Link>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => void handleDelete(bill.id)}
                    disabled={deletingId !== null}
                    aria-label={t('bills.deleteAria', { date: formatDate(bill.created_at) })}
                    className="mr-1 hover:bg-destructive/10 hover:text-destructive"
                  >
                    {deletingId === bill.id ? (
                      <Loader2 className="size-4 animate-spin" aria-hidden />
                    ) : (
                      <Trash2 className="size-4" aria-hidden />
                    )}
                  </Button>
                </div>
              </Reveal>
            ))}
          </div>
        )}
      </div>
    </PageTransition>
  )
}
