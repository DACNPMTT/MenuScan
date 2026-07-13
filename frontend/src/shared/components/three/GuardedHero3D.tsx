import { Suspense, lazy, useEffect, useState } from 'react'
import { DotGrid } from '@/shared/components/rb/DotGrid'

const HeroCanvas = lazy(() => import('./HeroCanvas'))

/** Static CSS fallback shown when 3D is skipped or still loading. A solid
 * blue orb with a glow over a dot grid — no gradients. */
function CssFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="absolute inset-0 opacity-50">
        <DotGrid color="rgba(37, 99, 235, 0.12)" />
      </div>
      <div className="relative size-[55%] rounded-full bg-primary/10 shadow-[0_0_100px_40px_rgba(37,99,235,0.15)]" />
    </div>
  )
}

/**
 * Guards the 3D hero behind reduced-motion + save-data checks. The R3F canvas
 * is React.lazy'd into a separate chunk so three.js never blocks first paint.
 * If the user prefers reduced motion or has Save-Data enabled, a pure-CSS
 * fallback orb is rendered instead — no WebGL context is created.
 */
export function GuardedHero3D() {
  const [show, setShow] = useState(false)

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const nav = navigator as Navigator & { connection?: { saveData?: boolean } }
    const saveData = nav.connection?.saveData ?? false
    setShow(!reduceMotion && !saveData)
  }, [])

  return (
    <div className="relative aspect-square w-full max-w-[420px]">
      {show ? (
        <Suspense fallback={<CssFallback />}>
          <HeroCanvas />
        </Suspense>
      ) : (
        <CssFallback />
      )}
    </div>
  )
}
