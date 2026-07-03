/** Format a decimal-string/number amount for display, VND-aware like the
 * rest of the scan result screen (see `ScanResultPage.formatPrice`). */
export function formatMoney(amount: string | number, currency: string | null): string {
  const num = typeof amount === 'number' ? amount : Number(amount)
  if (!Number.isFinite(num)) return String(amount)
  const isVnd = (currency ?? '').toUpperCase() === 'VND'
  const formatted = isVnd ? Math.round(num).toLocaleString('vi-VN') : num.toFixed(2)
  return isVnd ? `${formatted} ₫` : `${formatted} ${currency ?? ''}`.trim()
}