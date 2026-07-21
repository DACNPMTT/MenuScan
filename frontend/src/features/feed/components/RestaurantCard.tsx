import { useState } from 'react'
import { Bookmark, MapPin, Star, TriangleAlert, X } from 'lucide-react'
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
        // Duolingo dialect: 2px hairline border + flat 4px gray lip
        // (shadow-as-lip, not diffuse blur). No gradients anywhere.
        'relative overflow-hidden rounded-3xl border-2 border-border bg-canvas shadow-[0_4px_0_var(--border)] will-change-transform',
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
        {/* Image — solid owl-green-soft placeholder (NO gradient). Name +
            distance sit on a flat navy ink band (NO gradient). */}
        <div className="relative aspect-[4/3] w-full overflow-hidden bg-[#d7ffb8]">
          {restaurant.image_url ? (
            <img
              src={restaurant.image_url}
              alt={restaurant.name}
              loading="lazy"
              className="size-full object-cover object-center"
            />
          ) : (
            <div className="flex size-full items-center justify-center">
              <MapPin className="size-16 text-primary" aria-hidden />
            </div>
          )}
          <div className="absolute inset-x-0 bottom-0 bg-ink/92 px-4 py-3">
            <h3 className="text-[20px] font-extrabold leading-tight text-canvas">
              {restaurant.name}
            </h3>
            {restaurant.distance_km != null && (
              <p className="mt-0.5 flex items-center gap-1 text-[12px] font-semibold text-white/75">
                <MapPin className="size-3.5" aria-hidden />
                {t('feed.card.distance', { km: restaurant.distance_km.toFixed(1) })}
              </p>
            )}
          </div>
        </div>
      </Link>

      {/* Swipe hint badges — visible only on the interactive front card,
          opacity tracks the drag so they fade in as the user commits.
          White pill + colored border + colored uppercase label, matching
          the design doc's badge-pill pattern. */}
      {interactive && (
        <>
          <motion.div
            style={{ opacity: likeOpacity }}
            aria-hidden
            className="pointer-events-none absolute left-5 top-5 z-20 -rotate-12 rounded-full border-2 border-primary bg-canvas px-4 py-1.5 text-[15px] font-extrabold uppercase tracking-[0.1em] text-primary shadow-[0_3px_0_var(--primary-dark)]"
          >
            {t('feed.card.like')}
          </motion.div>
          <motion.div
            style={{ opacity: nopeOpacity }}
            aria-hidden
            className="pointer-events-none absolute right-5 top-5 z-20 rotate-12 rounded-full border-2 border-destructive bg-canvas px-4 py-1.5 text-[15px] font-extrabold uppercase tracking-[0.1em] text-destructive shadow-[0_3px_0_#be123c]"
          >
            {t('feed.card.nope')}
          </motion.div>
        </>
      )}

      {/* Meta + actions */}
      <div className="flex flex-col gap-3 px-5 py-4">
        {/* Star + price + cuisines. Bee-gold star, owl-green-soft chips. */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px]">
          {restaurant.star != null && (
            <span className="flex items-center gap-1 font-extrabold text-ink">
              <Star className="size-4 fill-[#ffc800] text-[#ffc800]" aria-hidden />
              {restaurant.star.toFixed(1)}
            </span>
          )}
          <span className="font-extrabold text-ink">{price}</span>
          {restaurant.type.length > 0 && (
            <div className="ml-auto flex flex-wrap gap-1.5">
              {restaurant.type.slice(0, 3).map((cuisine) => (
                <span
                  key={cuisine}
                  className="rounded-full bg-[#d7ffb8] px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[#3c8a02]"
                >
                  {cuisine}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Match + caution reasons. Match uses owl-green-soft; caution uses
            destructive tint with an icon (no emoji per design policy). */}
        {(restaurant.match_reasons.length > 0 ||
          restaurant.caution_reasons.length > 0) && (
          <div className="flex flex-wrap gap-1.5">
            {restaurant.match_reasons.map((reason) => (
              <span
                key={`m-${reason}`}
                className="rounded-full bg-[#d7ffb8] px-2.5 py-1 text-[11px] font-bold text-[#3c8a02]"
              >
                {reason}
              </span>
            ))}
            {restaurant.caution_reasons.map((reason) => (
              <span
                key={`c-${reason}`}
                className="inline-flex items-center gap-1 rounded-full bg-destructive/10 px-2.5 py-1 text-[11px] font-bold text-destructive"
              >
                <TriangleAlert className="size-3" aria-hidden />
                {reason}
              </span>
            ))}
          </div>
        )}

        {/* Action buttons — front card only. Save = button-duo (owl-green
            fill + 4px pressed lip + uppercase label). Skip = white circle
            with X icon, hairline border + gray lip. Both collapse on
            :active to simulate a physical press. */}
        {!peek && (onSaveToggle || onSkip) && (
          <div className="mt-1 flex items-center gap-3">
            {onSaveToggle && (
              <button
                type="button"
                onClick={() =>
                  interactive ? flyOff(1, onSaveToggle) : onSaveToggle()
                }
                disabled={flying || busy}
                className={cn(
                  'flex flex-1 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-[14px] font-extrabold uppercase tracking-[0.08em] transition-all active:translate-y-[2px]',
                  saved
                    ? 'bg-success text-white shadow-[0_4px_0_#15843d] active:shadow-[0_2px_0_#15843d]'
                    : 'bg-primary text-white shadow-[0_4px_0_var(--primary-dark)] active:shadow-[0_2px_0_var(--primary-dark)]',
                  (flying || busy) && 'cursor-not-allowed opacity-60',
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
                aria-label={t('feed.card.skip')}
                className={cn(
                  'flex size-12 shrink-0 items-center justify-center rounded-full border-2 border-border bg-canvas text-ink-variant transition-all shadow-[0_4px_0_var(--border)] active:translate-y-[2px] active:shadow-[0_2px_0_var(--border)]',
                  (flying || busy) && 'cursor-not-allowed opacity-60',
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
