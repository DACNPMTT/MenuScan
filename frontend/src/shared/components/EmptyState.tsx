import type { ComponentType, ReactNode, SVGProps } from 'react'
import { motion } from 'motion/react'
import { cn } from '@/shared/lib/cn'

type IconType = ComponentType<SVGProps<SVGSVGElement> & { size?: number | string }>
type Tone = 'primary' | 'accent' | 'destructive' | 'success' | 'muted'

const TONES: Record<Tone, string> = {
  primary: 'bg-primary/10 text-primary',
  accent: 'bg-accent/30 text-accent-foreground',
  destructive: 'bg-destructive/10 text-destructive',
  success: 'bg-success/10 text-success',
  muted: 'bg-panel text-ink-variant',
}

interface EmptyStateProps {
  icon?: IconType
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  tone?: Tone
  className?: string
}

/** Centered empty / idle / not-found block: icon badge + title + body + CTA.
 * Replaces the per-page ad-hoc empty markup with one consistent layout. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  tone = 'primary',
  className,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        'mx-auto flex max-w-md flex-col items-center gap-4 px-6 py-12 text-center',
        className,
      )}
    >
      {Icon && (
        <span
          className={cn(
            'flex size-16 items-center justify-center rounded-3xl',
            TONES[tone],
          )}
        >
          <Icon className="size-8" aria-hidden />
        </span>
      )}
      <div className="flex flex-col gap-1.5">
        <p className="text-[18px] font-bold leading-tight text-ink">{title}</p>
        {description && (
          <p className="text-[14px] leading-relaxed text-ink-variant">{description}</p>
        )}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </motion.div>
  )
}
