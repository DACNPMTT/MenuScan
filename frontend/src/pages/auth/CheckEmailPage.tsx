import { useLocation } from 'react-router-dom'
import { Mail } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/ui/button'
import { useMagicLink } from '@/features/auth/hooks/useMagicLink'

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
    <div className="flex min-h-dvh items-center justify-center bg-ink px-5 py-[95px] font-sans">
      <div className="flex w-full max-w-[400px] flex-col">
        <div className="flex flex-col items-center gap-[30px] border border-hairline bg-canvas p-[50px]">
          <h1 className="text-center text-[30px] font-bold leading-[34px] tracking-[-0.75px] text-primary-dark">
            MenuScan
          </h1>

          <div className="flex size-20 items-center justify-center rounded-full border border-hairline bg-app-bg">
            <Mail className="size-8 text-primary-dark" aria-hidden />
          </div>

          <div className="flex flex-col items-center gap-2">
            <h2 className="text-center text-[20px] leading-[30px] text-ink">
              {t('auth.checkInbox')}
            </h2>
            <p className="max-w-[260px] text-center text-[16px] leading-[22px] text-ink-variant">
              {email
                ? t('checkEmail.bodyWithEmail', { email })
                : t('checkEmail.bodyNoEmail')}
            </p>
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
            className="h-12 w-full rounded-full border border-ink bg-canvas text-[17px] font-bold text-ink hover:bg-ink/5"
          >
            {isLoading ? t('checkEmail.sending') : t('auth.resendEmail')}
          </Button>
        </div>
      </div>
    </div>
  )
}
