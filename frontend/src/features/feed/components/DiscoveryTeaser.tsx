import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useReducedMotion, type PanInfo } from 'motion/react'
import { useTranslation } from 'react-i18next'
import { ChevronRight, Star } from 'lucide-react'
import { cn } from '@/shared/lib/cn'
import { formatCurrency } from '@/shared/lib/currency'

/** Auto-advance cadence for the front card. */
const SWAP_INTERVAL_MS = 4000
/** Number of cards visible in the stack (front + mid + back). */
const VISIBLE_STACK = 3
/** Horizontal drag (px) past which a release opens the feed. */
const SWIPE_THRESHOLD_PX = 80
/** Drag velocity (px/s) past which a release opens the feed. */
const SWIPE_VELOCITY = 500
/** Preview-card dimensions. Compact (~20% smaller than the original
 *  RestaurantCard shape) so the teaser reads as a dock icon, not a hero. */
const CARD_W = 192
const CARD_H = 224
/** Top inset inside the cluster — gives the back card (y = -CLUSTER_PAD_TOP)
 *  room to rise without overflowing the cluster's top edge (which used to
 *  crash into the dashboard h1 above). */
const CLUSTER_PAD_TOP = 44
/** Extra slack on the right side so the back card's scaled right edge
 *  (x offset + scaled width) is fully contained inside the cluster frame. */
const CLUSTER_RIGHT_SLACK = 64
/** Bottom space below the front card so the cluster frame breathes. */
const CLUSTER_BOTTOM_SLACK = 20

interface SampleRestaurant {
  source_id: number
  name: string
  image_url: string
  type: string
  star: number
  avg_price: number
}

// Pulled from data/restaurants.json id 1, 2, 3 — all three have working
// image_urls and Vietnamese cuisine. Minimal subset only; this is a decorative
// teaser, so we avoid the full 14-field RestaurantCard shape.
const SAMPLE_RESTAURANTS: SampleRestaurant[] = [
  {
    source_id: 1,
    name: 'Ăn Thôi',
    image_url:
      'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT-1PzC5iv80HA3vJ0ziU1rzNCMnBRrLdSPgg&s',
    type: 'Quán Việt',
    star: 4.8,
    avg_price: 150000,
  },
  {
    source_id: 2,
    name: 'Hải sản Mộc Quán Đà Nẵng',
    image_url:
      'https://hellodanang.vn/wp-content/uploads/2025/12/bai-viet-danh-gia-ve-hai-san-moc-quan-da-nang-1764818921.jpg',
    type: 'Hải sản',
    star: 4.8,
    avg_price: 300000,
  },
  {
    source_id: 3,
    name: 'Nhà Bếp Xưa Restaurant',
    image_url:
      'https://dynamic-media-cdn.tripadvisor.com/media/photo-o/2c/ed/e7/e6/caption.jpg?w=900&h=500&s=1',
    type: 'Quán Việt',
    star: 4.8,
    avg_price: 120000,
  },
]

/** Stack slot: 0 = front, 1 = mid, 2 = back. null = hidden. */
type Slot = 0 | 1 | 2

/** Compute the slot for the card at `indexInArray` given the current
 * `frontIdx`. Cards beyond the visible window return null and unmount. */
function slotFor(indexInArray: number, frontIdx: number, total: number): Slot | null {
  const offset = (indexInArray - frontIdx + total) % total
  return offset < VISIBLE_STACK ? (offset as Slot) : null
}

/** CardSwap-inspired 3D stack: each slot offsets +X, -Y, slight Y-rotation.
 * Front (0): identity. Mid (1): right & up, scaled down, faded. Back (2): more.
 * The y offset of the back slot (−44) is exactly contained by the cluster's
 * `CLUSTER_PAD_TOP`, so cards never overflow the cluster's top edge. */
function slotTransform(slot: Slot) {
  switch (slot) {
    case 0:
      return { x: 0, y: 0, rotateY: 0, scale: 1, opacity: 1, zIndex: 30 }
    case 1:
      return { x: 30, y: -22, rotateY: -8, scale: 0.92, opacity: 0.7, zIndex: 20 }
    case 2:
      return { x: 60, y: -44, rotateY: -16, scale: 0.84, opacity: 0.45, zIndex: 10 }
  }
}

/**
 * Discovery CardSwap teaser for the Dashboard.
 *
 * Compact dock-style 3-card stack (~256×288px) that auto-cycles sample
 * restaurants every 4s. Tap the cluster, swipe it rightward, or press the
 * CTA to navigate to `/app/feed`. Honors `prefers-reduced-motion` (auto-swap
 * disabled, cards static) and pauses on hover.
 *
 * Single text column (h2 + one CTA pill) — eyebrow "Khám phá" và nhãn
 * "Mở feed" được gộp vào CTA "Khám phá Feed" để tiết kiệm vertical space.
 *
 * Self-contained: the only prop is an optional `className` merge onto the
 * root. All sample data is hard-coded above; no API calls.
 */
