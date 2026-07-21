import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bookmark, MapPin, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/ui/button'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Spinner } from '@/shared/components/Spinner'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useToast } from '@/app/providers/ToastProvider'
import { describeError } from '@/shared/lib/errors'
import { ApiError } from '@/shared/lib/api'
import { fetchFeed, fetchLocation } from '@/features/feed/api'
import type { FeedResponse, UserLocation } from '@/features/feed/types'
import { FeedStack } from '@/features/feed/components/FeedStack'
import { LocationPrompt } from '@/features/feed/components/LocationPrompt'

const INITIAL_RADIUS_KM = 5
// Backend caps radius_km at 100 (Query(le=100.0)). Sync here so "widen radius"
// never fires a request the backend will reject with a generic 422.
const MAX_RADIUS_KM = 100

/**
 * Discovery feed page.
 *
 * First visit prompts for location (mandatory — the feed cannot rank without
 * it). Subsequent visits load the ranked cards directly. The user can swap
 * location or widen the radius at any time.
 */
export function FeedPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('feed.pageTitle')} | MenuScan`)
  const toast = useToast()

  const [location, setLocalLocation] = useState<UserLocation | null>(null)
  const [locationLoaded, setLocationLoaded] = useState(false)
  const [promptOpen, setPromptOpen] = useState(false)
  const [feed, setFeed] = useState<FeedResponse | null>(null)
  const [radius, setRadius] = useState(INITIAL_RADIUS_KM)
  const [loading, setLoading] = useState(true)

  const loadFeed = useCallback(
    async (radiusKm: number) => {
      setLoading(true)
      try {
        const data = await fetchFeed(radiusKm, 20)
        setFeed(data)
      } catch (err) {
        if (err instanceof ApiError && err.code === 'LOCATION_NOT_SET') {
          setPromptOpen(true)
          setFeed(null)
          return
        }
        // 422 / VALIDATION_ERROR typically means radius_km out of range —
        // surface a friendly message instead of the backend's generic
        // "request data invalid".
        if (
          err instanceof ApiError &&
          (err.status === 422 || err.code === 'VALIDATION_ERROR')
        ) {
          toast.show({
            variant: 'error',
            title: t('feed.errors.radiusTooLarge'),
          })
          return
        }
        toast.show({
          variant: 'error',
          title: describeError(err, t, 'feed.pageTitle'),
        })
      } finally {
        setLoading(false)
      }
    },
    [t, toast],
  )

  useEffect(() => {
    void (async () => {
      try {
        const loc = await fetchLocation()
        setLocalLocation(loc)
        if (loc) {
          await loadFeed(INITIAL_RADIUS_KM)
        } else {
          setPromptOpen(true)
          setLoading(false)
        }
      } catch {
        setLoading(false)
      }
      setLocationLoaded(true)
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onLocationSettled = async (loc: UserLocation) => {
    setLocalLocation(loc)
    setPromptOpen(false)
    await loadFeed(INITIAL_RADIUS_KM)
  }

  const widenRadius = async () => {
    if (radius >= MAX_RADIUS_KM) {
      toast.show({
        variant: 'info',
        title: t('feed.maxRadiusReached'),
      })
      return
    }
    const next = Math.min(radius * 2, MAX_RADIUS_KM)
    setRadius(next)
    await loadFeed(next)
  }

  return (
    <PageTransition>
      <div className="mx-auto w-full max-w-[1200px] px-4 py-6 sm:px-8">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-[28px] font-extrabold leading-tight text-ink">
              {t('feed.pageTitle')}
            </h1>
            {location && (
              <p className="mt-1 flex items-center gap-1 text-[13px] text-ink-variant">
                <MapPin className="size-3.5" aria-hidden />
                {location.address_text ??
                  `${location.lat.toFixed(3)}, ${location.lng.toFixed(3)}`}
                <span className="mx-1">·</span>
                {t('feed.radiusLabel', { km: radius })}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPromptOpen(true)}
              disabled={!locationLoaded}
            >
              {t('feed.changeLocation')}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => loadFeed(radius)}
              disabled={loading}
            >
              <RefreshCw className="size-4" aria-hidden />
            </Button>
            <Link
              to="/app/feed/saved"
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-[13px] font-bold text-ink-variant hover:bg-panel"
            >
              <Bookmark className="size-3.5" aria-hidden />
              {t('feed.savedTitle')}
            </Link>
          </div>
        </header>

        <div className="mt-6">
          {loading ? (
            <div className="flex justify-center py-20">
              <Spinner />
            </div>
          ) : feed && feed.items.length > 0 ? (
            <FeedStack
              items={feed.items}
              onStackExhausted={() => loadFeed(radius)}
              onWidenRadius={widenRadius}
            />
          ) : feed && feed.items.length === 0 ? (
            <FeedStack
              items={[]}
              onStackExhausted={() => loadFeed(radius)}
              onWidenRadius={widenRadius}
            />
          ) : null}
        </div>

        <LocationPrompt
          open={promptOpen}
          onSettled={onLocationSettled}
          onClose={() => location && setPromptOpen(false)}
        />
      </div>
    </PageTransition>
  )
}
