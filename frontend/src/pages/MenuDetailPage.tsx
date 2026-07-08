import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  HandCoins,
  Loader2,
  Percent,
  Plus,
  Receipt,
  ReceiptText,
  RefreshCw,
  Tag,
  Trash2,
  Users,
  XCircle,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { ApiError, apiRequest, apiRequestWithMeta } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useDebouncedValue } from '@/shared/hooks/useDebouncedValue'
import { useExchangeRates } from '@/shared/hooks/useExchangeRates'
import { CurrencySelect } from '@/shared/components/CurrencySelect'
import { formatConvertedAmount } from '@/shared/lib/currency'
import {
  ALL_CATEGORY,
  ITEMS_PAGE_SIZE,
  SEARCH_DEBOUNCE_MS,
  clampPercent,
  draftFromItem,
  draftMatchesItem,
  itemCategory,
  itemPrice,
  normalizeDraft,
  normalizePrice,
  validateDraft,
} from '@/features/menu-scan/lib'
import { type DietProfile } from '@/features/menu-scan/dietary'
import { BillItemCard } from '@/features/menu-scan/components/menu-detail/BillItemCard'
import { ItemDisplayName } from '@/features/menu-scan/components/menu-detail/ItemDisplayName'
import { ManualItemCard } from '@/features/menu-scan/components/menu-detail/ManualItemCard'
import { MenuFilterBar } from '@/features/menu-scan/components/menu-detail/MenuFilterBar'
import type { Bill } from '@/features/billing/types'
import { SourcePreview } from '@/features/menu-scan/components/menu-detail/SourcePreview'
import type {
  BillItem,
  BillLineState,
  ItemDraft,
  ItemValidationErrors,
  MenuDetail,
  MenuItemResult,
  PaginationMeta,
} from '@/features/menu-scan/types'

