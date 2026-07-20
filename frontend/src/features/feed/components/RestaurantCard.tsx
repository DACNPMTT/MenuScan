import { Bookmark, MapPin, Star, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { cn } from '@/shared/lib/cn'
import { formatCurrency } from '@/shared/lib/currency'
import type { RestaurantCard } from '../types'

interface RestaurantCardViewProps {
  restaurant: RestaurantCard
  /** Whether the bookmark button shows "saved" state. */
  saved: boolean
  /** Save/unsave toggle. When undefined the bookmark button is hidden. */
  onSaveToggle?: () => void
  /** Skip button callback. When undefined the skip button is hidden. */
  onSkip?: () => void
  /** Disable buttons (e.g., during in-flight API call). */
  busy?: boolean
  /**
   * When true, renders as a non-interactive visual preview stacked behind the
   * active card. Used by FeedStack to show depth. `peekIndex` is 0 from the
   * front of the stack (i.e. 1 = first peek behind, 2 = second).
   */
  peek?: boolean
  peekIndex?: number
  className?: string
}
export function RestaurantCardView({
  restaurant,
  saved,
  onSaveToggle,
  onSkip,
  busy = false,
  peek = false,
  peekIndex = 0,
  className,
}: RestaurantCardViewProps) {
  const { t } = useTranslation()
  const price = restaurant.avg_price
    ? formatCurrency(restaurant.avg_price, 'VND')
    : t('feed.card.noPrice')

  // Stack transforms for peek cards. Front card (peekIndex 0 / non-peek) keeps
  // its identity; deeper peek cards sit higher (-y), smaller (scale), dimmer
  // (opacity), and behind (zIndex). Motion's `animate` interpolates between
  // these when a card's position changes (e.g. mid → front after a swipe).
  const stackTransform = peek
    ? peekIndex === 1
      ? { scale: 0.95, y: -12, opacity: 0.7, zIndex: 20 }
      : peekIndex >= 2
        ? { scale: 0.9, y: -24, opacity: 0.4, zIndex: 10 }
        : { scale: 1, y: 0, opacity: 1, zIndex: 30 }
    : { scale: 1, y: 0, opacity: 1, zIndex: 30 }

  return (
    <motion.article
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={stackTransform}
      exit={{ opacity: 0, y: -16, scale: 0.98 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        'relative overflow-hidden rounded-3xl border border-border bg-surface shadow-3',
        // Peek cards are absolutely positioned so they stack behind the
        // front card within the same parent. The front card keeps its
        // `relative` so its z-index applies. tailwind-merge resolves the
        // `relative` + `absolute` conflict in favor of `absolute` for peeks.
        // Standalone cards (SavedPage grid) keep their default block flow.
        peek && 'absolute inset-x-0 top-0',
        peek && 'pointer-events-none',
        className,
      )}
    >
      <Link
        to={`/app/feed/r/${restaurant.source_id}`}
        className="block focus:outline-none"
      >
        {/* Image with name + distance overlay */}
        <div className="relative aspect-[16/10] w-full overflow-hidden bg-panel">
          {restaurant.image_url ? (
            <img
              src={restaurant.image_url}
              alt={restaurant.name}
              loading="lazy"
              className="size-full object-cover"
            />
          ) : (
            <div className="flex size-full items-center justify-center bg-gradient-to-br from-primary/15 to-accent/30">
              <MapPin className="size-12 text-primary/50" aria-hidden />
            </div>
          )}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/80 via-ink/40 to-transparent p-4">
            <h3 className="text-[22px] font-extrabold leading-tight text-white">
              {restaurant.name}
            </h3>
            {restaurant.distance_km != null && (
              <p className="mt-1 flex items-center gap-1 text-[13px] text-white/85">
                <MapPin className="size-3.5" aria-hidden />
                {t('feed.card.distance', { km: restaurant.distance_km.toFixed(1) })}
              </p>
            )}
          </div>
        </div>
      </Link>

      {/* Meta row */}
      <div className="flex flex-col gap-3 px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3 text-[13px] text-ink-variant">
            {restaurant.star != null && (
              <span className="flex items-center gap-1 font-bold text-ink">
                <Star className="size-4 fill-amber text-amber" aria-hidden />
                {restaurant.star.toFixed(1)}
              </span>
            )}
            <span className="font-bold text-ink">{price}</span>
          </div>
          {restaurant.type.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {restaurant.type.slice(0, 3).map((cuisine) => (
                <span
                  key={cuisine}
                  className="rounded-full bg-panel px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-ink-variant"
                >
                  {cuisine}
                </span>
              ))}
            </div>
          )}
        </div>

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

        {!peek && (onSaveToggle || onSkip) && (
          <div className="mt-1 flex items-center gap-2">
            {onSaveToggle && (
              <button
                type="button"
                onClick={onSaveToggle}
                disabled={busy}
                className={cn(
                  'flex flex-1 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-[14px] font-bold transition-all',
                  saved
                    ? 'bg-success text-white hover:bg-success/90'
                    : 'bg-primary text-white hover:bg-primary-dark',
                  busy && 'cursor-not-allowed opacity-60',
                )}
              >
                <Bookmark className={cn('size-4', saved && 'fill-white')} aria-hidden />
                {saved ? t('feed.card.unsave') : t('feed.card.save')}
              </button>
            )}
            {onSkip && (
              <button
                type="button"
                onClick={onSkip}
                disabled={busy}
                className={cn(
                  'flex size-12 shrink-0 items-center justify-center rounded-2xl border border-border bg-surface text-ink-variant transition-all hover:bg-panel',
                  busy && 'cursor-not-allowed opacity-60',
                )}
                aria-label={t('feed.card.skip')}
              >
                <X className="size-5" aria-hidden />
              </button>
            )}
          </div>
        )}
      </div>
    </motion.article>
  )
}
