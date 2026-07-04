import { useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { formatMoney } from '@/features/billing/format'
import { AdjustmentForm } from '@/features/billing/components/AdjustmentForm'
import {
  ADJUSTMENT_TYPE_LABELS,
  type AdjustmentInput,
  type BillResponse,
} from '@/features/billing/types'

interface AdjustmentsSectionProps {
  adjustments: BillResponse['adjustments']
  currency: string | null
  disabled: boolean
  onAdd: (payload: AdjustmentInput) => Promise<void>
  onUpdate: (adjustmentId: string, payload: AdjustmentInput) => Promise<void>
  onRemove: (adjustmentId: string) => Promise<void>
}

type FormMode =
  | { kind: 'closed' }
  | { kind: 'create' }
  | { kind: 'edit'; adjustmentId: string }

/** Lists existing adjustments (discount/surcharge/tax/...) and toggles the
 * add/edit form (`AdjustmentForm`) for creating or editing one. */
export function AdjustmentsSection({
  adjustments,
  currency,
  disabled,
  onAdd,
  onUpdate,
  onRemove,
}: AdjustmentsSectionProps) {
  const [mode, setMode] = useState<FormMode>({ kind: 'closed' })

  const editingAdjustment =
    mode.kind === 'edit' ? adjustments.find((a) => a.id === mode.adjustmentId) ?? null : null

  return (
    <div className="flex flex-col gap-2 border-t border-hairline pt-3">
      {adjustments.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {adjustments.map((adj) => (
            <li key={adj.id} className="flex items-center justify-between gap-2 text-[13px]">
              <span className="truncate text-ink">
                {adj.label}
                <span className="ml-1 text-ink-variant">
                  ({ADJUSTMENT_TYPE_LABELS[adj.type]})
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="text-ink-variant">
                  {Number(adj.calculated_amount) < 0 ? '' : '+'}
                  {formatMoney(adj.calculated_amount, currency)}
                </span>
                {!disabled && (
                  <>
                    <button
                      type="button"
                      onClick={() => setMode({ kind: 'edit', adjustmentId: adj.id })}
                      className="text-ink-variant hover:text-primary-dark"
                      aria-label={`Sửa điều chỉnh ${adj.label}`}
                    >
                      <Pencil className="size-3.5" aria-hidden />
                    </button>
                    <button
                      type="button"
                      onClick={() => void onRemove(adj.id)}
                      className="text-destructive hover:opacity-70"
                      aria-label={`Xóa điều chỉnh ${adj.label}`}
                    >
                      <Trash2 className="size-3.5" aria-hidden />
                    </button>
                  </>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}

      {!disabled &&
        (mode.kind === 'closed' ? (
          <button
            type="button"
            onClick={() => setMode({ kind: 'create' })}
            className="flex w-fit items-center gap-1.5 text-[13px] font-semibold text-primary-dark hover:opacity-80"
          >
            <Plus className="size-3.5" aria-hidden />
            Thêm phí / giảm giá
          </button>
        ) : (
          <AdjustmentForm
            key={mode.kind === 'edit' ? mode.adjustmentId : 'create'}
            initial={editingAdjustment}
            onCancel={() => setMode({ kind: 'closed' })}
            onSubmit={async (payload) => {
              if (mode.kind === 'edit') {
                await onUpdate(mode.adjustmentId, payload)
              } else {
                await onAdd(payload)
              }
              setMode({ kind: 'closed' })
            }}
          />
        ))}
    </div>
  )
}