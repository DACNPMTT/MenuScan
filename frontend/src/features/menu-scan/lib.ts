// Pure helpers and constants for the menu detail / bill experience.
//
// Kept free of React so they are trivial to reason about and reuse across the
// MenuDetailPage orchestrator and its presentational components.

import type {
  BillItem,
  ItemDraft,
  ItemValidationErrors,
} from '@/features/menu-scan/types'

export const API_BASE_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(
  /\/$/,
  '',
)

export const LOW_CONFIDENCE_THRESHOLD = 0.75
export const SEARCH_DEBOUNCE_MS = 300
export const ITEMS_PAGE_SIZE = 50
export const ALL_CATEGORY = 'All'

/** Normalize a price-filter input into a non-negative decimal string the API
 * accepts (`min_price`/`max_price`), or '' when empty/invalid. */
export function normalizePrice(raw: string): string {
  const trimmed = raw.trim().replace(',', '.')
  if (trimmed === '') return ''
  const value = Number(trimmed)
  return Number.isFinite(value) && value >= 0 ? trimmed : ''
}

/** Clamp a percentage input (VAT / tip) to 0-100; non-numeric becomes 0. */
export function clampPercent(raw: string | number): number {
  const value = Number(raw)
  if (!Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, value))
}

export function formatMoney(amount: number, currency: string | null): string {
  const resolvedCurrency = currency ?? 'VND'
  if (resolvedCurrency === 'VND') {
    return `${Math.round(amount).toLocaleString('vi-VN')}đ`
  }
  return `${amount.toFixed(2)} ${resolvedCurrency}`
}

export function itemPrice(item: BillItem): number {
  const value = Number(item.price)
  return Number.isFinite(value) ? value : 0
}

export function draftFromItem(item: BillItem, fallbackCurrency: string | null): ItemDraft {
  return {
    original_name: item.original_name ?? '',
    translated_name: item.translated_name ?? '',
    original_description: item.original_description ?? '',
    translated_description: item.translated_description ?? '',
    price: item.price ?? '',
    currency: item.currency ?? fallbackCurrency ?? '',
    category: item.category ?? '',
  }
}

export function normalizeDraft(draft: ItemDraft) {
  return {
    original_name: draft.original_name.trim(),
    translated_name: draft.translated_name.trim() || null,
    original_description: draft.original_description.trim() || null,
    translated_description: draft.translated_description.trim() || null,
    price: draft.price.trim() || null,
    currency: draft.currency.trim().toUpperCase() || null,
    category: draft.category.trim() || null,
  }
}

export function draftMatchesItem(
  draft: ItemDraft,
  item: BillItem,
  fallbackCurrency: string | null,
): boolean {
  const normalized = normalizeDraft(draft)
  return (
    normalized.original_name === item.original_name &&
    normalized.translated_name === item.translated_name &&
    normalized.original_description === item.original_description &&
    normalized.translated_description === item.translated_description &&
    normalized.price === (item.price ?? null) &&
    normalized.currency === (item.currency ?? fallbackCurrency ?? null) &&
    normalized.category === item.category
  )
}

export function validateDraft(
  draft: ItemDraft,
  t: (key: string) => string,
): ItemValidationErrors {
  const errors: ItemValidationErrors = {}
  if (!draft.original_name.trim()) {
    errors.original_name = t('billItem.errors.nameRequired')
  }
  const price = draft.price.trim()
  if (price) {
    const numericPrice = Number(price)
    if (!Number.isFinite(numericPrice) || numericPrice < 0) {
      errors.price = t('billItem.errors.priceInvalid')
    }
  }
  return errors
}

export function confidenceValue(item: BillItem): number | null {
  if (item.confidence_score === null || item.confidence_score === undefined) {
    return null
  }
  const value = Number(item.confidence_score)
  return Number.isFinite(value) ? value : null
}

export function itemCategory(item: BillItem): string {
  return item.category?.trim() || 'Other'
}

export function hasAllergySignal(item: BillItem): boolean {
  const text = [
    item.category,
    item.original_name,
    item.translated_name,
    item.original_description,
    item.translated_description,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  return /(seafood|shellfish|shrimp|prawn|crab|lobster|hải sản|tôm|cua)/i.test(text)
}
