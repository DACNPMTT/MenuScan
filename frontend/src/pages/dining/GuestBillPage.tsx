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
import { useTranslation } from 'react-i18next'
import { apiRequest } from '@/shared/lib/api'
import { describeError } from '@/shared/lib/errors'
import { formatMoney } from '@/features/menu-scan/lib'
import { Button } from '@/shared/components/ui/button'
import { Card } from '@/shared/components/ui/card'
import { EmptyState } from '@/shared/components/EmptyState'
import { IconBadge } from '@/shared/components/IconBadge'
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

interface SplitLineItem {
  name: string
  quantity: number
  amount: string
}

interface SplitShare {
  participant_id: string | null
  name: string
  is_host: boolean
  food_subtotal: string
  fee_share: string
  total: string
  line_items: SplitLineItem[]
}

interface SplitBreakdown {
  mode: 'EVENLY' | 'BY_PERSON'
  people_count: number
  shares: SplitShare[]
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
  split_breakdown: SplitBreakdown | null
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
  const { t } = useTranslation()
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
        setError(describeError(err, t, 'errors.generic'))
      } finally {
        if (showLoading) setLoading(false)
      }
    },
    [guest, token, t],
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
      <div className="mx-auto w-full max-w-[960px] px-4 py-8 sm:px-6">
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
          <div
            className={`grid grid-cols-1 items-start gap-8 ${
              bills.length > 1 ? 'lg:grid-cols-2' : ''
            }`}
          >
            {bills.map((bill) => (
              <Card
                key={bill.bill_id}
                className="mx-auto w-full max-w-[420px] gap-0 overflow-hidden rounded-3xl border border-border bg-canvas p-0 shadow-pop"
              >
                <header className="border-b border-dashed border-border px-[30px] pb-[26px] pt-[34px] text-center">
                  <div className="mb-2 flex justify-center">
                    <IconBadge icon={ReceiptText} size="sm" solid />
                  </div>
                  <h2 className="mb-0 text-[24px] font-bold uppercase tracking-[-0.5px] text-primary-dark">
                    MenuScan
                  </h2>
                  <p className="mb-0 text-[14px] font-semibold text-ink-variant">
                    Hóa đơn thanh toán
                  </p>
                  <p className="mb-0 mt-3 flex items-center justify-center gap-2 text-[15px] font-bold text-ink">
                    <UtensilsCrossed className="size-4 text-primary" aria-hidden />
                    {bill.menu_title || 'Bữa ăn'}
                  </p>
                  <div className="mt-3 flex items-center justify-center gap-3 text-[13px] text-ink-variant">
                    {bill.finalized_at && (
                      <>
                        <span>
                          {new Date(bill.finalized_at).toLocaleDateString('vi-VN', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </span>
                        <span aria-hidden>·</span>
                        <span>
                          {new Date(bill.finalized_at).toLocaleTimeString('vi-VN', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </>
                    )}
                  </div>
                  <p className="mb-0 mt-1 text-[13px] text-ink-variant">
                    Mã hóa đơn #{bill.bill_id.slice(0, 8)}
                  </p>
                </header>

                {/* Line items */}
                <div className="flex flex-col gap-[18px] border-b border-dashed border-border px-[30px] py-[24px]">
                  {bill.items.map((item, index) => (
                    <div
                      key={`${bill.bill_id}-${index}`}
                      className="flex items-start justify-between gap-3"
                    >
                      <div className="flex min-w-0 items-baseline gap-2">
                        <span className="shrink-0 text-[15px] font-bold text-primary-dark">
                          {item.quantity}×
                        </span>
                        <span className="truncate text-[15px] font-bold text-ink">
                          {item.name}
                        </span>
                      </div>
                      <span className="shrink-0 text-[15px] font-bold text-ink">
                        {money(item.line_total, bill.currency)}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Totals + adjustments */}
                <div className="flex flex-col gap-2 bg-surface-muted px-[30px] py-[24px]">
                  {bill.adjustments.length > 0 && (
                    <div className="mb-2 flex flex-col gap-1">
                      {bill.adjustments.map((adj, index) => (
                        <div
                          key={`${bill.bill_id}-adj-${index}`}
                          className="flex items-center justify-between text-[14px] text-ink-variant"
                        >
                          <span>{adj.label}</span>
                          <span>{money(adj.amount, bill.currency)}</span>
                        </div>
                      ))}
                      <div className="my-1 border-t border-dashed border-border" />
                    </div>
                  )}
                  <div className="flex items-center justify-between text-[14px] text-ink-variant">
                    <span>Tạm tính</span>
                    <span>{money(bill.subtotal_amount, bill.currency)}</span>
                  </div>
                  <div className="flex items-center justify-between text-[20px] font-bold text-ink">
                    <span>Tổng cộng</span>
                    <span>{money(bill.total_amount, bill.currency)}</span>
                  </div>

                  {(() => {
                    const breakdown = bill.split_breakdown
                    const myShare =
                      breakdown && breakdown.mode === 'BY_PERSON'
                        ? breakdown.shares.find(
                            (s) =>
                              s.participant_id != null &&
                              s.participant_id === guest.participantId,
                          )
                        : undefined

                    // Per-person plan the host set — show the guest's own real
                    // share and the whole group's breakdown.
                    if (breakdown && breakdown.mode === 'BY_PERSON' && breakdown.shares.length > 0) {
                      return (
                        <div className="mt-3 flex flex-col gap-3">
                          {myShare && (
                            <div className="rounded-2xl bg-primary/15 px-3 py-3">
                              <div className="flex items-center justify-between">
                                <span className="flex items-center gap-2 text-[15px] text-primary-dark">
                                  <Wallet className="size-4" aria-hidden />
                                  Bạn trả
                                </span>
                                <span className="text-[17px] font-bold text-primary-dark">
                                  {money(myShare.total, bill.currency)}
                                </span>
                              </div>
                              {(myShare.line_items.length > 0 ||
                                Number(myShare.fee_share) > 0) && (
                                <ul className="mt-2 flex flex-col gap-0.5">
                                  {myShare.line_items.map((li, i) => (
                                    <li
                                      key={`${bill.bill_id}-mine-${i}`}
                                      className="flex justify-between text-[12px] text-primary-dark/80"
                                    >
                                      <span>
                                        {li.quantity}× {li.name}
                                      </span>
                                      <span>{money(li.amount, bill.currency)}</span>
                                    </li>
                                  ))}
                                  {Number(myShare.fee_share) > 0 && (
                                    <li className="flex justify-between text-[12px] text-primary-dark/80">
                                      <span>Phí (chia đều)</span>
                                      <span>{money(myShare.fee_share, bill.currency)}</span>
                                    </li>
                                  )}
                                </ul>
                              )}
                            </div>
                          )}
                          <div className="rounded-2xl border border-hairline px-4 py-3">
                            <p className="mb-2 text-[11px] font-bold uppercase tracking-wide text-ink-variant">
                              Cả nhóm chia
                            </p>
                            <div className="flex flex-col gap-1.5">
                              {breakdown.shares.map((s, i) => {
                                const isMe =
                                  s.participant_id != null &&
                                  s.participant_id === guest.participantId
                                return (
                                  <div
                                    key={`${bill.bill_id}-share-${i}`}
                                    className={`flex items-center justify-between text-[13px] ${
                                      isMe
                                        ? 'font-bold text-primary-dark'
                                        : 'text-ink-variant'
                                    }`}
                                  >
                                    <span>
                                      {s.name}
                                      {isMe ? ' (bạn)' : ''}
                                    </span>
                                    <span>{money(s.total, bill.currency)}</span>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        </div>
                      )
                    }

                    // Even split — everyone pays total / N.
                    if (bill.per_person && bill.people_count) {
                      return (
                        <div className="mt-3 flex items-center justify-between gap-3 rounded-2xl bg-primary/15 px-3 py-3">
                          <span className="flex items-center gap-2 text-[15px] text-primary-dark">
                            <Wallet className="size-4" aria-hidden />
                            Bạn trả (chia {bill.people_count} người)
                          </span>
                          <span className="shrink-0 text-[17px] font-bold text-primary-dark">
                            {money(bill.per_person, bill.currency)}
                          </span>
                        </div>
                      )
                    }

                    return (
                      <p className="mb-0 mt-2 text-[12px] italic text-ink-variant">
                        Host chưa chia hóa đơn này theo người.
                      </p>
                    )
                  })()}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </PageTransition>
  )
}
