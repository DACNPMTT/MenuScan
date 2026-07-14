import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { ApiError, apiRequest } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { DigitalReceipt } from '@/features/billing/components/DigitalReceipt'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Reveal } from '@/shared/components/motion/Reveal'
import { SectionCard } from '@/shared/components/SectionCard'
import { IconBadge } from '@/shared/components/IconBadge'
import { Spinner } from '@/shared/components/Spinner'
import { Button } from '@/shared/components/ui/button'
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
    <PageTransition>
      <div className="mx-auto w-full max-w-[900px] px-4 py-8 sm:px-8 sm:py-10">
        <Button variant="ghost" size="sm" asChild className="mb-6">
          <Link to={bill ? `/app/menus/${bill.menu_id}` : '/app/menus'}>
            <ArrowLeft className="size-4" aria-hidden />
            {t('billReceipt.backToMenu')}
          </Link>
        </Button>

        {loading ? (
          <SectionCard>
            <div className="flex flex-col items-center gap-3 py-[80px]">
              <Spinner label={t('billReceipt.loading')} className="text-primary-dark" />
              <span className="text-[14px] text-ink-variant">{t('billReceipt.loading')}</span>
            </div>
          </SectionCard>
        ) : error ? (
          <SectionCard>
            <div className="flex flex-col items-center gap-4 px-5 py-[50px] text-center">
              <IconBadge icon={AlertCircle} tone="destructive" size="lg" />
              <p
                role="alert"
                className="max-w-[360px] text-[14px] leading-relaxed text-destructive"
              >
                {error}
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <Button variant="outline" onClick={() => void loadBill()}>
                  <RefreshCw className="size-4" aria-hidden />
                  {t('common.retry')}
                </Button>
                <Button asChild>
                  <Link to="/app/menus">{t('billReceipt.backToMenus')}</Link>
                </Button>
              </div>
            </div>
          </SectionCard>
        ) : bill ? (
          <Reveal>
            <DigitalReceipt
              bill={bill}
              split={split}
              finalizing={finalizing}
              onFinalize={() => void handleFinalize()}
              backToEditHref={`/app/menus/${bill.menu_id}`}
            />
          </Reveal>
        ) : null}
      </div>
    </PageTransition>
  )
}
