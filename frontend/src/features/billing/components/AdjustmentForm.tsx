import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import {
  ADJUSTMENT_TYPE_LABELS,
  type AdjustmentInput,
  type BillAdjustmentCalculationType,
  type BillAdjustmentType,
  type BillResponse,
} from '@/features/billing/types'

const ADJUSTMENT_TYPES: BillAdjustmentType[] = [
  'DISCOUNT',
  'SURCHARGE',
  'TAX',
  'SERVICE_CHARGE',
  'ROUNDING',
]

interface AdjustmentFormProps {
  /** Existing adjustment to prefill when editing; `null` when creating. */
  initial: BillResponse['adjustments'][number] | null
  onCancel: () => void
  onSubmit: (payload: AdjustmentInput) => Promise<void>
}

/** Inline create/edit form for a single bill adjustment. Shared by the
 * "Thêm phí / giảm giá" and "Sửa" actions in `AdjustmentsSection`. */
export function AdjustmentForm({ initial, onCancel, onSubmit }: AdjustmentFormProps) {
  const [type, setType] = useState<BillAdjustmentType>(initial?.type ?? 'SERVICE_CHARGE')
  const [calcType, setCalcType] = useState<BillAdjustmentCalculationType>(
    initial?.calculation_type ?? 'PERCENTAGE',
  )
  const [label, setLabel] = useState(initial?.label ?? 'Phí dịch vụ')
  const [value, setValue] = useState(initial?.value ?? '')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const validate = (): string | null => {
    if (!label.trim()) return 'Vui lòng nhập nhãn hiển thị.'
    if (value.trim() === '') return 'Vui lòng nhập giá trị.'
    const num = Number(value)
    if (!Number.isFinite(num) || num < 0) return 'Giá trị phải là số không âm.'
    if (calcType === 'PERCENTAGE' && num > 100) return 'Phần trăm phải từ 0 đến 100.'
    return null
  }

  const handleSubmit = async () => {
    const error = validate()
    if (error) {
      setFieldError(error)
      return
    }
    setFieldError(null)
    setSubmitting(true)
    try {
      await onSubmit({ type, calculation_type: calcType, label: label.trim(), value })
    } catch {
      // Error surface is owned by the sync hook (syncError banner); keep the
      // form open so the person can retry without re-typing.
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-[8px] bg-surface-muted p-2.5">
      <div className="flex gap-2">
        <select
          value={type}
          onChange={(e) => setType(e.target.value as BillAdjustmentType)}
          className="min-w-0 flex-1 rounded-[6px] border border-hairline bg-canvas px-2 py-1.5 text-[13px]"
        >
          {ADJUSTMENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {ADJUSTMENT_TYPE_LABELS[t]}
            </option>
          ))}
        </select>
        <select
          value={calcType}
          onChange={(e) => setCalcType(e.target.value as BillAdjustmentCalculationType)}
          className="min-w-0 flex-1 rounded-[6px] border border-hairline bg-canvas px-2 py-1.5 text-[13px]"
        >
          <option value="FIXED">Số tiền</option>
          <option value="PERCENTAGE">Phần trăm</option>
        </select>
      </div>
      <input
        type="text"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        placeholder="Nhãn hiển thị, ví dụ 'Phí dịch vụ'"
        className="rounded-[6px] border border-hairline bg-canvas px-2 py-1.5 text-[13px]"
      />
      <input
        type="number"
        inputMode="decimal"
        min={0}
        max={calcType === 'PERCENTAGE' ? 100 : undefined}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={calcType === 'PERCENTAGE' ? '0-100 (%)' : 'Số tiền'}
        className="rounded-[6px] border border-hairline bg-canvas px-2 py-1.5 text-[13px]"
      />
      {fieldError && (
        <span role="alert" className="text-[12px] text-destructive">
          {fieldError}
        </span>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={submitting}
          onClick={() => void handleSubmit()}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-[6px] bg-primary-dark px-3 py-1.5 text-[13px] font-semibold text-white disabled:opacity-60"
        >
          {submitting && <Loader2 className="size-3.5 animate-spin" aria-hidden />}
          {initial ? 'Lưu thay đổi' : 'Thêm'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 rounded-[6px] border border-hairline px-3 py-1.5 text-[13px] font-medium text-ink-variant"
        >
          Hủy
        </button>
      </div>
    </div>
  )
}