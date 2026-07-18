import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Lock,
  Minus,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  UtensilsCrossed,
  XCircle,
} from 'lucide-react'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { Button } from '@/shared/components/ui/button'
import { Card } from '@/shared/components/ui/card'
import { EmptyState } from '@/shared/components/EmptyState'
import { Spinner } from '@/shared/components/Spinner'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { FoodProfilePreferencePicker } from '@/features/food-profile/components/FoodProfilePreferencePicker'
import {
  createEmptyFoodProfileDraft,
  foodProfileDraftToPreferences,
  type FoodProfilePreferenceDraft,
} from '@/features/food-profile/preferences'
import {
  loadGuestSession,
  loadGuestPrefsDraft,
  saveGuestPrefsDraft,
} from '@/features/dining/guestSession'

interface PublicMenuItem {
  id: string
  original_name: string
  translated_name: string | null
  translated_description: string | null
  assistant_summary: string | null
  category: string | null
  price: string | null
  currency: string | null
  allergens: string[]
}

interface PublicSessionMenu {
  session_id: string
  menu_id: string | null
  title: string | null
  default_currency: string | null
  status: string
  items: PublicMenuItem[]
}

interface LineState {
  quantity: number
  note: string
}

const ALL_CATEGORY = 'Tất cả'
const PAGE_SIZE = 8

function formatPrice(price: string | null, currency: string | null): string {
  if (!price) return ''
  const amount = Number(price)
  if (!Number.isFinite(amount)) return `${price} ${currency ?? ''}`.trim()
  return `${amount.toLocaleString('vi-VN')} ${currency ?? ''}`.trim()
}

