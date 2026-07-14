import { CheckCircle2, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/ui/button'

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
    <div className="flex min-h-[190px] flex-col gap-4 rounded-2xl border-2 border-dashed border-primary/60 bg-surface p-5 shadow-1">
      <div className="grid grid-cols-[minmax(0,1fr)_120px]">
        <input
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          placeholder={t('manualItem.name')}
          className="h-11 rounded-l-xl border border-hairline bg-surface px-3 text-[14px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
        />
        <input
          value={price}
          onChange={(event) => onPriceChange(event.target.value)}
          placeholder={t('manualItem.price')}
          inputMode="decimal"
          className="h-11 rounded-r-xl border border-l-0 border-hairline bg-surface px-3 text-right text-[14px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
        />
      </div>
      <textarea
        value={note}
        onChange={(event) => onNoteChange(event.target.value)}
        placeholder={t('manualItem.note')}
        className="min-h-[74px] resize-none rounded-xl border border-hairline bg-panel px-3 py-2 text-[14px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
      />
      <Button
        type="button"
        variant="default"
        size="sm"
        onClick={onSave}
        disabled={saving || !name.trim() || !Number.isFinite(Number(price))}
        className="ml-auto"
      >
        {saving ? (
          <Loader2 className="size-4 animate-spin" aria-hidden />
        ) : (
          <CheckCircle2 className="size-4" aria-hidden />
        )}
        {t('manualItem.save')}
      </Button>
    </div>
  )
}
