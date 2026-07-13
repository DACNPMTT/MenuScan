import type { ElementType } from 'react'
import { motion } from 'motion/react'

/**
 * Word-by-word blur-in (ReactBits-inspired, motion-only). Each word de-blurs
 * and rises with a stagger. Used on the Landing hero and auth titles.
 */
interface BlurTextProps {
  text: string
  className?: string
  delay?: number
  step?: number
  as?: 'h1' | 'h2' | 'h3' | 'p' | 'span'
}

const EASE = [0.22, 1, 0.36, 1] as const

export function BlurText({
  text,
  className,
  delay = 0,
  step = 0.05,
  as = 'h1',
}: BlurTextProps) {
  const words = text.split(' ')
  const MotionTag = motion[as] as ElementType
  return (
    <MotionTag
      className={className}
      initial="hidden"
      animate="visible"
      aria-label={text}
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: step, delayChildren: delay } },
      }}
    >
      {words.map((word, i) => (
        <span key={`${word}-${i}`} className="inline-block whitespace-nowrap" aria-hidden>
          <motion.span
            className="inline-block"
            variants={{
              hidden: { opacity: 0, y: 12, filter: 'blur(10px)' },
              visible: { opacity: 1, y: 0, filter: 'blur(0px)', transition: { duration: 0.5, ease: EASE } },
            }}
          >
            {word}
          </motion.span>
          {i < words.length - 1 ? '\u00A0' : ''}
        </span>
      ))}
    </MotionTag>
  )
}
