import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  ClipboardList,
  ReceiptText,
  UtensilsCrossed,
} from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { useTranslation } from 'react-i18next'
import { apiRequest } from '@/shared/lib/api'
import { describeError } from '@/shared/lib/errors'
import { Button } from '@/shared/components/ui/button'
import { Card } from '@/shared/components/ui/card'
import { EmptyState } from '@/shared/components/EmptyState'
import { Spinner } from '@/shared/components/Spinner'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

interface MenuItemLite {
  id: string
  translated_name: string | null
  original_name: string
  price: string | null
  currency: string | null
}

interface MenuFull {
  id: string
  title: string
  default_currency: string | null
  created_at: string
  items: MenuItemLite[]
}

interface BillSummary {
  id: string
  menu_id: string
  status: string
  currency: string
  total_amount: string
  item_count: number
  created_at: string
  finalized_at: string | null
}

interface HostSelection {
  food_item_id: string
  quantity: number
  note: string | null
}

interface GuestPick {
  participant_id: string
  display_name: string
  quantity: number
  note: string | null
}

interface SelectionSummaryItem {
  food_item_id: string
  total_quantity: number
  selected_by: GuestPick[]
}

function formatDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

/** A meal's detail, in two parts:
 *   1. what was picked — host's own picks + every guest's, both persisted;
 *   2. the exported bill(s).
 */
