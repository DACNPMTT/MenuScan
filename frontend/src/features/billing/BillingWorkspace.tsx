import { useMemo, useState } from 'react'
import { Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { MenuItemResult } from '@/features/menu-scan/types'
import { useBillSync } from '@/features/billing/hooks/useBillSync'
import { ItemFilterBar } from '@/features/billing/components/ItemFilterBar'
import { ItemQuantityRow } from '@/features/billing/components/ItemQuantityRow'
import { BillSummaryPanel } from '@/features/billing/components/BillSummaryPanel'

interface BillingWorkspaceProps {
  menuId: string
  currency: string | null
  items: MenuItemResult[]
  accessToken: string | null
}

/** Connects the Scan Results screen to the billing workflow (issue #131):
 * pick items + quantity, search/filter, adjustments, split by headcount,
 * and finalize. All totals are server-derived (`BillResponse`); this
 * component never computes money itself. */
export function BillingWorkspace({
  menuId,
  currency,
  items,
  accessToken,
}: BillingWorkspaceProps) {
  const billableItems = useMemo(() => items.filter((item) => item.price != null), [items])

  const [quantities, setQuantities] = useState<Record<string, number>>({})
  const [numPeople, setNumPeople] = useState(1)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string | null>(null)

  const {
    bill,
    syncing,
    syncError,
    isFinalized,
    retrySync,
    finalize,
    addAdjustment,
    updateAdjustment,
    removeAdjustment,
  } = useBillSync(menuId, quantities, accessToken)

  const hasSelection = Object.values(quantities).some((qty) => qty > 0)

  const setQuantity = (foodItemId: string, quantity: number) => {
    if (isFinalized) return
    setQuantities((current) => {
      const next = { ...current }
      if (quantity <= 0) {
        delete next[foodItemId]
      } else {
        next[foodItemId] = quantity
      }
      return next
    })
  }

  const visibleItems = useMemo(() => {
    const term = search.trim().toLowerCase()
    return billableItems.filter((item) => {
      if (category && item.category !== category) return false
      if (!term) return true
      const haystack = `${item.translated_name ?? ''} ${item.original_name}`.toLowerCase()
      return haystack.includes(term)
    })
  }, [billableItems, search, category])

  if (!accessToken) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-[12px] border border-dashed border-hairline bg-canvas px-4 py-[30px] text-center">
        <Users className="size-6 text-ink-variant" aria-hidden />
        <p className="text-[14px] text-ink-variant">
          Đăng nhập để chọn món và chia hóa đơn cho nhóm của bạn.
        </p>
        <Link
          to="/auth/login"
          className="mt-1 rounded-[8px] bg-primary-dark px-[20px] py-[10px] text-[15px] font-bold text-white transition-opacity hover:opacity-90"
        >
          Đăng nhập
        </Link>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex flex-col gap-3">
        {isFinalized && (
          <div className="flex items-center gap-2 rounded-[8px] bg-primary/10 px-3 py-2 text-[13px] font-medium text-primary-dark">
            Hóa đơn đã chốt. Không thể chỉnh sửa món hoặc điều chỉnh nữa.
          </div>
        )}

        {billableItems.length === 0 ? (
          <p className="rounded-[8px] bg-surface-muted px-3 py-2 text-[13px] text-ink-variant">
            Không có món nào có giá để thêm vào hóa đơn.
          </p>
        ) : (
          <>
            <ItemFilterBar
              items={billableItems}
              search={search}
              onSearchChange={setSearch}
              activeCategory={category}
              onCategoryChange={setCategory}
            />
            {visibleItems.length === 0 ? (
              <p className="rounded-[8px] bg-surface-muted px-3 py-2 text-[13px] text-ink-variant">
                Không tìm thấy món phù hợp.
              </p>
            ) : (
              visibleItems.map((item) => (
                <ItemQuantityRow
                  key={item.id}
                  item={item}
                  quantity={quantities[item.id] ?? 0}
                  disabled={isFinalized}
                  onChange={(qty) => setQuantity(item.id, qty)}
                />
              ))
            )}
          </>
        )}
      </div>

      <BillSummaryPanel
        bill={bill}
        currency={currency}
        numPeople={numPeople}
        onNumPeopleChange={setNumPeople}
        syncing={syncing}
        syncError={syncError}
        hasSelection={hasSelection}
        isFinalized={isFinalized}
        onFinalize={() => void finalize()}
        onRetrySync={retrySync}
        onAddAdjustment={addAdjustment}
        onUpdateAdjustment={updateAdjustment}
        onRemoveAdjustment={removeAdjustment}
      />
    </div>
  )
}