export function DiscoveryTeaser({ className }: { className?: string }) {
  const { t } = useTranslation()
  const [frontIdx, setFrontIdx] = useState(0)
  const [paused, setPaused] = useState(false)
  const reduce = useReducedMotion()
  const navigate = useNavigate()
  // True between motion's onDragStart (which fires synchronously during the
  // first pointermove past motion's drag threshold) and the browser-synthesized
  // click that follows pointerup. This is what lets onClick tell a genuine tap
  // apart from a click after a real drag — onDragEnd runs too late to gate it.
  // Reset on the next pointerdown so the next gesture starts clean.
  const justDraggedRef = useRef(false)

  const open = useCallback(() => navigate('/app/feed'), [navigate])

  const handleDragStart = useCallback(() => {
    justDraggedRef.current = true
  }, [])

  const handleDragEnd = useCallback(
    (_: unknown, info: PanInfo) => {
      if (info.offset.x >= SWIPE_THRESHOLD_PX || info.velocity.x >= SWIPE_VELOCITY) {
        open()
      }
    },
    [open],
  )

  const handleClick = useCallback(() => {
    if (justDraggedRef.current) {
      // This click followed a real drag — onDragEnd already decided whether
      // to open. Swallow it so a sub-threshold drag doesn't navigate.
      justDraggedRef.current = false
      return
    }
    open()
  }, [open])

  // Auto-advance the front card on a fixed cadence. Disabled under
  // reduced-motion (cards stay static at slot 0) and paused on hover.
  useEffect(() => {
    if (paused || reduce) return
    const id = window.setInterval(
      () => setFrontIdx((i) => (i + 1) % SAMPLE_RESTAURANTS.length),
      SWAP_INTERVAL_MS,
    )
    return () => window.clearInterval(id)
  }, [paused, reduce])

  return (
    <motion.div
      className={cn(
        'mt-7 flex flex-col items-center gap-5 sm:flex-row sm:gap-8',
        className,
      )}
      onHoverStart={() => setPaused(true)}
      onHoverEnd={() => setPaused(false)}
    >
      {/* CardSwap cluster — also the swipe/tap target. */}
      <motion.div
        role="button"
        tabIndex={0}
        aria-label={t('feed.teaser.openFeed')}
        onClick={handleClick}
        onPointerDown={() => {
          justDraggedRef.current = false
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            open()
          }
        }}
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.5}
        dragMomentum={false}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        whileTap={{ scale: 0.97 }}
        className="relative shrink-0 cursor-pointer touch-pan-y select-none"
        style={{
          width: CARD_W + CLUSTER_RIGHT_SLACK,
          height: CARD_H + CLUSTER_PAD_TOP + CLUSTER_BOTTOM_SLACK,
          perspective: 900,
        }}
      >
        {SAMPLE_RESTAURANTS.map((r, i) => {
          const slot = slotFor(i, frontIdx, SAMPLE_RESTAURANTS.length)
          if (slot === null) return null
          return <PreviewCard key={r.source_id} restaurant={r} slot={slot} />
        })}
      </motion.div>

      {/* Text column — single h2 + single CTA pill. Eyebrow "Khám phá" gộp
          vào CTA để bỏ 2 element dư (eyebrow pill + subtitle). */}
      <div className="flex flex-col items-start gap-4">
        <h2 className="max-w-[420px] text-[24px] font-extrabold leading-tight text-ink sm:text-[28px]">
          {t('feed.teaser.title')}
        </h2>
        <button
          type="button"
          onClick={open}
          className="inline-flex items-center gap-2 rounded-2xl bg-primary px-6 py-3.5 text-[14px] font-extrabold uppercase tracking-[0.08em] text-white shadow-[0_4px_0_var(--primary-dark)] transition-all hover:-translate-y-0.5 active:translate-y-[2px] active:shadow-[0_2px_0_var(--primary-dark)]"
        >
          {t('feed.teaser.cta')}
          <ChevronRight className="size-4" aria-hidden />
        </button>
      </div>
    </motion.div>
  )
}

/** One stacked preview card. Position/scale/opacity are driven by `slot`;
 * when `frontIdx` advances, motion animates the card to its new slot in one
 * spring. Styling lifted from the RestaurantCard redesign (owl-green-soft
 * placeholder, bee-gold star, solid navy ink band, hairline border + gray
 * lip) so the teaser matches the feed cards it opens. The card is anchored
 * `top: CLUSTER_PAD_TOP` so the back slot's negative y-offset stays inside
 * the cluster frame. The IMG is set `draggable={false}` +
 * `pointer-events-none` so native HTML5 drag-and-drop on the image can't
 * preempt motion's pointer-based drag on the cluster. */
function PreviewCard({ restaurant, slot }: { restaurant: SampleRestaurant; slot: Slot }) {
  return (
    <motion.div
      layout
      initial={false}
      animate={slotTransform(slot)}
      transition={{ type: 'spring', stiffness: 140, damping: 18, mass: 0.8 }}
      className="absolute left-0 overflow-hidden rounded-3xl border-2 border-border bg-canvas shadow-[0_6px_0_var(--border)] will-change-transform"
      style={{
        width: CARD_W,
        height: CARD_H,
        top: CLUSTER_PAD_TOP,
        transformOrigin: 'center center',
      }}
    >
      <div className="relative aspect-[4/5] w-full overflow-hidden bg-[#d7ffb8]">
        <img
          src={restaurant.image_url}
          alt={restaurant.name}
          loading="lazy"
          draggable={false}
          className="pointer-events-none size-full object-cover object-center"
        />
        {/* Solid navy ink band (NO gradient). */}
        <div className="absolute inset-x-0 bottom-0 bg-ink/92 px-3 py-2">
          <p className="text-[13px] font-extrabold leading-tight text-canvas">
            {restaurant.name}
          </p>
          <p className="mt-0.5 text-[9px] font-bold uppercase tracking-[0.08em] text-[#d7ffb8]">
            {restaurant.type}
          </p>
        </div>
      </div>
      {/* Meta row — star (bee-gold) + price. */}
      <div className="flex items-center justify-between px-3 py-1.5 text-[11px]">
        <span className="flex items-center gap-1 font-extrabold text-ink">
          <Star className="size-3 fill-[#ffc800] text-[#ffc800]" aria-hidden />
          {restaurant.star.toFixed(1)}
        </span>
        <span className="font-extrabold text-ink">
          {formatCurrency(restaurant.avg_price, 'VND')}
        </span>
      </div>
    </motion.div>
  )
}
