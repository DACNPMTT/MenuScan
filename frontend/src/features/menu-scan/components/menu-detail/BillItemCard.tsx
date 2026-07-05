import { AlertCircle, Loader2, Minus, Pencil, Plus, RotateCcw, Save, Trash2 } from 'lucide-react'
import { ItemDisplayName } from '@/features/menu-scan/components/menu-detail/ItemDisplayName'
import {
  LOW_CONFIDENCE_THRESHOLD,
  confidenceValue,
  hasAllergySignal,
  itemCategory,
  itemPrice,
} from '@/features/menu-scan/lib'
import { formatConvertedAmount, type ExchangeRates } from '@/shared/lib/currency'
import type {
  BillItem,
  BillLineState,
  ItemDraft,
  ItemValidationErrors,
} from '@/features/menu-scan/types'

export interface BillItemCardProps {
  item: BillItem
  draft: ItemDraft
  editing: boolean
  dirty: boolean
  line: BillLineState
  currency: string | null
  displayCurrency: string
  rates: ExchangeRates | null
  validationErrors: ItemValidationErrors
  saveError: string | null
  saving: boolean
  deleting: boolean
  onDraftChange: (patch: Partial<ItemDraft>) => void
  onEdit: () => void
  onSave: () => void
  onCancel: () => void
  onDelete: () => void
  onQuantityChange: (quantity: number) => void
  onNoteChange: (note: string) => void
}

/** A single menu item card: read-only display or inline editor, plus the
 * quantity / note bill-line controls pinned to the bottom. */
