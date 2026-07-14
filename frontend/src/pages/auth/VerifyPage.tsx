import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { Button } from '@/shared/components/ui/button'
import { Spinner } from '@/shared/components/Spinner'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { AuthShell } from '@/features/auth/components/AuthShell'
import { IconBadge } from '@/shared/components/IconBadge'
import { motion } from 'motion/react'

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
      <div className="flex min-h-dvh items-center justify-center bg-app-bg">
        <Spinner label={t('verify.verifyingAria')} />
      </div>
    )
  }

  if (status === 'error') {
    return (
      <AuthShell>
        <div className="flex flex-col items-center gap-5 text-center">
          <IconBadge icon={Check} tone="destructive" size="lg" />
          <div className="flex flex-col gap-2">
            <h1 className="text-[24px] font-bold leading-tight text-ink">
              {t('verify.errorTitle')}
            </h1>
            <p className="max-w-[300px] text-[15px] leading-relaxed text-ink-variant">
              {t('verify.errorBody')}
            </p>
          </div>
        </div>
        <Button type="button" size="lg" onClick={() => navigate('/auth/login')}>
          {t('auth.backToLogin')}
        </Button>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <div className="flex flex-col items-center gap-5 text-center">
        <motion.span
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 260, damping: 16 }}
          className="flex size-20 items-center justify-center rounded-full bg-success/15"
        >
          <Check className="size-10 text-success" aria-hidden />
        </motion.span>
        <div className="flex flex-col gap-2">
          <h1 className="text-[26px] font-extrabold leading-tight tracking-tight text-ink">
            {t('verify.successTitle')}
          </h1>
          <p className="max-w-[300px] text-[15px] leading-relaxed text-ink-variant">
            {t('verify.successBody')}
          </p>
        </div>
      </div>
      <Button
        type="button"
        size="lg"
        onClick={() => navigate('/auth/set-password', { replace: true })}
      >
        {t('verify.continue')}
      </Button>
    </AuthShell>
  )
}
