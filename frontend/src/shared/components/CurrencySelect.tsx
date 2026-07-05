import { Coins } from 'lucide-react'
import { CURRENCY_OPTIONS } from '@/shared/lib/currency'

interface CurrencySelectProps {
  value: string
  onChange: (currency: string) => void
  disabled?: boolean
}

/** Small currency picker used to display-convert prices on the scan result and
 * menu detail pages. */
export function CurrencySelect({ value, onChange, disabled }: CurrencySelectProps) {
  return (
    <label className="flex items-center gap-2 text-[14px] font-medium text-ink">
      <Coins className="size-4 text-primary-dark" aria-hidden />
      <span className="whitespace-nowrap">Tiền tệ</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        aria-label="Đổi tiền tệ hiển thị"
        className="h-9 rounded-[8px] border border-hairline bg-white px-2 text-[14px] text-ink outline-none focus:border-primary-dark disabled:opacity-50"
      >
        {CURRENCY_OPTIONS.map((option) => (
          <option key={option.code} value={option.code}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
