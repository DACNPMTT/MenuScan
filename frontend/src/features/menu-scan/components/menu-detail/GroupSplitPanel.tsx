import { useTranslation } from 'react-i18next'
import { Receipt, Users } from 'lucide-react'
import { formatConvertedAmount, type ExchangeRates } from '@/shared/lib/currency'

/** One person's slice of the bill, already computed by the caller. */
export interface PayerView {
  key: string
  name: string
  lineItems: { name: string; quantity: number; amount: number }[]
  foodSubtotal: number
  feeShare: number
  total: number
}

interface GroupSplitPanelProps {
  payers: PayerView[]
  /** The host's own ticked dishes, needing an owner when splitting per person. */
  hostOwnItems: { id: string; name: string; quantity: number; amount: number }[]
  guestParticipants: { id: string; name: string }[]
  assignments: Record<string, string>
  onAssign: (itemId: string, value: string) => void
  currency: string
  displayCurrency: string
  rates: ExchangeRates | null
}

/** Per-person split view: who owes what once each guest's picks, the host's own
 * dishes (assigned here) and the equally-shared fees are added up. Pure display —
 * the numbers arrive already computed in the bill's currency. */
export function GroupSplitPanel({
  payers,
  hostOwnItems,
  guestParticipants,
  assignments,
  onAssign,
  currency,
  displayCurrency,
  rates,
}: GroupSplitPanelProps) {
  const { t } = useTranslation()
  const money = (amount: number) =>
    formatConvertedAmount(amount, currency, displayCurrency, rates)

  return (
    <div className="flex flex-col gap-4">
      {hostOwnItems.length > 0 && (
        <div className="rounded-2xl border border-border bg-panel/60 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-[13px] font-bold text-ink">
            <Receipt className="size-4 text-primary-dark" aria-hidden />
            {t('menuDetail.split.assignTitle')}
          </p>
          <div className="flex flex-col gap-2">
            {hostOwnItems.map((item) => (
              <div
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-surface px-3 py-2"
              >
                <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-ink">
                  {item.quantity} x {item.name}
                  <span className="ml-1 text-[12px] font-normal text-ink-variant">
                    ({money(item.amount)})
                  </span>
                </span>
                <select
                  value={assignments[item.id] ?? 'SPLIT'}
                  onChange={(event) => onAssign(item.id, event.target.value)}
                  className="h-8 shrink-0 rounded-lg border border-border bg-canvas px-2 text-[12px] font-semibold text-ink outline-none focus:border-primary"
                >
                  <option value="SPLIT">{t('menuDetail.split.shared')}</option>
                  <option value="HOST">{t('menuDetail.split.hostPays')}</option>
                  {guestParticipants.map((guest) => (
                    <option key={guest.id} value={guest.id}>
                      {guest.name}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {payers.map((payer) => (
          <div
            key={payer.key}
            className="flex flex-col gap-2 rounded-2xl border border-border bg-surface p-4 shadow-1"
          >
            <div className="flex items-center justify-between gap-2 border-b border-hairline pb-2">
              <span className="flex items-center gap-1.5 text-[14px] font-bold text-ink">
                <Users className="size-4 text-primary" aria-hidden />
                {payer.name}
              </span>
              <strong className="text-[16px] text-primary-dark">
                {money(payer.total)}
              </strong>
            </div>

            {payer.lineItems.length > 0 ? (
              <div className="flex flex-col gap-1">
                {payer.lineItems.map((line, index) => (
                  <div
                    key={`${line.name}-${index}`}
                    className="flex items-start justify-between gap-2 text-[12px]"
                  >
                    <span className="min-w-0 truncate text-ink-variant">
                      {line.quantity} x {line.name}
                    </span>
                    <span className="shrink-0 text-ink">{money(line.amount)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mb-0 text-[12px] italic text-ink-variant">
                {t('menuDetail.split.noItems')}
              </p>
            )}

            <div className="mt-1 flex flex-col gap-1 border-t border-hairline pt-2 text-[12px]">
              <div className="flex justify-between text-ink-variant">
                <span>{t('menuDetail.subtotal')}</span>
                <span>{money(payer.foodSubtotal)}</span>
              </div>
              <div className="flex justify-between text-ink-variant">
                <span>{t('menuDetail.split.feeShare')}</span>
                <span>{money(payer.feeShare)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
