import type { ReactNode } from 'react'
import { cn } from '@/shared/lib/cn'

interface SectionCardProps {
  title?: ReactNode
  description?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
  /** When true, the body has no horizontal padding (for full-bleed lists). */
  flush?: boolean
}

/** Elevated panel wrapper: rounded-3xl white surface with a layered shadow and
 * an optional header row (title + description + trailing action). The default
 * container for grouped content across the app. */
export function SectionCard({
  title,
  description,
  action,
  children,
  className,
  bodyClassName,
  flush = false,
}: SectionCardProps) {
  return (
    <section
      className={cn(
        'overflow-hidden rounded-3xl border border-border bg-surface shadow-2',
        className,
      )}
    >
      {(title || action) && (
        <header className="flex items-start justify-between gap-3 px-6 pt-5">
          <div className="flex flex-col gap-1">
            {title && (
              <h2 className="text-[17px] font-bold leading-tight text-ink">{title}</h2>
            )}
            {description && (
              <p className="text-[13px] text-ink-variant">{description}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </header>
      )}
      <div className={cn(flush ? '' : 'px-6 py-5', bodyClassName)}>{children}</div>
    </section>
  )
}
