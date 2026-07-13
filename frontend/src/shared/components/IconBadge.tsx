import type { ComponentType, SVGProps } from 'react'
import { motion } from 'motion/react'
import { cn } from '@/shared/lib/cn'

type IconType = ComponentType<SVGProps<SVGSVGElement> & { size?: number | string }>

type Tone = 'primary' | 'accent' | 'destructive' | 'success' | 'muted'
type Size = 'sm' | 'md' | 'lg'

const SIZES: Record<Size, string> = {
  sm: 'size-10 rounded-xl',
  md: 'size-12 rounded-2xl',
  lg: 'size-16 rounded-2xl',
}

const ICON_SIZES: Record<Size, string> = {
  sm: 'size-5',
  md: 'size-6',
  lg: 'size-8',
}

const TONES: Record<Tone, string> = {
  primary: 'bg-primary/10 text-primary',
  accent: 'bg-accent/30 text-accent-foreground',
  destructive: 'bg-destructive/10 text-destructive',
  success: 'bg-success/10 text-success',
  muted: 'bg-panel text-ink-variant',
}

interface IconBadgeProps {
  icon: IconType
  tone?: Tone
  size?: Size
  className?: string
  /** Render a solid filled badge instead of a tinted one. */
  solid?: boolean
}

/** Icon-in-a-rounded-tile badge. The single visual unit used across the app
 * for action cards, empty states and section headers. Solid = filled primary. */
export function IconBadge({
  icon: Icon,
  tone = 'primary',
  size = 'md',
  className,
  solid = false,
}: IconBadgeProps) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        'inline-flex shrink-0 items-center justify-center',
        SIZES[size],
        solid ? 'bg-primary text-white shadow-2 shadow-primary/30' : TONES[tone],
        className,
      )}
    >
      <Icon className={ICON_SIZES[size]} aria-hidden />
    </motion.span>
  )
}
