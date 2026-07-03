import { Loader2, Plus, Search, X } from 'lucide-react'

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
  return (
    <div className="mb-6 flex flex-col gap-3">
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
            placeholder="Tìm món theo tên hoặc mô tả..."
            aria-label="Tìm kiếm món"
            className="h-11 w-full rounded-[8px] border border-hairline bg-canvas pl-10 pr-9 text-[14px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary-dark"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              aria-label="Xóa tìm kiếm"
              className="absolute right-2 top-1/2 flex size-6 -translate-y-1/2 items-center justify-center rounded-full text-ink-variant transition-colors hover:bg-surface-muted hover:text-ink"
            >
              <X className="size-4" aria-hidden />
            </button>
          )}
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-11 items-center overflow-hidden rounded-[8px] border border-hairline bg-canvas">
            <input
              type="text"
              inputMode="decimal"
              value={minPriceInput}
              onChange={(event) => onMinPriceChange(event.target.value)}
              placeholder="Giá từ"
              aria-label="Giá tối thiểu"
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
              placeholder="đến"
              aria-label="Giá tối đa"
              className="h-full w-[88px] bg-transparent pr-3 text-[14px] text-ink outline-none placeholder:text-placeholder"
            />
          </div>
          <button
            type="button"
            onClick={onAddManualItem}
            disabled={addingManual}
            className="flex h-11 items-center gap-2 rounded-[8px] bg-primary-dark px-4 text-[14px] font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {addingManual ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Plus className="size-4" aria-hidden />
            )}
            Thêm món
          </button>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {categories.map((category) => (
          <button
            type="button"
            key={category}
            onClick={() => onCategoryChange(category)}
            className={
              activeCategory === category
                ? 'h-9 rounded-full bg-primary-dark px-4 text-[13px] font-bold text-white'
                : 'h-9 rounded-full border border-hairline bg-canvas px-4 text-[13px] font-medium text-primary-dark transition-colors hover:bg-surface-muted'
            }
          >
            {category}
          </button>
        ))}
        {hasActiveFilter && (
          <button
            type="button"
            onClick={onClearFilters}
            className="ml-auto flex h-9 items-center gap-1.5 rounded-full border border-hairline bg-canvas px-3 text-[13px] font-medium text-ink-variant transition-colors hover:bg-surface-muted hover:text-ink"
          >
            <X className="size-3.5" aria-hidden />
            Xóa bộ lọc
          </button>
        )}
      </div>
    </div>
  )
}

