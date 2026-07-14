import { useEffect, useState, useRef, type FormEvent, type KeyboardEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { AuthShell } from '@/features/auth/components/AuthShell'
import { SplitText } from '@/shared/components/rb/SplitText'

interface LocationState {
  from?: {
    pathname: string
    state?: unknown
  }
}

export function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { user, login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const passwordRef = useRef<HTMLInputElement>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    const state = location.state as LocationState | null
    const origin = state?.from?.pathname || '/app'
    // Replay the state the original navigation carried, or the destination loses
    // whatever the click meant — the menu screen's "run the enrichment pass" flag,
    // for one.
    navigate(origin, { replace: true, state: state?.from?.state ?? undefined })
  }, [location.state, navigate, user])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)

    if (!email || !password) {
      setErrorMessage(t('auth.fillEmailPassword'))
      return
    }

    setIsSubmitting(true)
    try {
      await login(email, password)
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : t('auth.invalidCredentials'),
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthShell>
      <SplitText
        as="h1"
        text={t('auth.welcomeBack')}
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
            onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                passwordRef.current?.focus()
              }
            }}
          />
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-[14px] font-semibold text-ink">{t('auth.passwordLabel')}</span>
          <div className="relative">
            <Input
              ref={passwordRef}
              type={showPassword ? 'text' : 'password'}
              required
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t('auth.passwordPlaceholder')}
              aria-label={t('auth.passwordLabel')}
              className="pr-11"
            />
            <button
              type="button"
              className="absolute right-1 top-1/2 flex size-9 -translate-y-1/2 items-center justify-center rounded-lg text-ink-variant transition-colors hover:bg-panel hover:text-primary"
              onClick={() => setShowPassword((current) => !current)}
              aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
            >
              {showPassword ? (
                <EyeOff className="size-5" aria-hidden />
              ) : (
                <Eye className="size-5" aria-hidden />
              )}
            </button>
          </div>
        </label>

        {errorMessage && (
          <p role="alert" className="-mt-2 text-[14px] text-destructive">
            {errorMessage}
          </p>
        )}

        <Button type="submit" size="lg" disabled={isSubmitting}>
          {isSubmitting ? t('auth.loggingIn') : t('auth.logIn')}
        </Button>
      </form>

      <p className="pt-2 text-center text-[14px] leading-relaxed text-ink-variant">
        {t('auth.noAccount')}{' '}
        <Link to="/auth/register" className="font-bold text-primary">
          {t('auth.signUp')}
        </Link>
      </p>
    </AuthShell>
  )
}
