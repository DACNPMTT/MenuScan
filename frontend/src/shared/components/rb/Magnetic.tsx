import type { PointerEvent, ReactNode } from 'react'
import { useRef } from 'react'
import { motion, useMotionValue, useSpring } from 'motion/react'
import { cn } from '@/shared/lib/cn'

/**
 * Pointer-driven magnetic wrapper (ReactBits-inspired, motion-only). Translates
 * the child toward the cursor within `radius` px, springing back to center on
 * leave. Honors reduced-motion via motion's built-in guard. No third deps
 * beyond motion.
 */
interface MagneticProps {
  children: ReactNode
  /** Max translation in px toward the pointer. */
  radius?: number
  className?: string
}

export function Magnetic({ children, radius = 18, className }: MagneticProps) {
  const ref = useRef<HTMLDivElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const sx = useSpring(x, { stiffness: 250, damping: 18, mass: 0.3 })
  const sy = useSpring(y, { stiffness: 250, damping: 18, mass: 0.3 })

  const handleMove = (e: PointerEvent<HTMLDivElement>) => {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    let dx = e.clientX - (rect.left + rect.width / 2)
    let dy = e.clientY - (rect.top + rect.height / 2)
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist > radius) {
      const scale = radius / dist
      dx *= scale
      dy *= scale
    }
    x.set(dx)
    y.set(dy)
  }

  const reset = () => {
    x.set(0)
    y.set(0)
  }

  return (
    <motion.div
      ref={ref}
      onPointerMove={handleMove}
      onPointerLeave={reset}
      style={{ x: sx, y: sy }}
      className={cn('inline-flex will-change-transform', className)}
    >
      {children}
    </motion.div>
  )
}
