import { AlertTriangle, RotateCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { Button } from '@/shared/components/ui/button'
import { SectionCard } from '@/shared/components/SectionCard'
import { IconBadge } from '@/shared/components/IconBadge'

interface GlobalErrorFallbackProps {
  error: Error
  onReset: () => void
}

/** App-level fallback: a render error crashed the router, so we show a full
 * page with a reload (the reliable way back) and a safe link to the landing
 * page. The stack is never shown in production. */
export function GlobalErrorFallback({ error, onReset }: GlobalErrorFallbackProps) {
  const { t } = useTranslation()
  void onReset // app-level recovery is reload, not reset (re-render re-throws)
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center bg-app-bg px-4 py-10 text-center">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      >
        <SectionCard className="w-full max-w-[460px] gap-6 px-8 py-10 shadow-pop">
          <div className="flex flex-col items-center gap-5">
            <IconBadge icon={AlertTriangle} tone="destructive" size="lg" />
            <div className="flex flex-col gap-2">
              <h1 className="text-[24px] font-extrabold leading-tight text-ink">
                {t('errorFallback.title')}
              </h1>
              <p className="max-w-[380px] text-[14px] leading-relaxed text-ink-variant">
                {t('errorFallback.body')}
              </p>
            </div>
            <div className="flex flex-col items-center gap-3 sm:flex-row">
              <Button size="lg" onClick={() => window.location.reload()}>
                <RotateCw className="size-4" aria-hidden />
                {t('errorFallback.reload')}
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/">{t('errorFallback.toHome')}</Link>
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
    </main>
  )
}
