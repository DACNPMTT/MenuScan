import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { useMagicLink } from '@/features/auth/hooks/useMagicLink'
import { AuthShell } from '@/features/auth/components/AuthShell'
import { SplitText } from '@/shared/components/rb/SplitText'

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
    <AuthShell>
      <SplitText
        as="h1"
        text={heading}
        className="text-center text-[24px] font-bold leading-tight tracking-tight text-ink"
      />

      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-6 pb-2">
        <label className="flex flex-col gap-2">
          <span className="text-[14px] font-semibold text-ink">{t('auth.emailLabel')}</span>
          <Input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder={t('auth.emailLabel')}
            aria-label={t('auth.emailLabel')}
          />
        </label>

        {errorMessage && (
          <p role="alert" className="-mt-2 text-[14px] text-destructive">
            {errorMessage}
          </p>
        )}

        <Button type="submit" size="lg" disabled={isLoading}>
          {isLoading ? t('checkEmail.sending') : ctaLabel}
        </Button>
      </form>

      <p className="pt-2 text-center text-[14px] leading-relaxed text-ink-variant">
        {alternate.prompt}{' '}
        <Link to={alternate.to} className="font-bold text-primary">
          {alternate.label}
        </Link>
      </p>
    </AuthShell>
  )
}
