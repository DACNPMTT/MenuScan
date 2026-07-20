import { useState } from 'react'
import { Bookmark, MapPin, Star, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  animate,
  motion,
  useMotionValue,
  useTransform,
  type PanInfo,
} from 'motion/react'
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
  /**
   * When true, renders as a non-interactive visual preview stacked behind the
   * active card. Used by FeedStack to show depth. `peekIndex` is 0 from the
   * front of the stack (i.e. 1 = first peek behind, 2 = second).
   */
  peek?: boolean
  peekIndex?: number
  /**
   * Disable the action buttons (e.g. while an unsave API call is in-flight
   * on the SavedPage grid). FeedStack cards manage their own `flying` state
   * and don't use this.
   */
  busy?: boolean
  className?: string
}

/** Drag offset (px) past which a release counts as a swipe. */
const SWIPE_THRESHOLD_PX = 100
/** Drag velocity (px/s) past which a release counts as a swipe. */
const SWIPE_VELOCITY = 500

/**
 * Full-bleed restaurant card for the Discovery feed.
 *
 * The front-of-stack card is horizontally draggable: swipe right to save,
 * left to skip. Buttons trigger the same fly-off animation for tactile parity.
 * Behind-cards render as non-interactive scaled previews.
 *
 * z-index lives in Tailwind classes (z-30 / z-20 / z-10), NOT in motion's
 * `animate`, because motion doesn't snap zIndex reliably across exit
 * transitions — that was the root cause of the back-card-overlapping-front
 * bug. Exit variants explicitly drop zIndex to 0 so an exiting card never
 * fights its successor.
 *
 * All animation is GPU-friendly (transform + opacity only); spring physics
 * tuned for mobile feel without being heavy.
 */
