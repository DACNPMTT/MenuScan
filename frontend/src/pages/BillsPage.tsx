import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, Loader2, ReceiptText, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { ApiError, apiRequest } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { formatMoney } from '@/features/menu-scan/lib'
import type { BillSummary } from '@/features/billing/types'

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

/** Bill history: every receipt the signed-in diner has created. */
export function BillsPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('bills.title')} | MenuScan`)
  const { accessToken } = useAuth()

  const [bills, setBills] = useState<BillSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

      {error && (
        <p
          role="alert"
          className="flex items-center gap-2 rounded-[8px] border border-destructive/30 bg-destructive/5 px-3 py-2 text-[14px] text-destructive"
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

      {!loading && bills.length > 0 && (
        <ul className="flex flex-col gap-3">
          {bills.map((bill) => (
            <li key={bill.id}>
              <Link
                to={`/app/bills/${bill.id}`}
                className="flex flex-wrap items-center justify-between gap-4 rounded-[12px] border border-hairline bg-canvas px-5 py-4 transition-colors hover:border-primary/40 hover:bg-surface-muted"
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
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
