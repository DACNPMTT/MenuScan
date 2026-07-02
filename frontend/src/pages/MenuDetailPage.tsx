import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Minus,
  Plus,
  ReceiptText,
  Search,
  Trash2,
  Users,
  XCircle,
} from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { ApiError, apiRequest } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import type { MenuDetail, MenuItemResult } from '@/features/menu-scan/types'

interface BillLineState {
  quantity: number
  note: string
}

type BillItem = MenuItemResult

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

  const handleDelete = async () => {
    if (!menuId || deleting) return
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
                  line={billLines[item.id] ?? { quantity: 0, note: '' }}
                  currency={currency}
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

function BillItemCard({
  item,
  line,
  currency,
  onQuantityChange,
  onNoteChange,
}: {
  item: BillItem
  line: BillLineState
  currency: string | null
  onQuantityChange: (quantity: number) => void
  onNoteChange: (note: string) => void
}) {
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
        <strong className="shrink-0 text-[17px] text-primary-dark">
          {formatMoney(itemPrice(item), item.currency ?? currency)}
        </strong>
      </div>
      {primaryDescription && (
        <div className="flex flex-col gap-1.5">
          <p className="mb-0 text-[14px] leading-6 text-ink-variant">
            {primaryDescription}
          </p>
          {secondaryDescription && (
            <p className="mb-0 border-l-2 border-hairline pl-3 text-[13px] leading-5 text-ink-variant/65">
              {secondaryDescription}
            </p>
          )}
        </div>
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
