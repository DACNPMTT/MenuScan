import { Coins } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { CURRENCY_OPTIONS } from '@/shared/lib/currency'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'

interface CurrencySelectProps {
  value: string
  onChange: (currency: string) => void
  disabled?: boolean
}

/** Small currency picker used to display-convert prices on the scan result and
 * menu detail pages. */
export function CurrencySelect({ value, onChange, disabled }: CurrencySelectProps) {
  const { t } = useTranslation()
  return (
    <label className="flex items-center gap-2 text-[14px] font-medium text-ink">
      <Coins className="size-4 text-primary-dark" aria-hidden />
      <span className="whitespace-nowrap">{t('currencySelect.label')}</span>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger
          aria-label={t('currencySelect.changeAria')}
          className="h-9 w-auto gap-2 rounded-[8px] border border-hairline bg-white px-2 text-[14px] text-ink"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {CURRENCY_OPTIONS.map((option) => (
            <SelectItem key={option.code} value={option.code}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  )
}