export function RestaurantCardView({
  restaurant,
  saved,
  onSaveToggle,
  onSkip,
  peek = false,
  peekIndex = 0,
  busy = false,
  className,
}: RestaurantCardViewProps) {
  const { t } = useTranslation()
  const price = restaurant.avg_price
    ? formatCurrency(restaurant.avg_price, 'VND')
    : t('feed.card.noPrice')

  // Drag is driven by an explicit motion value so we can imperatively fly the
  // card off-screen on swipe. Hooks are unconditional (React rules); the
  // `drag` prop below gates whether pointer input actually moves it.
  const x = useMotionValue(0)
  const rotate = useTransform(x, [-200, 0, 200], [-12, 0, 12])
  const likeOpacity = useTransform(x, [20, 120], [0, 1])
  const nopeOpacity = useTransform(x, [-120, -20], [1, 0])
  const [flying, setFlying] = useState(false)

  // The card is interactive (draggable + animated buttons) only when it's the
  // front of the feed stack AND both swipe handlers are wired. SavedPage only
  // passes onSaveToggle (unsave), so its cards stay non-draggable.
  const interactive = !peek && !flying && onSkip !== undefined && onSaveToggle !== undefined

  const flyOff = (direction: 1 | -1, cb?: () => void) => {
    if (flying) return
    setFlying(true)
    const distance =
      direction * (typeof window !== 'undefined' ? window.innerWidth : 500)
    animate(x, distance, {
      duration: 0.28,
      ease: [0.4, 0, 0.2, 1],
      onComplete: () => cb?.(),
    })
  }

  const snapBack = () => {
    animate(x, 0, { type: 'spring', stiffness: 450, damping: 32 })
  }

  const handleDragEnd = (_: unknown, info: PanInfo) => {
    if (info.offset.x <= -SWIPE_THRESHOLD_PX || info.velocity.x <= -SWIPE_VELOCITY) {
      flyOff(-1, onSkip)
    } else if (info.offset.x >= SWIPE_THRESHOLD_PX || info.velocity.x >= SWIPE_VELOCITY) {
      flyOff(1, onSaveToggle)
    } else {
      snapBack()
    }
  }

  // Steady-state stack transform. y=0 (no vertical offset) is the key fix
  // for the back-card-overlap complaint: with center origin + scale<1, the
  // peek card is fully contained within the front card's bounds, so the
  // front (z-30) completely occludes it. Depth is conveyed only during the
  // swipe transition, when cards reposition. No more "back content
  // overlapping front" in steady state.
  const stackAnimate = peek
    ? peekIndex === 1
      ? { scale: 0.96, y: 0, opacity: 0.55 }
      : peekIndex >= 2
        ? { scale: 0.92, y: 0, opacity: 0.3 }
        : { scale: 1, y: 0, opacity: 1 }
    : { scale: 1, y: 0, opacity: 1 }

  const stackZ = peek
    ? peekIndex === 1
      ? 'z-20'
      : peekIndex >= 2
        ? 'z-10'
        : 'z-30'
    : 'z-30'

  return (
    <motion.article
      style={{ x, rotate }}
      drag={interactive ? 'x' : false}
      dragElastic={0.6}
      dragMomentum={false}
      onDragEnd={handleDragEnd}
      initial={{ opacity: 0, y: 24, scale: 0.96 }}
      animate={stackAnimate}
      transition={{ type: 'spring', stiffness: 320, damping: 30, mass: 0.7 }}
      className={cn(
        'relative overflow-hidden rounded-3xl border border-border bg-canvas shadow-2 will-change-transform',
        peek && 'absolute inset-x-0 top-0 pointer-events-none',
        // touch-pan-y lets the page scroll vertically while we capture the
        // horizontal pan for swipe — critical for mobile.
        interactive && 'cursor-grab touch-pan-y active:cursor-grabbing',
        stackZ,
        className,
      )}
    >
      <Link
        to={`/app/feed/r/${restaurant.source_id}`}
        className="block focus:outline-none"
        // Prevent navigation when the user is mid-drag (the card body is a
        // link, but a swipe shouldn't route).
        onClick={(e) => {
          if (Math.abs(x.get()) > 4) e.preventDefault()
        }}
      >
        {/* Image with name + distance overlay */}
        <div className="relative aspect-[4/3] w-full overflow-hidden bg-panel">
          {restaurant.image_url ? (
            <img
              src={restaurant.image_url}
              alt={restaurant.name}
              loading="lazy"
              className="size-full object-cover object-center"
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

      {/* Swipe hint badges — visible only on the interactive front card,
          opacity tracks the drag so they fade in as the user commits. */}
      {interactive && (
        <>
          <motion.div
            style={{ opacity: likeOpacity }}
            aria-hidden
            className="pointer-events-none absolute left-5 top-5 z-20 -rotate-12 rounded-2xl border-4 border-success px-3 py-1 text-[18px] font-extrabold uppercase tracking-wide text-success"
          >
            {t('feed.card.like')}
          </motion.div>
          <motion.div
            style={{ opacity: nopeOpacity }}
            aria-hidden
            className="pointer-events-none absolute right-5 top-5 z-20 rotate-12 rounded-2xl border-4 border-destructive px-3 py-1 text-[18px] font-extrabold uppercase tracking-wide text-destructive"
          >
            {t('feed.card.nope')}
          </motion.div>
        </>
      )}

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

        {/* Action buttons — front card only. Tap routes through the same
            flyOff as a drag so the animation is identical either way. */}
        {!peek && (onSaveToggle || onSkip) && (
          <div className="mt-1 flex items-center gap-2">
            {onSaveToggle && (
              <button
                type="button"
                onClick={() =>
                  interactive ? flyOff(1, onSaveToggle) : onSaveToggle()
                }
                disabled={flying || busy}
                className={cn(
                  'flex flex-1 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-[14px] font-bold transition-colors',
                  saved
                    ? 'bg-success text-white hover:bg-success/90'
                    : 'bg-primary text-white hover:bg-primary-dark',
                  flying && 'cursor-not-allowed opacity-60',
                )}
              >
                <Bookmark className={cn('size-4', saved && 'fill-white')} aria-hidden />
                {saved ? t('feed.card.unsave') : t('feed.card.save')}
              </button>
            )}
            {onSkip && (
              <button
                type="button"
                onClick={() => (interactive ? flyOff(-1, onSkip) : onSkip())}
                disabled={flying || busy}
                className={cn(
                  'flex size-12 shrink-0 items-center justify-center rounded-2xl border border-border bg-surface text-ink-variant transition-colors hover:bg-panel',
                  flying && 'cursor-not-allowed opacity-60',
                )}
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
