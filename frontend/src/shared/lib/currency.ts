/** Currency options + display-only conversion helpers.
 *
 * Rates come from `GET /api/v1/exchange-rates?base=<base>` and are keyed by
 * currency code relative to `base` (rates[base] === 1). Conversion is purely
 * for display; stored prices are never modified. */

export interface CurrencyOption {
  code: string
  label: string
}

export const CURRENCY_OPTIONS: readonly CurrencyOption[] = [
  { code: 'VND', label: '🇻🇳 VND (₫)' },
  { code: 'USD', label: '🇺🇸 USD ($)' },
  { code: 'EUR', label: '🇪🇺 EUR (€)' },
  { code: 'JPY', label: '🇯🇵 JPY (¥)' },
  { code: 'KRW', label: '🇰🇷 KRW (₩)' },
  { code: 'CNY', label: '🇨🇳 CNY (¥)' },
  { code: 'THB', label: '🇹🇭 THB (฿)' },
  { code: 'GBP', label: '🇬🇧 GBP (£)' },
] as const

export type ExchangeRates = Record<string, number>

/** Convert `amount` from `from` currency to `to` currency using `rates`
 * (relative to any single base). Returns null when a needed rate is missing so
 * callers can fall back to showing the original currency. */
export function convertAmount(
  amount: number,
  from: string,
  to: string,
  rates: ExchangeRates | null,
): number | null {
  if (from === to) return amount
  if (!rates) return null
  const rateFrom = rates[from]
  const rateTo = rates[to]
  if (!rateFrom || !rateTo) return null
  return (amount * rateTo) / rateFrom
}

/** Format a numeric amount in the given currency. VND is rounded with a
 * localized grouping + ₫; other currencies use Intl currency formatting. */
export function formatCurrency(amount: number, currency: string): string {
  if (currency === 'VND') {
    return `${Math.round(amount).toLocaleString('vi-VN')}₫`
  }
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return `${amount.toFixed(2)} ${currency}`
  }
}

/** Format an amount (in `sourceCurrency`) for display in `displayCurrency`.
 * Falls back to the source currency when the rate is unavailable. */
export function formatConvertedAmount(
  amount: number,
  sourceCurrency: string | null,
  displayCurrency: string,
  rates: ExchangeRates | null,
): string {
  const source = sourceCurrency ?? 'VND'
  const converted = convertAmount(amount, source, displayCurrency, rates)
  if (converted === null) return formatCurrency(amount, source)
  return formatCurrency(converted, displayCurrency)
}