export function MenuDetailPage() {
  const { t } = useTranslation()
  const { menuId } = useParams<{ menuId: string }>()
  const navigate = useNavigate()
  const { accessToken, user } = useAuth()
  const dietProfile = useMemo<DietProfile>(
    () => ({
      allergies: user?.allergies ?? [],
      dietary_preferences: user?.dietary_preferences ?? [],
    }),
    [user?.allergies, user?.dietary_preferences],
  )
  const toast = useToast()
  const [menu, setMenu] = useState<MenuDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  // Raw filter inputs update instantly for a responsive feel; the debounced
  // mirrors below drive the actual request so typing fires one request per
  // debounce window, not one per keystroke.
  const [searchInput, setSearchInput] = useState(() => searchParams.get('q') ?? '')
  const [minPriceInput, setMinPriceInput] = useState(() => searchParams.get('min') ?? '')
  const [maxPriceInput, setMaxPriceInput] = useState(() => searchParams.get('max') ?? '')
  const [activeCategory, setActiveCategory] = useState(
    () => searchParams.get('cat') ?? ALL_CATEGORY,
  )
  const debouncedSearch = useDebouncedValue(searchInput, SEARCH_DEBOUNCE_MS)
  const debouncedMinPrice = useDebouncedValue(minPriceInput, SEARCH_DEBOUNCE_MS)
  const debouncedMaxPrice = useDebouncedValue(maxPriceInput, SEARCH_DEBOUNCE_MS)
  const trimmedSearch = debouncedSearch.trim()
  const normalizedMinPrice = normalizePrice(debouncedMinPrice)
  const normalizedMaxPrice = normalizePrice(debouncedMaxPrice)
  const hasActiveFilter =
    trimmedSearch !== '' || normalizedMinPrice !== '' || normalizedMaxPrice !== ''
  // Server-driven filtered results. When no filter is active we reuse the items
  // already embedded in the menu detail, avoiding a redundant request.
  const [serverItems, setServerItems] = useState<MenuItemResult[]>([])
  const [itemsMeta, setItemsMeta] = useState<PaginationMeta | null>(null)
  const [itemsPage, setItemsPage] = useState(1)
  const [itemsLoading, setItemsLoading] = useState(false)
  const [itemsError, setItemsError] = useState<string | null>(null)
  const requestIdRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)
  const [peopleCount, setPeopleCount] = useState(1)
  // Bill adjustments. Percentages apply to the subtotal (same base the backend
  // uses), surcharge is a flat amount in the bill's own currency.
  const [vatPercent, setVatPercent] = useState(0)
  const [tipPercent, setTipPercent] = useState(0)
  const [surcharge, setSurcharge] = useState(0)
  const [discountPercent, setDiscountPercent] = useState(0)
  const [billLines, setBillLines] = useState<Record<string, BillLineState>>({})
  const [addingManual, setAddingManual] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [manualName, setManualName] = useState('')
  const [manualPrice, setManualPrice] = useState('')
  const [manualNote, setManualNote] = useState('')
  const [creatingBill, setCreatingBill] = useState(false)
  const [itemDrafts, setItemDrafts] = useState<Record<string, ItemDraft>>({})
  const [itemValidationErrors, setItemValidationErrors] = useState<
    Record<string, ItemValidationErrors>
  >({})
  const [itemSaveErrors, setItemSaveErrors] = useState<Record<string, string>>({})
  const [savingItemId, setSavingItemId] = useState<string | null>(null)
  const [deletingItemId, setDeletingItemId] = useState<string | null>(null)
  const [editingItemIds, setEditingItemIds] = useState<Set<string>>(() => new Set())

  useDocumentTitle(menu ? `${menu.title} | MenuScan` : 'Menu | MenuScan')

  const loadMenu = useCallback(async () => {
    if (!menuId) return
    setLoading(true)
    setError(null)
    try {
      const data = await apiRequest<MenuDetail>(`/api/v1/menus/${menuId}`, {
        method: 'GET',
        token: accessToken ?? undefined,
      })
      setMenu(data)
      setItemDrafts({})
      setItemValidationErrors({})
      setItemSaveErrors({})
      setEditingItemIds(new Set())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('menuDetail.errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [accessToken, menuId, t])

  useEffect(() => {
    void Promise.resolve().then(loadMenu)
  }, [loadMenu])

  const allItems = useMemo<BillItem[]>(() => menu?.items ?? [], [menu?.items])

  const currency = useMemo(
    () => menu?.default_currency ?? allItems.find((item) => item.currency)?.currency ?? 'VND',
    [allItems, menu?.default_currency],
  )
  const [displayCurrency, setDisplayCurrency] = useState(currency)
  const { rates: exchangeRates } = useExchangeRates(currency)

  const dirtyItemIds = useMemo(
    () =>
      allItems
        .filter((item) => {
          const draft = itemDrafts[item.id]
          return draft ? !draftMatchesItem(draft, item, currency) : false
        })
        .map((item) => item.id),
    [allItems, currency, itemDrafts],
  )
  const hasUnsavedChanges = dirtyItemIds.length > 0

  useEffect(() => {
    if (!hasUnsavedChanges) return
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])

  const confirmLeaveWithUnsavedChanges = () =>
    !hasUnsavedChanges || window.confirm(t('menuDetail.unsavedConfirm'))

  // Items shown in the grid: server-filtered results while a filter is active,
  // otherwise the full set embedded in the menu detail (no extra request).
  const browseItems = useMemo<BillItem[]>(
    () => (hasActiveFilter ? serverItems : allItems),
    [hasActiveFilter, serverItems, allItems],
  )

  const categories = useMemo(() => {
    const seen = new Set<string>()
    browseItems.forEach((item) => seen.add(itemCategory(item)))
    return [ALL_CATEGORY, ...Array.from(seen)]
  }, [browseItems])

  const filteredItems = useMemo(
    () =>
      activeCategory === ALL_CATEGORY
        ? browseItems
        : browseItems.filter((item) => itemCategory(item) === activeCategory),
    [activeCategory, browseItems],
  )

  const canLoadMoreItems =
    hasActiveFilter && itemsMeta ? itemsPage < itemsMeta.total_pages : false

  const loadItems = useCallback(
    async (page: number, mode: 'replace' | 'append') => {
      if (!menuId) return
      // Cancel any in-flight request and stamp this one so a slow earlier
      // response can never overwrite a newer one (no stale results).
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      const requestId = ++requestIdRef.current
      setItemsLoading(true)
      setItemsError(null)
      if (mode === 'replace') setServerItems([])
      try {
        const params = new URLSearchParams()
        params.set('page', String(page))
        params.set('page_size', String(ITEMS_PAGE_SIZE))
        if (trimmedSearch) params.set('search', trimmedSearch)
        if (normalizedMinPrice) params.set('min_price', normalizedMinPrice)
        if (normalizedMaxPrice) params.set('max_price', normalizedMaxPrice)
        const result = await apiRequestWithMeta<MenuItemResult[], PaginationMeta>(
          `/api/v1/menus/${menuId}/items?${params.toString()}`,
          { method: 'GET', token: accessToken ?? undefined, signal: controller.signal },
        )
        if (requestId !== requestIdRef.current) return // superseded by a newer request
        setServerItems((current) =>
          mode === 'replace' ? result.data : [...current, ...result.data],
        )
        setItemsMeta(result.meta)
        setItemsPage(page)
      } catch (err) {
        if (requestId !== requestIdRef.current || controller.signal.aborted) return
        setItemsError(
          err instanceof ApiError ? err.message : t('menuDetail.errors.loadItemsFailed'),
        )
      } finally {
        if (requestId === requestIdRef.current) setItemsLoading(false)
      }
    },
    [accessToken, menuId, normalizedMaxPrice, normalizedMinPrice, trimmedSearch, t],
  )

  // Refetch on menu change or whenever the debounced filters settle. Skipping
  // when there's no active filter avoids a redundant request — the detail
  // payload already carries every item.
  useEffect(() => {
    if (!hasActiveFilter) {
      setServerItems([])
      setItemsMeta(null)
      setItemsPage(1)
      return
    }
    void loadItems(1, 'replace')
  }, [hasActiveFilter, loadItems])

  // Reflect the applied (debounced) filters in the URL so a refresh or shared
  // link preserves the current view. `replace` keeps filter edits out of the
  // back/forward history.
  useEffect(() => {
    const next: Record<string, string> = {}
    if (trimmedSearch) next.q = trimmedSearch
    if (normalizedMinPrice) next.min = normalizedMinPrice
    if (normalizedMaxPrice) next.max = normalizedMaxPrice
    if (activeCategory !== ALL_CATEGORY) next.cat = activeCategory
    setSearchParams(next, { replace: true })
  }, [trimmedSearch, normalizedMinPrice, normalizedMaxPrice, activeCategory, setSearchParams])

  const handleClearFilters = () => {
    setSearchInput('')
    setMinPriceInput('')
    setMaxPriceInput('')
    setActiveCategory(ALL_CATEGORY)
  }

  const selectedLines = useMemo(
    () =>
      allItems
        .map((item) => ({
          item,
          state: billLines[item.id] ?? { quantity: 0, note: '' },
        }))
        .filter((line) => line.state.quantity > 0),
    [allItems, billLines],
  )

  const subtotal = useMemo(
    () =>
      selectedLines.reduce(
        (sum, line) => sum + itemPrice(line.item) * line.state.quantity,
        0,
      ),
    [selectedLines],
  )

  // Mirrors BillingService: percentage adjustments are computed on the subtotal
  // (never compounded), then summed into the total.
  const vatAmount = (subtotal * vatPercent) / 100
  const tipAmount = (subtotal * tipPercent) / 100
  const discountAmount = (subtotal * discountPercent) / 100
  // Discount is capped at 100% of the subtotal, so the total can never go
  // negative (the server rejects a negative total).
  const total = subtotal + vatAmount + tipAmount + surcharge - discountAmount
  const perPerson = peopleCount > 0 ? total / peopleCount : total

  const updateLine = (itemId: string, updater: (line: BillLineState) => BillLineState) => {
    setBillLines((current) => {
      const existing = current[itemId] ?? { quantity: 0, note: '' }
      return { ...current, [itemId]: updater(existing) }
    })
  }

  const updateItemDraft = (item: BillItem, patch: Partial<ItemDraft>) => {
    setItemDrafts((current) => ({
      ...current,
      [item.id]: {
        ...(current[item.id] ?? draftFromItem(item, currency)),
        ...patch,
      },
    }))
    setItemValidationErrors((current) => ({ ...current, [item.id]: {} }))
    setItemSaveErrors((current) => {
      const next = { ...current }
      delete next[item.id]
      return next
    })
  }

  const beginItemEdit = (item: BillItem) => {
    setItemDrafts((current) => ({
      ...current,
      [item.id]: current[item.id] ?? draftFromItem(item, currency),
    }))
    setEditingItemIds((current) => new Set(current).add(item.id))
  }

  const closeItemEdit = (itemId: string) => {
    setEditingItemIds((current) => {
      const next = new Set(current)
      next.delete(itemId)
      return next
    })
  }

  const cancelItemDraft = (itemId: string) => {
    setItemDrafts((current) => {
      const next = { ...current }
      delete next[itemId]
      return next
    })
    setItemValidationErrors((current) => {
      const next = { ...current }
      delete next[itemId]
      return next
    })
    setItemSaveErrors((current) => {
      const next = { ...current }
      delete next[itemId]
      return next
    })
    closeItemEdit(itemId)
  }

  const handleSaveItem = async (item: BillItem) => {
    if (!menuId || savingItemId) return
    const draft = itemDrafts[item.id] ?? draftFromItem(item, currency)
    const validationErrors = validateDraft(draft, t)
    if (Object.keys(validationErrors).length > 0) {
      setItemValidationErrors((current) => ({
        ...current,
        [item.id]: validationErrors,
      }))
      return
    }

    setSavingItemId(item.id)
    setItemSaveErrors((current) => {
      const next = { ...current }
      delete next[item.id]
      return next
    })
    try {
      const normalized = normalizeDraft(draft)
      const updated = await apiRequest<MenuItemResult>(
        `/api/v1/menus/${menuId}/items/${item.id}`,
        {
          method: 'PATCH',
          token: accessToken ?? undefined,
          body: JSON.stringify(normalized),
        },
      )
      setMenu((current) =>
        current
          ? {
              ...current,
              items: current.items.map((existing) =>
                existing.id === updated.id ? updated : existing,
              ),
              updated_at: new Date().toISOString(),
            }
          : current,
      )
      setServerItems((current) =>
        current.map((existing) => (existing.id === updated.id ? updated : existing)),
      )
      cancelItemDraft(item.id)
      closeItemEdit(item.id)
      toast.show({ variant: 'success', title: t('menuDetail.toast.itemSaved') })
    } catch (err) {
      setItemSaveErrors((current) => ({
        ...current,
        [item.id]: err instanceof ApiError ? err.message : t('menuDetail.errors.saveItemFailed'),
      }))
    } finally {
      setSavingItemId(null)
    }
  }

  const handleDeleteItem = async (item: BillItem) => {
    if (!menuId || deletingItemId) return
    const shouldDelete = window.confirm(t('menuDetail.confirmDeleteItem', { name: item.original_name }))
    if (!shouldDelete) return

    setDeletingItemId(item.id)
    setItemSaveErrors((current) => {
      const next = { ...current }
      delete next[item.id]
      return next
    })
    try {
      await apiRequest(`/api/v1/menus/${menuId}/items/${item.id}`, {
        method: 'DELETE',
        token: accessToken ?? undefined,
      })
      setMenu((current) =>
        current
          ? {
              ...current,
              items: current.items.filter((existing) => existing.id !== item.id),
              updated_at: new Date().toISOString(),
            }
          : current,
      )
      setBillLines((current) => {
        const next = { ...current }
        delete next[item.id]
        return next
      })
      setServerItems((current) => current.filter((existing) => existing.id !== item.id))
      setItemsMeta((current) =>
        current ? { ...current, total: Math.max(0, current.total - 1) } : current,
      )
      cancelItemDraft(item.id)
      closeItemEdit(item.id)
      toast.show({ variant: 'success', title: t('menuDetail.toast.itemDeleted') })
    } catch (err) {
      setItemSaveErrors((current) => ({
        ...current,
        [item.id]: err instanceof ApiError ? err.message : t('menuDetail.errors.deleteItemFailed'),
      }))
    } finally {
      setDeletingItemId(null)
    }
  }

  const handleDelete = async () => {
    if (!menuId || deleting) return
    if (!confirmLeaveWithUnsavedChanges()) return
    setDeleting(true)
    setError(null)
    try {
      await apiRequest(`/api/v1/menus/${menuId}`, {
        method: 'DELETE',
        token: accessToken ?? undefined,
      })
      navigate('/app/menus', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('menuDetail.errors.deleteMenuFailed'))
      setDeleting(false)
    }
  }

  const handleAddManualItem = async () => {
    if (!menuId || addingManual) return
    const name = manualName.trim()
    const price = Number(manualPrice)
    if (!name || !Number.isFinite(price) || price < 0) return

    setAddingManual(true)
    setError(null)
    try {
      const item = await apiRequest<MenuItemResult>(
        `/api/v1/menus/${menuId}/items`,
        {
          method: 'POST',
          token: accessToken ?? undefined,
          body: JSON.stringify({
            original_name: name,
            original_description: manualNote.trim() || null,
            price: String(price),
            currency,
            category: 'Manual',
          }),
        },
      )
      setMenu((current) =>
        current
          ? {
              ...current,
              items: [...current.items, item],
              updated_at: new Date().toISOString(),
            }
          : current,
      )
      setBillLines((current) => ({
        ...current,
        [item.id]: { quantity: 1, note: manualNote.trim() },
      }))
      setManualName('')
      setManualPrice('')
      setManualNote('')
      setActiveCategory('All')
      toast.show({ variant: 'success', title: t('menuDetail.toast.itemAdded') })
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : t('menuDetail.errors.addManualFailed'),
      )
    } finally {
      setAddingManual(false)
    }
  }

  const handleConfirmMenu = async () => {
    if (!menuId || confirming || selectedLines.length === 0) return
    if (!confirmLeaveWithUnsavedChanges()) return
    setConfirming(true)
    setError(null)
    try {
      const confirmed = await apiRequest<MenuDetail>(
        `/api/v1/menus/${menuId}/confirm`,
        {
          method: 'POST',
          token: accessToken ?? undefined,
        },
      )
      setMenu((current) =>
        current
          ? {
              ...confirmed,
              items: current.items,
            }
          : confirmed,
      )
      toast.show({ variant: 'success', title: t('menuDetail.toast.menuConfirmed') })
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : t('menuDetail.errors.confirmMenuFailed'),
      )
    } finally {
      setConfirming(false)
    }
  }

  const handleCreateReceipt = async () => {
    if (!menuId || creatingBill || selectedLines.length === 0) return
    setCreatingBill(true)
    try {
      const bill = await apiRequest<Bill>(`/api/v1/bills`, {
        method: 'POST',
        token: accessToken ?? undefined,
        body: JSON.stringify({ menu_id: menuId }),
      })
      await apiRequest<Bill>(`/api/v1/bills/${bill.id}/items`, {
        method: 'PATCH',
        token: accessToken ?? undefined,
        body: JSON.stringify({
          items: selectedLines.map((line) => ({
            food_item_id: line.item.id,
            quantity: line.state.quantity,
          })),
        }),
      })

      // Persist the calculator's VAT / tip / surcharge so the receipt matches the
      // preview. The server recomputes every amount from these values.
      const adjustments: Array<{
        type: string
        calculation_type: string
        label: string
        value: number
      }> = []
      if (vatPercent > 0) {
        adjustments.push({
          type: 'TAX',
          calculation_type: 'PERCENTAGE',
          label: t('menuDetail.vat'),
          value: vatPercent,
        })
      }
      if (tipPercent > 0) {
        adjustments.push({
          type: 'SERVICE_CHARGE',
          calculation_type: 'PERCENTAGE',
          label: t('menuDetail.tip'),
          value: tipPercent,
        })
      }
      if (surcharge > 0) {
        adjustments.push({
          type: 'SURCHARGE',
          calculation_type: 'FIXED',
          label: t('menuDetail.surcharge'),
          value: surcharge,
        })
      }
      if (discountPercent > 0) {
        adjustments.push({
          type: 'DISCOUNT',
          calculation_type: 'PERCENTAGE',
          label: t('menuDetail.discount'),
          value: discountPercent,
        })
      }
      for (const adjustment of adjustments) {
        await apiRequest<unknown>(`/api/v1/bills/${bill.id}/adjustments`, {
          method: 'POST',
          token: accessToken ?? undefined,
          body: JSON.stringify(adjustment),
        })
      }

      navigate(`/app/bills/${bill.id}?people=${peopleCount}`)
    } catch (err) {
      const description = err instanceof ApiError ? err.message : undefined
      toast.show({
        variant: 'error',
        title: t('menuDetail.toast.createReceiptFailed'),
        description: description ?? t('menuDetail.errors.tryAgain'),
      })
    } finally {
      setCreatingBill(false)
    }
  }

  return (
    <div className="min-h-full bg-app-bg">
      <div className="mx-auto w-full max-w-[1240px] px-4 py-[24px] pb-[150px] sm:px-[50px]">
        <Link
          to="/app/menus"
          onClick={(event) => {
            if (!confirmLeaveWithUnsavedChanges()) event.preventDefault()
          }}
          className="mb-5 flex w-fit items-center gap-2 text-[14px] text-ink-variant transition-colors hover:text-primary-dark"
        >
          <ArrowLeft className="size-4" aria-hidden />
          {t('menuDetail.backToMenus')}
        </Link>

        {error && (
          <div
            role="alert"
            className="mb-5 flex items-center gap-3 rounded-[8px] border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
          >
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center gap-4 rounded-[8px] border border-hairline bg-canvas px-4 py-[70px] text-center text-ink-variant">
            <Loader2 className="size-8 animate-spin text-primary-dark" aria-hidden />
            {t('menuDetail.loading')}
          </div>
        ) : menu ? (
          <>
            <header className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="flex items-center gap-1 rounded-full bg-[#e4f4df] px-2.5 py-0.5 text-[12px] font-bold text-[#256b2b]">
                    <CheckCircle2 className="size-3.5" aria-hidden />
                    {menu.status === 'CONFIRMED' ? t('menuDetail.confirmed') : t('menuDetail.draft')}
                  </span>
                  <span className="rounded-full bg-secondary px-2.5 py-0.5 text-[12px] font-medium text-ink-variant">
                    {t('menuDetail.dishCount', { count: allItems.length })}
                  </span>
                </div>
                <h1 className="mb-1 text-[30px] font-bold leading-[38px] text-primary-dark sm:text-[38px] sm:leading-[46px]">
                  {menu.title}
                </h1>
                <p className="mb-0 text-[14px] text-ink-variant">
                  {menu.source.file_name} · {menu.default_currency ?? currency}
                </p>
              </div>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="flex min-h-10 w-fit items-center gap-2 rounded-[8px] border border-destructive/30 px-4 py-2 text-[14px] font-bold text-destructive transition-colors hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {deleting ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Trash2 className="size-4" aria-hidden />
                )}
                {t('menuDetail.deleteMenu')}
              </button>
            </header>

            <SourcePreview source={menu.source} accessToken={accessToken} />

            {hasUnsavedChanges && (
              <div className="mb-5 flex items-center gap-3 rounded-[8px] border border-[#d7a315]/40 bg-[#fff8e2] px-4 py-3 text-[14px] font-medium text-[#80600d]">
                <AlertCircle className="size-4 shrink-0" aria-hidden />
                {t('menuDetail.unsavedChanges', { count: dirtyItemIds.length })}
              </div>
            )}

            <MenuFilterBar
              searchInput={searchInput}
              onSearchChange={setSearchInput}
              minPriceInput={minPriceInput}
              onMinPriceChange={setMinPriceInput}
              maxPriceInput={maxPriceInput}
              onMaxPriceChange={setMaxPriceInput}
              categories={categories}
              activeCategory={activeCategory}
              onCategoryChange={setActiveCategory}
              hasActiveFilter={hasActiveFilter}
              onClearFilters={handleClearFilters}
              addingManual={addingManual}
              onAddManualItem={() => void handleAddManualItem()}
            />

            {itemsError && (
              <div
                role="alert"
                className="mb-4 flex items-center gap-3 rounded-[8px] border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
              >
                <AlertCircle className="size-4 shrink-0" aria-hidden />
                {itemsError}
              </div>
            )}

            <p className="mb-3 text-[13px] text-ink-variant" aria-live="polite">
              {itemsLoading && hasActiveFilter
                ? t('menuDetail.searching')
                : (hasActiveFilter && itemsMeta ? t('menuDetail.resultCountOf', { count: filteredItems.length, total: itemsMeta.total }) : t('menuDetail.resultCount', { count: filteredItems.length }))}
            </p>

            <main className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              {filteredItems.map((item) => (
                <BillItemCard
                  key={item.id}
                  item={item}
                  dietProfile={dietProfile}
                  draft={itemDrafts[item.id] ?? draftFromItem(item, currency)}
                  editing={editingItemIds.has(item.id)}
                  dirty={
                    itemDrafts[item.id]
                      ? !draftMatchesItem(itemDrafts[item.id], item, currency)
                      : false
                  }
                  line={billLines[item.id] ?? { quantity: 0, note: '' }}
                  currency={currency}
                  displayCurrency={displayCurrency}
                  rates={exchangeRates}
                  validationErrors={itemValidationErrors[item.id] ?? {}}
                  saveError={itemSaveErrors[item.id] ?? null}
                  saving={savingItemId === item.id}
                  deleting={deletingItemId === item.id}
                  onDraftChange={(patch) => updateItemDraft(item, patch)}
                  onEdit={() => beginItemEdit(item)}
                  onSave={() => void handleSaveItem(item)}
                  onCancel={() => cancelItemDraft(item.id)}
                  onDelete={() => void handleDeleteItem(item)}
                  onQuantityChange={(nextQuantity) =>
                    updateLine(item.id, (line) => ({
                      ...line,
                      quantity: Math.max(0, nextQuantity),
                    }))
                  }
                  onNoteChange={(note) =>
                    updateLine(item.id, (line) => ({ ...line, note }))
                  }
                />
              ))}
              <ManualItemCard
                name={manualName}
                price={manualPrice}
                note={manualNote}
                saving={addingManual}
                onNameChange={setManualName}
                onPriceChange={setManualPrice}
                onNoteChange={setManualNote}
                onSave={() => void handleAddManualItem()}
              />
              {!itemsLoading && filteredItems.length === 0 && (
                <div className="col-span-full flex min-h-[170px] flex-col items-center justify-center gap-3 rounded-[8px] border border-dashed border-hairline bg-canvas/70 p-6 text-center text-ink-variant">
                  <XCircle className="size-7" aria-hidden />
                  {hasActiveFilter ? (
                    <>
                      <span>{t('menuDetail.noFilterMatch')}</span>
                      <button
                        type="button"
                        onClick={handleClearFilters}
                        className="rounded-[8px] border border-primary-dark px-4 py-2 text-[13px] font-bold text-primary-dark transition-colors hover:bg-primary/10"
                      >
                        {t('menuDetail.clearFilters')}
                      </button>
                    </>
                  ) : (
                    <span>{t('menuDetail.noItems')}</span>
                  )}
                </div>
              )}
              {itemsLoading && hasActiveFilter && filteredItems.length === 0 && (
                <div className="col-span-full flex min-h-[170px] items-center justify-center gap-3 rounded-[8px] border border-dashed border-hairline bg-canvas/70 p-6 text-[14px] text-ink-variant">
                  <Loader2 className="size-6 animate-spin text-primary-dark" aria-hidden />
                  {t('menuDetail.loadingShort')}
                </div>
              )}
            </main>

            {canLoadMoreItems && (
              <div className="mt-5 flex justify-center">
                <button
                  type="button"
                  onClick={() => void loadItems(itemsPage + 1, 'append')}
                  disabled={itemsLoading}
                  className="flex min-h-10 items-center gap-2 rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {itemsLoading ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <Plus className="size-4" aria-hidden />
                  )}
                  {t('menuDetail.loadMore')}
                </button>
              </div>
            )}

            <section
              aria-labelledby="bill-calculator-title"
              className="mt-8 rounded-[8px] border border-hairline bg-canvas px-4 py-4"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2
                    id="bill-calculator-title"
                    className="mb-1 text-[16px] font-bold text-primary-dark"
                  >
                    {t('menuDetail.calcTitle')}
                  </h2>
                  <p className="mb-0 text-[13px] text-ink-variant">
                    {selectedLines.length > 0
                      ? t('menuDetail.selectedCount', { count: selectedLines.length })
                      : t('menuDetail.selectPrompt')}
                  </p>
                </div>
                <CurrencySelect
                  value={displayCurrency}
                  onChange={setDisplayCurrency}
                />
                <label className="flex items-center gap-3 text-[14px] font-medium text-ink">
                  <Users className="size-4 text-primary-dark" aria-hidden />
                  {t('menuDetail.peopleCount')}
                  <input
                    type="number"
                    min={1}
                    value={peopleCount}
                    onChange={(event) =>
                      setPeopleCount(Math.max(1, Number(event.target.value) || 1))
                    }
                    className="h-9 w-20 rounded-[8px] border border-hairline bg-white px-3 text-center text-[14px] text-ink outline-none focus:border-primary-dark"
                  />
                </label>
                <div className="flex items-center gap-2 text-[14px] text-ink-variant">
                  <span>{t('menuDetail.perPerson')}</span>
                  <strong className="text-[20px] text-primary-dark">
                    {formatConvertedAmount(perPerson, currency, displayCurrency, exchangeRates)}
                  </strong>
                </div>
              </div>

              {/* VAT / tip / surcharge / discount — percentages apply to the subtotal. */}
              <div className="mt-4 grid grid-cols-1 gap-3 border-t border-hairline pt-4 sm:grid-cols-2 lg:grid-cols-4">
                <label className="flex items-center justify-between gap-3 text-[14px] font-medium text-ink">
                  <span className="flex items-center gap-2">
                    <Percent className="size-4 text-primary-dark" aria-hidden />
                    {t('menuDetail.vat')}
                    <span className="text-[12px] font-normal text-ink-variant">(%)</span>
                  </span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min={0}
                    max={100}
                    step={0.5}
                    value={vatPercent}
                    onChange={(event) => setVatPercent(clampPercent(event.target.value))}
                    className="h-9 w-24 rounded-[8px] border border-hairline bg-white px-3 text-right text-[14px] text-ink outline-none focus:border-primary-dark"
                  />
                </label>
                <label className="flex items-center justify-between gap-3 text-[14px] font-medium text-ink">
                  <span className="flex items-center gap-2">
                    <HandCoins className="size-4 text-primary-dark" aria-hidden />
                    {t('menuDetail.tip')}
                    <span className="text-[12px] font-normal text-ink-variant">(%)</span>
                  </span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min={0}
                    max={100}
                    step={1}
                    value={tipPercent}
                    onChange={(event) => setTipPercent(clampPercent(event.target.value))}
                    className="h-9 w-24 rounded-[8px] border border-hairline bg-white px-3 text-right text-[14px] text-ink outline-none focus:border-primary-dark"
                  />
                </label>
                <label className="flex items-center justify-between gap-3 text-[14px] font-medium text-ink">
                  <span className="flex items-center gap-2">
                    <Receipt className="size-4 text-primary-dark" aria-hidden />
                    {t('menuDetail.surcharge')}
                    {currency && (
                      <span className="text-[12px] font-normal text-ink-variant">
                        ({currency})
                      </span>
                    )}
                  </span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min={0}
                    value={surcharge}
                    onChange={(event) =>
                      setSurcharge(Math.max(0, Number(event.target.value) || 0))
                    }
                    className="h-9 w-24 rounded-[8px] border border-hairline bg-white px-3 text-right text-[14px] text-ink outline-none focus:border-primary-dark"
                  />
                </label>
                <label className="flex items-center justify-between gap-3 text-[14px] font-medium text-ink">
                  <span className="flex items-center gap-2">
                    <Tag className="size-4 text-primary-dark" aria-hidden />
                    {t('menuDetail.discount')}
                    <span className="text-[12px] font-normal text-ink-variant">(%)</span>
                  </span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min={0}
                    max={100}
                    step={1}
                    value={discountPercent}
                    onChange={(event) => setDiscountPercent(clampPercent(event.target.value))}
                    className="h-9 w-24 rounded-[8px] border border-hairline bg-white px-3 text-right text-[14px] text-ink outline-none focus:border-primary-dark"
                  />
                </label>
              </div>

              {selectedLines.length > 0 && (
                <div className="mt-4 border-t border-hairline pt-4">
                  <div className="flex flex-col gap-2">
                    {selectedLines.map(({ item, state }) => (
                      <div
                        key={item.id}
                        className="flex items-start justify-between gap-3 rounded-[8px] bg-surface-muted px-3 py-2 text-[14px]"
                      >
                        <div className="min-w-0">
                          <p className="mb-0 truncate font-semibold text-ink">
                            {state.quantity} x{' '}
                            <ItemDisplayName
                              item={item}
                              originalClassName="text-[12px] text-ink-variant/50"
                            />
                          </p>
                          {state.note && (
                            <p className="mb-0 mt-1 text-[12px] text-ink-variant">
                              {state.note}
                            </p>
                          )}
                        </div>
                        <span className="shrink-0 font-bold text-primary-dark">
                          {formatConvertedAmount(
                            itemPrice(item) * state.quantity,
                            item.currency ?? currency,
                            displayCurrency,
                            exchangeRates,
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 flex flex-col gap-2 border-t border-hairline pt-4 text-[14px] sm:items-end">
                    <div className="flex w-full justify-between gap-3 sm:w-[280px]">
                      <span className="text-ink-variant">{t('menuDetail.subtotal')}</span>
                      <strong className="text-ink">
                        {formatConvertedAmount(subtotal, currency, displayCurrency, exchangeRates)}
                      </strong>
                    </div>
                    {vatAmount > 0 && (
                      <div className="flex w-full justify-between gap-3 sm:w-[280px]">
                        <span className="text-ink-variant">
                          {t('menuDetail.vat')} · {vatPercent}%
                        </span>
                        <span className="text-ink">
                          {formatConvertedAmount(vatAmount, currency, displayCurrency, exchangeRates)}
                        </span>
                      </div>
                    )}
                    {tipAmount > 0 && (
                      <div className="flex w-full justify-between gap-3 sm:w-[280px]">
                        <span className="text-ink-variant">
                          {t('menuDetail.tip')} · {tipPercent}%
                        </span>
                        <span className="text-ink">
                          {formatConvertedAmount(tipAmount, currency, displayCurrency, exchangeRates)}
                        </span>
                      </div>
                    )}
                    {surcharge > 0 && (
                      <div className="flex w-full justify-between gap-3 sm:w-[280px]">
                        <span className="text-ink-variant">{t('menuDetail.surcharge')}</span>
                        <span className="text-ink">
                          {formatConvertedAmount(surcharge, currency, displayCurrency, exchangeRates)}
                        </span>
                      </div>
                    )}
                    {discountAmount > 0 && (
                      <div className="flex w-full justify-between gap-3 sm:w-[280px]">
                        <span className="text-ink-variant">
                          {t('menuDetail.discount')} · {discountPercent}%
                        </span>
                        <span className="text-primary-dark">
                          −{formatConvertedAmount(discountAmount, currency, displayCurrency, exchangeRates)}
                        </span>
                      </div>
                    )}
                    <div className="flex w-full justify-between gap-3 border-t border-hairline pt-2 sm:w-[280px]">
                      <span className="font-bold text-ink">{t('menuDetail.total')}</span>
                      <strong className="text-[16px] text-ink">
                        {formatConvertedAmount(total, currency, displayCurrency, exchangeRates)}
                      </strong>
                    </div>
                    <div className="flex w-full justify-between gap-3 sm:w-[280px]">
                      <span className="text-ink-variant">{t('menuDetail.splitAmong', { count: peopleCount })}</span>
                      <strong className="text-primary-dark">
                        {formatConvertedAmount(perPerson, currency, displayCurrency, exchangeRates)}
                      </strong>
                    </div>
                  </div>
                </div>
              )}
            </section>
            <div className="fixed inset-x-0 bottom-0 z-20 border-t border-hairline bg-surface-muted px-4 py-[20px] shadow-[0_-10px_30px_rgba(24,29,21,0.08)] sm:px-[50px] sm:py-[30px]">
              <div className="mx-auto flex max-w-[1240px] flex-col justify-center gap-3 sm:min-h-11 sm:flex-row sm:items-center sm:justify-end">
                <Link
                  to="/app/scan"
                  onClick={(event) => {
                    if (!confirmLeaveWithUnsavedChanges()) event.preventDefault()
                  }}
                  className="flex min-h-11 items-center justify-center rounded-[8px] border border-hairline bg-canvas px-5 text-[14px] font-bold text-ink transition-colors hover:bg-white"
                >
                  {t('menuDetail.scanAnother')}
                </Link>
                <button
                  type="button"
                  onClick={() => void handleCreateReceipt()}
                  disabled={creatingBill || selectedLines.length === 0}
                  className="flex min-h-11 items-center justify-center gap-2 rounded-[8px] border border-primary-dark bg-canvas px-5 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {creatingBill ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <ReceiptText className="size-4" aria-hidden />
                  )}
                  {t('menuDetail.showBill')}
                </button>
                <button
                  type="button"
                  onClick={() => void handleConfirmMenu()}
                  disabled={confirming || selectedLines.length === 0}
                  className="flex min-h-11 items-center justify-center rounded-[8px] bg-primary-dark px-8 text-[14px] font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {confirming ? (
                    <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />
                  ) : null}
                  {menu.status === 'CONFIRMED' ? t('menuDetail.confirmedBtn') : t('menuDetail.reviewConfirm')}
                </button>
              </div>
            </div>
          </>
        ) : error ? (
          <div className="flex flex-col items-center gap-4 rounded-[8px] border border-hairline bg-canvas px-4 py-[70px] text-center">
            <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10">
              <AlertCircle className="size-7 text-destructive" aria-hidden />
            </span>
            <p role="alert" className="max-w-[360px] text-[14px] text-destructive">
              {error}
            </p>
            <button
              type="button"
              onClick={() => void loadMenu()}
              className="flex min-h-10 items-center gap-2 rounded-[8px] border border-destructive/30 px-4 py-2 text-[14px] font-medium text-destructive transition-colors hover:bg-destructive/10"
            >
              <RefreshCw className="size-4" aria-hidden />
              {t('common.retry')}
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 rounded-[8px] border border-hairline bg-canvas px-4 py-[70px] text-center text-ink-variant">
            <XCircle className="size-8 text-destructive" aria-hidden />
            <p className="text-[15px] font-medium text-ink">{t('menuDetail.notFound')}</p>
            <Link
              to="/app/menus"
              className="rounded-[8px] bg-primary-dark px-5 py-2 text-[14px] font-bold text-white transition-opacity hover:opacity-90"
            >
              {t('menuDetail.backToMenus')}
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
