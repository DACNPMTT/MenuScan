import { useId } from 'react'
import { cn } from '@/shared/lib/cn'

/**
 * Decorative dot grid background (ReactBits-inspired). Implemented as a tiled
 * SVG <pattern> of solid circles — NO gradient/mask, so it complies with the
 * no-gradient rule. Layer behind hero sections at low opacity.
 */
interface DotGridProps {
  className?: string
  /** Dot diameter in px. */
  size?: number
  /** Tile size (spacing) in px. */
  gap?: number
  /** Dot fill color. */
  color?: string
}

export function DotGrid({
  className,
  size = 1.6,
  gap = 30,
  color = 'rgba(37, 99, 235, 0.16)',
}: DotGridProps) {
  const rawId = useId()
  const patternId = `dotgrid-${rawId.replace(/[:]/g, '')}`
  return (
    <svg
      aria-hidden
      className={cn('h-full w-full', className)}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <pattern
          id={patternId}
          width={gap}
          height={gap}
          patternUnits="userSpaceOnUse"
          patternContentUnits="userSpaceOnUse"
        >
          <circle cx={size} cy={size} r={size} fill={color} />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${patternId})`} />
    </svg>
  )
}
