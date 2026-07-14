import type { ReactNode } from 'react'
import { motion } from 'motion/react'
import { cn } from '@/shared/lib/cn'

/**
 * Page-level enter/exit wrapper. A `motion.div` (not <main>, since most pages
 * already render their own landmark) that fades + slides on mount and unmount.
 * For exit to play it must sit inside an <AnimatePresence> keyed by route.
 */
interface PageTransitionProps {
  children: ReactNode
  className?: string
}

export function PageTransition({ children, className }: PageTransitionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
      className={cn('min-h-0', className)}
    >
      {children}
    </motion.div>
  )
}
