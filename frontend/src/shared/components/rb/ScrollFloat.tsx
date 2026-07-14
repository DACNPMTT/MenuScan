import type { ReactNode } from 'react'
import { motion, useScroll, useTransform } from 'motion/react'
import { cn } from '@/shared/lib/cn'

/**
 * Gentle vertical drift driven by page scroll (ReactBits-inspired,
 * motion-only). Content translates up as the user scrolls down. Used to add
 * parallax depth to hero visuals.
 */
interface ScrollFloatProps {
  children: ReactNode
  className?: string
  /** Max upward drift in px at 600px of scroll. */
  amount?: number
}

export function ScrollFloat({ children, className, amount = 36 }: ScrollFloatProps) {
  const { scrollY } = useScroll()
  const y = useTransform(scrollY, [0, 600], [0, -amount])
  return (
    <motion.div style={{ y }} className={cn('will-change-transform', className)}>
      {children}
    </motion.div>
  )
}
