import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { Button } from '@/shared/components/ui/button'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

type VerifyStatus = 'verifying' | 'success' | 'error'

const verificationRequests = new Map<string, Promise<void>>()

export function VerifyPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('verify.docTitle')} | MenuScan`)
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { verifyMagicLink } = useAuth()
  const token = params.get('token')
  const [status, setStatus] = useState<VerifyStatus>('verifying')

  useEffect(() => {
    let active = true
    async function run() {
      if (!token) {
        if (active) setStatus('error')
        return
      }

      const existingRequest = verificationRequests.get(token)
      const request =
        existingRequest ??
        verifyMagicLink(token).then(() => {
          // Verify tokens are one-time-use. Keep this request shared long enough
          // for React StrictMode remounts to reuse the successful result.
          window.setTimeout(() => {
            verificationRequests.delete(token)
          }, 5000)
        })

      if (!existingRequest) {
        verificationRequests.set(token, request)
      }

      try {
        await request
        if (active) {
          setStatus('success')
          navigate('/auth/set-password', { replace: true })
        }
      } catch {
        if (active) setStatus('error')
      }
    }
    void run()
    return () => {
      active = false
    }
  }, [navigate, token, verifyMagicLink])

  if (status === 'verifying') {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-app-bg font-sans">
        <div
          className="size-8 animate-spin rounded-full border-2 border-hairline border-t-primary"
          role="status"
          aria-label={t('verify.verifyingAria')}
        />
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-app-bg px-5 font-sans">
        <div className="flex w-full max-w-[400px] flex-col items-center gap-6 border border-hairline bg-canvas p-[50px] text-center">
          <h1 className="text-[30px] font-bold tracking-normal text-primary-dark">
            MenuScan
          </h1>
          <h2 className="text-[24px] text-ink">{t('verify.errorTitle')}</h2>
          <p className="text-[16px] leading-[22px] text-ink-variant">
            {t('verify.errorBody')}
                    </p>
          <Button
            type="button"
            className="h-12 rounded-full bg-primary font-bold text-white hover:bg-primary/90"
            onClick={() => navigate('/auth/login')}
          >
            {t('auth.backToLogin')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-app-bg px-5 py-[95px] font-sans">
      <div className="pointer-events-none absolute -bottom-48 -right-48 size-96 rounded-full bg-primary-dark opacity-5 blur-2xl" />
      <div className="relative flex w-full max-w-[400px] flex-col">
        <div className="flex flex-col items-center gap-[30px] border border-hairline bg-canvas py-[50px]">
          <h1 className="text-center text-[30px] font-bold leading-[34px] tracking-normal text-primary-dark">
            MenuScan
          </h1>

          <div className="relative flex size-24 items-center justify-center rounded-full bg-surface-muted">
            <div className="absolute inset-0 rounded-full bg-success-glow opacity-20" />
            <Check className="relative size-10 text-primary" aria-hidden />
          </div>

          <div className="flex flex-col items-center gap-[7px]">
            <h2 className="text-center text-[30px] font-bold leading-[34px] text-ink">
              {t('verify.successTitle')}
            </h2>
            <p className="text-center text-[16px] leading-[22px] text-ink-variant">
              {t('verify.successBody')}
            </p>
          </div>

          <Button
            type="button"
            className="h-12 rounded-full bg-primary px-[25px] text-[17px] font-bold text-white hover:bg-primary/90"
            onClick={() => navigate('/auth/set-password', { replace: true })}
          >
            {t('verify.continue')}
          </Button>
        </div>
      </div>
    </div>
  )
}
