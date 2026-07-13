import { Link } from 'react-router-dom'
import { Home, UtensilsCrossed } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { Button } from '@/shared/components/ui/button'
import { useAuth } from '@/app/providers/AuthProvider'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { SectionCard } from '@/shared/components/SectionCard'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { SplitText } from '@/shared/components/rb/SplitText'

export function NotFoundPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('notFound.title')} | MenuScan`)
  const { user } = useAuth()

  return (
    <PageTransition>
      <main className="flex min-h-dvh flex-col items-center justify-center bg-app-bg px-6 py-16 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <SectionCard className="w-full max-w-[480px] gap-6 px-8 py-12 shadow-pop">
            <div className="flex flex-col items-center gap-5">
              <div className="relative">
                <span className="flex size-20 items-center justify-center rounded-3xl bg-panel text-primary shadow-2">
                  <UtensilsCrossed className="size-10" aria-hidden />
                </span>
                <motion.span
                  initial={{ opacity: 0, rotate: -20, scale: 0.6 }}
                  animate={{ opacity: 1, rotate: 8, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 260, damping: 14, delay: 0.15 }}
                  className="absolute -right-3 -top-3 flex size-12 items-center justify-center rounded-2xl bg-accent text-[13px] font-extrabold text-accent-foreground shadow-2"
                >
                  404
                </motion.span>
              </div>
              <div className="flex flex-col gap-2">
                <SplitText
                  as="h1"
                  id="not-found-title"
                  text={t('notFound.title')}
                  className="text-[30px] font-extrabold leading-tight tracking-tight text-ink"
                />
                <p className="mx-auto max-w-[420px] text-[15px] leading-relaxed text-ink-variant">
                  {t('notFound.body')}
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-3">
                <Button asChild size="lg">
                  <Link to={user ? '/app' : '/'}>
                    {user ? t('notFound.toDashboard') : t('notFound.toHome')}
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg">
                  <Link to="/">
                    <Home className="size-4" aria-hidden />
                    {t('notFound.home')}
                  </Link>
                </Button>
              </div>
            </div>
          </SectionCard>
        </motion.div>
      </main>
    </PageTransition>
  )
}
