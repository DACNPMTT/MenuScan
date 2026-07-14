import { cn } from '@/shared/lib/cn'
import { motion } from 'motion/react'
import { MenuScanLogo } from '@/shared/components/mascot/NonLaMark'

type SpinnerProps = {
  label?: string
  className?: string
}

/** Animated rolling durian mascot loader. Replaces the generic spinner. */
export function Spinner({ label, className }: SpinnerProps) {
  return (
    <span className={cn('inline-flex flex-col items-center justify-center gap-4', className)} role="status">
      <div className="relative w-[120px] h-[60px] flex items-center justify-center">
        <motion.div
          animate={{ x: [-35, 35, -35], rotate: [-80, 80, -80] }}
          transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
          className="flex items-center justify-center drop-shadow-md"
        >
          <MenuScanLogo size={48} />
        </motion.div>
      </div>
      {label && label !== 'Loading' && (
        <span className="text-[14px] font-bold text-[#58cc02] opacity-80 animate-pulse">
          {label}
        </span>
      )}
      <span className="visually-hidden">{label || 'Loading'}</span>
    </span>
  )
}
