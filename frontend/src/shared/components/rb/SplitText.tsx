import type { ElementType } from 'react'
import { motion } from 'motion/react'
import { cn } from '@/shared/lib/cn'

/**
 * Character-by-character masked rise (ReactBits-inspired, motion-only). Each
 * glyph rises out of a clip mask with a springy stagger. Use on titles that
 * should feel kinetic without the blur of <BlurText>.
 */
interface SplitTextProps {
  text: string
  className?: string
  delay?: number
  step?: number
  as?: 'h1' | 'h2' | 'h3' | 'p' | 'span'
  id?: string
}

export function SplitText({
  text,
  className,
  delay = 0,
  step = 0.03,
  as = 'h2',
  id,
}: SplitTextProps) {
  const chars = Array.from(text)
  const MotionTag = motion[as] as ElementType
  return (
    <MotionTag
      id={id}
      className={cn(className)}
      initial="hidden"
      animate="visible"
      aria-label={text}
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: step, delayChildren: delay } },
      }}
    >
      {chars.map((ch, i) =>
        ch === ' ' ? (
          <span key={`sp-${i}`} className="inline-block" aria-hidden>
            {'\u00A0'}
          </span>
        ) : (
          <span
            key={`ch-${i}`}
            className="inline-block overflow-hidden align-bottom"
            aria-hidden
          >
            <motion.span
              className="inline-block"
              variants={{
                hidden: { y: '110%' },
                visible: { y: 0, transition: { type: 'spring', stiffness: 280, damping: 24 } },
              }}
            >
              {ch}
            </motion.span>
          </span>
        ),
      )}
    </MotionTag>
  )
}
