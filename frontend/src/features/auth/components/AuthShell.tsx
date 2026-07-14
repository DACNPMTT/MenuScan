import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { MenuScanLogo } from '@/shared/components/mascot/NonLaMark'
import { SectionCard } from '@/shared/components/SectionCard'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { cn } from '@/shared/lib/cn'

interface AuthShellProps {
  children: ReactNode
  maxWidth?: string
}

/**
 * Shared chrome for the auth screens: a centered, elevated SectionCard on the
 * app background with a nón lá logo badge + MenuScan wordmark. Each page renders
 * its own heading and form as children. Light, elevated, no gradient.
 */
export function AuthShell({ children, maxWidth = 'max-w-[420px]' }: AuthShellProps) {
  return (
    <PageTransition>
      <div className="flex min-h-dvh flex-col items-center justify-center bg-app-bg px-5 py-[75px]">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className={cn('w-full', maxWidth)}
        >
          <SectionCard className="gap-7 px-8 py-10 shadow-pop">
            <header className="flex flex-col items-center gap-2">
              <a
                href="/"
                aria-label="MenuScan home"
                className="flex size-11 items-center justify-center rounded-2xl bg-[#f59e0b] shadow-2 shadow-[#f59e0b]/40"
              >
                <MenuScanLogo size={30} />
              </a>
              <span className="text-[24px] font-extrabold tracking-tight text-ink">
                MenuScan
              </span>
            </header>
            {children}
          </SectionCard>
        </motion.div>
      </div>
    </PageTransition>
  )
}
