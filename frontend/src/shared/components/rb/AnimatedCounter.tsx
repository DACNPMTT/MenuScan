import { useEffect, useRef } from 'react'
import { animate, useInView, useMotionValue } from 'motion/react'

/**
 * Counts from `from` to `to` when scrolled into view (ReactBits-inspired,
 * motion-only). Renders a plain span whose textContent is driven by a motion
 * value — no React re-render per frame. The DOM write happens inside the
 * motion-value change callback (after render), never during render.
 */
interface AnimatedCounterProps {
  to: number
  from?: number
  duration?: number
  /** Format the live value (e.g. thousands separators, decimals). */
  format?: (value: number) => string
  className?: string
}

export function AnimatedCounter({
  to,
  from = 0,
  duration = 1.6,
  format,
  className,
}: AnimatedCounterProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-40px' })
  const value = useMotionValue(from)

  useEffect(() => {
    if (!inView) return
    const controls = animate(value, to, {
      duration,
      ease: [0.22, 1, 0.36, 1],
    })
    const unsubscribe = value.on('change', (latest) => {
      const node = ref.current
      if (node) {
        node.textContent = format
          ? format(latest)
          : Math.round(latest).toLocaleString()
      }
    })
    return () => {
      controls.stop()
      unsubscribe()
    }
  }, [inView, to, duration, value, format])

  const initialText = format ? format(from) : Math.round(from).toLocaleString()

  return (
    <span ref={ref} className={className}>
      {initialText}
    </span>
  )
}