export function MealDetailPage() {
  const { t } = useTranslation()
  const { sessionId, menuId } = useParams<{ sessionId: string; menuId: string }>()
  const { accessToken } = useAuth()
  const [menu, setMenu] = useState<MenuFull | null>(null)
  const [bills, setBills] = useState<BillSummary[]>([])
  const [hostSelections, setHostSelections] = useState<HostSelection[]>([])
  const [selections, setSelections] = useState<SelectionSummaryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useDocumentTitle(menu ? `${menu.title} | MenuScan` : 'Bữa ăn | MenuScan')

  const load = useCallback(
    async (showLoading = false) => {
      if (!menuId) return
      if (showLoading) setLoading(true)
      setError(null)
      try {
        const detail = await apiRequest<MenuFull>(`/api/v1/menus/${menuId}`, {
          method: 'GET',
          token: accessToken ?? undefined,
        })
        setMenu(detail)

        try {
          const host = await apiRequest<{ items: HostSelection[] }>(
            `/api/v1/dining/menus/${menuId}/host-selections`,
            { method: 'GET', token: accessToken ?? undefined },
          )
          setHostSelections(host.items ?? [])
        } catch {
          // ignore
        }

        if (sessionId) {
          try {
            const sel = await apiRequest<{ items: SelectionSummaryItem[] }>(
              `/api/v1/dining/sessions/${sessionId}/selections`,
              { method: 'GET', token: accessToken ?? undefined },
            )
            setSelections(sel.items ?? [])
          } catch {
            // ignore
          }
        }

        try {
          const allBills = await apiRequest<BillSummary[]>('/api/v1/bills', {
            method: 'GET',
            token: accessToken ?? undefined,
          })
          setBills(
            allBills
              .filter((bill) => bill.menu_id === menuId)
              .sort((a, b) => b.created_at.localeCompare(a.created_at)),
          )
        } catch {
          // ignore
        }
      } catch (err) {
        setError(describeError(err, t, 'errors.generic'))
      } finally {
        if (showLoading) setLoading(false)
      }
    },
    [menuId, sessionId, accessToken, t],
  )

  useEffect(() => {
    let active = true
    Promise.resolve().then(() => {
      if (active) void load(true)
    })
    return () => {
      active = false
    }
  }, [load])

  // The full order: the host's own picks + every guest's, per dish.
  const order = useMemo(() => {
    const itemById = new Map((menu?.items ?? []).map((item) => [item.id, item]))
    const currency = menu?.default_currency ?? 'VND'
    const rows = new Map<
      string,
      { name: string; price: number; hostQuantity: number; guests: GuestPick[] }
    >()

    for (const host of hostSelections) {
      const item = itemById.get(host.food_item_id)
      if (!item) continue
      rows.set(host.food_item_id, {
        name: item.translated_name || item.original_name,
        price: Number(item.price ?? 0) || 0,
        hostQuantity: host.quantity,
        guests: [],
      })
    }
    for (const selection of selections) {
      const item = itemById.get(selection.food_item_id)
      if (!item) continue
      const existing = rows.get(selection.food_item_id)
      if (existing) {
        existing.guests = selection.selected_by
      } else {
        rows.set(selection.food_item_id, {
          name: item.translated_name || item.original_name,
          price: Number(item.price ?? 0) || 0,
          hostQuantity: 0,
          guests: selection.selected_by,
        })
      }
    }

    const list = Array.from(rows, ([id, row]) => {
      const guestQuantity = row.guests.reduce((sum, g) => sum + g.quantity, 0)
      const totalQuantity = row.hostQuantity + guestQuantity
      return {
        id,
        name: row.name,
        totalQuantity,
        amount: row.price * totalQuantity,
        hostQuantity: row.hostQuantity,
        guests: row.guests,
      }
    }).filter((row) => row.totalQuantity > 0)

    const subtotal = list.reduce((sum, row) => sum + row.amount, 0)
    return { rows: list, subtotal, currency }
  }, [hostSelections, selections, menu])

  const backTo = sessionId ? `/app/dining/sessions/${sessionId}` : '/app/dining'
  const money = (amount: number) =>
    `${amount.toLocaleString('vi-VN')} ${order.currency}`

  if (loading) {
    return (
      <PageTransition className="flex h-[60vh] w-full flex-col items-center justify-center text-ink-variant">
        <Spinner label="Đang tải bữa ăn..." />
      </PageTransition>
    )
  }

  if (error || !menu) {
    return (
      <PageTransition className="mx-auto w-full max-w-[600px] px-4 py-16">
        <EmptyState
          icon={AlertCircle}
          tone="destructive"
          title="Không tải được bữa ăn"
          description={error || 'Không tìm thấy bữa ăn.'}
          action={
            <Button variant="outline" asChild>
              <Link to={backTo}>
                <ArrowLeft className="size-4" aria-hidden /> Quay lại phiên
              </Link>
            </Button>
          }
        />
      </PageTransition>
    )
  }

  return (
    <PageTransition className="mx-auto w-full max-w-[720px] px-4 py-[30px] sm:px-6 sm:py-[40px]">
      <Button variant="ghost" size="sm" asChild className="mb-6 -ml-2">
        <Link to={backTo}>
          <ArrowLeft className="size-4" aria-hidden />
          Quay lại phiên
        </Link>
      </Button>

      <header className="mb-6 flex flex-col gap-1">
        <span className="flex items-center gap-2 text-[13px] font-semibold text-primary">
          <UtensilsCrossed className="size-4" aria-hidden />
          Bữa ăn trong phiên
        </span>
        <h1 className="mb-0 text-[24px] font-bold leading-tight text-ink sm:text-[30px]">
          {menu.title}
        </h1>
        <p className="mb-0 text-[13px] text-ink-variant">
          {formatDateTime(menu.created_at)} · {menu.items.length} món
        </p>
      </header>

      {/* Mục 1 — the order (host + guests), plus the way back into the menu. */}
      <Card className="gap-3 rounded-2xl p-5 shadow-1">
        <div className="flex items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-[16px] font-bold text-ink">
            <ClipboardList className="size-5 text-primary" aria-hidden />
            Món đã gọi
          </h2>
          {order.rows.length > 0 && (
            <strong className="text-[15px] text-primary-dark">
              {money(order.subtotal)}
            </strong>
          )}
        </div>

        {order.rows.length === 0 ? (
          <p className="mb-0 text-[13px] italic text-ink-variant">
            Chưa ai chọn món. Mở thực đơn, bấm chọn món của bạn và khách sẽ tự chốt phần
            của họ.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {order.rows.map((row) => (
              <div key={row.id} className="flex flex-col gap-1 rounded-xl bg-panel px-3 py-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="min-w-0 truncate font-semibold text-ink">
                    {row.totalQuantity} x {row.name}
                  </span>
                  <span className="shrink-0 text-[13px] font-bold text-primary-dark">
                    {money(row.amount)}
                  </span>
                </div>
                <p className="mb-0 text-[12px] text-ink-variant">
                  {[
                    ...(row.hostQuantity > 0
                      ? [`Bạn/Host (x${row.hostQuantity})`]
                      : []),
                    ...row.guests.map(
                      (guest) =>
                        `${guest.display_name} (x${guest.quantity})${
                          guest.note ? ` – ${guest.note}` : ''
                        }`,
                    ),
                  ].join(', ')}
                </p>
              </div>
            ))}
          </div>
        )}

        <Button asChild size="lg" className="mt-1 w-full">
          <Link to={`/app/menus/${menu.id}`}>
            <UtensilsCrossed className="size-5" aria-hidden />
            Mở thực đơn · gọi món · chia bill
          </Link>
        </Button>
      </Card>

      {/* Mục 2 — the exported bill(s). */}
      <Card className="mt-6 gap-3 rounded-2xl p-5 shadow-1">
        <h2 className="flex items-center gap-2 text-[16px] font-bold text-ink">
          <ReceiptText className="size-5 text-primary" aria-hidden />
          Hóa đơn ({bills.length})
        </h2>
        {bills.length === 0 ? (
          <p className="mb-0 text-[13px] italic text-ink-variant">
            Chưa có hóa đơn xuất ra.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {bills.map((bill) => (
              <Link
                key={bill.id}
                to={`/app/bills/${bill.id}`}
                className="flex items-center justify-between gap-3 rounded-xl border border-border bg-panel px-3 py-2.5 transition-colors hover:border-primary/40 hover:bg-primary/5"
              >
                <span className="min-w-0 text-[13px] text-ink-variant">
                  {formatDateTime(bill.created_at)} · {bill.item_count} món ·{' '}
                  <span
                    className={
                      bill.status === 'FINALIZED'
                        ? 'font-semibold text-success'
                        : 'font-semibold text-amber'
                    }
                  >
                    {bill.status === 'FINALIZED' ? 'Đã chốt' : 'Nháp'}
                  </span>
                </span>
                <strong className="shrink-0 text-[14px] text-primary-dark">
                  {Number(bill.total_amount).toLocaleString('vi-VN')} {bill.currency}
                </strong>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </PageTransition>
  )
}
