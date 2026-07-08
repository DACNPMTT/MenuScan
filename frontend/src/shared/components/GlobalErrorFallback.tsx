import { AlertTriangle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

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
    <main className="flex min-h-dvh flex-col items-center justify-center gap-5 bg-app-bg px-4 py-10 text-center">
      <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="size-7 text-destructive" aria-hidden />
      </span>
      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-bold leading-[30px] text-primary-dark">
          {t('errorFallback.title')}
        </h1>
        <p className="max-w-[420px] text-[14px] text-ink-variant">
          {t('errorFallback.body')}
        </p>
      </div>
      <div className="flex flex-col items-center gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="flex min-h-10 items-center justify-center rounded-[8px] bg-primary-dark px-6 text-[14px] font-bold text-white transition-opacity hover:opacity-90"
        >
          {t('errorFallback.reload')}
        </button>
        <Link
          to="/"
          className="flex min-h-10 items-center justify-center rounded-[8px] border border-hairline bg-canvas px-6 text-[14px] font-bold text-ink transition-colors hover:bg-surface-muted"
        >
          {t('errorFallback.toHome')}
        </Link>
      </div>
      {import.meta.env.DEV && (
        <p className="mt-2 max-w-[600px] break-words rounded-[6px] bg-surface-muted px-3 py-2 text-left font-mono text-[12px] text-destructive">
          {error.message}
        </p>
      )}
    </main>
  )
}
