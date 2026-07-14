import type { PointerEvent, ReactNode } from 'react'
import { useRef } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'motion/react'
import { cn } from '@/shared/lib/cn'

/**
 * Pointer-driven 3D tilt (ReactBits-inspired, motion-only). Rotates toward the
 * cursor with a soft spring. Honors reduced-motion via motion's built-in guard
 * (the transforms still apply but transitions collapse to instant under the
 * global reduced-motion CSS rule). No third deps beyond motion.
 */
interface TiltCardProps {
  children: ReactNode
  className?: string
  /** Max rotation in degrees. */
  max?: number
}

export function TiltCard({ children, className, max = 8 }: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null)
  const px = useMotionValue(0.5)
  const py = useMotionValue(0.5)
  const sx = useSpring(px, { stiffness: 200, damping: 18, mass: 0.4 })
  const sy = useSpring(py, { stiffness: 200, damping: 18, mass: 0.4 })
  const rotateX = useTransform(sy, [0, 1], [max, -max])
  const rotateY = useTransform(sx, [0, 1], [-max, max])

  const handleMove = (e: PointerEvent<HTMLDivElement>) => {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    px.set((e.clientX - rect.left) / rect.width)
    py.set((e.clientY - rect.top) / rect.height)
  }

  const reset = () => {
    px.set(0.5)
    py.set(0.5)
  }

  return (
    <motion.div
      ref={ref}
      onPointerMove={handleMove}
      onPointerLeave={reset}
      style={{ rotateX, rotateY, transformPerspective: 900 }}
      className={cn('will-change-transform', className)}
    >
      {children}
    </motion.div>
  )
}
