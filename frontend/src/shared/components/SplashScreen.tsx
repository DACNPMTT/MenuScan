import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { MenuScanLogo } from '@/shared/components/mascot/NonLaMark'

export function SplashScreen({ onComplete }: { onComplete: () => void }) {
  const [show, setShow] = useState(true)

  useEffect(() => {
    // Hide the splash screen after 2 seconds
    const timer = setTimeout(() => {
      setShow(false)
      // Call onComplete shortly after the exit animation starts
      setTimeout(onComplete, 500)
    }, 2000)
    return () => clearTimeout(timer)
  }, [onComplete])

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="splash-screen"
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-white dark:bg-[#0a0a0a]"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.05 }}
          transition={{ duration: 0.5, ease: 'easeInOut' }}
        >
          <div className="flex flex-col items-center justify-center gap-4">
            <motion.div
              initial={{ scale: 0.5, opacity: 0, rotate: -20 }}
              animate={{ scale: 1, opacity: 1, rotate: 0 }}
              transition={{
                duration: 0.8,
                ease: [0.34, 1.56, 0.64, 1], // Custom spring-like easing
              }}
            >
              <MenuScanLogo className="size-24 text-primary" />
            </motion.div>
            
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5, ease: 'easeOut' }}
              className="flex flex-col items-center gap-1"
            >
              <h1 className="text-3xl font-extrabold tracking-tight text-ink">
                MenuScan
              </h1>
              <p className="text-[14px] font-medium text-ink-variant">
                Made Easy
              </p>
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
