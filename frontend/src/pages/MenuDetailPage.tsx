import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Coins,
  HandCoins,
  Loader2,
  Percent,
  Receipt,
  ReceiptText,
  RefreshCw,
  Sparkles,
  Tag,
  Trash2,
  Users,
  XCircle,
} from 'lucide-react'
import { Spinner } from '@/shared/components/Spinner'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { apiRequest, apiRequestWithMeta } from '@/shared/lib/api'
import { describeError } from '@/shared/lib/errors'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useDebouncedValue } from '@/shared/hooks/useDebouncedValue'
import { useExchangeRates } from '@/shared/hooks/useExchangeRates'
import { CurrencySelect } from '@/shared/components/CurrencySelect'
import { Button } from '@/shared/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Reveal } from '@/shared/components/motion/Reveal'
import { CURRENCY_OPTIONS, convertAmount, formatConvertedAmount } from '@/shared/lib/currency'
import { cn } from '@/shared/lib/cn'
import {
  ALL_CATEGORY,
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
import {
  VERDICT_LEVELS,
  hasVerdicts,
  isProfileActive,
  rankByVerdict,
  rankDishes,
} from '@/features/menu-scan/ranking'
import { BillItemCard } from '@/features/menu-scan/components/menu-detail/BillItemCard'
import { GroupSplitPanel } from '@/features/menu-scan/components/menu-detail/GroupSplitPanel'
import { AssistantChat } from '@/features/menu-scan/components/menu-detail/AssistantChat'
import { ItemDisplayName } from '@/features/menu-scan/components/menu-detail/ItemDisplayName'
import { ManualItemCard } from '@/features/menu-scan/components/menu-detail/ManualItemCard'
import { MenuFilterBar } from '@/features/menu-scan/components/menu-detail/MenuFilterBar'
import type { Bill } from '@/features/billing/types'
import { SourcePreview } from '@/features/menu-scan/components/menu-detail/SourcePreview'
import type {
  BillItem,
  BillLineState,
  EnrichmentStatus,
  ItemDraft,
  ItemValidationErrors,
  MenuDetail,
  MenuEnrichResult,
  MenuItemResult,
  PaginationMeta,
} from '@/features/menu-scan/types'

// Bill-calculator adjustment fields (VAT / tip / surcharge / discount). The label
// stacks above a full-width input so the boxes align across the row no matter how
// long each label is.
const ADJUSTMENT_FIELD = 'flex flex-col gap-1.5'
const ADJUSTMENT_LABEL = 'flex items-center gap-1.5 text-[13px] font-medium text-ink'
const ADJUSTMENT_INPUT =
  'h-9 w-full rounded-xl border border-border bg-surface px-3 text-right text-[14px] text-ink outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary'
// A money field: a right-aligned number glued to a compact currency picker.
const MONEY_GROUP =
  'flex h-9 overflow-hidden rounded-xl border border-border bg-surface transition-colors focus-within:border-primary'
const MONEY_INPUT =
  'min-w-0 flex-1 px-3 text-right text-[14px] text-ink outline-none'

/** Dishes per page on the menu grid.
 *
 * Not ITEMS_PAGE_SIZE (50) — that is the server's search page. These cards are tall
 * and editable, two to a row; fifty of them is a page nobody scrolls to the bottom
 * of, and the diner is standing in a restaurant. */
const MENU_PAGE_SIZE = 10

/** Legend swatches. These must stay the same colours the cards carry on their left
 * edge (verdictCardClass in BillItemCard) — a key that does not match the thing it
 * is keying is worse than no key. */
const VERDICT_LEGEND_COLOR = {
  RECOMMENDED: 'bg-primary',
  OK: 'bg-primary/50',
  CAUTION: 'bg-amber',
  AVOID: 'bg-destructive',
} as const

/** Round to the 2 decimals the backend stores (NUMERIC(14,2)). */
function roundMoney(value: number): number {
  return Math.round(value * 100) / 100
}

/** One guest's pick of a dish, as the host's selections summary reports it. */
interface GuestPick {
  participant_id: string
  display_name: string
  quantity: number
  note: string | null
}

interface SelectionSummaryItem {
  food_item_id: string
  total_quantity: number
  selected_by: GuestPick[]
}

/** How a host's own (manually ticked) dish is charged when splitting per person. */
type HostItemAssignment = 'SPLIT' | 'HOST' | string // 'SPLIT' | 'HOST' | participant_id

const HOST_PAYER_KEY = 'HOST'

/** A non-negative money amount plus the currency it is typed in. The currency
 * picker is disabled while exchange rates are unavailable, so an amount can
 * never be entered in a currency we cannot convert to the bill's. */
function MoneyField({
  value,
  onValueChange,
  currency,
  onCurrencyChange,
  currencyLabel,
  currencyDisabled,
}: {
  value: number
  onValueChange: (next: number) => void
  currency: string
  onCurrencyChange: (next: string) => void
  currencyLabel: string
  currencyDisabled: boolean
}) {
  return (
    <div className={MONEY_GROUP}>
      <input
        type="number"
        inputMode="decimal"
        min={0}
        value={value}
        onChange={(event) => onValueChange(Math.max(0, Number(event.target.value) || 0))}
        className={MONEY_INPUT}
      />
      <Select value={currency} onValueChange={onCurrencyChange} disabled={currencyDisabled}>
        <SelectTrigger
          aria-label={currencyLabel}
          className="h-9 shrink-0 gap-1 border-0 border-l border-border bg-panel px-2 text-[12px] font-bold text-primary-dark shadow-none focus-visible:ring-0 data-[placeholder]:text-primary-dark"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {CURRENCY_OPTIONS.map((option) => (
            <SelectItem key={option.code} value={option.code}>
              {option.code}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

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
  const [discountPercent, setDiscountPercent] = useState(0)
  // Tip can be a percentage of the subtotal or a flat amount. Flat amounts (tip
  // and surcharge) are typed in a currency of the diner's choosing and converted
  // to the bill's own currency before they reach the server.
  // `currency` is derived further down (and is null until the menu loads), so the
  // pickers start unset and fall back to the bill's currency.
  const [tipMode, setTipMode] = useState<'PERCENT' | 'AMOUNT'>('PERCENT')
  const [tipPercent, setTipPercent] = useState(0)
  const [tipInput, setTipInput] = useState(0)
  const [tipCurrency, setTipCurrency] = useState<string | null>(null)
  const [surchargeInput, setSurchargeInput] = useState(0)
  const [surchargeCurrency, setSurchargeCurrency] = useState<string | null>(null)
  const [billLines, setBillLines] = useState<Record<string, BillLineState>>({})
  // The dish the diner most recently added — the assistant suggests it for a
  // quick question.
  const [lastSelectedItemId, setLastSelectedItemId] = useState<string | null>(null)
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
  // Group-session extras: which dining session (if any) produced this menu, what
  // each guest picked, and how the host wants the bill divided.
  const [diningSessionId, setDiningSessionId] = useState<string | null>(null)
  const [selectionsSummary, setSelectionsSummary] = useState<SelectionSummaryItem[]>([])
  const [splitMode, setSplitMode] = useState<'EVENLY' | 'BY_PERSON'>('EVENLY')
  const [hostItemAssignments, setHostItemAssignments] = useState<
    Record<string, HostItemAssignment>
  >({})

  useDocumentTitle(menu ? `${menu.title} | MenuScan` : 'Menu | MenuScan')

  // Guards a slow GET /menus from landing after — and overwriting — the enriched
  // menu the POST /enrich just gave us. A token refresh or a language switch is
  // enough to re-fire loadMenu mid-enrichment, and the stale response wins.
  const menuRequestRef = useRef(0)

  const loadMenu = useCallback(async () => {
    if (!menuId) return
    const requestId = ++menuRequestRef.current
    setLoading(true)
    setError(null)
    try {
      const data = await apiRequest<MenuDetail>(`/api/v1/menus/${menuId}`, {
        method: 'GET',
        token: accessToken ?? undefined,
      })
      if (requestId !== menuRequestRef.current) return
      setMenu(data)
      setItemDrafts({})
      setItemValidationErrors({})
      setItemSaveErrors({})
      setEditingItemIds(new Set())
    } catch (err) {
      if (requestId !== menuRequestRef.current) return
      setError(describeError(err, t, 'menuDetail.errors.loadFailed'))
    } finally {
      if (requestId === menuRequestRef.current) setLoading(false)
    }
  }, [accessToken, menuId, t])

  useEffect(() => {
    void Promise.resolve().then(loadMenu)
  }, [loadMenu])

  // Food tags, taste levels and verdicts come from a second LLM pass, kept off the
  // scan path so scanning stays fast. It runs by itself, once, when the diner opens
  // the menu — there is no button, because there is no decision for them to make:
  // they never asked for "tags", they asked for a menu. The cards fill in behind
  // them, and re-opening the menu costs nothing (the pass is idempotent server-side).
  const [enriching, setEnriching] = useState(false)
  const [enrichStatus, setEnrichStatus] = useState<EnrichmentStatus | null>(null)
  const enrichedRef = useRef(false)

  const needsEnrichment = useMemo(
    () =>
      (menu?.items ?? []).some(
        (item) =>
          !item.assistant_summary &&
          (item.ingredient_tags?.length ?? 0) === 0 &&
          (item.main_ingredients?.length ?? 0) === 0,
      ),
    [menu?.items],
  )

  useEffect(() => {
    if (!menuId || !menu || !needsEnrichment || enrichedRef.current) return
    enrichedRef.current = true

    let cancelled = false
    setEnriching(true)
    void apiRequest<MenuEnrichResult>(`/api/v1/menus/${menuId}/enrich`, {
      method: 'POST',
      token: accessToken ?? undefined,
    })
      .then((result) => {
        if (cancelled) return
        menuRequestRef.current += 1 // newer than any GET still in flight
        setMenu(result.menu)
        setEnrichStatus(result.status)
      })
      .catch(() => {
        if (!cancelled) setEnrichStatus('UNAVAILABLE')
      })
      .finally(() => {
        if (!cancelled) setEnriching(false)
      })

    return () => {
      cancelled = true
    }
  }, [accessToken, menu, menuId, needsEnrichment])

  const allItems = useMemo<BillItem[]>(() => menu?.items ?? [], [menu?.items])

  // Does this menu belong to a group dining session the host created? If so we
  // can show who ordered what and offer a per-person split. A 404 just means an
  // ordinary personal menu — no guest features, and that is fine.
  useEffect(() => {
    if (!menuId) return
    let active = true
    void apiRequest<{ session_id: string }>(
      `/api/v1/dining/sessions/by-menu/${menuId}`,
      { method: 'GET', token: accessToken ?? undefined },
    )
      .then((data) => {
        if (active) setDiningSessionId(data.session_id)
      })
      .catch(() => {
        if (active) setDiningSessionId(null)
      })
    return () => {
      active = false
    }
  }, [menuId, accessToken])

  // Poll what guests have picked — same 5s cadence as the host session page, so
  // the host sees picks land without a manual refresh.
  useEffect(() => {
    if (!diningSessionId) {
      setSelectionsSummary([])
      return
    }
    let active = true
    const fetchSummary = () => {
      void apiRequest<{ items: SelectionSummaryItem[] }>(
        `/api/v1/dining/sessions/${diningSessionId}/selections`,
        { method: 'GET', token: accessToken ?? undefined },
      )
        .then((data) => {
          if (active) setSelectionsSummary(data.items ?? [])
        })
        .catch(() => {
          // A transient poll failure is not worth interrupting the host over.
        })
    }
    fetchSummary()
    const timer = window.setInterval(fetchSummary, 5000)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [diningSessionId, accessToken])

  // Persist the host's own picks. Guests are saved server-side already; the
  // host's clicks used to live only in this component and vanished on reload.
  // We seed billLines from the saved picks once, then debounce-save changes.
  const hostSeededRef = useRef(false)
  useEffect(() => {
    hostSeededRef.current = false
  }, [menuId])

  useEffect(() => {
    if (!diningSessionId || !menuId || hostSeededRef.current) return
    let active = true
    void apiRequest<{
      items: { food_item_id: string; quantity: number; note: string | null }[]
    }>(`/api/v1/dining/menus/${menuId}/host-selections`, {
      method: 'GET',
      token: accessToken ?? undefined,
    })
      .then((data) => {
        if (!active) return
        hostSeededRef.current = true
        if ((data.items ?? []).length === 0) return
        setBillLines((current) => {
          const next = { ...current }
          for (const item of data.items) {
            // Do not clobber a pick the host already made this session.
            if (!next[item.food_item_id]) {
              next[item.food_item_id] = {
                quantity: item.quantity,
                note: item.note ?? '',
              }
            }
          }
          return next
        })
      })
      .catch(() => {
        // Leave the seed guard false on failure so a later save cannot wipe the
        // host's saved picks with an empty set.
      })
    return () => {
      active = false
    }
  }, [diningSessionId, menuId, accessToken])

  const debouncedBillLines = useDebouncedValue(billLines, 800)
  useEffect(() => {
    if (!diningSessionId || !menuId || !hostSeededRef.current) return
    const selections = Object.entries(debouncedBillLines)
      .filter(([, line]) => line.quantity > 0)
      .map(([food_item_id, line]) => ({
        food_item_id,
        quantity: line.quantity,
        note: line.note.trim() || null,
      }))
    void apiRequest(`/api/v1/dining/menus/${menuId}/host-selections`, {
      method: 'PUT',
      token: accessToken ?? undefined,
      body: JSON.stringify({ selections }),
    }).catch(() => {
      // A dropped save is recoverable on the next edit; nothing to surface.
    })
  }, [debouncedBillLines, diningSessionId, menuId, accessToken])

  const currency = useMemo(
    () => menu?.default_currency ?? allItems.find((item) => item.currency)?.currency ?? 'VND',
    [allItems, menu?.default_currency],
  )
  // Null until the diner actually picks a currency, so the menu is always priced
  // in its own currency first — that is the number printed on the paper in front
  // of them. Seeding this from `currency` did not work anyway: on the first render
  // the menu is still loading, so it froze on the 'VND' fallback.
  const [pickedCurrency, setPickedCurrency] = useState<string | null>(null)
  const displayCurrency = pickedCurrency ?? currency

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

  // Personalized ordering: when the diner has a profile, float best-fit dishes
  // up and sink risky ones (reusing assessDish). With no profile, keep the menu
  // in its original order.
  const profileActive = isProfileActive(dietProfile)
  // Three tiers of ordering, in decreasing order of how much we actually know:
  //   1. Real verdicts (the enrichment pass ran AND the diner has a food profile)
  //      — sort by the advice itself: recommended first, avoid last.
  //   2. No verdicts, but a declared profile — fall back to the allergen/diet
  //      signal we can compute client-side.
  //   3. Nothing declared — leave the menu exactly as the restaurant wrote it.
  //      Inventing an order for someone we know nothing about is just noise.
  const verdictsShown = hasVerdicts(filteredItems)
  const rankedItems = useMemo(() => {
    if (verdictsShown) return rankByVerdict(filteredItems)
    if (profileActive) return rankDishes(filteredItems, dietProfile)
    return filteredItems
  }, [dietProfile, filteredItems, profileActive, verdictsShown])

  // Name the ordering the diner is looking at. Sorting a menu silently is the same
  // as not sorting it: they cannot tell "best dish first" from "the order the
  // restaurant printed". Empty when we are not reordering anything — claiming a
  // sort we did not do would be worse than saying nothing.
  const sortLabel = verdictsShown
    ? t('menuDetail.sortedByAdvice')
    : profileActive
      ? t('menuDetail.sortedByProfile')
      : ''

  // Pagination.
  //
  // Two sources, one pager. With no filter the whole menu is already in the detail
  // payload, so we slice it here — which also means the ordering above is applied
  // across the WHOLE menu before it is cut into pages. Sorting each page on its own
  // would put a "recommended" dish on page 3 below an "avoid" dish on page 1.
  //
  // With a search/price filter the server does the paging (it owns the
  // Vietnamese-aware search), so a page is whatever it hands back.
  const totalItems = hasActiveFilter
    ? itemsMeta?.total ?? rankedItems.length
    : rankedItems.length
  const totalPages = hasActiveFilter
    ? itemsMeta?.total_pages ?? 1
    : Math.max(1, Math.ceil(rankedItems.length / MENU_PAGE_SIZE))
  const pagedItems = useMemo(
    () =>
      hasActiveFilter
        ? rankedItems
        : rankedItems.slice(
          (itemsPage - 1) * MENU_PAGE_SIZE,
          itemsPage * MENU_PAGE_SIZE,
        ),
    [hasActiveFilter, itemsPage, rankedItems],
  )
  const pageStart = totalItems === 0 ? 0 : (itemsPage - 1) * MENU_PAGE_SIZE + 1
  const pageEnd = hasActiveFilter
    ? Math.min(itemsPage * (itemsMeta?.page_size ?? MENU_PAGE_SIZE), totalItems)
    : Math.min(itemsPage * MENU_PAGE_SIZE, totalItems)

  const loadItems = useCallback(
    async (page: number) => {
      if (!menuId) return
      // Cancel any in-flight request and stamp this one so a slow earlier
      // response can never overwrite a newer one (no stale results).
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      const requestId = ++requestIdRef.current
      setItemsLoading(true)
      setItemsError(null)
      setServerItems([])
      try {
        const params = new URLSearchParams()
        params.set('page', String(page))
        // Same page size as the unfiltered grid, or searching would silently switch
        // the diner from 10-dish pages to 50-dish ones.
        params.set('page_size', String(MENU_PAGE_SIZE))
        if (trimmedSearch) params.set('search', trimmedSearch)
        if (normalizedMinPrice) params.set('min_price', normalizedMinPrice)
        if (normalizedMaxPrice) params.set('max_price', normalizedMaxPrice)
        const result = await apiRequestWithMeta<MenuItemResult[], PaginationMeta>(
          `/api/v1/menus/${menuId}/items?${params.toString()}`,
          { method: 'GET', token: accessToken ?? undefined, signal: controller.signal },
        )
        if (requestId !== requestIdRef.current) return // superseded by a newer request
        setServerItems(result.data)
        setItemsMeta(result.meta)
        setItemsPage(page)
      } catch (err) {
        if (requestId !== requestIdRef.current || controller.signal.aborted) return
        setItemsError(describeError(err, t, 'menuDetail.errors.loadItemsFailed'))
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
    void loadItems(1)
  }, [hasActiveFilter, loadItems])

  // Switching category re-cuts the list; page 4 of a two-page list shows nothing.
  useEffect(() => {
    setItemsPage(1)
  }, [activeCategory])

  const goToPage = useCallback(
    (next: number) => {
      const clamped = Math.min(Math.max(1, next), totalPages)
      if (clamped === itemsPage) return
      // Filtered results are paged by the server (it owns the search); the
      // unfiltered menu is already in memory, so we just move the window.
      if (hasActiveFilter) {
        void loadItems(clamped)
      } else {
        setItemsPage(clamped)
      }
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [hasActiveFilter, itemsPage, loadItems, totalPages],
  )

  // Enrichment rewrote the dishes, but the filtered grid is served by a different
  // endpoint and holds its own copy. Without this, a diner who was searching when
  // enrichment landed keeps staring at the pre-enrichment cards with no way to
  // refresh short of clearing the filter.
  useEffect(() => {
    if (!hasActiveFilter) return
    if (enrichStatus !== 'COMPLETED' && enrichStatus !== 'PARTIAL') return
    void loadItems(1)
  }, [enrichStatus, hasActiveFilter, loadItems])

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

  // Selected dishes passed to the assistant for quick-ask chips + the "+" picker.
  const selectedDishes = useMemo(
    () =>
      selectedLines.map(({ item }) => ({
        id: item.id,
        name: item.translated_name || item.original_name,
      })),
    [selectedLines],
  )

  // Guests who picked each dish, keyed by dish id — feeds each card's
  // "Khách đã chọn" line and the per-person split.
  const selectionsByItem = useMemo(() => {
    const map = new Map<string, GuestPick[]>()
    for (const summaryItem of selectionsSummary) {
      map.set(summaryItem.food_item_id, summaryItem.selected_by)
    }
    return map
  }, [selectionsSummary])

  // Everyone at the table who has picked at least one dish. The host is added as
  // a payer separately (they are not a participant row).
  const guestParticipants = useMemo(() => {
    const seen = new Map<string, string>()
    for (const summaryItem of selectionsSummary) {
      for (const pick of summaryItem.selected_by) {
        seen.set(pick.participant_id, pick.display_name)
      }
    }
    return Array.from(seen, ([id, name]) => ({ id, name }))
  }, [selectionsSummary])

  const isGroupSession = diningSessionId !== null

  // One line per dish, quantity = what the host ticked + everything guests picked.
  // This is the single source of truth for the subtotal, the printed receipt and
  // the split, so guest picks always land in the total (the whole point of this).
  const combinedLines = useMemo(() => {
    const byId = new Map<
      string,
      { item: BillItem; quantity: number; hostQuantity: number; guestQuantity: number }
    >()
    for (const { item, state } of selectedLines) {
      byId.set(item.id, {
        item,
        quantity: state.quantity,
        hostQuantity: state.quantity,
        guestQuantity: 0,
      })
    }
    for (const summaryItem of selectionsSummary) {
      const item = allItems.find((candidate) => candidate.id === summaryItem.food_item_id)
      if (!item) continue
      const existing = byId.get(item.id)
      if (existing) {
        existing.quantity += summaryItem.total_quantity
        existing.guestQuantity += summaryItem.total_quantity
      } else {
        byId.set(item.id, {
          item,
          quantity: summaryItem.total_quantity,
          hostQuantity: 0,
          guestQuantity: summaryItem.total_quantity,
        })
      }
    }
    return Array.from(byId.values())
  }, [selectedLines, selectionsSummary, allItems])

  const subtotal = useMemo(
    () =>
      combinedLines.reduce(
        (sum, line) => sum + itemPrice(line.item) * line.quantity,
        0,
      ),
    [combinedLines],
  )

  const hasSelections = combinedLines.length > 0

  // Mirrors BillingService: percentage adjustments are computed on the subtotal
  // (never compounded), then summed into the total.
  const billCurrency = currency ?? 'VND'
  const tipMoneyCurrency = tipCurrency ?? billCurrency
  const surchargeMoneyCurrency = surchargeCurrency ?? billCurrency

  // Rates are only worth fetching once something actually has to be converted:
  // the diner asked to see another currency, or typed a tip/surcharge in one.
  // Until then the menu is shown in its own currency and nothing is converted, so
  // loading rates on every menu open was a request spent on nothing.
  const needsConversion =
    displayCurrency !== currency ||
    tipMoneyCurrency !== billCurrency ||
    surchargeMoneyCurrency !== billCurrency
  const { rates: exchangeRates, error: ratesError } = useExchangeRates(
    currency,
    needsConversion,
  )
  // A conversion we cannot perform yet. `toBill` below would quietly turn the
  // amount into 0 — the tip would vanish from the bill with no warning — so the
  // confirm action is blocked until the rates land.
  const ratesPending = needsConversion && !exchangeRates

  // Flat amounts are typed in the diner's chosen currency; every figure below is
  // expressed in the bill's currency, which is what the server stores.
  const toBill = (amount: number, from: string) =>
    convertAmount(amount, from, billCurrency, exchangeRates) ?? 0

  const vatAmount = (subtotal * vatPercent) / 100
  const tipAmount =
    tipMode === 'PERCENT'
      ? (subtotal * tipPercent) / 100
      : toBill(tipInput, tipMoneyCurrency)
  const surchargeAmount = toBill(surchargeInput, surchargeMoneyCurrency)
  const discountAmount = (subtotal * discountPercent) / 100
  // Discount is capped at 100% of the subtotal, so the total can never go
  // negative (the server rejects a negative total).
  const total = subtotal + vatAmount + tipAmount + surchargeAmount - discountAmount
  const perPerson = peopleCount > 0 ? total / peopleCount : total

  // Extra charges to spread. Per the host's choice these are split EQUALLY across
  // heads, not by how much each person ate.
  const totalFees = vatAmount + tipAmount + surchargeAmount - discountAmount

  // The host's own ticked dishes (not what guests picked). Each of these is
  // charged per the host's per-item assignment when splitting by person.
  const hostOwnItems = useMemo(
    () =>
      selectedLines.map(({ item, state }) => ({
        id: item.id,
        name: item.translated_name || item.original_name,
        quantity: state.quantity,
        amount: itemPrice(item) * state.quantity,
      })),
    [selectedLines],
  )

  // Per-person breakdown: each guest owns what they picked; the host's own dishes
  // go where the host assigned them (shared / to a person / host pays); the extra
  // fees are divided equally across everyone at the table.
  const payers = useMemo(() => {
    const payerKeys = [...guestParticipants.map((p) => p.id), HOST_PAYER_KEY]
    const food: Record<string, number> = {}
    const lineItems: Record<
      string,
      { name: string; quantity: number; amount: number }[]
    > = {}
    for (const key of payerKeys) {
      food[key] = 0
      lineItems[key] = []
    }

    for (const summaryItem of selectionsSummary) {
      const item = allItems.find((candidate) => candidate.id === summaryItem.food_item_id)
      if (!item) continue
      const price = itemPrice(item)
      const name = item.translated_name || item.original_name
      for (const pick of summaryItem.selected_by) {
        if (food[pick.participant_id] === undefined) continue
        const amount = price * pick.quantity
        food[pick.participant_id] += amount
        lineItems[pick.participant_id].push({ name, quantity: pick.quantity, amount })
      }
    }

    for (const hostItem of hostOwnItems) {
      const assignment = hostItemAssignments[hostItem.id] ?? 'SPLIT'
      if (assignment === 'HOST') {
        food[HOST_PAYER_KEY] += hostItem.amount
        lineItems[HOST_PAYER_KEY].push({
          name: hostItem.name,
          quantity: hostItem.quantity,
          amount: hostItem.amount,
        })
      } else if (assignment === 'SPLIT') {
        const share = payerKeys.length ? hostItem.amount / payerKeys.length : hostItem.amount
        for (const key of payerKeys) {
          food[key] += share
          lineItems[key].push({
            name: `${hostItem.name} · ${t('menuDetail.split.shared')}`,
            quantity: hostItem.quantity,
            amount: share,
          })
        }
      } else {
        const key = food[assignment] !== undefined ? assignment : HOST_PAYER_KEY
        food[key] += hostItem.amount
        lineItems[key].push({
          name: hostItem.name,
          quantity: hostItem.quantity,
          amount: hostItem.amount,
        })
      }
    }

    const feePerHead = payerKeys.length ? totalFees / payerKeys.length : 0
    return payerKeys.map((key) => ({
      key,
      name:
        key === HOST_PAYER_KEY
          ? t('menuDetail.split.hostPayer')
          : guestParticipants.find((p) => p.id === key)?.name ?? key,
      lineItems: lineItems[key],
      foodSubtotal: food[key],
      feeShare: feePerHead,
      total: food[key] + feePerHead,
    }))
  }, [
    guestParticipants,
    selectionsSummary,
    allItems,
    hostOwnItems,
    hostItemAssignments,
    totalFees,
    t,
  ])

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
        [item.id]: describeError(err, t, 'menuDetail.errors.saveItemFailed'),
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
        [item.id]: describeError(err, t, 'menuDetail.errors.deleteItemFailed'),
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
      setError(describeError(err, t, 'menuDetail.errors.deleteMenuFailed'))
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
      setError(describeError(err, t, 'menuDetail.errors.addManualFailed'))
    } finally {
      setAddingManual(false)
    }
  }

  const handleConfirmMenu = async () => {
    if (!menuId || confirming || !hasSelections) return
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
      setError(describeError(err, t, 'menuDetail.errors.confirmMenuFailed'))
    } finally {
      setConfirming(false)
    }
  }

  const handleCreateReceipt = async () => {
    if (!menuId || creatingBill || ratesPending || !hasSelections) return
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
          // Combined host + guest quantities, so the receipt matches the total
          // the calculator showed (guest picks included).
          items: combinedLines.map((line) => ({
            food_item_id: line.item.id,
            quantity: line.quantity,
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
      if (tipMode === 'PERCENT' && tipPercent > 0) {
        adjustments.push({
          type: 'SERVICE_CHARGE',
          calculation_type: 'PERCENTAGE',
          label: t('menuDetail.tip'),
          value: tipPercent,
        })
      } else if (tipMode === 'AMOUNT' && tipAmount > 0) {
        // Already converted to the bill's currency, which is what FIXED means.
        adjustments.push({
          type: 'SERVICE_CHARGE',
          calculation_type: 'FIXED',
          label: t('menuDetail.tip'),
          value: roundMoney(tipAmount),
        })
      }
      if (surchargeAmount > 0) {
        adjustments.push({
          type: 'SURCHARGE',
          calculation_type: 'FIXED',
          label: t('menuDetail.surcharge'),
          value: roundMoney(surchargeAmount),
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
      toast.show({
        variant: 'error',
        title: t('menuDetail.toast.createReceiptFailed'),
        description: describeError(err, t, 'menuDetail.errors.tryAgain'),
      })
    } finally {
      setCreatingBill(false)
    }
  }

  return (
    <PageTransition className="min-h-full bg-app-bg">
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
            className="mb-5 flex items-center gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
          >
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-border bg-surface px-4 py-[70px] text-center text-ink-variant shadow-1">
            <Spinner label={t('menuDetail.loading')} />
          </div>
        ) : menu ? (
          <>
            <header className="mb-5 flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0 sm:flex-1">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-0.5 text-[12px] font-bold text-primary-dark">
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
                <p className="mb-0 flex min-w-0 max-w-full items-center text-[14px] text-ink-variant">
                  <span className="min-w-0 truncate" title={menu.source.file_name}>
                    {menu.source.file_name}
                  </span>
                  <span className="shrink-0">
                    {' '}
                    · {menu.default_currency ?? currency}
                  </span>
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={handleDelete}
                disabled={deleting}
                className="shrink-0 self-start border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                {deleting ? (
                  <Loader2 className="animate-spin" aria-hidden />
                ) : (
                  <Trash2 aria-hidden />
                )}
                {t('menuDetail.deleteMenu')}
              </Button>
            </header>

            {/* The pass runs on its own, so the only thing worth saying is when it
                is still working, or when it failed — silence on failure is how the
                last broken enrichment went unnoticed for a whole release. */}
            {(enriching || enrichStatus === 'UNAVAILABLE') && (
              <p
                role="status"
                className="mb-5 flex items-center gap-2 text-[13px] text-ink-variant"
              >
                {enriching ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" aria-hidden />
                    {t('menuDetail.enriching')}
                  </>
                ) : (
                  <>
                    <AlertCircle className="size-3.5 shrink-0" aria-hidden />
                    {t('menuDetail.enrichFailed')}
                  </>
                )}
              </p>
            )}

            <SourcePreview source={menu.source} accessToken={accessToken} />

            {hasUnsavedChanges && (
              <div className="mb-5 flex items-center gap-3 rounded-2xl border border-amber/30 bg-amber/10 px-4 py-3 text-[14px] font-medium text-amber">
                <AlertCircle className="size-4 shrink-0" aria-hidden />
                {t('menuDetail.unsavedChanges', { count: dirtyItemIds.length })}
              </div>
            )}

            {menuId && (
              <AssistantChat
                menuId={menuId}
                selectedDishes={selectedDishes}
                lastSelectedId={lastSelectedItemId}
              />
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
                className="mb-4 flex items-center gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
              >
                <AlertCircle className="size-4 shrink-0" aria-hidden />
                {itemsError}
              </div>
            )}

            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <p className="text-[13px] text-ink-variant" aria-live="polite">
                {itemsLoading && hasActiveFilter
                  ? t('menuDetail.searching')
                  : t('menuDetail.pageStatus', {
                    from: pageStart,
                    to: pageEnd,
                    total: totalItems,
                  })}
              </p>
              {sortLabel && (
                <p className="flex items-center gap-1.5 text-[12px] font-medium text-primary-dark">
                  <Sparkles className="size-3.5" aria-hidden />
                  {sortLabel}
                </p>
              )}
            </div>

            {/* The colour key. Only shown when the cards are actually tinted — a
                legend for a colour system that is not in use is pure noise. */}
            {verdictsShown && (
              <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-xl border border-border bg-panel/50 px-3 py-2 text-[12px] text-ink-variant">
                <span className="font-bold">{t('menuDetail.legendTitle')}</span>
                {VERDICT_LEVELS.map((level) => (
                  <span key={level} className="flex items-center gap-1.5">
                    <span
                      className={cn('h-3.5 w-1 rounded-full', VERDICT_LEGEND_COLOR[level])}
                      aria-hidden
                    />
                    {t(`billItem.verdict.${level}`)}
                  </span>
                ))}
              </div>
            )}

            <Reveal>
              <main className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {pagedItems.map((item) => (
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
                    guestSelections={selectionsByItem.get(item.id)}
                    onDraftChange={(patch) => updateItemDraft(item, patch)}
                    onEdit={() => beginItemEdit(item)}
                    onSave={() => void handleSaveItem(item)}
                    onCancel={() => cancelItemDraft(item.id)}
                    onDelete={() => void handleDeleteItem(item)}
                    onQuantityChange={(nextQuantity) => {
                      if (nextQuantity >= 1) setLastSelectedItemId(item.id)
                      updateLine(item.id, (line) => ({
                        ...line,
                        quantity: Math.max(0, nextQuantity),
                      }))
                    }}
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
                  <div className="col-span-full flex min-h-[170px] flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border bg-surface/70 p-6 text-center text-ink-variant">
                    <XCircle className="size-7" aria-hidden />
                    {hasActiveFilter ? (
                      <>
                        <span>{t('menuDetail.noFilterMatch')}</span>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleClearFilters}
                          className="border-primary text-primary hover:bg-primary/10 hover:text-primary"
                        >
                          {t('menuDetail.clearFilters')}
                        </Button>
                      </>
                    ) : (
                      <span>{t('menuDetail.noItems')}</span>
                    )}
                  </div>
                )}
                {itemsLoading && hasActiveFilter && filteredItems.length === 0 && (
                  <div className="col-span-full flex min-h-[170px] items-center justify-center gap-3 rounded-2xl border border-dashed border-border bg-surface/70 p-6 text-[14px] text-ink-variant">
                    <Loader2 className="size-6 animate-spin text-primary-dark" aria-hidden />
                    {t('menuDetail.loadingShort')}
                  </div>
                )}
              </main>
            </Reveal>

            {totalPages > 1 && (
              <div className="mt-5 flex flex-col items-center justify-between gap-3 rounded-2xl border border-border bg-surface px-3 py-2 shadow-1 sm:flex-row">
                <p className="text-[13px] text-ink-variant" aria-live="polite">
                  {t('menuDetail.pageStatus', {
                    from: pageStart,
                    to: pageEnd,
                    total: totalItems,
                  })}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon-sm"
                    onClick={() => goToPage(itemsPage - 1)}
                    disabled={itemsLoading || itemsPage <= 1}
                    aria-label={t('menuDetail.prevPage')}
                  >
                    <ChevronLeft aria-hidden />
                  </Button>
                  <span className="min-w-[72px] text-center text-[13px] font-bold text-ink">
                    {itemsPage} / {totalPages}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon-sm"
                    onClick={() => goToPage(itemsPage + 1)}
                    disabled={itemsLoading || itemsPage >= totalPages}
                    aria-label={t('menuDetail.nextPage')}
                  >
                    {itemsLoading ? (
                      <Loader2 className="animate-spin" aria-hidden />
                    ) : (
                      <ChevronRight aria-hidden />
                    )}
                  </Button>
                </div>
              </div>
            )}

            <Reveal className="mt-8">
              <section
                aria-labelledby="bill-calculator-title"
                className="rounded-3xl border border-border bg-surface px-5 py-5 shadow-2"
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
                      {hasSelections
                        ? t('menuDetail.selectedCount', { count: combinedLines.length })
                        : t('menuDetail.selectPrompt')}
                    </p>
                  </div>
                  <CurrencySelect
                    value={displayCurrency}
                    onChange={setPickedCurrency}
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
                      className="h-9 w-20 rounded-xl border border-border bg-surface px-3 text-center text-[14px] text-ink outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary"
                    />
                  </label>
                  <div className="flex items-center gap-2 text-[14px] text-ink-variant">
                    <span>{t('menuDetail.perPerson')}</span>
                    <strong className="text-[20px] text-primary-dark">
                      {formatConvertedAmount(perPerson, currency, displayCurrency, exchangeRates)}
                    </strong>
                  </div>
                </div>

                {/* VAT / tip / surcharge / discount — percentages apply to the subtotal.
                  Label sits above a full-width input so every field lines up, no
                  matter how long its label is. */}
                <div className="mt-4 grid grid-cols-2 gap-3 border-t border-border pt-4 sm:grid-cols-4">
                  <label className={ADJUSTMENT_FIELD}>
                    <span className={ADJUSTMENT_LABEL}>
                      <Percent className="size-4 shrink-0 text-primary-dark" aria-hidden />
                      <span className="truncate">{t('menuDetail.vat')}</span>
                      <span className="shrink-0 text-[12px] font-normal text-ink-variant">
                        (%)
                      </span>
                    </span>
                    <input
                      type="number"
                      inputMode="decimal"
                      min={0}
                      max={100}
                      step={0.5}
                      value={vatPercent}
                      onChange={(event) => setVatPercent(clampPercent(event.target.value))}
                      className={ADJUSTMENT_INPUT}
                    />
                  </label>
                  <div className={ADJUSTMENT_FIELD}>
                    <span className={ADJUSTMENT_LABEL}>
                      <HandCoins className="size-4 shrink-0 text-primary-dark" aria-hidden />
                      <span className="truncate">{t('menuDetail.tip')}</span>
                      <span className="ml-auto flex shrink-0 overflow-hidden rounded-lg border border-border">
                        {(['PERCENT', 'AMOUNT'] as const).map((mode) => (
                          <button
                            key={mode}
                            type="button"
                            onClick={() => setTipMode(mode)}
                            aria-pressed={tipMode === mode}
                            title={t(
                              mode === 'PERCENT'
                                ? 'menuDetail.tipModePercent'
                                : 'menuDetail.tipModeAmount',
                            )}
                            className={cn(
                              'flex h-6 w-7 items-center justify-center text-[11px] font-bold transition-colors',
                              tipMode === mode
                                ? 'bg-primary text-white'
                                : 'bg-canvas text-ink-variant hover:bg-surface-muted',
                            )}
                          >
                            {mode === 'PERCENT' ? '%' : <Coins className="size-3" aria-hidden />}
                          </button>
                        ))}
                      </span>
                    </span>
                    {tipMode === 'PERCENT' ? (
                      <input
                        type="number"
                        inputMode="decimal"
                        min={0}
                        max={100}
                        step={1}
                        value={tipPercent}
                        onChange={(event) => setTipPercent(clampPercent(event.target.value))}
                        className={ADJUSTMENT_INPUT}
                      />
                    ) : (
                      <MoneyField
                        value={tipInput}
                        onValueChange={setTipInput}
                        currency={tipMoneyCurrency}
                        onCurrencyChange={setTipCurrency}
                        currencyLabel={t('menuDetail.tipCurrencyAria')}
                        currencyDisabled={ratesError}
                      />
                    )}
                  </div>
                  <div className={ADJUSTMENT_FIELD}>
                    <span className={ADJUSTMENT_LABEL}>
                      <Receipt className="size-4 shrink-0 text-primary-dark" aria-hidden />
                      <span className="truncate">{t('menuDetail.surcharge')}</span>
                    </span>
                    <MoneyField
                      value={surchargeInput}
                      onValueChange={setSurchargeInput}
                      currency={surchargeMoneyCurrency}
                      onCurrencyChange={setSurchargeCurrency}
                      currencyLabel={t('menuDetail.surchargeCurrencyAria')}
                      currencyDisabled={ratesError}
                    />
                  </div>
                  <label className={ADJUSTMENT_FIELD}>
                    <span className={ADJUSTMENT_LABEL}>
                      <Tag className="size-4 shrink-0 text-primary-dark" aria-hidden />
                      <span className="truncate">{t('menuDetail.discount')}</span>
                      <span className="shrink-0 text-[12px] font-normal text-ink-variant">
                        (%)
                      </span>
                    </span>
                    <input
                      type="number"
                      inputMode="decimal"
                      min={0}
                      max={100}
                      step={1}
                      value={discountPercent}
                      onChange={(event) => setDiscountPercent(clampPercent(event.target.value))}
                      className={ADJUSTMENT_INPUT}
                    />
                  </label>
                </div>

                {hasSelections && (
                  <div className="mt-4 border-t border-border pt-4">
                    <div className="flex flex-col gap-2">
                      {combinedLines.map(({ item, quantity, hostQuantity }) => {
                        const guestPicks = selectionsByItem.get(item.id) ?? []
                        return (
                        <div
                          key={item.id}
                          className="flex items-start justify-between gap-3 rounded-xl bg-panel px-3 py-2 text-[14px]"
                        >
                          <div className="min-w-0">
                            <p className="mb-0 truncate font-semibold text-ink">
                              {quantity} x{' '}
                              <ItemDisplayName
                                item={item}
                                originalClassName="text-[12px] text-ink-variant/50"
                              />
                            </p>
                            {guestPicks.length > 0 && (
                              <p className="mb-0 mt-1 text-[12px] text-primary-dark">
                                {guestPicks
                                  .map(
                                    (pick) =>
                                      `${pick.display_name} (x${pick.quantity})${
                                        pick.note ? ` – ${pick.note}` : ''
                                      }`,
                                  )
                                  .join(', ')}
                              </p>
                            )}
                            {hostQuantity > 0 && guestPicks.length > 0 && (
                              <p className="mb-0 mt-0.5 text-[12px] text-ink-variant">
                                {t('menuDetail.split.hostPayer')} (x{hostQuantity})
                              </p>
                            )}
                          </div>
                          <span className="shrink-0 font-bold text-primary-dark">
                            {formatConvertedAmount(
                              itemPrice(item) * quantity,
                              item.currency ?? currency,
                              displayCurrency,
                              exchangeRates,
                            )}
                          </span>
                        </div>
                        )
                      })}
                    </div>
                    <div className="mt-4 flex flex-col gap-2 border-t border-border pt-4 text-[14px] sm:items-end">
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
                            {t('menuDetail.tip')}
                            {tipMode === 'PERCENT' ? ` · ${tipPercent}%` : ''}
                          </span>
                          <span className="text-ink">
                            {formatConvertedAmount(tipAmount, currency, displayCurrency, exchangeRates)}
                          </span>
                        </div>
                      )}
                      {surchargeAmount > 0 && (
                        <div className="flex w-full justify-between gap-3 sm:w-[280px]">
                          <span className="text-ink-variant">{t('menuDetail.surcharge')}</span>
                          <span className="text-ink">
                            {formatConvertedAmount(surchargeAmount, currency, displayCurrency, exchangeRates)}
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
                      <div className="flex w-full justify-between gap-3 border-t border-border pt-2 sm:w-[280px]">
                        <span className="font-bold text-ink">{t('menuDetail.total')}</span>
                        <strong className="text-[16px] text-ink">
                          {formatConvertedAmount(total, currency, displayCurrency, exchangeRates)}
                        </strong>
                      </div>
                      {(!isGroupSession || splitMode === 'EVENLY') && (
                        <div className="flex w-full justify-between gap-3 sm:w-[280px]">
                          <span className="text-ink-variant">{t('menuDetail.splitAmong', { count: peopleCount })}</span>
                          <strong className="text-primary-dark">
                            {formatConvertedAmount(perPerson, currency, displayCurrency, exchangeRates)}
                          </strong>
                        </div>
                      )}
                    </div>

                    {isGroupSession && (
                      <div className="mt-5 border-t border-border pt-4">
                        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                          <h3 className="mb-0 text-[14px] font-bold text-primary-dark">
                            {t('menuDetail.split.title')}
                          </h3>
                          <div className="flex overflow-hidden rounded-xl border border-border">
                            {(['EVENLY', 'BY_PERSON'] as const).map((mode) => (
                              <button
                                key={mode}
                                type="button"
                                onClick={() => setSplitMode(mode)}
                                aria-pressed={splitMode === mode}
                                className={cn(
                                  'px-3 py-1.5 text-[13px] font-semibold transition-colors',
                                  splitMode === mode
                                    ? 'bg-primary text-white'
                                    : 'bg-canvas text-ink-variant hover:bg-surface-muted',
                                )}
                              >
                                {t(
                                  mode === 'EVENLY'
                                    ? 'menuDetail.split.evenly'
                                    : 'menuDetail.split.byPerson',
                                )}
                              </button>
                            ))}
                          </div>
                        </div>

                        {splitMode === 'BY_PERSON' && (
                          <GroupSplitPanel
                            payers={payers}
                            hostOwnItems={hostOwnItems}
                            guestParticipants={guestParticipants}
                            assignments={hostItemAssignments}
                            onAssign={(itemId, value) =>
                              setHostItemAssignments((current) => ({
                                ...current,
                                [itemId]: value,
                              }))
                            }
                            currency={currency}
                            displayCurrency={displayCurrency}
                            rates={exchangeRates}
                          />
                        )}
                      </div>
                    )}
                  </div>
                )}
              </section>
            </Reveal>
            <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-panel px-4 py-[20px] shadow-3 sm:px-[50px] sm:py-[30px]">
              <div className="mx-auto flex max-w-[1240px] flex-col justify-center gap-3 sm:min-h-11 sm:flex-row sm:items-center sm:justify-end">
                <Button asChild variant="outline" size="lg">
                  <Link
                    to="/app/scan"
                    onClick={(event) => {
                      if (!confirmLeaveWithUnsavedChanges()) event.preventDefault()
                    }}
                  >
                    {t('menuDetail.scanAnother')}
                  </Link>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="lg"
                  onClick={() => void handleCreateReceipt()}
                  // Blocked while a needed rate is still in flight: the tip would be
                  // converted to 0 and silently disappear from the bill.
                  disabled={creatingBill || ratesPending || !hasSelections}
                  className="border-primary bg-surface text-primary hover:bg-primary/10 hover:text-primary"
                >
                  {creatingBill ? (
                    <Loader2 className="animate-spin" aria-hidden />
                  ) : (
                    <ReceiptText aria-hidden />
                  )}
                  {t('menuDetail.showBill')}
                </Button>
                <Button
                  type="button"
                  size="lg"
                  onClick={() => void handleConfirmMenu()}
                  disabled={confirming || !hasSelections}
                >
                  {confirming ? (
                    <Loader2 className="animate-spin" aria-hidden />
                  ) : null}
                  {menu.status === 'CONFIRMED' ? t('menuDetail.confirmedBtn') : t('menuDetail.reviewConfirm')}
                </Button>
              </div>
            </div>
          </>
        ) : error ? (
          <div className="flex flex-col items-center gap-4 rounded-2xl border border-border bg-surface px-4 py-[70px] text-center shadow-1">
            <span className="flex size-14 items-center justify-center rounded-2xl bg-destructive/10">
              <AlertCircle className="size-7 text-destructive" aria-hidden />
            </span>
            <p role="alert" className="max-w-[360px] text-[14px] text-destructive">
              {error}
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={() => void loadMenu()}
              className="border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
            >
              <RefreshCw aria-hidden />
              {t('common.retry')}
            </Button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 rounded-2xl border border-border bg-surface px-4 py-[70px] text-center text-ink-variant shadow-1">
            <span className="flex size-16 items-center justify-center rounded-3xl bg-destructive/10">
              <XCircle className="size-8 text-destructive" aria-hidden />
            </span>
            <p className="text-[15px] font-medium text-ink">{t('menuDetail.notFound')}</p>
            <Button asChild>
              <Link to="/app/menus">{t('menuDetail.backToMenus')}</Link>
            </Button>
          </div>
        )}
      </div>
    </PageTransition>
  )
}
