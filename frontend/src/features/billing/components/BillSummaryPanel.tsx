import { AlertCircle, CheckCircle2, Loader2, Lock, Minus, Plus, Users } from 'lucide-react'
import { formatMoney } from '@/features/billing/format'
import { AdjustmentsSection } from '@/features/billing/components/AdjustmentsSection'
import type { AdjustmentInput, BillResponse } from '@/features/billing/types'

interface BillSummaryPanelProps {
  bill: BillResponse | null
  currency: string | null
  numPeople: number
  onNumPeopleChange: (n: number) => void
  syncing: boolean
  syncError: string | null
  hasSelection: boolean
  isFinalized: boolean
  onFinalize: () => void
  onRetrySync: () => void
  onAddAdjustment: (payload: AdjustmentInput) => Promise<void>
  onUpdateAdjustment: (adjustmentId: string, payload: AdjustmentInput) => Promise<void>
  onRemoveAdjustment: (adjustmentId: string) => Promise<void>
}

/** The sticky right-hand "digital order ticket" — mirrors the Figma bill
 * summary: line items, adjustments, subtotal/total, per-person split. */
export function BillSummaryPanel({
  bill,
  currency,
  numPeople,
  onNumPeopleChange,
  syncing,
  syncError,
  hasSelection,
  isFinalized,
  onFinalize,
  onRetrySync,
  onAddAdjustment,
  onUpdateAdjustment,
  onRemoveAdjustment,
}: BillSummaryPanelProps) {
  const billCurrency = bill?.currency ?? currency
  const total = bill ? Number(bill.total_amount) : 0
  const perPerson = numPeople > 0 ? total / numPeople : total

  return (
    <div className="flex h-fit flex-col gap-4 rounded-[12px] border border-hairline bg-canvas p-4 lg:sticky lg:top-[20px]">
      <div className="flex items-center justify-between">
        <h2 className="text-[15px] font-bold text-primary-dark">Hóa đơn</h2>
        {isFinalized ? (
          <span className="flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-[12px] font-medium text-primary-dark">
            <CheckCircle2 className="size-3.5" aria-hidden />
            Đã chốt
          </span>
        ) : (
          syncing && (
            <span className="flex items-center gap-1.5 text-[12px] text-ink-variant">
              <Loader2 className="size-3.5 animate-spin" aria-hidden />
              Đang cập nhật...
            </span>
          )
        )}
      </div>

      {syncError && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-[8px] border border-destructive/30 bg-destructive/5 px-3 py-2 text-[13px] text-destructive"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <div className="flex flex-col gap-1">
            <span>{syncError}</span>
            <button
              type="button"
              onClick={onRetrySync}
              className="w-fit text-[12px] font-semibold underline underline-offset-2"
            >
              Thử lại
            </button>
          </div>
        </div>
      )}

      {!bill || bill.items.length === 0 ? (
        <p className="text-[13px] text-ink-variant">
          Chọn món ở danh sách bên trái để bắt đầu chia hóa đơn.
        </p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {bill.items.map((line) => (
            <li key={line.id} className="flex items-center justify-between gap-2 text-[13px]">
              <span className="truncate text-ink">
                {line.quantity}× {line.name_snapshot}
              </span>
              <span className="shrink-0 text-ink-variant">
                {formatMoney(line.line_total, line.currency)}
              </span>
            </li>
          ))}
        </ul>
      )}

      <AdjustmentsSection
        adjustments={bill?.adjustments ?? []}
        currency={billCurrency}
        disabled={!bill || isFinalized}
        onAdd={onAddAdjustment}
        onUpdate={onUpdateAdjustment}
        onRemove={onRemoveAdjustment}
      />

      <div className="flex flex-col gap-1 border-t border-hairline pt-3 text-[14px]">
        <div className="flex justify-between text-ink-variant">
          <span>Tạm tính</span>
          <span>{formatMoney(bill?.subtotal_amount ?? '0', billCurrency)}</span>
        </div>
        <div className="flex justify-between text-ink-variant">
          <span>Điều chỉnh</span>
          <span>{formatMoney(bill?.adjustment_total ?? '0', billCurrency)}</span>
        </div>
        <div className="flex justify-between text-[16px] font-bold text-primary-dark">
          <span>Tổng cộng</span>
          <span>{formatMoney(bill?.total_amount ?? '0', billCurrency)}</span>
        </div>
      </div>

      <div className="flex flex-col gap-2 border-t border-hairline pt-3">
        <label className="flex items-center justify-between text-[13px] font-medium text-ink">
          <span className="flex items-center gap-1.5">
            <Users className="size-4" aria-hidden />
            Số người chia
          </span>
          <span className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onNumPeopleChange(Math.max(1, numPeople - 1))}
              className="flex size-7 items-center justify-center rounded-full border border-hairline hover:bg-surface-muted"
              aria-label="Giảm số người"
            >
              <Minus className="size-3.5" aria-hidden />
            </button>
            <span className="w-5 text-center">{numPeople}</span>
            <button
              type="button"
              onClick={() => onNumPeopleChange(numPeople + 1)}
              className="flex size-7 items-center justify-center rounded-full border border-hairline hover:bg-surface-muted"
              aria-label="Tăng số người"
            >
              <Plus className="size-3.5" aria-hidden />
            </button>
          </span>
        </label>
        <div className="flex justify-between rounded-[8px] bg-primary/10 px-3 py-2 text-[14px] font-semibold text-primary-dark">
          <span>Mỗi người trả</span>
          <span>{formatMoney(perPerson, billCurrency)}</span>
        </div>
      </div>

      {!isFinalized && (
        <button
          type="button"
          disabled={!bill || !hasSelection || syncing || bill.items.length === 0}
          onClick={onFinalize}
          className="mt-1 flex w-full items-center justify-center gap-2 rounded-[8px] bg-primary-dark px-4 py-2.5 text-[14px] font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {syncing ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <Lock className="size-4" aria-hidden />
          )}
          Chốt hóa đơn
        </button>
      )}
    </div>
  )
}