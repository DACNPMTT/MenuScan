import { ArrowLeft, CheckCircle2, ReceiptText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatMoney } from '@/features/menu-scan/lib'
import type { Bill, BillSplit } from '@/features/billing/types'

interface DigitalReceiptProps {
  bill: Bill
  split: BillSplit | null
  finalizing?: boolean
  onFinalize: () => void
  /** Route the user back to when the bill is still DRAFT. */
  backToEditHref: string
}

function formatLine(amount: string, currency: string): string {
  return formatMoney(Number(amount), currency)
}

/** The finalized/draft digital receipt. Renders the bill snapshot exactly as
 * the server computed it — no client-side totals math, so the displayed line
 * sums and split always match `total_amount` by construction. */
export function DigitalReceipt({
  bill,
  split,
  finalizing,
  onFinalize,
  backToEditHref,
}: DigitalReceiptProps) {
  const isDraft = bill.status === 'DRAFT'
  const created = new Date(bill.created_at)
  const dateLabel = created.toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
  const timeLabel = created.toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
  })
  const orderLabel = `#${bill.id.slice(0, 8)}`

  return (
    <section
      aria-labelledby="receipt-title"
      className="mx-auto w-full max-w-[420px] overflow-hidden rounded-[14px] border border-hairline bg-white"
    >
      {/* Receipt header */}
      <header className="border-b border-dashed border-[#e6e6e6] px-[30px] pb-[26px] pt-[34px] text-center">
        <div className="mb-2 flex justify-center">
          <span className="flex size-9 items-center justify-center rounded-full bg-primary-dark">
            <ReceiptText className="size-5 text-white" aria-hidden />
          </span>
        </div>
        <h1
          id="receipt-title"
          className="text-[24px] font-bold uppercase tracking-[-0.5px] text-primary-dark"
        >
          MenuScan
        </h1>
        <p className="text-[14px] font-semibold text-ink-variant">
          Digital Order Ticket
        </p>
        <div className="mt-3 flex items-center justify-center gap-4 text-[13px] text-ink-variant">
          <span>{dateLabel}</span>
          <span aria-hidden>·</span>
          <span>{timeLabel}</span>
        </div>
        <div className="mt-1 text-[13px] text-ink-variant">Order {orderLabel}</div>
      </header>

      {/* Line items */}
      <div className="flex flex-col gap-[18px] border-b border-dashed border-[#e6e6e6] px-[30px] py-[24px]">
        {bill.items.map((item) => (
          <div key={item.id} className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-baseline gap-2">
              <span className="shrink-0 text-[15px] font-bold text-ink">
                {item.quantity}×
              </span>
              <span className="truncate text-[15px] font-bold text-ink">
                {item.name_snapshot}
              </span>
            </div>
            <span className="shrink-0 text-[15px] font-bold text-ink">
              {formatLine(item.line_total, bill.currency)}
            </span>
          </div>
        ))}
      </div>

      {/* Totals + adjustments + split */}
      <div className="flex flex-col gap-2 bg-[#f7fbed] px-[30px] py-[24px]">
        {bill.adjustments.length > 0 && (
          <div className="mb-2 flex flex-col gap-1">
            {bill.adjustments.map((adj) => (
              <div
                key={adj.id}
                className="flex items-center justify-between text-[14px] text-ink-variant"
              >
                <span>{adj.label}</span>
                <span>{formatLine(adj.calculated_amount, bill.currency)}</span>
              </div>
            ))}
            <div className="my-1 border-t border-dashed border-[#e6e6e6]" />
          </div>
        )}

        <div className="flex items-center justify-between text-[14px] text-ink-variant">
          <span>Tạm tính</span>
          <span>{formatLine(bill.subtotal_amount, bill.currency)}</span>
        </div>

        <div className="flex items-center justify-between text-[18px] font-bold text-ink">
          <span>Tổng cộng</span>
          <span>{formatLine(bill.total_amount, bill.currency)}</span>
        </div>

        {split && split.people_count > 1 && (
          <div className="mt-3 border-t border-[#e6e6e6] pt-3">
            <div className="flex items-center justify-between text-[13px] text-ink-variant">
              <span>Chia cho</span>
              <span className="font-bold text-ink">
                {split.people_count} người
              </span>
            </div>
            <div className="mt-2 flex items-center justify-between rounded-[8px] bg-[rgba(65,134,19,0.2)] px-3 py-2">
              <span className="text-[16px] text-[#2e6b00]">Mỗi người trả</span>
              <span className="text-[16px] font-bold text-[#2e6b00]">
                {formatLine(split.base_share, bill.currency)}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2 px-[30px] py-[24px]">
        {isDraft ? (
          <>
            <button
              type="button"
              onClick={onFinalize}
              disabled={finalizing}
              className="flex h-12 w-full items-center justify-center rounded-full bg-primary-dark text-[15px] font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {finalizing ? 'Đang chốt…' : 'Xuất hóa đơn'}
            </button>
            <Link
              to={backToEditHref}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-full border border-hairline bg-white text-[15px] font-bold text-ink transition-colors hover:bg-surface-muted"
            >
              <ArrowLeft className="size-4" aria-hidden />
              Quay lại chỉnh bill
            </Link>
          </>
        ) : (
          <div className="flex items-center justify-center gap-2 rounded-full bg-[#eef6e9] px-4 py-3 text-[15px] font-bold text-[#256b2b]">
            <CheckCircle2 className="size-5" aria-hidden />
            Đã chốt · không thể chỉnh sửa
          </div>
        )}
      </div>
    </section>
  )
}
