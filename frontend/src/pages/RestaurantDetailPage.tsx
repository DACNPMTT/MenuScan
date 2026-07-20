import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, MapPin, Phone, Star, Utensils } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Spinner } from '@/shared/components/Spinner'
import { Button } from '@/shared/components/ui/button'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { useToast } from '@/app/providers/ToastProvider'
import { describeError } from '@/shared/lib/errors'
import { formatCurrency } from '@/shared/lib/currency'
import { fetchRestaurantDetail, saveRestaurant, unsaveRestaurant } from '@/features/feed/api'
import { googleMapsUrl } from '@/features/feed/types'
import type { RestaurantCard } from '@/features/feed/types'
import { InviteFriendsHere } from '@/features/feed/components/InviteFriendsHere'

/** Full detail page for one restaurant. */
export function RestaurantDetailPage() {
  const { restaurantSourceId } = useParams<{ restaurantSourceId: string }>()
  const sourceId = Number(restaurantSourceId)
  const { t } = useTranslation()
  useDocumentTitle(`${t('feed.detailTitle')} | MenuScan`)
  const toast = useToast()

  const [restaurant, setRestaurant] = useState<RestaurantCard | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!Number.isFinite(sourceId)) {
      setLoading(false)
      return
    }
    void (async () => {
      setLoading(true)
      try {
        const data = await fetchRestaurantDetail(sourceId)
        setRestaurant(data)
      } catch (err) {
        toast.show({
          variant: 'error',
          title: describeError(err, t, 'feed.detailTitle'),
        })
      } finally {
        setLoading(false)
      }
    })()
  }, [sourceId, t, toast])

  const handleSaveToggle = async () => {
    if (!restaurant) return
    setBusy(true)
    try {
      if (restaurant.saved) {
        await unsaveRestaurant(restaurant.source_id)
        setRestaurant({ ...restaurant, saved: false })
        toast.show({ variant: 'info', title: t('feed.toast.unsaved') })
      } else {
        const updated = await saveRestaurant(restaurant.source_id)
        setRestaurant(updated)
        toast.show({ variant: 'success', title: t('feed.toast.saved') })
      }
    } catch (err) {
      toast.show({
        variant: 'error',
        title: describeError(err, t, 'feed.detailTitle'),
      })
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <PageTransition>
        <div className="flex justify-center py-20">
          <Spinner />
        </div>
      </PageTransition>
    )
  }

  if (!restaurant) {
    return (
      <PageTransition>
        <div className="mx-auto w-full max-w-2xl px-4 py-8">
          <p className="text-[14px] text-ink-variant">{t('common.retry')}</p>
          <Link to="/app/feed" className="mt-3 inline-block text-primary">
            ← {t('common.back')}
          </Link>
        </div>
      </PageTransition>
    )
  }

  const price = restaurant.avg_price
    ? formatCurrency(restaurant.avg_price, 'VND')
    : t('feed.card.noPrice')

  return (
    <PageTransition>
      <div className="mx-auto w-full max-w-[860px] px-4 py-6 sm:px-8">
        <Link
          to="/app/feed"
          className="inline-flex items-center gap-1.5 text-[13px] font-bold text-ink-variant hover:text-ink"
        >
          <ArrowLeft className="size-4" aria-hidden />
          {t('common.back')}
        </Link>

        <article className="mt-4 overflow-hidden rounded-3xl border border-border bg-surface shadow-3">
          <div className="relative aspect-[16/9] w-full bg-panel">
            {restaurant.image_url && (
              <img
                src={restaurant.image_url}
                alt={restaurant.name}
                className="size-full object-cover"
              />
            )}
            <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/80 to-transparent p-5">
              <h1 className="text-[28px] font-extrabold leading-tight text-white">
                {restaurant.name}
              </h1>
              <p className="mt-1 flex items-center gap-1 text-[13px] text-white/85">
                <MapPin className="size-3.5" aria-hidden />
                {restaurant.address}
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-5 p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-4 text-[14px]">
                {restaurant.star != null && (
                  <span className="flex items-center gap-1 font-bold text-ink">
                    <Star className="size-5 fill-amber text-amber" aria-hidden />
                    {restaurant.star.toFixed(1)}
                  </span>
                )}
                <span className="font-bold text-ink">{price}</span>
                {restaurant.distance_km != null && (
                  <span className="text-ink-variant">
                    {t('feed.card.distance', {
                      km: restaurant.distance_km.toFixed(1),
                    })}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant={restaurant.saved ? 'default' : 'outline'}
                  onClick={handleSaveToggle}
                  disabled={busy}
                >
                  {restaurant.saved
                    ? t('feed.card.unsave')
                    : t('feed.card.save')}
                </Button>
              </div>
            </div>

            {restaurant.type.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {restaurant.type.map((cuisine) => (
                  <span
                    key={cuisine}
                    className="rounded-full bg-panel px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-ink-variant"
                  >
                    {cuisine}
                  </span>
                ))}
              </div>
            )}

            {(restaurant.match_reasons.length > 0 ||
              restaurant.caution_reasons.length > 0) && (
              <div className="flex flex-wrap gap-1.5">
                {restaurant.match_reasons.map((reason) => (
                  <span
                    key={`m-${reason}`}
                    className="rounded-full bg-success/15 px-2.5 py-1 text-[11px] font-bold text-success"
                  >
                    {reason}
                  </span>
                ))}
                {restaurant.caution_reasons.map((reason) => (
                  <span
                    key={`c-${reason}`}
                    className="rounded-full bg-destructive/15 px-2.5 py-1 text-[11px] font-bold text-destructive"
                  >
                    ⚠ {reason}
                  </span>
                ))}
              </div>
            )}

            {restaurant.semantic_text && (
              <section>
                <h2 className="mb-2 text-[16px] font-bold text-ink">
                  {t('feed.detail.about')}
                </h2>
                <p className="text-[14px] leading-relaxed text-ink-variant">
                  {restaurant.semantic_text}
                </p>
              </section>
            )}

            {restaurant.meals.length > 0 && (
              <section>
                <h2 className="mb-2 flex items-center gap-1.5 text-[16px] font-bold text-ink">
                  <Utensils className="size-4" aria-hidden />
                  {t('feed.detail.meals')}
                </h2>
                <ul className="divide-y divide-border rounded-2xl border border-border">
                  {restaurant.meals.map((meal, idx) => (
                    <li
                      key={`${meal.name}-${idx}`}
                      className="flex items-center justify-between gap-3 px-4 py-3 text-[14px]"
                    >
                      <span className="font-medium text-ink">{meal.name}</span>
                      {meal.price != null && (
                        <span className="text-ink-variant">
                          {formatCurrency(meal.price, 'VND')}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <div className="flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-col gap-1 text-[13px] text-ink-variant">
                <span className="flex items-center gap-1.5">
                  <MapPin className="size-3.5" aria-hidden />
                  {restaurant.address}
                </span>
                {restaurant.phone_num && (
                  <a
                    href={`tel:${restaurant.phone_num.replace(/\s+/g, '')}`}
                    className="flex items-center gap-1.5 hover:text-ink"
                  >
                    <Phone className="size-3.5" aria-hidden />
                    {restaurant.phone_num}
                  </a>
                )}
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <a
                  href={googleMapsUrl(restaurant.lat, restaurant.lng)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-border bg-surface px-4 py-2.5 text-[13px] font-bold text-ink hover:bg-panel"
                >
                  <MapPin className="size-4" aria-hidden />
                  {t('feed.detail.openMaps')}
                </a>
                <InviteFriendsHere restaurantSourceId={restaurant.source_id} />
              </div>
            </div>
          </div>
        </article>
      </div>
    </PageTransition>
  )
}
