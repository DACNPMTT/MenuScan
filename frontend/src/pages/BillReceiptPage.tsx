import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { AlertCircle, ArrowLeft, Loader2, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { ApiError, apiRequest } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { DigitalReceipt } from '@/features/billing/components/DigitalReceipt'
import type { Bill, BillSplit } from '@/features/billing/types'

export function BillReceiptPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('billReceipt.docTitle')} | MenuScan`)
  const { billId } = useParams<{ billId: string }>()
  const [searchParams] = useSearchParams()
  const { accessToken } = useAuth()
  const toast = useToast()

  const peopleCount = Math.max(1, Number(searchParams.get('people')) || 1)

  const [bill, setBill] = useState<Bill | null>(null)
  const [split, setSplit] = useState<BillSplit | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [finalizing, setFinalizing] = useState(false)

  const loadBill = useCallback(async () => {
    if (!billId) return
    setLoading(true)
    setError(null)
    try {
      const data = await apiRequest<Bill>(`/api/v1/bills/${billId}`, {
        method: 'GET',
        token: accessToken ?? undefined,
      })
      setBill(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('billReceipt.errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [accessToken, billId, t])

  // Split is a server-side compute (not persisted), so recompute on every load
  // from the bill's current snapshot + the requested people count.
  const computeSplit = useCallback(
    async (id: string) => {
      try {
        const result = await apiRequest<BillSplit>(
          `/api/v1/bills/${id}/split`,
          {
            method: 'POST',
            token: accessToken ?? undefined,
            body: JSON.stringify({ people_count: peopleCount }),
          },
        )
        setSplit(result)
      } catch {
        // Split is an enhancement; a failure must not block the receipt.
        setSplit(null)
      }
    },
    [accessToken, peopleCount],
  )

  useEffect(() => {
    void (async () => {
      await loadBill()
      if (billId) await computeSplit(billId)
    })()
  }, [loadBill, computeSplit, billId])

  const handleFinalize = async () => {
    if (!billId || finalizing) return
    setFinalizing(true)
    try {
      await apiRequest<Bill>(`/api/v1/bills/${billId}/finalize`, {
        method: 'POST',
        token: accessToken ?? undefined,
      })
      toast.show({ variant: 'success', title: t('billReceipt.toast.finalized') })
      await loadBill()
    } catch (err) {
      // Finalize is idempotent: a 409 means it was already finalized — treat
      // as success and refresh so the UI reflects the FINALIZED state.
      if (err instanceof ApiError && err.code === 'BILL_ALREADY_FINALIZED') {
        await loadBill()
      } else {
        toast.show({
          variant: 'error',
          title: t('billReceipt.toast.finalizeFailed'),
          description: err instanceof ApiError ? err.message : undefined,
        })
      }
    } finally {
      setFinalizing(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-[900px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
      <Link
        to={bill ? `/app/menus/${bill.menu_id}` : '/app/menus'}
        className="mb-6 flex w-fit items-center gap-2 text-[14px] text-ink-variant transition-colors hover:text-primary-dark"
      >
        <ArrowLeft className="size-4" aria-hidden />
        {t('billReceipt.backToMenu')}
      </Link>

      {loading ? (
        <div className="flex flex-col items-center gap-3 py-[80px] text-ink-variant">
          <Loader2 className="size-7 animate-spin text-primary-dark" aria-hidden />
          {t('billReceipt.loading')}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center gap-4 rounded-[12px] border border-destructive/30 bg-destructive/5 px-5 py-[50px] text-center">
          <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10">
            <AlertCircle className="size-7 text-destructive" aria-hidden />
          </span>
          <p role="alert" className="max-w-[360px] text-[14px] text-destructive">
            {error}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => void loadBill()}
              className="flex min-h-10 items-center gap-2 rounded-[8px] border border-destructive/30 px-4 py-2 text-[14px] font-medium text-destructive transition-colors hover:bg-destructive/10"
            >
              <RefreshCw className="size-4" aria-hidden />
              {t('common.retry')}
            </button>
            <Link
              to="/app/menus"
              className="flex min-h-10 items-center rounded-[8px] bg-primary-dark px-4 py-2 text-[14px] font-bold text-white transition-opacity hover:opacity-90"
            >
              {t('billReceipt.backToMenus')}
            </Link>
          </div>
        </div>
      ) : bill ? (
        <DigitalReceipt
          bill={bill}
          split={split}
          finalizing={finalizing}
          onFinalize={() => void handleFinalize()}
          backToEditHref={`/app/menus/${bill.menu_id}`}
        />
      ) : null}
    </div>
  )
}