export function GuestMenuSelectionPage() {
  useDocumentTitle('Chọn món | MenuScan')
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const guest = useMemo(() => (token ? loadGuestSession(token) : null), [token])

  const [menu, setMenu] = useState<PublicSessionMenu | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lines, setLines] = useState<Record<string, LineState>>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  // Enables "Chốt" even at zero items, so a guest can clear a previous basket.
  const [touched, setTouched] = useState(false)

  // Editing preferences after joining (add an allergy you forgot, etc.).
  const [showPrefs, setShowPrefs] = useState(false)
  const [prefsDraft, setPrefsDraft] = useState<FoodProfilePreferenceDraft>(() =>
    token ? loadGuestPrefsDraft(token) ?? createEmptyFoodProfileDraft() : createEmptyFoodProfileDraft(),
  )
  const [savingPrefs, setSavingPrefs] = useState(false)
  const [prefsSaved, setPrefsSaved] = useState(false)

  const handleSavePreferences = async () => {
    if (!guest || savingPrefs) return
    setSavingPrefs(true)
    setError(null)
    try {
      await apiRequest(
        `/api/v1/dining/public/sessions/${guest.sessionId}/preferences?invite_token=${encodeURIComponent(
          token,
        )}`,
        {
          method: 'PUT',
          body: JSON.stringify({
            participant_id: guest.participantId,
            preferences: foodProfileDraftToPreferences(prefsDraft),
          }),
        },
      )
      saveGuestPrefsDraft(token, prefsDraft)
      setPrefsSaved(true)
      window.setTimeout(() => setPrefsSaved(false), 2000)
      setShowPrefs(false)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Không cập nhật được sở thích. Thử lại nhé.',
      )
    } finally {
      setSavingPrefs(false)
    }
  }

  const loadMenu = useCallback(
    async (showLoading = false) => {
      if (!guest) return
      if (showLoading) setLoading(true)
      setError(null)
      try {
        const data = await apiRequest<PublicSessionMenu>(
          `/api/v1/dining/public/sessions/${guest.sessionId}/menu?invite_token=${encodeURIComponent(
            token,
          )}`,
          { method: 'GET' },
        )
        setMenu(data)
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : 'Không tải được thực đơn của phiên ăn.',
        )
      } finally {
        if (showLoading) setLoading(false)
      }
    },
    [guest, token],
  )

  useEffect(() => {
    if (!guest) {
      // Nothing to load; render the "join first" state below.
      Promise.resolve().then(() => setLoading(false))
      return
    }
    // Deferred so the initial setLoading inside loadMenu does not fire
    // synchronously in the effect body.
    let active = true
    Promise.resolve().then(() => {
      if (active) void loadMenu(true)
    })
    return () => {
      active = false
    }
  }, [guest, loadMenu])

  // Auto-poll while the menu is not ready yet, so a guest who joined before the
  // host scanned never has to hit "Làm mới" — it just appears.
  const menuReadyNow = Boolean(menu && menu.menu_id && menu.items.length > 0)
  useEffect(() => {
    if (!guest || menuReadyNow) return
    const timer = window.setInterval(() => void loadMenu(false), 5000)
    return () => clearInterval(timer)
  }, [guest, menuReadyNow, loadMenu])

  const selectedCount = useMemo(
    () => Object.values(lines).filter((line) => line.quantity > 0).length,
    [lines],
  )

  // Menus can be long, so the guest gets the same essentials as the host: search
  // by name, filter by category, and pagination. All client-side — the public
  // endpoint already handed over the whole menu in one go.
  const [searchInput, setSearchInput] = useState('')
  const [activeCategory, setActiveCategory] = useState(ALL_CATEGORY)
  const [page, setPage] = useState(1)

  const categories = useMemo(() => {
    const seen = new Set<string>()
    for (const item of menu?.items ?? []) {
      if (item.category) seen.add(item.category)
    }
    return [ALL_CATEGORY, ...seen]
  }, [menu])

  const filteredItems = useMemo(() => {
    const query = searchInput.trim().toLowerCase()
    return (menu?.items ?? []).filter((item) => {
      const matchesCategory =
        activeCategory === ALL_CATEGORY || item.category === activeCategory
      const haystack = `${item.translated_name ?? ''} ${item.original_name}`.toLowerCase()
      return matchesCategory && (!query || haystack.includes(query))
    })
  }, [menu, searchInput, activeCategory])

  const totalPages = Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE))
  // Clamp rather than reset-in-effect: if the list shrinks (filter or a poll),
  // the page index can point past the end.
  const currentPage = Math.min(page, totalPages)
  const pagedItems = useMemo(
    () => filteredItems.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [filteredItems, currentPage],
  )

  const updateLine = (
    itemId: string,
    updater: (line: LineState) => LineState,
  ) => {
    setTouched(true)
    setSaved(false)
    setLines((current) => {
      const existing = current[itemId] ?? { quantity: 0, note: '' }
      return { ...current, [itemId]: updater(existing) }
    })
  }

  const handleConfirm = async () => {
    if (!guest || saving) return
    setSaving(true)
    setError(null)
    try {
      const selections = Object.entries(lines)
        .filter(([, line]) => line.quantity > 0)
        .map(([food_item_id, line]) => ({
          food_item_id,
          quantity: line.quantity,
          note: line.note.trim() || null,
        }))
      await apiRequest(
        `/api/v1/dining/public/sessions/${guest.sessionId}/selections?invite_token=${encodeURIComponent(
          token,
        )}`,
        {
          method: 'PUT',
          body: JSON.stringify({
            participant_id: guest.participantId,
            selections,
          }),
        },
      )
      setSaved(true)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Không gửi được lựa chọn. Thử lại nhé.',
      )
    } finally {
      setSaving(false)
    }
  }

  // No saved guest identity for this token — they have to join first.
  if (!guest) {
    return (
      <PageTransition className="flex min-h-dvh flex-col items-center justify-center bg-app-bg px-6 text-center">
        <EmptyState
          icon={AlertCircle}
          tone="destructive"
          title="Bạn chưa tham gia phiên ăn"
          description="Hãy mở lại link/QR của Host và điền tên + sở thích trước, rồi mới chọn món được."
          action={
            token ? (
              <Button asChild>
                <Link to={`/dining/join?token=${encodeURIComponent(token)}`}>
                  Tham gia phiên ăn
                </Link>
              </Button>
            ) : undefined
          }
        />
      </PageTransition>
    )
  }

  if (loading) {
    return (
      <PageTransition className="flex min-h-dvh w-full flex-col items-center justify-center bg-app-bg">
        <Spinner label="Đang tải thực đơn..." />
      </PageTransition>
    )
  }

  const menuReady = menu && menu.menu_id && menu.items.length > 0
  const sessionClosed = menu?.status === 'CLOSED'

  return (
    <PageTransition className="min-h-dvh bg-app-bg">
      <div className="mx-auto w-full max-w-[720px] px-4 py-8 pb-[130px] sm:px-6">
        <header className="mb-6 flex flex-col gap-1">
          <span className="flex items-center gap-2 text-[13px] font-semibold text-primary">
            <UtensilsCrossed className="size-4" aria-hidden />
            Xin chào {guest.displayName || 'bạn'}
          </span>
          <h1 className="mb-0 text-[22px] font-bold leading-tight text-ink sm:text-[26px]">
            {menu?.title || 'Chọn món cho bữa ăn'}
          </h1>
          <p className="mb-0 text-[14px] text-ink-variant">
            Chọn số lượng và ghi chú cho từng món. Host sẽ thấy lựa chọn của bạn để gộp
            hóa đơn.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowPrefs((current) => !current)}
              disabled={sessionClosed}
            >
              <SlidersHorizontal className="size-4" aria-hidden />
              Sửa sở thích & dị ứng
            </Button>
            {prefsSaved && (
              <span className="flex items-center gap-1 text-[12px] font-semibold text-success">
                <CheckCircle2 className="size-3.5" aria-hidden />
                Đã cập nhật
              </span>
            )}
          </div>
        </header>

        {showPrefs && (
          <Card className="mb-4 gap-4 rounded-2xl p-5 shadow-1">
            <div className="flex items-center justify-between">
              <h2 className="mb-0 text-[16px] font-bold text-ink">
                Sở thích & dị ứng của bạn
              </h2>
              <button
                type="button"
                onClick={() => setShowPrefs(false)}
                aria-label="Đóng"
                className="text-ink-variant hover:text-ink"
              >
                <XCircle className="size-5" aria-hidden />
              </button>
            </div>
            <FoodProfilePreferencePicker
              value={prefsDraft}
              onChange={setPrefsDraft}
              disabled={savingPrefs}
            />
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowPrefs(false)}
                disabled={savingPrefs}
              >
                Hủy
              </Button>
              <Button
                type="button"
                onClick={() => void handleSavePreferences()}
                disabled={savingPrefs}
              >
                {savingPrefs ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  <CheckCircle2 className="size-4" aria-hidden />
                )}
                Lưu sở thích
              </Button>
            </div>
          </Card>
        )}

        {error && (
          <div
            role="alert"
            className="mb-4 flex items-center gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
          >
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            {error}
          </div>
        )}

        {sessionClosed && (
          <div className="mb-4 flex items-center gap-3 rounded-2xl border border-amber/40 bg-amber/10 px-4 py-3 text-[14px] font-medium text-amber">
            <Lock className="size-4 shrink-0" aria-hidden />
            Phiên ăn đã đóng — Host đã khóa, bạn chưa đổi lựa chọn được lúc này.
          </div>
        )}

        {!menuReady ? (
          <EmptyState
            icon={UtensilsCrossed}
            tone="primary"
            title="Thực đơn chưa sẵn sàng"
            description="Host chưa quét thực đơn cho phiên này. Đợi một chút rồi bấm làm mới."
            action={
              <Button
                variant="outline"
                onClick={() => void loadMenu(true)}
                disabled={loading}
              >
                <RefreshCw className="size-4" aria-hidden />
                Làm mới
              </Button>
            }
          />
        ) : (
          <>
            {/* Search + category filter */}
            <div className="mb-4 flex flex-col gap-3">
              <div className="flex h-11 items-center gap-2 rounded-xl border border-border bg-surface px-3">
                <Search className="size-4 shrink-0 text-ink-variant" aria-hidden />
                <input
                  value={searchInput}
                  onChange={(event) => {
                    setSearchInput(event.target.value)
                    setPage(1)
                  }}
                  placeholder="Tìm món theo tên…"
                  className="h-full min-w-0 flex-1 bg-transparent text-[14px] text-ink outline-none placeholder:text-placeholder"
                />
                {searchInput && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchInput('')
                      setPage(1)
                    }}
                    aria-label="Xóa tìm kiếm"
                    className="shrink-0 text-ink-variant hover:text-ink"
                  >
                    <XCircle className="size-4" aria-hidden />
                  </button>
                )}
              </div>
              {categories.length > 1 && (
                <div className="flex flex-wrap gap-2">
                  {categories.map((category) => (
                    <button
                      key={category}
                      type="button"
                      onClick={() => {
                        setActiveCategory(category)
                        setPage(1)
                      }}
                      className={`rounded-full border px-3 py-1 text-[12px] font-semibold transition-colors ${
                        activeCategory === category
                          ? 'border-primary bg-primary text-white'
                          : 'border-border bg-surface text-ink-variant hover:bg-surface-muted'
                      }`}
                    >
                      {category}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {filteredItems.length === 0 ? (
              <EmptyState
                icon={XCircle}
                tone="primary"
                title="Không tìm thấy món"
                description="Thử từ khóa khác hoặc bỏ bộ lọc."
              />
            ) : (
          <div className="flex flex-col gap-3">
            {pagedItems.map((item) => {
              const line = lines[item.id] ?? { quantity: 0, note: '' }
              const name = item.translated_name || item.original_name
              const summary = item.assistant_summary || item.translated_description
              return (
                <Card
                  key={item.id}
                  className={`gap-3 rounded-2xl p-4 shadow-1 transition-colors ${
                    line.quantity > 0 ? 'border-primary/40 bg-primary/[0.03]' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="mb-0.5 text-[16px] font-bold leading-tight text-ink">
                        {name}
                      </h2>
                      {item.translated_name && (
                        <p className="mb-0 text-[12px] text-ink-variant/60">
                          {item.original_name}
                        </p>
                      )}
                    </div>
                    <strong className="shrink-0 text-[15px] text-primary-dark">
                      {formatPrice(item.price, item.currency ?? menu.default_currency)}
                    </strong>
                  </div>

                  {summary && (
                    <p className="mb-0 line-clamp-2 text-[13px] leading-5 text-ink-variant">
                      {summary}
                    </p>
                  )}

                  {item.allergens.length > 0 && (
                    <p className="mb-0 text-[11px] text-amber">
                      Chứa: {item.allergens.join(', ')}
                    </p>
                  )}

                  <div className="flex items-center gap-2 border-t border-hairline pt-3">
                    <div className="flex h-9 shrink-0 items-center overflow-hidden rounded-full border border-hairline">
                      <button
                        type="button"
                        onClick={() =>
                          updateLine(item.id, (l) => ({
                            ...l,
                            quantity: Math.max(0, l.quantity - 1),
                          }))
                        }
                        className="flex size-9 items-center justify-center text-primary-dark transition-colors hover:bg-primary/10"
                        aria-label={`Bớt ${name}`}
                      >
                        <Minus className="size-4" aria-hidden />
                      </button>
                      <span className="flex h-9 min-w-8 items-center justify-center text-[14px] font-bold text-ink">
                        {line.quantity}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          updateLine(item.id, (l) => ({
                            ...l,
                            quantity: Math.min(99, l.quantity + 1),
                          }))
                        }
                        className="flex size-9 items-center justify-center text-primary-dark transition-colors hover:bg-primary/10"
                        aria-label={`Thêm ${name}`}
                      >
                        <Plus className="size-4" aria-hidden />
                      </button>
                    </div>
                    <input
                      value={line.note}
                      onChange={(event) =>
                        updateLine(item.id, (l) => ({ ...l, note: event.target.value }))
                      }
                      placeholder="Ghi chú (vd: ít cay, không hành)"
                      maxLength={500}
                      className="h-9 min-w-0 flex-1 rounded-full border border-hairline bg-surface-muted px-3 text-[13px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </Card>
              )
            })}
          </div>
            )}

            {totalPages > 1 && (
              <div className="mt-5 flex items-center justify-center gap-3">
                <Button
                  variant="outline"
                  size="icon-sm"
                  onClick={() => setPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage <= 1}
                  aria-label="Trang trước"
                >
                  <ChevronLeft className="size-4" aria-hidden />
                </Button>
                <span className="min-w-[64px] text-center text-[13px] font-bold text-ink">
                  {currentPage} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="icon-sm"
                  onClick={() => setPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage >= totalPages}
                  aria-label="Trang sau"
                >
                  <ChevronRight className="size-4" aria-hidden />
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {menuReady && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-panel px-4 py-4 shadow-3 sm:px-6">
          <div className="mx-auto flex max-w-[720px] items-center justify-between gap-3">
            <div className="flex flex-col text-[13px] text-ink-variant">
              {saved ? (
                <span className="flex items-center gap-1.5 font-semibold text-success">
                  <CheckCircle2 className="size-4" aria-hidden />
                  Đã gửi lựa chọn cho Host
                </span>
              ) : (
                <span>{selectedCount} món đã chọn</span>
              )}
            </div>
            <Button
              type="button"
              size="lg"
              onClick={() => void handleConfirm()}
              disabled={saving || sessionClosed || (selectedCount === 0 && !touched)}
            >
              {saving ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <CheckCircle2 className="size-4" aria-hidden />
              )}
              {saved ? 'Cập nhật lại' : 'Chốt lựa chọn'}
            </Button>
          </div>
        </div>
      )}
    </PageTransition>
  )
}