export function BillItemCard({
  item,
  draft,
  editing,
  dirty,
  line,
  currency,
  displayCurrency,
  rates,
  validationErrors,
  saveError,
  saving,
  deleting,
  onDraftChange,
  onEdit,
  onSave,
  onCancel,
  onDelete,
  onQuantityChange,
  onNoteChange,
}: BillItemCardProps) {
  const confidence = confidenceValue(item)
  const lowConfidenceLabel =
    confidence !== null && confidence < LOW_CONFIDENCE_THRESHOLD
      ? Math.round(confidence * 100)
      : null
  const priceCurrency = draft.currency.trim() || item.currency || currency || ''
  const category = itemCategory(item)
  const hasTranslatedDescription =
    item.translated_description &&
    item.translated_description !== item.original_description
  const primaryDescription =
    item.translated_description || item.original_description || null
  const secondaryDescription = hasTranslatedDescription
    ? item.original_description
    : null

  return (
    <article className="flex min-h-[190px] flex-col gap-3 rounded-[8px] border border-hairline bg-canvas p-5">
      {hasAllergySignal(item) && (
        <div className="flex items-center gap-2 rounded-[6px] bg-destructive px-3 py-1.5 text-[12px] font-bold text-white">
          <AlertCircle className="size-3.5" aria-hidden />
          WARNING: Allergy Match Found (Seafood)
        </div>
      )}
      {lowConfidenceLabel !== null && (
        <div className="flex items-center gap-2 rounded-[6px] border border-[#d7a315]/40 bg-[#fff8e2] px-3 py-1.5 text-[12px] font-bold text-[#80600d]">
          <AlertCircle className="size-3.5" aria-hidden />
          OCR confidence thấp ({lowConfidenceLabel}%).
        </div>
      )}
      {saveError && (
        <div className="flex items-center gap-2 rounded-[6px] border border-destructive/30 bg-destructive/5 px-3 py-2 text-[13px] font-medium text-destructive">
          <AlertCircle className="size-3.5" aria-hidden />
          {saveError}
        </div>
      )}

      {editing ? (
        <>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_140px]">
            <label className="min-w-0">
              <span className="sr-only">Tên món</span>
              <input
                value={draft.translated_name}
                onChange={(event) =>
                  onDraftChange({ translated_name: event.target.value })
                }
                placeholder="Tên món"
                className="h-10 w-full rounded-t-[8px] border border-hairline bg-white px-3 text-[17px] font-bold text-primary-dark outline-none placeholder:text-placeholder focus:border-primary-dark"
              />
              <div className="flex items-center rounded-b-[8px] border border-t-0 border-hairline bg-surface-muted px-3">
                <span className="shrink-0 text-[14px] font-bold text-ink-variant/40">
                  (
                </span>
                <input
                  value={draft.original_name}
                  onChange={(event) =>
                    onDraftChange({ original_name: event.target.value })
                  }
                  placeholder="Tên trên ảnh"
                  className="h-9 min-w-0 flex-1 bg-transparent text-[14px] font-medium text-ink-variant/45 outline-none placeholder:text-placeholder/60"
                />
                <span className="shrink-0 text-[14px] font-bold text-ink-variant/40">
                  )
                </span>
              </div>
              {validationErrors.original_name && (
                <p className="mb-0 mt-1 text-[12px] font-medium text-destructive">
                  {validationErrors.original_name}
                </p>
              )}
            </label>
            <label>
              <span className="sr-only">Giá</span>
              <div className="flex h-10 overflow-hidden rounded-[8px] border border-hairline bg-white focus-within:border-primary-dark">
                <input
                  value={draft.price}
                  onChange={(event) => onDraftChange({ price: event.target.value })}
                  placeholder="Price"
                  inputMode="decimal"
                  className="min-w-0 flex-1 px-3 text-right text-[15px] font-bold text-primary-dark outline-none placeholder:text-placeholder"
                />
                {priceCurrency && (
                  <span className="flex items-center border-l border-hairline bg-surface-muted px-2 text-[12px] font-bold text-primary-dark">
                    {priceCurrency}
                  </span>
                )}
              </div>
              {validationErrors.price && (
                <p className="mb-0 mt-1 text-[12px] font-medium text-destructive">
                  {validationErrors.price}
                </p>
              )}
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_130px]">
            <input
              value={draft.category}
              onChange={(event) => onDraftChange({ category: event.target.value })}
              placeholder="Category"
              className="h-9 rounded-[8px] border border-hairline bg-surface-muted px-3 text-[13px] font-medium text-primary-dark outline-none placeholder:text-placeholder focus:border-primary-dark"
            />
            <input
              value={draft.currency}
              onChange={(event) => onDraftChange({ currency: event.target.value })}
              placeholder="Currency"
              maxLength={3}
              className="h-9 rounded-[8px] border border-hairline bg-surface-muted px-3 text-[13px] font-medium uppercase text-primary-dark outline-none placeholder:text-placeholder focus:border-primary-dark"
            />
          </div>

          <div className="grid gap-2">
            <textarea
              value={draft.translated_description}
              onChange={(event) =>
                onDraftChange({ translated_description: event.target.value })
              }
              placeholder="Mô tả"
              className="min-h-[70px] resize-none rounded-[8px] border border-hairline bg-white px-3 py-2 text-[14px] leading-6 text-ink outline-none placeholder:text-placeholder focus:border-primary-dark"
            />
            <textarea
              value={draft.original_description}
              onChange={(event) =>
                onDraftChange({ original_description: event.target.value })
              }
              placeholder="Mô tả trên ảnh"
              className="min-h-[54px] resize-none rounded-[8px] border border-hairline bg-surface-muted px-3 py-2 text-[13px] leading-5 text-ink-variant/55 outline-none placeholder:text-placeholder/60 focus:border-primary-dark"
            />
          </div>

          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              onClick={onDelete}
              disabled={deleting || saving}
              className="flex min-h-9 items-center gap-2 rounded-[8px] border border-destructive/30 px-3 text-[13px] font-bold text-destructive transition-colors hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {deleting ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Trash2 className="size-4" aria-hidden />
              )}
              Xóa
            </button>
            <button
              type="button"
              onClick={onCancel}
              disabled={saving || deleting}
              className="flex min-h-9 items-center gap-2 rounded-[8px] border border-hairline px-3 text-[13px] font-bold text-ink transition-colors hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RotateCcw className="size-4" aria-hidden />
              Cancel
            </button>
            <button
              type="button"
              onClick={onSave}
              disabled={!dirty || saving || deleting}
              className="flex min-h-9 items-center gap-2 rounded-[8px] bg-primary-dark px-3 text-[13px] font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Save className="size-4" aria-hidden />
              )}
              Save
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h2 className="mb-1 text-[19px] font-bold leading-[25px] text-primary-dark">
                <ItemDisplayName
                  item={item}
                  originalClassName="text-[14px] text-ink-variant/40"
                />
              </h2>
              <span className="rounded-[4px] border border-primary-dark/30 bg-surface-muted px-2 py-0.5 text-[11px] font-medium text-primary-dark">
                {category}
              </span>
            </div>
            <div className="flex shrink-0 items-start gap-2">
              <strong className="pt-1 text-[17px] text-primary-dark">
                {formatConvertedAmount(
                  itemPrice(item),
                  item.currency ?? currency ?? 'VND',
                  displayCurrency,
                  rates,
                )}
              </strong>
              <button
                type="button"
                onClick={onEdit}
                className="flex size-9 items-center justify-center rounded-[8px] border border-hairline text-primary-dark transition-colors hover:bg-primary/10"
                aria-label={`Sửa ${item.original_name}`}
                title="Edit"
              >
                <Pencil className="size-4" aria-hidden />
              </button>
            </div>
          </div>
          {primaryDescription && (
            <div className="flex flex-col gap-1.5">
              <p className="mb-0 text-[14px] leading-6 text-ink-variant">
                {primaryDescription}
              </p>
              {secondaryDescription && (
                <p className="mb-0 border-l-2 border-hairline pl-3 text-[13px] leading-5 text-ink-variant/45">
                  {secondaryDescription}
                </p>
              )}
            </div>
          )}
        </>
      )}

      <div className="mt-auto flex items-center gap-0 border-t border-hairline pt-3">
        <div className="flex h-9 shrink-0 items-center overflow-hidden rounded-[8px] border border-primary-dark">
          <button
            type="button"
            onClick={() => onQuantityChange(line.quantity - 1)}
            className="flex size-9 items-center justify-center text-primary-dark transition-colors hover:bg-primary/10"
            aria-label={`Giảm ${item.original_name}`}
          >
            <Minus className="size-4" aria-hidden />
          </button>
          <span className="flex h-9 min-w-8 items-center justify-center text-[14px] font-bold text-ink">
            {line.quantity}
          </span>
          <button
            type="button"
            onClick={() => onQuantityChange(line.quantity + 1)}
            className="flex size-9 items-center justify-center text-primary-dark transition-colors hover:bg-primary/10"
            aria-label={`Tăng ${item.original_name}`}
          >
            <Plus className="size-4" aria-hidden />
          </button>
        </div>
        <input
          value={line.note}
          onChange={(event) => onNoteChange(event.target.value)}
          placeholder="Add note..."
          className="h-9 min-w-0 flex-1 rounded-r-[8px] border border-l-0 border-hairline bg-surface-muted px-3 text-[13px] text-ink outline-none placeholder:text-placeholder focus:border-primary-dark"
        />
      </div>
    </article>
  )
}
