import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bookmark, Search, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Spinner } from '@/shared/components/Spinner'
import { EmptyState } from '@/shared/components/EmptyState'
import { Input } from '@/shared/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useToast } from '@/app/providers/ToastProvider'
import { describeError } from '@/shared/lib/errors'
import { fetchSaved, unsaveRestaurant } from '@/features/feed/api'
import type { RestaurantCard as RestaurantCardType } from '@/features/feed/types'
import { RestaurantCardView } from '@/features/feed/components/RestaurantCard'

type SortKey = 'recent' | 'name' | 'distance' | 'rating'

  
/** Vertical list of saved restaurants with search + sort. */
export function SavedPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('feed.savedTitle')} | MenuScan`)
  const toast = useToast()

  const [saved, setSaved] = useState<RestaurantCardType[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortKey>('recent')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchSaved()
      setSaved(data)
    } catch (err) {
      toast.show({
        variant: 'error',
        title: describeError(err, t, 'feed.savedTitle'),
      })
    } finally {
      setLoading(false)
    }
  }, [t, toast])

  useEffect(() => {
    // Deferred so the initial setLoading inside load does not fire
    // synchronously in the effect body (react-hooks/set-state-in-effect).
    let active = true
    Promise.resolve().then(() => {
      if (active) void load()
    })
    return () => {
      active = false
    }
  }, [load])

  const handleUnsave = async (sourceId: number) => {
    setBusyId(sourceId)
    try {
      await unsaveRestaurant(sourceId)
      setSaved((prev) => prev.filter((item) => item.source_id !== sourceId))
      toast.show({ variant: 'info', title: t('feed.toast.unsaved') })
    } catch (err) {
      toast.show({
        variant: 'error',
        title: describeError(err, t, 'feed.savedTitle'),
      })
    } finally {
      setBusyId(null)
    }
  }

  // Filter + sort — derived from `saved` so the original server order (used as
  // proxy for "recently saved" since the API doesn't expose saved_at on the
  // card) is preserved when `sortBy === 'recent'`.
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filtered = q
      ? saved.filter(
          (r) =>
            r.name.toLowerCase().includes(q) ||
            r.address.toLowerCase().includes(q) ||
            r.type.some((c) => c.toLowerCase().includes(q)),
        )
      : saved

    const sorted = [...filtered]
    switch (sortBy) {
      case 'name':
        sorted.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
        break
      case 'distance':
        sorted.sort((a, b) => (a.distance_km ?? Infinity) - (b.distance_km ?? Infinity))
        break
      case 'rating':
        sorted.sort((a, b) => (b.star ?? 0) - (a.star ?? 0))
        break
      case 'recent':
      default:
        break
    }
    return sorted
  }, [saved, query, sortBy])

  return (
    <PageTransition>
      <div className="mx-auto w-full max-w-[1200px] px-4 py-6 sm:px-8">
        <header className="flex flex-col gap-1">
          <h1 className="text-[28px] font-extrabold leading-tight text-ink">
            {t('feed.savedTitle')}
          </h1>
          <p className="text-[14px] text-ink-variant">
            {t('feed.savedCount', { count: saved.length })}
          </p>
        </header>

        {/* Toolbar — only when there's something to filter/sort. */}
        {saved.length > 0 && (
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-variant/60"
                aria-hidden
              />
              <Input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('feed.savedSearchPlaceholder')}
                className="h-10 rounded-xl bg-canvas pl-9 pr-9"
                aria-label={t('feed.savedSearchPlaceholder')}
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-variant/60 transition-colors hover:text-ink"
                  aria-label={t('feed.savedSearchClear')}
                >
                  <X className="size-4" aria-hidden />
                </button>
              )}
            </div>
            <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortKey)}>
              <SelectTrigger
                className="h-10 w-full rounded-xl border-border bg-canvas sm:w-[180px]"
                aria-label={t('feed.savedSortLabel')}
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recent">{t('feed.savedSort.recent')}</SelectItem>
                <SelectItem value="name">{t('feed.savedSort.name')}</SelectItem>
                <SelectItem value="distance">{t('feed.savedSort.distance')}</SelectItem>
                <SelectItem value="rating">{t('feed.savedSort.rating')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="mt-6">
          {loading ? (
            <div className="flex justify-center py-20">
              <Spinner />
            </div>
          ) : saved.length === 0 ? (
            <EmptyState
              icon={Bookmark}
              title={t('feed.noSaved.title')}
              description={t('feed.noSaved.subtitle')}
              action={
                <Link
                  to="/app/feed"
                  className="rounded-full bg-primary px-4 py-2 text-[13px] font-bold text-white"
                >
                  {t('feed.pageTitle')}
                </Link>
              }
            />
          ) : visible.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center">
              <Search className="size-8 text-ink-variant/40" aria-hidden />
              <p className="text-[14px] font-semibold text-ink">
                {t('feed.savedNoMatch.title')}
              </p>
              <p className="text-[13px] text-ink-variant">
                {t('feed.savedNoMatch.subtitle')}
              </p>
              <button
                type="button"
                onClick={() => setQuery('')}
                className="mt-2 rounded-full border border-border bg-canvas px-3 py-1.5 text-[12px] font-semibold text-ink-variant hover:bg-panel"
              >
                {t('feed.savedSearchClear')}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {visible.map((restaurant) => (
                <RestaurantCardView
                  key={restaurant.source_id}
                  restaurant={restaurant}
                  saved
                  onSaveToggle={() => handleUnsave(restaurant.source_id)}
                  busy={busyId === restaurant.source_id}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </PageTransition>
  )
}
