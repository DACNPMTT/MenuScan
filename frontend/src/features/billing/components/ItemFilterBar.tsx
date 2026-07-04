import { useMemo } from 'react'
import { Search } from 'lucide-react'
import type { MenuItemResult } from '@/features/menu-scan/types'

interface ItemFilterBarProps {
  items: MenuItemResult[]
  search: string
  onSearchChange: (value: string) => void
  activeCategory: string | null
  onCategoryChange: (category: string | null) => void
}

/**
 * Search box + category tabs above the item list (Figma "Scan Results" —
 * search field, `All` / `Mains` / `Drinks` tabs). Categories are derived
 * from `item.category`, which the scan pipeline already returns, so this
 * stays a pure client-side filter with no new endpoint.
 */
export function ItemFilterBar({
  items,
  search,
  onSearchChange,
  activeCategory,
  onCategoryChange,
}: ItemFilterBarProps) {
  const categories = useMemo(() => {
    const seen = new Set<string>()
    for (const item of items) {
      if (item.category) seen.add(item.category)
    }
    return Array.from(seen)
  }, [items])

  return (
    <div className="flex flex-col gap-2">
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-variant"
          aria-hidden
        />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Tìm món..."
          aria-label="Tìm món"
          className="w-full rounded-[8px] border border-hairline bg-canvas py-2 pl-9 pr-3 text-[14px] text-ink placeholder:text-placeholder focus:border-primary focus:outline-none"
        />
      </div>

      {categories.length > 0 && (
        <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Lọc theo danh mục">
          <button
            type="button"
            role="tab"
            aria-selected={activeCategory === null}
            onClick={() => onCategoryChange(null)}
            className={`rounded-full px-3 py-1 text-[13px] font-medium transition-colors ${
              activeCategory === null
                ? 'bg-primary-dark text-white'
                : 'bg-surface-muted text-ink-variant hover:bg-secondary'
            }`}
          >
            Tất cả
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              role="tab"
              aria-selected={activeCategory === cat}
              onClick={() => onCategoryChange(cat)}
              className={`rounded-full px-3 py-1 text-[13px] font-medium capitalize transition-colors ${
                activeCategory === cat
                  ? 'bg-primary-dark text-white'
                  : 'bg-surface-muted text-ink-variant hover:bg-secondary'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}