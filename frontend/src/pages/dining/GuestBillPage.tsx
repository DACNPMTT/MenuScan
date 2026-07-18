import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  ReceiptText,
  RefreshCw,
  UtensilsCrossed,
  Wallet,
} from 'lucide-react'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { formatMoney } from '@/features/menu-scan/lib'
import { Button } from '@/shared/components/ui/button'
import { Card } from '@/shared/components/ui/card'
import { EmptyState } from '@/shared/components/EmptyState'
import { Spinner } from '@/shared/components/Spinner'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { loadGuestSession } from '@/features/dining/guestSession'

interface PublicBillItem {
  name: string
  quantity: number
  line_total: string
}

interface PublicBillAdjustment {
  label: string
  amount: string
}

interface PublicBill {
  bill_id: string
  menu_id: string
  menu_title: string | null
  currency: string
  subtotal_amount: string
  total_amount: string
  finalized_at: string | null
  items: PublicBillItem[]
  adjustments: PublicBillAdjustment[]
  people_count: number | null
  per_person: string | null
}

interface PublicSessionBills {
  session_id: string
  status: string
  items: PublicBill[]
}

function money(amount: string, currency: string): string {
  return formatMoney(Number(amount), currency)
}

export function GuestBillPage() {
  useDocumentTitle('Hóa đơn | MenuScan')
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const guest = useMemo(() => (token ? loadGuestSession(token) : null), [token])

  const [bills, setBills] = useState<PublicBill[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(
    async (showLoading = false) => {
      if (!guest) return
      if (showLoading) setLoading(true)
      setError(null)
      try {
        const data = await apiRequest<PublicSessionBills>(
          `/api/v1/dining/public/sessions/${guest.sessionId}/bills?invite_token=${encodeURIComponent(
            token,
          )}`,
          { method: 'GET' },
        )
        setBills(data.items ?? [])
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : 'Không tải được hóa đơn của phiên ăn.',
        )
      } finally {
        if (showLoading) setLoading(false)
      }
    },
    [guest, token],
  )

  useEffect(() => {
    if (!guest) {
      Promise.resolve().then(() => setLoading(false))
      return
    }
    let active = true
    Promise.resolve().then(() => {
      if (active) void load(true)
    })
    return () => {
      active = false
    }
  }, [guest, load])

  // Poll while no bill has been finalized yet, so a guest waiting for the host
  // to chốt sees it appear without reloading.
  useEffect(() => {
    if (!guest || bills.length > 0) return
    const timer = window.setInterval(() => void load(false), 8000)
    return () => clearInterval(timer)
  }, [guest, bills.length, load])

  const backToMenu = token
    ? `/dining/select?token=${encodeURIComponent(token)}`
    : '/dining/join'

  if (!guest) {
    return (
      <PageTransition className="flex min-h-dvh flex-col items-center justify-center bg-app-bg px-6 text-center">
        <EmptyState
          icon={AlertCircle}
          tone="destructive"
          title="Bạn chưa tham gia phiên ăn"
          description="Hãy mở lại link/QR của Host và tham gia phiên trước, rồi mới xem được hóa đơn."
          action={
            token ? (
              <Button asChild>
                <Link to={`/dining/join?token=${encodeURIComponent(token)}`}>
                  Tham gia phiên ăn
                </Link>
              </Button>
            ) : undefined
          }
        />
      </PageTransition>
    )
  }

  if (loading) {
    return (
      <PageTransition className="flex min-h-dvh w-full flex-col items-center justify-center bg-app-bg">
        <Spinner label="Đang tải hóa đơn..." />
      </PageTransition>
    )
  }

  return (
    <PageTransition className="min-h-dvh bg-app-bg">
      <div className="mx-auto w-full max-w-[720px] px-4 py-8 sm:px-6">
        <Button variant="ghost" size="sm" asChild className="mb-6 -ml-2">
          <Link to={backToMenu}>
            <ArrowLeft className="size-4" aria-hidden />
            Quay lại chọn món
          </Link>
        </Button>

        <header className="mb-6 flex flex-col gap-1">
          <span className="flex items-center gap-2 text-[13px] font-semibold text-primary">
            <ReceiptText className="size-4" aria-hidden />
            Hóa đơn của {guest.displayName || 'bạn'}
          </span>
          <h1 className="mb-0 text-[22px] font-bold leading-tight text-ink sm:text-[26px]">
            Hóa đơn phiên ăn
          </h1>
          <p className="mb-0 text-[14px] text-ink-variant">
            Host chốt hóa đơn xong là phần bạn phải trả sẽ hiện ở đây.
          </p>
        </header>

        {error && (
          <div
            role="alert"
            className="mb-4 flex items-center gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
          >
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            {error}
          </div>
        )}

        {bills.length === 0 ? (
          <EmptyState
            icon={ReceiptText}
            tone="primary"
            title="Chưa có hóa đơn"
            description="Host chưa chốt hóa đơn cho phiên này. Đợi một chút rồi bấm làm mới."
            action={
              <Button variant="outline" onClick={() => void load(true)}>
                <RefreshCw className="size-4" aria-hidden />
                Làm mới
              </Button>
            }
          />
        ) : (
          <div className="flex flex-col gap-6">
            {bills.map((bill) => (
              <Card
                key={bill.bill_id}
                className="gap-0 overflow-hidden rounded-3xl p-0 shadow-2"
              >
                <div className="flex items-center gap-2 border-b border-dashed border-border px-5 py-4">
                  <UtensilsCrossed className="size-5 text-primary" aria-hidden />
                  <h2 className="mb-0 text-[17px] font-bold text-ink">
                    {bill.menu_title || 'Bữa ăn'}
                  </h2>
                </div>

                {/* Line items */}
                <div className="flex flex-col gap-3 border-b border-dashed border-border px-5 py-4">
                  {bill.items.map((item, index) => (
                    <div
                      key={`${bill.bill_id}-${index}`}
                      className="flex items-start justify-between gap-3"
                    >
                      <div className="flex min-w-0 items-baseline gap-2">
                        <span className="shrink-0 text-[14px] font-bold text-primary-dark">
                          {item.quantity}×
                        </span>
                        <span className="truncate text-[14px] font-semibold text-ink">
                          {item.name}
                        </span>
                      </div>
                      <span className="shrink-0 text-[14px] font-bold text-ink">
                        {money(item.line_total, bill.currency)}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Totals + adjustments */}
                <div className="flex flex-col gap-2 bg-surface-muted px-5 py-4">
                  <div className="flex items-center justify-between text-[13px] text-ink-variant">
                    <span>Tạm tính</span>
                    <span>{money(bill.subtotal_amount, bill.currency)}</span>
                  </div>
                  {bill.adjustments.map((adj, index) => (
                    <div
                      key={`${bill.bill_id}-adj-${index}`}
                      className="flex items-center justify-between text-[13px] text-ink-variant"
                    >
                      <span>{adj.label}</span>
                      <span>{money(adj.amount, bill.currency)}</span>
                    </div>
                  ))}
                  <div className="mt-1 flex items-center justify-between text-[18px] font-bold text-ink">
                    <span>Tổng cộng</span>
                    <span>{money(bill.total_amount, bill.currency)}</span>
                  </div>

                  {bill.per_person && bill.people_count ? (
                    <div className="mt-3 flex items-center justify-between rounded-2xl bg-primary/15 px-4 py-3">
                      <span className="flex items-center gap-2 text-[15px] text-primary-dark">
                        <Wallet className="size-4" aria-hidden />
                        Bạn trả (chia {bill.people_count} người)
                      </span>
                      <span className="text-[18px] font-bold text-primary-dark">
                        {money(bill.per_person, bill.currency)}
                      </span>
                    </div>
                  ) : (
                    <p className="mb-0 mt-2 text-[12px] italic text-ink-variant">
                      Host chưa chia đều hóa đơn này theo số người.
                    </p>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </PageTransition>
  )
}
