import { useState } from 'react'
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

type VerifyStatus = 'ready' | 'verifying' | 'success' | 'error'

export function VerifyPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('verify.docTitle')} | MenuScan`)
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { verifyMagicLink } = useAuth()
  const token = params.get('token')
  // Magic-link tokens are one-time-use. We do NOT verify on load: email security
  // scanners prefetch the URL and would burn the token before the human clicks.
  // Consuming it only on an explicit button press keeps the token alive for the
  // real user. A missing token is a broken link — show the error straight away.
  const [status, setStatus] = useState<VerifyStatus>(token ? 'ready' : 'error')

  async function handleConfirm() {
    if (!token || status === 'verifying') return
    setStatus('verifying')
    try {
      await verifyMagicLink(token)
      setStatus('success')
      navigate('/auth/set-password', { replace: true })
    } catch {
      setStatus('error')
    }
  }

  if (status === 'verifying') {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-app-bg">
        <Spinner label={t('verify.verifyingAria')} />
      </div>
    )
  }

  if (status === 'ready') {
    return (
      <AuthShell>
        <div className="flex w-full flex-col items-center gap-6 text-center">
          <div className="flex flex-col items-center gap-5">
            <IconBadge icon={Check} tone="primary" size="lg" />
            <div className="flex flex-col items-center gap-2">
              <h1 className="text-[24px] font-bold leading-tight text-ink">
                {t('verify.confirmTitle')}
              </h1>
              <p className="max-w-[300px] text-[15px] leading-relaxed text-ink-variant">
                {t('verify.confirmBody')}
              </p>
            </div>
          </div>
          <Button type="button" size="lg" onClick={handleConfirm}>
            {t('verify.confirmButton')}
          </Button>
        </div>
      </AuthShell>
    )
  }

  if (status === 'error') {
    return (
      <AuthShell>
        <div className="flex w-full flex-col items-center gap-6 text-center">
          <div className="flex flex-col items-center gap-5">
            <IconBadge icon={Check} tone="destructive" size="lg" />
            <div className="flex flex-col items-center gap-2">
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
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <div className="flex w-full flex-col items-center gap-6 text-center">
        <div className="flex flex-col items-center gap-5">
          <motion.span
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 260, damping: 16 }}
            className="flex size-20 items-center justify-center rounded-full bg-success/15"
          >
            <Check className="size-10 text-success" aria-hidden />
          </motion.span>
          <div className="flex flex-col items-center gap-2">
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
      </div>
    </AuthShell>
  )
}
