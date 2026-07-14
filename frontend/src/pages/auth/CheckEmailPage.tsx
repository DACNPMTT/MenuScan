import { useLocation } from 'react-router-dom'
import { Mail } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/ui/button'
import { useMagicLink } from '@/features/auth/hooks/useMagicLink'
import { AuthShell } from '@/features/auth/components/AuthShell'
import { IconBadge } from '@/shared/components/IconBadge'

interface CheckEmailLocationState {
  email?: string
}

export function CheckEmailPage() {
  const { t } = useTranslation()
  const location = useLocation()
  const email = (location.state as CheckEmailLocationState | null)?.email ?? ''
  const { state, errorMessage, request } = useMagicLink()
  const isLoading = state === 'loading'

  async function handleResend() {
    if (email) {
      void request(email)
    }
  }

  return (
    <AuthShell>
      <div className="flex w-full flex-col items-center gap-6 text-center">
        <div className="flex flex-col items-center gap-5">
          <IconBadge icon={Mail} tone="primary" size="lg" />
          <div className="flex flex-col items-center gap-2">
            <h1 className="text-[22px] font-bold leading-tight text-ink">
              {t('auth.checkInbox')}
            </h1>
            {email ? (
              <p className="max-w-[300px] text-[15px] leading-relaxed text-ink-variant">
                {t('checkEmail.bodyWithEmailPrefix')}
                <span
                  className="mx-auto mt-1 block max-w-full truncate font-bold text-ink"
                  title={email}
                >
                  {email}
                </span>
                <span className="mt-1 block">{t('checkEmail.bodyWithEmailSuffix')}</span>
              </p>
            ) : (
              <p className="max-w-[300px] text-[15px] leading-relaxed text-ink-variant">
                {t('checkEmail.bodyNoEmail')}
              </p>
            )}
          </div>
        </div>

        {errorMessage && (
          <p role="alert" className="text-center text-[14px] text-destructive">
            {errorMessage}
          </p>
        )}

        <Button
          type="button"
          onClick={handleResend}
          disabled={isLoading || !email}
          variant="outline"
          size="lg"
          className="self-center"
        >
          {isLoading ? t('checkEmail.sending') : t('auth.resendEmail')}
        </Button>
      </div>
    </AuthShell>
  )
}
