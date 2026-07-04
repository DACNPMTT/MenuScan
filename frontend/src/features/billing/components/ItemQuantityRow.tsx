import { Minus, Plus } from 'lucide-react'
import type { MenuItemResult } from '@/features/menu-scan/types'
import { formatMoney } from '@/features/billing/format'

interface ItemQuantityRowProps {
  item: MenuItemResult
  quantity: number
  disabled: boolean
  onChange: (quantity: number) => void
}

export function ItemQuantityRow({ item, quantity, disabled, onChange }: ItemQuantityRowProps) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-[12px] border border-hairline bg-canvas p-3">
      <div className="flex min-w-0 flex-col">
        <span className="truncate text-[15px] font-semibold text-ink">
          {item.translated_name || item.original_name}
        </span>
        <span className="text-[13px] text-ink-variant">
          {formatMoney(item.price ?? '0', item.currency)}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          disabled={disabled || quantity <= 0}
          onClick={() => onChange(Math.max(0, quantity - 1))}
          className="flex size-8 items-center justify-center rounded-full border border-hairline text-ink transition-colors hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40"
          aria-label={`Giảm số lượng ${item.original_name}`}
        >
          <Minus className="size-4" aria-hidden />
        </button>
        <span className="w-6 text-center text-[15px] font-medium text-ink" aria-live="polite">
          {quantity}
        </span>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange(quantity + 1)}
          className="flex size-8 items-center justify-center rounded-full border border-hairline text-ink transition-colors hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40"
          aria-label={`Tăng số lượng ${item.original_name}`}
        >
          <Plus className="size-4" aria-hidden />
        </button>
      </div>
    </div>
  )
}