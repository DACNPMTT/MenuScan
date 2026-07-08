import { CheckCircle2, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export interface ManualItemCardProps {
  name: string
  price: string
  note: string
  saving: boolean
  onNameChange: (value: string) => void
  onPriceChange: (value: string) => void
  onNoteChange: (value: string) => void
  onSave: () => void
}

/** Inline form to add a new item to the menu by hand. */
export function ManualItemCard({
  name,
  price,
  note,
  saving,
  onNameChange,
  onPriceChange,
  onNoteChange,
  onSave,
}: ManualItemCardProps) {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-[190px] flex-col gap-4 rounded-[8px] border border-dashed border-primary-dark/70 bg-canvas/70 p-5">
      <div className="grid grid-cols-[minmax(0,1fr)_120px]">
        <input
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          placeholder={t('manualItem.name')}
          className="h-11 rounded-l-[6px] border border-hairline bg-white px-3 text-[14px] outline-none placeholder:text-placeholder focus:border-primary-dark"
        />
        <input
          value={price}
          onChange={(event) => onPriceChange(event.target.value)}
          placeholder={t('manualItem.price')}
          inputMode="decimal"
          className="h-11 rounded-r-[6px] border border-l-0 border-hairline bg-white px-3 text-right text-[14px] outline-none placeholder:text-placeholder focus:border-primary-dark"
        />
      </div>
      <textarea
        value={note}
        onChange={(event) => onNoteChange(event.target.value)}
        placeholder={t('manualItem.note')}
        className="min-h-[74px] resize-none rounded-[8px] border border-hairline bg-surface-muted px-3 py-2 text-[14px] outline-none placeholder:text-placeholder focus:border-primary-dark"
      />
      <button
        type="button"
        onClick={onSave}
        disabled={saving || !name.trim() || !Number.isFinite(Number(price))}
        className="ml-auto flex min-h-9 items-center gap-2 rounded-[8px] px-3 text-[13px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? (
          <Loader2 className="size-4 animate-spin" aria-hidden />
        ) : (
          <CheckCircle2 className="size-4" aria-hidden />
        )}
        {t('manualItem.save')}
      </button>
    </div>
  )
}
