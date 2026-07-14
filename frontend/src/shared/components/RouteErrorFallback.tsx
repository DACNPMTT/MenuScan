import { AlertTriangle, RotateCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { Button } from '@/shared/components/ui/button'
import { SectionCard } from '@/shared/components/SectionCard'
import { IconBadge } from '@/shared/components/IconBadge'

interface RouteErrorFallbackProps {
  error: Error
  onReset: () => void
}

/** Route-level fallback: rendered inside the authenticated shell (header and
 * footer stay visible). The page content failed, so the user keeps navigation
 * and a reload to recover the broken route. */
export function RouteErrorFallback({ error, onReset }: RouteErrorFallbackProps) {
  const { t } = useTranslation()
  void onReset
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="mx-auto flex w-full max-w-[640px] flex-col px-4 py-[60px]"
    >
      <SectionCard className="gap-6 text-center shadow-pop">
        <div className="flex flex-col items-center gap-5">
          <IconBadge icon={AlertTriangle} tone="destructive" size="lg" />
          <div className="flex flex-col gap-2">
            <h1 className="text-[22px] font-extrabold leading-tight text-ink">
              {t('routeError.title')}
            </h1>
            <p className="max-w-[420px] text-[14px] leading-relaxed text-ink-variant">
              {t('routeError.body')}
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button onClick={() => window.location.reload()}>
              <RotateCw className="size-4" aria-hidden />
              {t('errorFallback.reload')}
            </Button>
            <Button asChild variant="outline">
              <Link to="/app">{t('common.backToDashboard')}</Link>
            </Button>
          </div>
          {import.meta.env.DEV && (
            <p className="mt-2 max-w-[600px] break-words rounded-xl bg-panel px-3 py-2 text-left font-mono text-[12px] text-destructive">
              {error.message}
            </p>
          )}
        </div>
      </SectionCard>
    </motion.div>
  )
}
