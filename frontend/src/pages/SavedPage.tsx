import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bookmark } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Spinner } from '@/shared/components/Spinner'
import { EmptyState } from '@/shared/components/EmptyState'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useToast } from '@/app/providers/ToastProvider'
import { describeError } from '@/shared/lib/errors'
import { fetchSaved, unsaveRestaurant } from '@/features/feed/api'
import type { RestaurantCard as RestaurantCardType } from '@/features/feed/types'
import { RestaurantCardView } from '@/features/feed/components/RestaurantCard'

/** Vertical list of saved restaurants with Unsave buttons. */
export function SavedPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('feed.savedTitle')} | MenuScan`)
  const toast = useToast()

  const [saved, setSaved] = useState<RestaurantCardType[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)

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
    void load()
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

  return (
    <PageTransition>
      <div className="mx-auto w-full max-w-[1200px] px-4 py-6 sm:px-8">
        <header className="flex flex-col gap-1">
          <h1 className="text-[28px] font-extrabold leading-tight text-ink">
            {t('feed.savedTitle')}
          </h1>
          <p className="text-[14px] text-ink-variant">
            {saved.length > 0
              ? `${saved.length}`
              : ''}
          </p>
        </header>

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
          ) : (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {saved.map((restaurant) => (
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
