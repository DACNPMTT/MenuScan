import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FileText,
  ImageIcon,
  Loader2,
  Minus,
  Pencil,
  Plus,
  ReceiptText,
  RotateCcw,
  Save,
  Search,
  Trash2,
  Users,
  XCircle,
} from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { getAccessToken, refreshAccessToken } from '@/shared/lib/auth-token'
import { ApiError, apiRequest } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import type { MenuDetail, MenuItemResult } from '@/features/menu-scan/types'

interface BillLineState {
  quantity: number
  note: string
}

interface ItemDraft {
  original_name: string
  translated_name: string
  original_description: string
  translated_description: string
  price: string
  currency: string
  category: string
}

interface ItemValidationErrors {
  original_name?: string
  price?: string
}

type BillItem = MenuItemResult

const API_BASE_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(
  /\/$/,
  '',
)
const LOW_CONFIDENCE_THRESHOLD = 0.75
const UNSAVED_CHANGES_MESSAGE =
  'Bạn có thay đổi chưa lưu. Rời trang sẽ mất các chỉnh sửa này?'

function formatMoney(amount: number, currency: string | null): string {
  const resolvedCurrency = currency ?? 'VND'
  if (resolvedCurrency === 'VND') {
    return `${Math.round(amount).toLocaleString('vi-VN')}đ`
  }
  return `${amount.toFixed(2)} ${resolvedCurrency}`
}

function itemPrice(item: BillItem): number {
  const value = Number(item.price)
  return Number.isFinite(value) ? value : 0
}

