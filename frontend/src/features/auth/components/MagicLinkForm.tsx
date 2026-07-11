import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { useMagicLink } from '@/features/auth/hooks/useMagicLink'

interface AlternateLink {
  to: string
  prompt: string
  label: string
}

interface MagicLinkFormProps {
  heading: string
  ctaLabel: string
  alternate: AlternateLink
}

/**
 * Email-only magic-link form shared by Login and Register. On a successful
 * request it navigates to the check-email screen carrying the submitted email
 * (the backend returns an identical 202 whether or not the email exists, so no
 * user enumeration).
 */
export function MagicLinkForm({ heading, ctaLabel, alternate }: MagicLinkFormProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { state, errorMessage, request } = useMagicLink()
  const [email, setEmail] = useState('')
  const isLoading = state === 'loading'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await request(email)
    if (ok) {
      navigate('/auth/check-email', { state: { email } })
    }
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-5 py-[75px] font-sans">
      <div className="flex w-full max-w-[400px] flex-col">
        <header className="mb-[50px] flex flex-col gap-[5px]">
          <h1 className="text-center text-[30px] font-bold leading-[34px] tracking-[-0.75px] text-primary-dark">
            MenuScan
          </h1>
          <p className="text-center text-[20px] leading-[30px] text-ink">
            {heading}
          </p>
        </header>

        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-[30px] pb-4">
          <label className="flex flex-col gap-[5px]">
            <span className="text-[14px] leading-[14px] text-ink">{t('auth.emailLabel')}</span>
            <Input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder={t('auth.emailLabel')}
              aria-label={t('auth.emailLabel')}
              className="rounded-none border-0 border-b border-hairline bg-transparent px-0 py-1 text-[16px] text-ink shadow-none placeholder:text-placeholder focus-visible:border-primary-dark focus-visible:ring-0"
            />
          </label>

          {errorMessage && (
            <p role="alert" className="-mt-4 text-[14px] text-destructive">
              {errorMessage}
            </p>
          )}

          <Button
            type="submit"
            disabled={isLoading}
            className="h-12 rounded-full bg-primary text-[17px] font-bold text-white hover:bg-primary/90"
          >
            {isLoading ? t('checkEmail.sending') : ctaLabel}
          </Button>
        </form>

        <p className="pt-[50px] text-center text-[14px] leading-[21px] text-ink-variant">
          {alternate.prompt}{' '}
          <Link to={alternate.to} className="font-bold text-primary-dark">
            {alternate.label}
          </Link>
        </p>
      </div>
    </div>
  )
}
