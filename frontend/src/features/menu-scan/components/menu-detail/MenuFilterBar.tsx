import { Loader2, Plus, Search, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { ALL_CATEGORY } from '@/features/menu-scan/lib'
import { Button } from '@/shared/components/ui/button'

export interface MenuFilterBarProps {
  searchInput: string
  onSearchChange: (value: string) => void
  minPriceInput: string
  onMinPriceChange: (value: string) => void
  maxPriceInput: string
  onMaxPriceChange: (value: string) => void
  categories: string[]
  activeCategory: string
  onCategoryChange: (category: string) => void
  hasActiveFilter: boolean
  onClearFilters: () => void
  addingManual: boolean
  onAddManualItem: () => void
}

/** Search + price-range + category filter controls for the menu detail grid.
 * Pure presentational: all state lives in the parent orchestrator. */
export function MenuFilterBar({
  searchInput,
  onSearchChange,
  minPriceInput,
  onMinPriceChange,
  maxPriceInput,
  onMaxPriceChange,
  categories,
  activeCategory,
  onCategoryChange,
  hasActiveFilter,
  onClearFilters,
  addingManual,
  onAddManualItem,
}: MenuFilterBarProps) {
  const { t } = useTranslation()
  return (
    <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-hairline bg-surface p-4 shadow-1">
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
        <label className="relative block">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-variant"
            aria-hidden
          />
          <input
            type="text"
            value={searchInput}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={t('filter.searchPlaceholder')}
            aria-label={t('filter.searchAria')}
            className="h-11 w-full rounded-xl border border-hairline bg-surface pl-10 pr-9 text-[14px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              aria-label={t('filter.clearSearchAria')}
              className="absolute right-2 top-1/2 flex size-6 -translate-y-1/2 items-center justify-center rounded-full text-ink-variant transition-colors hover:bg-panel hover:text-ink"
            >
              <X className="size-4" aria-hidden />
            </button>
          )}
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-11 items-center overflow-hidden rounded-xl border border-hairline bg-surface transition-colors focus-within:border-primary">
            <input
              type="text"
              inputMode="decimal"
              value={minPriceInput}
              onChange={(event) => onMinPriceChange(event.target.value)}
              placeholder={t('filter.minPrice')}
              aria-label={t('filter.minPriceAria')}
              className="h-full w-[88px] bg-transparent px-3 text-[14px] text-ink outline-none placeholder:text-placeholder"
            />
            <span className="select-none px-1 text-ink-variant" aria-hidden>
              –
            </span>
            <input
              type="text"
              inputMode="decimal"
              value={maxPriceInput}
              onChange={(event) => onMaxPriceChange(event.target.value)}
              placeholder={t('filter.maxPrice')}
              aria-label={t('filter.maxPriceAria')}
              className="h-full w-[88px] bg-transparent pr-3 text-[14px] text-ink outline-none placeholder:text-placeholder"
            />
          </div>
          <Button
            type="button"
            variant="default"
            onClick={onAddManualItem}
            disabled={addingManual}
          >
            {addingManual ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Plus className="size-4" aria-hidden />
            )}
            {t('filter.addItem')}
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {categories.map((category) => (
          <Button
            type="button"
            key={category}
            variant={activeCategory === category ? 'default' : 'outline'}
            size="sm"
            onClick={() => onCategoryChange(category)}
          >
            {category === ALL_CATEGORY ? t('filter.allCategories') : category}
          </Button>
        ))}
        {hasActiveFilter && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClearFilters}
            className="ml-auto"
          >
            <X className="size-3.5" aria-hidden />
            {t('menuDetail.clearFilters')}
          </Button>
        )}
      </div>
    </div>
  )
}