function draftFromItem(item: BillItem, fallbackCurrency: string | null): ItemDraft {
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

function normalizeDraft(draft: ItemDraft) {
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

function draftMatchesItem(
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

function validateDraft(draft: ItemDraft): ItemValidationErrors {
  const errors: ItemValidationErrors = {}
  if (!draft.original_name.trim()) {
    errors.original_name = 'Tên gốc không được để trống.'
  }
  const price = draft.price.trim()
  if (price) {
    const numericPrice = Number(price)
    if (!Number.isFinite(numericPrice) || numericPrice < 0) {
      errors.price = 'Giá phải là số không âm.'
    }
  }
  return errors
}

function confidenceValue(item: BillItem): number | null {
  if (item.confidence_score === null || item.confidence_score === undefined) {
    return null
  }
  const value = Number(item.confidence_score)
  return Number.isFinite(value) ? value : null
}

function itemCategory(item: BillItem): string {
  return item.category?.trim() || 'Other'
}

function hasAllergySignal(item: BillItem): boolean {
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

function ItemDisplayName({
  item,
  originalClassName = 'text-ink-variant/40',
}: {
  item: BillItem
  originalClassName?: string
}) {
  if (item.translated_name && item.translated_name !== item.original_name) {
    return (
      <>
        {item.translated_name}
        <span className={`ml-1 font-medium ${originalClassName}`}>
          ({item.original_name})
        </span>
      </>
    )
  }
  return item.original_name
}

export function MenuDetailPage() {
  const { menuId } = useParams<{ menuId: string }>()
  const navigate = useNavigate()
  const { accessToken } = useAuth()
  const [menu, setMenu] = useState<MenuDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState('All')
  const [peopleCount, setPeopleCount] = useState(1)
  const [billLines, setBillLines] = useState<Record<string, BillLineState>>({})
  const [addingManual, setAddingManual] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [manualName, setManualName] = useState('')
  const [manualPrice, setManualPrice] = useState('')
  const [manualNote, setManualNote] = useState('')
  const [showReceipt, setShowReceipt] = useState(false)
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
      setError(err instanceof ApiError ? err.message : 'Không thể tải menu.')
    } finally {
      setLoading(false)
    }
  }, [accessToken, menuId])

  useEffect(() => {
    void Promise.resolve().then(loadMenu)
  }, [loadMenu])

  const allItems = useMemo<BillItem[]>(() => menu?.items ?? [], [menu?.items])

  const currency = useMemo(
    () => menu?.default_currency ?? allItems.find((item) => item.currency)?.currency ?? 'VND',
    [allItems, menu?.default_currency],
  )

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
    !hasUnsavedChanges || window.confirm(UNSAVED_CHANGES_MESSAGE)

  const categories = useMemo(() => {
    const seen = new Set<string>()
    allItems.forEach((item) => seen.add(itemCategory(item)))
    return ['All', ...Array.from(seen)]
  }, [allItems])

  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    return allItems.filter((item) => {
      const matchesCategory =
        activeCategory === 'All' || itemCategory(item) === activeCategory
      if (!matchesCategory) return false
      if (!normalizedQuery) return true
      return [
        item.original_name,
        item.translated_name,
        item.original_description,
        item.translated_description,
        item.category,
      ]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(normalizedQuery))
    })
  }, [activeCategory, allItems, query])

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

  const perPerson = peopleCount > 0 ? subtotal / peopleCount : subtotal

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
    const validationErrors = validateDraft(draft)
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
      cancelItemDraft(item.id)
      closeItemEdit(item.id)
    } catch (err) {
      setItemSaveErrors((current) => ({
        ...current,
        [item.id]: err instanceof ApiError ? err.message : 'Không thể lưu món.',
      }))
    } finally {
      setSavingItemId(null)
    }
  }

  const handleDeleteItem = async (item: BillItem) => {
    if (!menuId || deletingItemId) return
    const shouldDelete = window.confirm(`Xóa món "${item.original_name}" khỏi menu?`)
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
      cancelItemDraft(item.id)
      closeItemEdit(item.id)
    } catch (err) {
      setItemSaveErrors((current) => ({
        ...current,
        [item.id]: err instanceof ApiError ? err.message : 'Không thể xóa món.',
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
      setError(err instanceof ApiError ? err.message : 'Không thể xóa menu.')
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
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Không thể lưu món thủ công.',
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
      setShowReceipt(true)
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Không thể xác nhận menu.',
      )
    } finally {
      setConfirming(false)
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
          Về Menus
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
            Đang tải menu...
          </div>
        ) : menu ? (
          <>
            <header className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="flex items-center gap-1 rounded-full bg-[#e4f4df] px-2.5 py-0.5 text-[12px] font-bold text-[#256b2b]">
                    <CheckCircle2 className="size-3.5" aria-hidden />
                    {menu.status === 'CONFIRMED' ? 'Đã xác nhận' : 'Bản nháp'}
                  </span>
                  <span className="rounded-full bg-secondary px-2.5 py-0.5 text-[12px] font-medium text-ink-variant">
                    {allItems.length} món
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
                Xóa menu
              </button>
            </header>

            <SourcePreview source={menu.source} accessToken={accessToken} />

            {hasUnsavedChanges && (
              <div className="mb-5 flex items-center gap-3 rounded-[8px] border border-[#d7a315]/40 bg-[#fff8e2] px-4 py-3 text-[14px] font-medium text-[#80600d]">
                <AlertCircle className="size-4 shrink-0" aria-hidden />
                Có {dirtyItemIds.length} món đang chỉnh sửa chưa lưu.
              </div>
            )}

            <div className="mb-6 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
              <label className="relative block">
                <Search
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-variant"
                  aria-hidden
                />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search items..."
                  className="h-11 w-full rounded-[8px] border border-hairline bg-canvas pl-10 pr-3 text-[14px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary-dark"
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void handleAddManualItem()}
                  disabled={addingManual}
                  className="flex h-11 items-center gap-2 rounded-[8px] bg-primary-dark px-4 text-[14px] font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {addingManual ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <Plus className="size-4" aria-hidden />
                  )}
                  Add Manual Item
                </button>
                {categories.map((category) => (
                  <button
                    type="button"
                    key={category}
                    onClick={() => setActiveCategory(category)}
                    className={
                      activeCategory === category
                        ? 'h-11 rounded-[8px] bg-primary-dark px-4 text-[14px] font-bold text-white'
                        : 'h-11 rounded-[8px] border border-hairline bg-canvas px-4 text-[14px] font-medium text-primary-dark transition-colors hover:bg-surface-muted'
                    }
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>

            <main className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              {filteredItems.map((item) => (
                <BillItemCard
                  key={item.id}
                  item={item}
                  draft={itemDrafts[item.id] ?? draftFromItem(item, currency)}
                  editing={editingItemIds.has(item.id)}
                  dirty={
                    itemDrafts[item.id]
                      ? !draftMatchesItem(itemDrafts[item.id], item, currency)
                      : false
                  }
                  line={billLines[item.id] ?? { quantity: 0, note: '' }}
                  currency={currency}
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
              {filteredItems.length === 0 && (
                <div className="flex min-h-[170px] flex-col items-center justify-center gap-3 rounded-[8px] border border-dashed border-hairline bg-canvas/70 p-6 text-center text-ink-variant">
                  <XCircle className="size-7" aria-hidden />
                  Không có món phù hợp.
                </div>
              )}
            </main>

            <div className="mt-8 rounded-[8px] border border-hairline bg-canvas px-4 py-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <label className="flex items-center gap-3 text-[14px] font-medium text-ink">
                  <Users className="size-4 text-primary-dark" aria-hidden />
                  Number of People
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
                  <span>Estimated Per Person:</span>
                  <strong className="text-[20px] text-primary-dark">
                    {formatMoney(perPerson, currency)}
                  </strong>
                </div>
              </div>
            </div>

            {showReceipt && (
              <ReceiptPreview
                lines={selectedLines}
                currency={currency}
                subtotal={subtotal}
                peopleCount={peopleCount}
              />
            )}

            <div className="fixed inset-x-0 bottom-0 z-20 border-t border-hairline bg-surface-muted px-4 py-[20px] shadow-[0_-10px_30px_rgba(24,29,21,0.08)] sm:px-[50px] sm:py-[30px]">
              <div className="mx-auto flex max-w-[1240px] flex-col justify-center gap-3 sm:min-h-11 sm:flex-row sm:items-center sm:justify-end">
                <Link
                  to="/app/scan"
                  onClick={(event) => {
                    if (!confirmLeaveWithUnsavedChanges()) event.preventDefault()
                  }}
                  className="flex min-h-11 items-center justify-center rounded-[8px] border border-hairline bg-canvas px-5 text-[14px] font-bold text-ink transition-colors hover:bg-white"
                >
                  Scan Another Menu
                </Link>
                <button
                  type="button"
                  onClick={() => setShowReceipt((current) => !current)}
                  disabled={selectedLines.length === 0}
                  className="flex min-h-11 items-center justify-center gap-2 rounded-[8px] border border-primary-dark bg-canvas px-5 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <ReceiptText className="size-4" aria-hidden />
                  Show Digital Receipt
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
                  {menu.status === 'CONFIRMED' ? 'Confirmed' : 'Review / Confirm'}
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-4 rounded-[8px] border border-hairline bg-canvas px-4 py-[70px] text-center text-ink-variant">
            <XCircle className="size-8 text-destructive" aria-hidden />
            Không tìm thấy menu.
          </div>
        )}
      </div>
    </div>
  )
}

function SourcePreview({
  source,
  accessToken,
}: {
  source: MenuDetail['source']
  accessToken: string | null
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState(false)
  const isImage = source.mime_type.startsWith('image/')
  const isPdf = source.mime_type === 'application/pdf'

  useEffect(() => {
    let active = true
    let nextObjectUrl: string | null = null

    const fetchPreview = async (previewUrl: string, token: string | null) =>
      fetch(previewUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
      })

    const loadPreview = async () => {
      setPreviewError(false)
      setObjectUrl(null)
      try {
        const previewUrl = source.preview_url.startsWith('http')
          ? source.preview_url
          : `${API_BASE_URL}${source.preview_url}`
        const token = getAccessToken() ?? accessToken
        let response = await fetchPreview(previewUrl, token)
        if (response.status === 401 || response.status === 403) {
          const freshToken = await refreshAccessToken()
          if (freshToken) response = await fetchPreview(previewUrl, freshToken)
        }
        if (!response.ok) throw new Error('Preview request failed')
        const blob = await response.blob()
        nextObjectUrl = URL.createObjectURL(blob)
        if (active) {
          setObjectUrl(nextObjectUrl)
        } else {
          URL.revokeObjectURL(nextObjectUrl)
        }
      } catch {
        if (active) setPreviewError(true)
      }
    }

    void loadPreview()
    return () => {
      active = false
      if (nextObjectUrl) URL.revokeObjectURL(nextObjectUrl)
    }
  }, [accessToken, source.preview_url])

  return (
    <section className="mb-6 grid gap-4 rounded-[8px] border border-hairline bg-canvas p-4 lg:grid-cols-[300px_minmax(0,1fr)]">
      <div className="flex min-h-[220px] items-center justify-center overflow-hidden rounded-[8px] border border-hairline bg-surface-muted">
        {objectUrl && isImage ? (
          <img
            src={objectUrl}
            alt={source.file_name}
            className="h-full max-h-[360px] w-full object-contain"
          />
        ) : objectUrl && isPdf ? (
          <iframe
            title={source.file_name}
            src={objectUrl}
            className="h-[360px] w-full border-0"
          />
        ) : previewError ? (
          <div className="flex flex-col items-center gap-2 text-center text-[13px] text-ink-variant">
            <FileText className="size-7" aria-hidden />
            Không thể tải ảnh gốc.
          </div>
        ) : (
          <Loader2 className="size-6 animate-spin text-primary-dark" aria-hidden />
        )}
      </div>
      <div className="flex min-w-0 flex-col justify-center gap-3">
        <div className="flex items-center gap-2 text-primary-dark">
          <ImageIcon className="size-5" aria-hidden />
          <h2 className="mb-0 text-[18px] font-bold">Ảnh menu gốc</h2>
        </div>
        <p className="mb-0 truncate text-[14px] text-ink-variant">
          {source.file_name}
        </p>
        <p className="mb-0 text-[13px] text-ink-variant/70">
          {source.mime_type} · {(source.file_size / 1024).toFixed(1)} KB
        </p>
      </div>
    </section>
  )
}

function BillItemCard({
  item,
  draft,
  editing,
  dirty,
  line,
  currency,
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
}: {
  item: BillItem
  draft: ItemDraft
  editing: boolean
  dirty: boolean
  line: BillLineState
  currency: string | null
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
}) {
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
                {formatMoney(itemPrice(item), item.currency ?? currency)}
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

function ManualItemCard({
  name,
  price,
  note,
  saving,
  onNameChange,
  onPriceChange,
  onNoteChange,
  onSave,
}: {
  name: string
  price: string
  note: string
  saving: boolean
  onNameChange: (value: string) => void
  onPriceChange: (value: string) => void
  onNoteChange: (value: string) => void
  onSave: () => void
}) {
  return (
    <div className="flex min-h-[190px] flex-col gap-4 rounded-[8px] border border-dashed border-primary-dark/70 bg-canvas/70 p-5">
      <div className="grid grid-cols-[minmax(0,1fr)_120px]">
        <input
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          placeholder="Item Name"
          className="h-11 rounded-l-[6px] border border-hairline bg-white px-3 text-[14px] outline-none placeholder:text-placeholder focus:border-primary-dark"
        />
        <input
          value={price}
          onChange={(event) => onPriceChange(event.target.value)}
          placeholder="Price"
          inputMode="decimal"
          className="h-11 rounded-r-[6px] border border-l-0 border-hairline bg-white px-3 text-right text-[14px] outline-none placeholder:text-placeholder focus:border-primary-dark"
        />
      </div>
      <textarea
        value={note}
        onChange={(event) => onNoteChange(event.target.value)}
        placeholder="Description/Note"
        className="min-h-[74px] resize-none rounded-[8px] border border-hairline bg-surface-muted px-3 py-2 text-[14px] outline-none placeholder:text-placeholder focus:border-primary-dark"
      />
      <button
        type="button"
        onClick={onSave}
        disabled={saving || !name.trim() || !Number.isFinite(Number(price))}
        className="ml-auto flex min-h-9 items-center gap-2 rounded-[8px] px-3 text-[13px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? (
          <Loader2 className="size-4 animate-spin" aria-hidden />
        ) : (
          <CheckCircle2 className="size-4" aria-hidden />
        )}
        Save Item
      </button>
    </div>
  )
}

function ReceiptPreview({
  lines,
  currency,
  subtotal,
  peopleCount,
}: {
  lines: Array<{ item: BillItem; state: BillLineState }>
  currency: string | null
  subtotal: number
  peopleCount: number
}) {
  return (
    <section className="mt-6 rounded-[8px] border border-primary-dark/30 bg-canvas p-5">
      <div className="mb-4 flex items-center gap-2 text-primary-dark">
        <ReceiptText className="size-5" aria-hidden />
        <h2 className="mb-0 text-[20px] font-bold">Digital Receipt</h2>
      </div>
      <div className="divide-y divide-hairline">
        {lines.map(({ item, state }) => (
          <div key={item.id} className="flex items-start justify-between gap-4 py-3">
            <div className="min-w-0">
              <p className="mb-0 truncate text-[15px] font-bold text-ink">
                {state.quantity} ×{' '}
                <ItemDisplayName
                  item={item}
                  originalClassName="text-[13px] text-ink-variant/40"
                />
              </p>
              {state.note && (
                <p className="mb-0 mt-1 text-[13px] text-ink-variant">{state.note}</p>
              )}
            </div>
            <span className="shrink-0 text-[15px] font-bold text-primary-dark">
              {formatMoney(itemPrice(item) * state.quantity, item.currency ?? currency)}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-col gap-2 border-t border-hairline pt-4 text-[15px] sm:items-end">
        <strong className="text-primary-dark">
          Total: {formatMoney(subtotal, currency)}
        </strong>
        <span className="text-ink-variant">
          Per person: {formatMoney(subtotal / Math.max(1, peopleCount), currency)}
        </span>
      </div>
    </section>
  )
}
