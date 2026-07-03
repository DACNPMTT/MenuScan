import { ReceiptText } from 'lucide-react'
import { ItemDisplayName } from '@/features/menu-scan/components/menu-detail/ItemDisplayName'
import { formatMoney, itemPrice } from '@/features/menu-scan/lib'
import type { BillItem, BillLineState } from '@/features/menu-scan/types'

export interface ReceiptLine {
  item: BillItem
  state: BillLineState
}

export interface ReceiptPreviewProps {
  lines: ReceiptLine[]
  currency: string | null
  subtotal: number
  peopleCount: number
}

/** Read-only digital receipt: lists selected lines, the total and the
 * per-person split. */
export function ReceiptPreview({
  lines,
  currency,
  subtotal,
  peopleCount,
}: ReceiptPreviewProps) {
  return (
    <section className="mt-6 rounded-[8px] border border-primary-dark/30 bg-canvas p-5">
      <div className="mb-4 flex items-center gap-2 text-primary-dark">
        <ReceiptText className="size-5" aria-hidden />
        <h2 className="mb-0 text-[20px] font-bold">Digital Receipt</h2>
      </div>
      <div className="divide-y divide-hairline">
        {lines.map(({ item, state }) => (
          <div key={item.id} className="flex items-start justify-between gap-4 py-3">
            <div className="min-w-0">
              <p className="mb-0 truncate text-[15px] font-bold text-ink">
                {state.quantity} ×{' '}
                <ItemDisplayName
                  item={item}
                  originalClassName="text-[13px] text-ink-variant/40"
                />
              </p>
              {state.note && (
                <p className="mb-0 mt-1 text-[13px] text-ink-variant">{state.note}</p>
              )}
            </div>
            <span className="shrink-0 text-[15px] font-bold text-primary-dark">
              {formatMoney(itemPrice(item) * state.quantity, item.currency ?? currency)}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-col gap-2 border-t border-hairline pt-4 text-[15px] sm:items-end">
        <strong className="text-primary-dark">
          Total: {formatMoney(subtotal, currency)}
        </strong>
        <span className="text-ink-variant">
          Per person: {formatMoney(subtotal / Math.max(1, peopleCount), currency)}
        </span>
      </div>
    </section>
  )
}
