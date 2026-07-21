import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Compass } from 'lucide-react'
import { EmptyState } from '@/shared/components/EmptyState'
import { Spinner } from '@/shared/components/Spinner'
import { Button } from '@/shared/components/ui/button'
import { useToast } from '@/app/providers/ToastProvider'
import { useInteractionQueue } from '../interaction-queue'
import type { RestaurantCard as RestaurantCardType } from '../types'
import { RestaurantCardView } from './RestaurantCard'

/** How many cards render at once: 1 interactive front + up to 2 peek behind. */
const STACK_DEPTH = 3

interface FeedStackProps {
  items: RestaurantCardType[]
  /** Called when the user swipes past the last card — parent refetches. */
  onStackExhausted: () => void
  /** User asked to widen the radius — parent refetches at radius * 2. */
  onWidenRadius: () => void
}

/**
 * Card-stack focus view for the Discovery feed. Renders up to 3 cards (front
 * interactive + 2 peek behind as depth cues); interactions are pushed onto a
 * batched queue (`useInteractionQueue`) and the card advances optimistically —
 * no per-swipe network round-trip, no per-swipe blocking.
 *
 * When the local stack is exhausted, `onStackExhausted` fires once so the
 * parent can fetch the next page (by which time the queue has usually flushed
 * the just-recorded seens server-side, so they don't reappear).
 */
export function FeedStack({ items, onStackExhausted, onWidenRadius }: FeedStackProps) {
  const { t } = useTranslation()
  const toast = useToast()
  const [index, setIndex] = useState(0)

  const { enqueue } = useInteractionQueue({
    onError: (count) =>
      toast.show({
        variant: 'error',
        title: t('feed.toast.batchFailed', { count }),
      }),
  })

  // Keep the latest onStackExhausted without re-running the exhaustion effect
  // on every parent re-render (the parent passes a fresh closure each time).
  const onStackExhaustedRef = useRef(onStackExhausted)
  useEffect(() => {
    onStackExhaustedRef.current = onStackExhausted
  })

  // Reset to the front of the stack whenever the parent passes a fresh items
  // array (initial load, refetch, widen-radius). Without this, the index from
  // a previous batch would carry over and the user would start mid-stack.
  const prevItemsRef = useRef(items)
  useEffect(() => {
    if (prevItemsRef.current !== items) {
      setIndex(0)
      prevItemsRef.current = items
    }
  }, [items])

  // Fire onStackExhausted exactly once when the user swipes past the last
  // card. The guard `items.length > 0` prevents firing on the initial empty
  // state (genuine empty is handled by the EmptyState branch below).
  useEffect(() => {
    if (items.length > 0 && index >= items.length) {
      onStackExhaustedRef.current()
    }
  }, [index, items.length])

  // index is allowed to reach items.length (= "just swiped past the last
  // card"); visibleStack.slice handles the empty case below.
  const safeIndex = Math.max(0, Math.min(index, items.length))
  const visibleStack = items.slice(safeIndex, safeIndex + STACK_DEPTH)

  if (visibleStack.length === 0) {
    // No items at all → genuine empty state with the widen-radius CTA. If the
    // parent is mid-refetch (loading more after exhaustion), FeedStack will
    // have unmounted by the time the spinner would show, so we only render
    // EmptyState here.
    if (items.length === 0) {
      return (
        <EmptyState
          icon={Compass}
          title={t('feed.emptyFeed.title')}
          description={t('feed.emptyFeed.subtitle')}
          action={
            <Button onClick={onWidenRadius} variant="default">
              {t('feed.expandRadius')}
            </Button>
          }
        />
      )
    }
    // Swiped past the last card while the parent hasn't unmounted us yet —
    // flash the loader until the refetch lands.
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    )
  }

  const advance = () => setIndex((i) => Math.min(i + 1, items.length))

  const handleSkip = () => {
    const front = visibleStack[0]
    if (!front) return
    enqueue({ kind: 'seen', sourceId: front.source_id, action: 'skip' })
    advance()
  }

  const handleSaveToggle = () => {
    const front = visibleStack[0]
    if (!front) return
    // Saved cards don't normally show in the feed (filtered server-side); if
    // we somehow see one, fall through to skip so it leaves the feed. Both
    // `save` and `seen=view` enqueue — they have distinct dedupe keys
    // (`save:id` vs `seen:id`) so both ship in the same flush.
    if (!front.saved) {
      enqueue({ kind: 'save', sourceId: front.source_id })
      enqueue({ kind: 'seen', sourceId: front.source_id, action: 'view' })
    } else {
      enqueue({ kind: 'seen', sourceId: front.source_id, action: 'skip' })
    }
    advance()
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4">
      <div className="relative overflow-hidden">
        {[...visibleStack].reverse().map((restaurant, domIndex) => {
          // After reverse: domIndex 0 = back-most child, last = front child.
          // visibleStack[0] is always the front of the stack.
          const positionFromFront = visibleStack.length - 1 - domIndex
          const isFront = positionFromFront === 0
          return (
            <RestaurantCardView
              key={restaurant.source_id}
              restaurant={restaurant}
              saved={restaurant.saved}
              onSaveToggle={isFront ? handleSaveToggle : undefined}
              onSkip={isFront ? handleSkip : undefined}
              peek={!isFront}
              peekIndex={positionFromFront}
            />
          )
        })}
      </div>
      <p className="text-center text-[12px] text-ink-variant">
        {Math.min(safeIndex + 1, items.length)} / {items.length}
      </p>
    </div>
  )
}
