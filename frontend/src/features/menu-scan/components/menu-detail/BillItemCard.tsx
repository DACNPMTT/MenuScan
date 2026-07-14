
import {
  AlertCircle,
  AlertTriangle,
  Loader2,
  Minus,
  Pencil,
  Plus,
  RotateCcw,
  Save,
  ShieldCheck,
  Trash2,
} from 'lucide-react'

import { useTranslation } from 'react-i18next'
import { ItemDisplayName } from '@/features/menu-scan/components/menu-detail/ItemDisplayName'
import {
  LOW_CONFIDENCE_THRESHOLD,
  confidenceValue,
  itemCategory,
  itemPrice,
} from '@/features/menu-scan/lib'
import { assessDish, type DietProfile } from '@/features/menu-scan/dietary'
import { formatConvertedAmount, type ExchangeRates } from '@/shared/lib/currency'
import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/components/ui/button'
import type {
  BillItem,
  BillLineState,
  ItemDraft,
  ItemValidationErrors,
} from '@/features/menu-scan/types'

export interface BillItemCardProps {
  item: BillItem
  dietProfile: DietProfile
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

/** Compact menu item card for the menu overview.
 *
 * There is no "see full details" view any more. The assistant covers that: a dish
 * has too many things worth asking about (what's in it, how spicy, can I eat it)
 * to enumerate on a card, and a chat can answer the one the diner actually cares
 * about instead of printing all of them. */
export function BillItemCard({
  item,
  dietProfile,
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
  const { t } = useTranslation()
  const risk = assessDish(item, dietProfile)
  const confidence = confidenceValue(item)
  const lowConfidenceLabel =
    confidence !== null && confidence < LOW_CONFIDENCE_THRESHOLD
      ? Math.round(confidence * 100)
      : null
  const priceCurrency = draft.currency.trim() || item.currency || currency || ''
  const category = itemCategory(item)
  const summary =
    item.assistant_summary || item.translated_description || item.original_description
  const quickTags = uniqueCompact([
    ...item.main_ingredients,
    ...item.cooking_methods,
    ...item.flavor_tags,
  ]).slice(0, 4)
  const recommendation = item.recommendation
  const recommendationNote =
    recommendation?.why_not_suitable ||
    recommendation?.explanation ||
    recommendation?.why_suitable
  const recommendationFitTags = uniqueCompact([
    ...(recommendation?.suggested_for ?? []).map((name) => `Hợp: ${name}`),
    ...(recommendation?.fit_reasons ?? []),
  ]).slice(0, 3)
  const recommendationRiskTags = uniqueCompact([
    ...(recommendation?.warning_for ?? []).map((name) => `Tránh: ${name}`),
    ...(recommendation?.risk_reasons ?? []),
    ...(recommendation?.warning_reasons ?? []),
  ]).slice(0, 3)

  return (

    <article
      className={cn(
        'flex min-h-[260px] flex-col gap-3 rounded-2xl border p-5 shadow-1 transition-all duration-200 ease-[var(--ease-out-quint)] hover:-translate-y-1 hover:shadow-3',
        verdictCardClass(recommendation?.verdict ?? null),
      )}
    >
      {risk.allergens.length > 0 && (
        <div className="flex items-center gap-2 rounded-lg bg-destructive px-3 py-1.5 text-[12px] font-bold text-white">
          <AlertCircle className="size-3.5 shrink-0" aria-hidden />
          {t('billItem.allergyMatch', {
            list: risk.allergens.map((code) => t(`diet.allergens.${code}`)).join(', '),
          })}
        </div>
      )}
      {risk.dietFlags.length > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-amber/40 bg-amber/10 px-3 py-1.5 text-[12px] font-bold text-amber">
          <AlertTriangle className="size-3.5 shrink-0" aria-hidden />
          {t('billItem.dietMatch', {
            list: risk.dietFlags.map((code) => t(`diet.preferences.${code}`)).join(', '),
          })}

        </div>
      )}
      {lowConfidenceLabel !== null && (
        <div className="flex items-center gap-2 rounded-lg border border-amber/40 bg-amber/10 px-3 py-1.5 text-[12px] font-bold text-amber">
          <AlertCircle className="size-3.5" aria-hidden />
          {t('billItem.lowConfidence', { value: lowConfidenceLabel })}
        </div>
      )}
      {saveError && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-[13px] font-medium text-destructive">
          <AlertCircle className="size-3.5" aria-hidden />
          {saveError}
        </div>
      )}

      {editing ? (
        <>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_140px]">
            <label className="min-w-0">
              <span className="sr-only">{t('billItem.namePlaceholder')}</span>
              <input
                value={draft.translated_name}
                onChange={(event) =>
                  onDraftChange({ translated_name: event.target.value })
                }
                placeholder={t('billItem.namePlaceholder')}
                className="h-10 w-full rounded-t-xl border border-hairline bg-canvas px-3 text-[17px] font-bold text-primary-dark outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
              />
              <div className="flex items-center rounded-b-xl border border-t-0 border-hairline bg-surface-muted px-3">
                <span className="shrink-0 text-[14px] font-bold text-ink-variant/40">
                  (
                </span>
                <input
                  value={draft.original_name}
                  onChange={(event) =>
                    onDraftChange({ original_name: event.target.value })
                  }
                  placeholder={t('billItem.originalNamePlaceholder')}
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
              <span className="sr-only">{t('billItem.pricePlaceholder')}</span>
              <div className="flex h-10 overflow-hidden rounded-xl border border-hairline bg-canvas transition-colors focus-within:border-primary">
                <input
                  value={draft.price}
                  onChange={(event) => onDraftChange({ price: event.target.value })}
                  placeholder={t('billItem.pricePlaceholder')}
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
              placeholder={t('billItem.categoryPlaceholder')}
              className="h-9 rounded-xl border border-hairline bg-surface-muted px-3 text-[13px] font-medium text-primary-dark outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
            />
            <input
              value={draft.currency}
              onChange={(event) => onDraftChange({ currency: event.target.value })}
              placeholder={t('billItem.currencyPlaceholder')}
              maxLength={3}
              className="h-9 rounded-xl border border-hairline bg-surface-muted px-3 text-[13px] font-medium uppercase text-primary-dark outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="grid gap-2">
            <textarea
              value={draft.translated_description}
              onChange={(event) =>
                onDraftChange({ translated_description: event.target.value })
              }
              placeholder={t('billItem.descPlaceholder')}
              className="min-h-[70px] resize-none rounded-xl border border-hairline bg-canvas px-3 py-2 text-[14px] leading-6 text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
            />
            <textarea
              value={draft.original_description}
              onChange={(event) =>
                onDraftChange({ original_description: event.target.value })
              }
              placeholder={t('billItem.originalDescPlaceholder')}
              className="min-h-[54px] resize-none rounded-xl border border-hairline bg-surface-muted px-3 py-2 text-[13px] leading-5 text-ink-variant/55 outline-none transition-colors placeholder:text-placeholder/60 focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex flex-wrap justify-end gap-2">
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={onDelete}
              disabled={deleting || saving}
            >
              {deleting ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Trash2 className="size-4" aria-hidden />
              )}
              {t('common.delete')}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onCancel}
              disabled={saving || deleting}
            >
              <RotateCcw className="size-4" aria-hidden />
              {t('common.cancel')}
            </Button>
            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={onSave}
              disabled={!dirty || saving || deleting}
            >
              {saving ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Save className="size-4" aria-hidden />
              )}
              {t('common.save')}
            </Button>
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
              <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-primary-dark">
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
              <Button
                type="button"
                variant="outline"
                size="icon-sm"
                onClick={onEdit}
                aria-label={t('billItem.editAria', { name: item.original_name })}
                title={t('common.edit')}
              >
                <Pencil className="size-4" aria-hidden />
              </Button>
            </div>
          </div>

