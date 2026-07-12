import {
  AlertTriangle,
  Info,
  ShieldCheck,
  Sparkles,
  Utensils,
  X,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { ItemDisplayName } from '@/features/menu-scan/components/menu-detail/ItemDisplayName'
import { itemCategory, itemPrice } from '@/features/menu-scan/lib'
import { formatConvertedAmount, type ExchangeRates } from '@/shared/lib/currency'
import type { BillItem } from '@/features/menu-scan/types'

interface MenuItemDetailDialogProps {
  item: BillItem
  currency: string | null
  displayCurrency: string
  rates: ExchangeRates | null
  onClose: () => void
}

export function MenuItemDetailDialog({
  item,
  currency,
  displayCurrency,
  rates,
  onClose,
}: MenuItemDetailDialogProps) {
  const ingredients = uniqueCompact(item.main_ingredients)
  const descriptorTags = uniqueCompact([
    ...item.cooking_methods,
    ...item.flavor_tags,
    ...item.texture_tags,
    ...item.ingredient_tags,
  ])
  const tasteRows = TASTE_ROWS.map((row) => ({
    ...row,
    value: item[row.key] ?? 0,
  })).filter((row) => row.value > 0)
  const recommendation = item.recommendation

  return (
    <div
      className="fixed inset-0 z-50 flex items-end bg-black/35 p-0 sm:items-center sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="menu-item-detail-title"
      onClick={onClose}
    >
      <div
        className="max-h-[92vh] w-full overflow-y-auto rounded-t-[12px] bg-app-bg p-5 shadow-xl sm:mx-auto sm:max-w-3xl sm:rounded-[12px] sm:p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-hairline pb-4">
          <div className="min-w-0">
            <p className="mb-2 w-fit rounded-[4px] border border-primary-dark/25 bg-surface-muted px-2 py-1 text-[11px] font-bold uppercase text-primary-dark">
              {itemCategory(item)}
            </p>
            <h2
              id="menu-item-detail-title"
              className="mb-1 break-words text-[24px] font-bold leading-tight text-ink"
            >
              <ItemDisplayName
                item={item}
                originalClassName="text-[15px] text-ink-variant/55"
              />
            </h2>
            <p className="mb-0 text-[16px] font-bold text-primary-dark">
              {formatConvertedAmount(
                itemPrice(item),
                item.currency ?? currency ?? 'VND',
                displayCurrency,
                rates,
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex size-10 shrink-0 items-center justify-center rounded-[8px] border border-hairline bg-canvas text-primary-dark transition-colors hover:bg-primary/10"
            aria-label="Đóng chi tiết món"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>

        <div className="mt-5 grid gap-4">
          {(item.assistant_summary ||
            item.translated_description ||
            item.original_description) && (
            <DetailSection
              icon={<Info className="size-4" aria-hidden />}
              title="Tóm tắt món"
            >
              {item.assistant_summary && (
                <p className="mb-0 text-[15px] leading-7 text-ink">
                  {item.assistant_summary}
                </p>
              )}
              {item.translated_description &&
                item.translated_description !== item.assistant_summary && (
                  <p className="mb-0 text-[14px] leading-6 text-ink-variant">
                    {item.translated_description}
                  </p>
                )}
              {item.original_description &&
                item.original_description !== item.translated_description && (
                  <p className="mb-0 border-l-2 border-hairline pl-3 text-[13px] leading-6 text-ink-variant/60">
                    {item.original_description}
                  </p>
                )}
            </DetailSection>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {ingredients.length > 0 && (
              <DetailSection
                icon={<Utensils className="size-4" aria-hidden />}
                title="Nguyên liệu"
              >
                <TagList values={ingredients} />
              </DetailSection>
            )}

            {descriptorTags.length > 0 && (
              <DetailSection
                icon={<Sparkles className="size-4" aria-hidden />}
                title="Đặc tính món"
              >
                <TagList values={descriptorTags} tone="muted" />
              </DetailSection>
            )}
          </div>

          {tasteRows.length > 0 && (
            <DetailSection
              icon={<Sparkles className="size-4" aria-hidden />}
              title="Mức vị"
            >
              <div className="grid gap-x-5 gap-y-3 sm:grid-cols-2">
                {tasteRows.map((row) => (
                  <TasteMeter key={row.key} label={row.label} value={row.value} />
                ))}
              </div>
            </DetailSection>
          )}

          {item.risk_notes && (
            <DetailSection
              icon={<AlertTriangle className="size-4" aria-hidden />}
              title="Lưu ý món"
              tone="warning"
            >
              <p className="mb-0 text-[14px] leading-6 text-amber-800">
                {item.risk_notes}
              </p>
            </DetailSection>
          )}

          {recommendation && (
            <DetailSection
              icon={<ShieldCheck className="size-4" aria-hidden />}
              title="Khuyến nghị"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[13px] font-bold text-ink-variant">
                  Độ phù hợp
                </span>
                <span
                  className={`rounded-full px-2 py-1 text-[12px] font-bold ${verdictClass(recommendation.verdict)}`}
                >
                  {verdictLabel(recommendation.verdict)}
                  {recommendation.score !== undefined && recommendation.score !== null
                    ? ` ${Number(recommendation.score).toFixed(0)}/100`
                    : ''}
                </span>
              </div>

              {recommendation.explanation && (
                <p className="mb-0 text-[14px] leading-6 text-ink-variant">
                  {recommendation.explanation}
                </p>
              )}

              {(recommendation.why_suitable || recommendation.why_not_suitable) && (
                <div className="grid gap-2 sm:grid-cols-2">
                  {recommendation.why_suitable && (
                    <p className="mb-0 rounded-[6px] border border-[#e4f4df] bg-[#e4f4df]/35 px-3 py-2 text-[12px] leading-5 text-[#256b2b]">
                      {recommendation.why_suitable}
                    </p>
                  )}
                  {recommendation.why_not_suitable && (
                    <p className="mb-0 rounded-[6px] border border-red-100 bg-red-50 px-3 py-2 text-[12px] leading-5 text-red-700">
                      {recommendation.why_not_suitable}
                    </p>
                  )}
                </div>
              )}

              {(recommendation.fit_reasons?.length ||
                recommendation.risk_reasons?.length ||
                recommendation.warning_reasons?.length ||
                recommendation.suggested_for?.length ||
                recommendation.warning_for?.length) && (
                <div className="flex flex-wrap gap-1.5">
                  <TagList
                    values={[
                      ...(recommendation.suggested_for ?? []).map(
                        (name) => `Hợp: ${name}`,
                      ),
                      ...(recommendation.fit_reasons ?? []),
                    ]}
                    tone="positive"
                  />
                  <TagList
                    values={[
                      ...(recommendation.warning_for ?? []).map(
                        (name) => `Tránh: ${name}`,
                      ),
                      ...(recommendation.risk_reasons ?? []),
                      ...(recommendation.warning_reasons ?? []),
                    ]}
                    tone="danger"
                  />
                </div>
              )}

              {recommendation.participant_breakdowns &&
                recommendation.participant_breakdowns.length > 0 && (
                  <div className="grid gap-2 border-t border-hairline pt-3">
                    <p className="mb-0 text-[11px] font-bold uppercase text-ink-variant/60">
                      Chi tiết thành viên
                    </p>
                    {recommendation.participant_breakdowns.map((breakdown) => (
                      <div
                        key={`${breakdown.display_name}-${breakdown.verdict}`}
                        className="rounded-[8px] border border-hairline bg-surface-muted/60 px-3 py-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-bold text-ink">
                            {breakdown.display_name}
                          </span>
                          <span
                            className={`rounded-full px-2 py-1 text-[10px] font-bold ${verdictClass(breakdown.verdict)}`}
                          >
                            {verdictLabel(breakdown.verdict)}
                            {breakdown.score !== undefined &&
                            breakdown.score !== null
                              ? ` ${Number(breakdown.score).toFixed(0)}/100`
                              : ''}
                          </span>
                        </div>
                        {breakdown.explanation && (
                          <p className="mb-0 mt-1 text-[12px] leading-5 text-ink-variant">
                            {breakdown.explanation}
                          </p>
                        )}
                        {(breakdown.fit_reasons?.length ||
                          breakdown.risk_reasons?.length) && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            <TagList
                              values={breakdown.fit_reasons ?? []}
                              tone="positive"
                            />
                            <TagList
                              values={breakdown.risk_reasons ?? []}
                              tone="danger"
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
            </DetailSection>
          )}
        </div>
      </div>
    </div>
  )
}

const TASTE_ROWS = [
  { key: 'spice_level', label: 'Cay' },
  { key: 'sweetness_level', label: 'Ngọt' },
  { key: 'saltiness_level', label: 'Mặn' },
  { key: 'sourness_level', label: 'Chua' },
  { key: 'richness_level', label: 'Béo' },
  { key: 'oiliness_level', label: 'Dầu' },
] as const

type RecommendationVerdict = NonNullable<BillItem['recommendation']>['verdict']

function DetailSection({
  icon,
  title,
  children,
  tone = 'default',
}: {
  icon: ReactNode
  title: string
  children: ReactNode
  tone?: 'default' | 'danger' | 'warning'
}) {
  const sectionClass =
    tone === 'danger'
      ? 'border-red-100 bg-red-50'
      : tone === 'warning'
        ? 'border-amber-200 bg-amber-50'
        : 'border-hairline bg-canvas'
  const titleClass =
    tone === 'danger'
      ? 'text-red-700'
      : tone === 'warning'
        ? 'text-amber-800'
        : 'text-ink-variant/70'
  const iconClass =
    tone === 'danger'
      ? 'text-red-700'
      : tone === 'warning'
        ? 'text-amber-700'
        : 'text-primary-dark'

  return (
    <section className={`flex flex-col gap-3 rounded-[8px] border px-4 py-3 ${sectionClass}`}>
      <div
        className={`flex items-center gap-2 text-[12px] font-bold uppercase ${titleClass}`}
      >
        <span className={iconClass}>{icon}</span>
        {title}
      </div>
      {children}
    </section>
  )
}

function TagList({
  values,
  tone = 'default',
}: {
  values: string[]
  tone?: 'default' | 'muted' | 'positive' | 'danger'
}) {
  const tags = uniqueCompact(values)
  if (tags.length === 0) return null

  const toneClass =
    tone === 'positive'
      ? 'border-[#cfeac5] bg-[#e4f4df]/65 text-[#256b2b]'
      : tone === 'danger'
        ? 'border-red-100 bg-red-50 text-red-700'
        : tone === 'muted'
          ? 'border-hairline bg-surface-muted text-ink-variant'
          : 'border-primary-dark/20 bg-surface-muted text-primary-dark'

  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((value) => (
        <span
          key={value}
          className={`rounded-[4px] border px-2 py-1 text-[11px] font-semibold ${toneClass}`}
        >
          {value}
        </span>
      ))}
    </div>
  )
}

function TasteMeter({ label, value }: { label: string; value: number }) {
  const normalized = Math.max(0, Math.min(5, value))
  return (
    <div className="grid grid-cols-[46px_1fr_20px] items-center gap-2">
      <span className="text-[12px] font-semibold text-ink-variant">{label}</span>
      <span className="h-2 overflow-hidden rounded-full bg-surface-muted">
        <span
          className="block h-full rounded-full bg-primary-dark"
          style={{ width: `${(normalized / 5) * 100}%` }}
        />
      </span>
      <span className="text-right text-[11px] font-bold text-ink-variant">
        {normalized}
      </span>
    </div>
  )
}

function verdictLabel(verdict: RecommendationVerdict): string {
  if (verdict === 'RECOMMENDED') return 'Nên dùng'
  if (verdict === 'OK') return 'Phù hợp'
  if (verdict === 'CAUTION') return 'Cân nhắc'
  return 'Nên tránh'
}

function verdictClass(verdict: RecommendationVerdict): string {
  if (verdict === 'RECOMMENDED') return 'bg-[#e4f4df] text-[#256b2b]'
  if (verdict === 'OK') return 'bg-primary/10 text-primary-dark'
  if (verdict === 'CAUTION') return 'bg-amber-100 text-amber-800'
  return 'bg-red-100 text-red-800'
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
