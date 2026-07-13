import { Loader2 } from 'lucide-react'
import { cn } from '@/shared/lib/cn'

type SpinnerProps = {
  label?: string
  className?: string
}

/** Accessible loading indicator. Visually-hidden label keeps it usable for
 * screen readers; size/colour can be tuned through className. */
export function Spinner({ label = 'Loading', className }: SpinnerProps) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)} role="status">
      <Loader2 className="size-7 animate-spin text-primary-dark" aria-hidden="true" />
      <span className="visually-hidden">{label}</span>
    </span>
  )
}