          {summary && (
            <p className="mb-0 line-clamp-2 text-[14px] leading-6 text-ink-variant">
              {summary}
            </p>
          )}

          {quickTags.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              {quickTags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-hairline bg-surface-muted px-2 py-1 text-[11px] font-semibold text-ink-variant"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {recommendation && (
            <div className="rounded-xl border border-hairline bg-surface-muted/60 px-3 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 text-[12px] font-bold text-ink-variant">
                  <ShieldCheck className="size-3.5 text-primary-dark" aria-hidden />
                  {t('billItem.recommendation')}
                </span>
                <span
                  className={`rounded-full px-2 py-1 text-[11px] font-bold ${verdictClass(recommendation.verdict)}`}
                >
                  {t(`billItem.verdict.${recommendation.verdict}`)}
                  {recommendation.score !== undefined && recommendation.score !== null
                    ? ` ${Number(recommendation.score).toFixed(0)}/100`
                    : ''}
                </span>
              </div>

              {recommendationNote && (
                <p className="mb-0 mt-2 line-clamp-2 text-[12px] leading-5 text-ink-variant">
                  {recommendationNote}
                </p>
              )}

              {(recommendationFitTags.length > 0 ||
                recommendationRiskTags.length > 0) && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {recommendationFitTags.map((tag) => (
                    <span
                      key={`fit-${tag}`}
                      className="rounded-full border border-primary/20 bg-primary/10 px-2 py-1 text-[10px] font-semibold text-primary-dark"
                    >
                      {tag}
                    </span>
                  ))}
                  {recommendationRiskTags.map((tag) => (
                    <span
                      key={`risk-${tag}`}
                      className="rounded-full border border-destructive/20 bg-destructive/10 px-2 py-1 text-[10px] font-semibold text-destructive"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {item.risk_notes && (
            <p className="mb-0 line-clamp-1 rounded-lg border border-amber/30 bg-amber/10 px-2 py-1.5 text-[11px] text-amber">
              {item.risk_notes}
            </p>
          )}

          {/* What the dish contains — plain information, not a warning. The red
              banner above is the warning, and it only fires on the diner's own
              declared allergies. A guest who has declared nothing still needs to
              know what is in the food. */}
          {(item.allergens?.length ?? 0) > 0 && (
            <p className="mb-0 text-[11px] leading-relaxed text-ink-variant">
              {t('billItem.contains', {
                list: item.allergens
                  .map((code) => t(`diet.allergens.${code}`))
                  .join(', '),
              })}
            </p>
          )}
        </>
      )}

      <div className="mt-auto flex items-center gap-2 border-t border-hairline pt-3">
        <div className="flex h-9 shrink-0 items-center overflow-hidden rounded-full border border-hairline">
          <button
            type="button"
            onClick={() => onQuantityChange(line.quantity - 1)}
            className="flex size-9 items-center justify-center text-primary-dark transition-colors hover:bg-primary/10"
            aria-label={t('billItem.decreaseAria', { name: item.original_name })}
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
            aria-label={t('billItem.increaseAria', { name: item.original_name })}
          >
            <Plus className="size-4" aria-hidden />
          </button>
        </div>
        <input
          value={line.note}
          onChange={(event) => onNoteChange(event.target.value)}
          placeholder={t('billItem.addNote')}
          className="h-9 min-w-0 flex-1 rounded-full border border-hairline bg-surface-muted px-3 text-[13px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
        />
      </div>
    </article>
  )
}

type RecommendationVerdict = NonNullable<BillItem['recommendation']>['verdict']

function verdictClass(verdict: RecommendationVerdict): string {
  if (verdict === 'RECOMMENDED') return 'bg-primary/15 text-primary-dark'
  if (verdict === 'OK') return 'bg-primary/10 text-primary-dark'
  if (verdict === 'CAUTION') return 'bg-amber/15 text-amber'
  return 'bg-destructive/10 text-destructive'
}

/** The card's own skin, so the verdict reads from across the table without having
 * to find the badge.
 *
 * Kept deliberately quiet — a tinted left edge and a faint wash, not a solid block
 * of colour. Thirty dishes each shouting a colour is a menu nobody can read, and
 * the tint must never fight the red allergy banner inside the card, which is the
 * one thing on this screen that can actually hurt someone.
 *
 * No verdict, no tint: a dish we know nothing about must look like a dish we know
 * nothing about. */
function verdictCardClass(verdict: RecommendationVerdict | null): string {
  switch (verdict) {
    case 'RECOMMENDED':
      return 'border-hairline border-l-4 border-l-primary bg-primary/5'
    case 'OK':
      return 'border-hairline border-l-4 border-l-primary/50 bg-canvas'
    case 'CAUTION':
      return 'border-hairline border-l-4 border-l-amber bg-amber/10'
    case 'AVOID':
      return 'border-destructive/30 border-l-4 border-l-destructive bg-destructive/[0.04]'
    default:
      return 'border-hairline bg-canvas'
  }
}

function uniqueCompact(values: string[]): string[] {
  const seen = new Set<string>()
  const result: string[] = []
  for (const value of values) {
    const clean = value.trim()
    const key = clean.toLowerCase()
    if (!clean || seen.has(key)) continue
    seen.add(key)
    result.push(clean)
  }
  return result
}
