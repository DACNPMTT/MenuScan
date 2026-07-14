import type { ReactNode } from 'react'
import { motion } from 'motion/react'
import { AnimatedCounter } from '@/shared/components/rb/AnimatedCounter'
import { cn } from '@/shared/lib/cn'

interface StatTileProps {
  label: ReactNode
  /** Static display value (string, node). Used when the value isn't a count. */
  value?: ReactNode
  /** Numeric value → rendered as an animated counter that counts up on view. */
  count?: number
  prefix?: string
  suffix?: string
  /** Counter formatter (only applies when `count` is given). */
  format?: (value: number) => string
  className?: string
}

/** Metric tile: a label above a large value. Animates in and (when numeric)
 * counts up when scrolled into view. */
export function StatTile({
  label,
  value,
  count,
  prefix,
  suffix,
  format,
  className,
}: StatTileProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        'flex flex-col gap-1.5 rounded-2xl border border-border bg-surface p-5 shadow-1',
        className,
      )}
    >
      <span className="text-[13px] font-semibold uppercase tracking-wide text-ink-variant">
        {label}
      </span>
      <span className="text-[32px] font-bold leading-none tracking-tight text-ink md:text-[40px]">
        {typeof count === 'number' ? (
          <>
            {prefix}
            <AnimatedCounter to={count} format={format} />
            {suffix}
          </>
        ) : (
          value
        )}
      </span>
    </motion.div>
  )
}
