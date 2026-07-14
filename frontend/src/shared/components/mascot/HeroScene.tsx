import { motion, useReducedMotion } from 'motion/react'
import { DotGrid } from '@/shared/components/rb/DotGrid'

const SPARKLES = [
  { top: '10%', left: '16%', delay: 0, color: '#ffc800', size: 8 },
  { top: '20%', right: '18%', delay: 0.6, color: '#58cc02', size: 6 },
  { top: '52%', left: '6%', delay: 1.2, color: '#f4a6c0', size: 6 },
  { top: '70%', right: '10%', delay: 1.8, color: '#ffc800', size: 7 },
  { top: '36%', right: '4%', delay: 0.3, color: '#a5ed6e', size: 4 },
]

/* Large detailed nón lá centerpiece */
function CenterpieceHat() {
  return (
    <svg viewBox="0 0 200 168" className="h-auto w-full" role="img" aria-label="Vietnamese conical hat (nón lá)">
      <path d="M100 12 L18 116 Q100 138 182 116 Z" fill="#e8c170" />
      <path d="M100 16 L34 112 Q72 124 94 122 Z" fill="#f3d98f" opacity="0.6" />
      <path d="M40 92 Q100 106 160 92" stroke="#c08a2e" strokeWidth="1.4" fill="none" opacity="0.4" />
      <path d="M48 74 Q100 86 152 74" stroke="#c08a2e" strokeWidth="1.3" fill="none" opacity="0.38" />
      <path d="M58 56 Q100 66 142 56" stroke="#c08a2e" strokeWidth="1.2" fill="none" opacity="0.34" />
      <path d="M68 40 Q100 48 132 40" stroke="#c08a2e" strokeWidth="1.1" fill="none" opacity="0.3" />
      <path d="M100 12 L100 128" stroke="#c08a2e" strokeWidth="1" opacity="0.22" />
      <circle cx="100" cy="13" r="2.2" fill="#c08a2e" />
      {/* Red ribbon band */}
      <path d="M30 112 Q100 130 170 112" stroke="#c1432e" strokeWidth="6.5" fill="none" strokeLinecap="round" />
      {/* Chin strap */}
      <path d="M46 120 Q100 154 154 120" stroke="#8b5e3c" strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.85" />
    </svg>
  )
}

/* Floating phở bowl with steam */
function PhoBowl() {
  return (
    <svg viewBox="0 0 80 72" className="h-auto w-full" role="img" aria-label="Phở bowl">
      <path d="M30 6 Q26 13 30 20 Q34 27 30 33" stroke="#ffffff" strokeWidth="2.4" fill="none" strokeLinecap="round" opacity="0.55" />
      <path d="M46 4 Q42 11 46 18 Q50 25 46 31" stroke="#ffffff" strokeWidth="2.4" fill="none" strokeLinecap="round" opacity="0.5" />
      <path d="M8 38 Q12 62 40 64 Q68 62 72 38 Z" fill="#c1432e" />
      <ellipse cx="40" cy="38" rx="31" ry="8.5" fill="#e8a44c" />
      <ellipse cx="40" cy="38" rx="31" ry="8.5" fill="none" stroke="#a8331f" strokeWidth="1.6" />
      <path d="M24 37 Q28 33 32 37 Q36 41 40 37" stroke="#f3e5c0" strokeWidth="1.6" fill="none" />
      <path d="M42 40 Q46 36 50 40" stroke="#f3e5c0" strokeWidth="1.6" fill="none" />
      <circle cx="34" cy="36" r="1.7" fill="#58a700" />
      <circle cx="49" cy="38" r="1.7" fill="#58a700" />
    </svg>
  )
}

/* Lotus flower (layered petals) */
function Lotus() {
  return (
    <svg viewBox="0 0 70 70" className="h-auto w-full" role="img" aria-label="Lotus flower">
      <g transform="translate(35 40)">
        {[36, 108, 180, 252, 324].map((rot) => (
          <ellipse key={rot} cx="0" cy="-15" rx="7" ry="16" fill="#f7b8cd" transform={`rotate(${rot})`} opacity="0.8" />
        ))}
        {[0, 72, 144, 216, 288].map((rot) => (
          <ellipse key={rot} cx="0" cy="-12" rx="8" ry="18" fill="#f4a6c0" transform={`rotate(${rot})`} />
        ))}
        <circle r="6.5" fill="#fff3d6" />
        <circle r="3.2" fill="#f4c969" />
      </g>
    </svg>
  )
}

/* Chopsticks (tapered pair) */
function Chopsticks() {
  return (
    <svg viewBox="0 0 84 30" className="h-auto w-full" role="img" aria-label="Chopsticks">
      <path d="M8 11 L74 8 L74 12 L8 15 Z" fill="#a06a3f" />
      <path d="M12 20 L78 17 L78 21 L12 24 Z" fill="#8b5e3c" />
    </svg>
  )
}

/**
 * Animated Vietnamese-culture hero scene: a floating nón lá centerpiece with a
 * phở bowl, lotus and chopsticks drifting around it over a subtle dot grid and
 * warm glow. Pure SVG + CSS transforms — no WebGL, no image assets. Honors
 * reduced-motion. All element widths are % of the aspect-square wrapper so the
 * cluster scales cleanly on mobile.
 */
export function HeroScene() {
  const reduceMotion = useReducedMotion()
  return (
    <div className="relative aspect-square w-full">
      {/* Dot grid */}
      <div className="absolute inset-0 opacity-40">
        <DotGrid color="rgba(88,204,2,0.10)" />
      </div>

      {/* Warm gold glow */}
      <div className="absolute left-1/2 top-1/2 h-[60%] w-[60%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#ffc800]/10 blur-3xl" />

      {/* Twinkling sparkles */}
      {SPARKLES.map((s, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full"
          style={{ top: s.top, left: s.left, right: s.right, width: s.size, height: s.size, backgroundColor: s.color }}
          animate={reduceMotion ? undefined : { opacity: [0, 1, 0], scale: [0, 1.3, 0] }}
          transition={{ duration: 2.2, delay: s.delay, repeat: Infinity, ease: 'easeInOut' }}
        />
      ))}

      {/* Centerpiece nón lá */}
      <motion.div
        animate={reduceMotion ? undefined : { y: [0, -12, 0], rotate: [-2, 2, -2] }}
        transition={{ y: { duration: 4, repeat: Infinity, ease: 'easeInOut' }, rotate: { duration: 6, repeat: Infinity, ease: 'easeInOut' } }}
        whileHover={{ scale: 1.04 }}
        className="absolute left-1/2 top-[46%] w-[68%] -translate-x-1/2 -translate-y-1/2 drop-shadow-[0_20px_40px_rgba(192,138,46,0.22)]"
      >
        <CenterpieceHat />
      </motion.div>

      {/* Floating phở bowl */}
      <motion.div
        animate={reduceMotion ? undefined : { y: [0, 10, 0], rotate: [3, -3, 3] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute right-[2%] top-[6%] w-[26%]"
      >
        <PhoBowl />
      </motion.div>

      {/* Floating lotus */}
      <motion.div
        animate={reduceMotion ? undefined : { y: [0, -8, 0], rotate: [-4, 4, -4] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute bottom-[6%] left-[2%] w-[23%]"
      >
        <Lotus />
      </motion.div>

      {/* Floating chopsticks */}
      <motion.div
        animate={reduceMotion ? undefined : { y: [0, 9, 0], rotate: [8, 14, 8] }}
        transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute bottom-[14%] right-[8%] w-[27%]"
      >
        <Chopsticks />
      </motion.div>
    </div>
  )
}
