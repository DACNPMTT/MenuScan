import { ArrowLeft, CheckCircle2, ReceiptText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { formatMoney } from '@/features/menu-scan/lib'
import { IconBadge } from '@/shared/components/IconBadge'
import { Button } from '@/shared/components/ui/button'
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
  const { t } = useTranslation()
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
      className="mx-auto w-full max-w-[420px] overflow-hidden rounded-3xl border border-border bg-canvas shadow-pop"
    >
      {/* Receipt header */}
      <header className="border-b border-dashed border-border px-[30px] pb-[26px] pt-[34px] text-center">
        <div className="mb-2 flex justify-center">
          <IconBadge icon={ReceiptText} size="sm" solid />
        </div>
        <h1
          id="receipt-title"
          className="text-[24px] font-bold uppercase tracking-[-0.5px] text-primary-dark"
        >
          MenuScan
        </h1>
        <p className="text-[14px] font-semibold text-ink-variant">
          {t('receipt.ticket')}
        </p>
        <div className="mt-3 flex items-center justify-center gap-4 text-[13px] text-ink-variant">
          <span>{dateLabel}</span>
          <span aria-hidden>·</span>
          <span>{timeLabel}</span>
        </div>
        <div className="mt-1 text-[13px] text-ink-variant">{t('receipt.order', { id: orderLabel })}</div>
      </header>

      {/* Line items */}
      <div className="flex flex-col gap-[18px] border-b border-dashed border-border px-[30px] py-[24px]">
        {bill.items.map((item) => (
          <div key={item.id} className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-baseline gap-2">
              <span className="shrink-0 text-[15px] font-bold text-primary-dark">
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
      <div className="flex flex-col gap-2 bg-surface-muted px-[30px] py-[24px]">
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
            <div className="my-1 border-t border-dashed border-border" />
          </div>
        )}

        <div className="flex items-center justify-between text-[14px] text-ink-variant">
          <span>{t('receipt.subtotal')}</span>
          <span>{formatLine(bill.subtotal_amount, bill.currency)}</span>
        </div>

        <div className="flex items-center justify-between text-[20px] font-bold text-ink">
          <span>{t('receipt.total')}</span>
          <span>{formatLine(bill.total_amount, bill.currency)}</span>
        </div>

        {split && split.people_count > 1 && (
          <div className="mt-3 border-t border-border pt-3">
            <div className="flex items-center justify-between text-[13px] text-ink-variant">
              <span>{t('receipt.splitAmong')}</span>
              <span className="font-bold text-ink">
                {t('receipt.people', { count: split.people_count })}
              </span>
            </div>
            <div className="mt-2 flex items-center justify-between rounded-2xl bg-primary/15 px-3 py-2">
              <span className="text-[16px] text-primary-dark">{t('receipt.perPersonPays')}</span>
              <span className="text-[16px] font-bold text-primary-dark">
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
            <Button
              size="lg"
              className="h-12 w-full text-[15px]"
              onClick={onFinalize}
              disabled={finalizing}
            >
              {finalizing ? t('receipt.finalizing') : t('receipt.finalize')}
            </Button>
            <Button variant="outline" size="lg" asChild className="h-12 w-full text-[15px]">
              <Link to={backToEditHref}>
                <ArrowLeft className="size-4" aria-hidden />
                {t('receipt.backToEdit')}
              </Link>
            </Button>
          </>
        ) : (
          <div className="flex items-center justify-center gap-2 rounded-full bg-primary/15 px-4 py-3 text-[15px] font-bold text-primary-dark">
            <CheckCircle2 className="size-5" aria-hidden />
            {t('receipt.finalized')}
          </div>
        )}
      </div>
    </section>
  )
}
