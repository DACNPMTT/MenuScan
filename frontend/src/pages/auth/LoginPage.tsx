import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'

interface LocationState {
  from?: {
    pathname: string
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
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    const state = location.state as LocationState | null
    const origin = state?.from?.pathname || '/app'
    navigate(origin, { replace: true })
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
    <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-5 py-[75px] font-sans">
      <div className="flex w-full max-w-[400px] flex-col">
        <header className="mb-[50px] flex flex-col gap-[5px]">
          <h1 className="text-center text-[30px] font-bold leading-[34px] tracking-normal text-primary-dark">
            MenuScan
          </h1>
          <p className="text-center text-[20px] leading-[30px] text-ink">
            {t('auth.welcomeBack')}
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
              placeholder="you@example.com"
              aria-label={t('auth.emailLabel')}
              className="rounded-none border-0 border-b border-hairline bg-transparent px-0 py-1 text-[16px] text-ink shadow-none placeholder:text-placeholder focus-visible:border-primary-dark focus-visible:ring-0"
            />
          </label>

          <label className="flex flex-col gap-[5px]">
            <span className="text-[14px] leading-[14px] text-ink">{t('auth.passwordLabel')}</span>
            <div className="relative">
              <Input
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={t('auth.passwordPlaceholder')}
                aria-label={t('auth.passwordLabel')}
                className="rounded-none border-0 border-b border-hairline bg-transparent px-0 py-1 pr-10 text-[16px] text-ink shadow-none placeholder:text-placeholder focus-visible:border-primary-dark focus-visible:ring-0"
              />
              <button
                type="button"
                className="absolute right-0 top-1/2 flex size-9 -translate-y-1/2 items-center justify-center text-ink-variant transition-colors hover:text-primary-dark"
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
            <p role="alert" className="-mt-4 text-[14px] text-destructive">
              {errorMessage}
            </p>
          )}

          <Button
            type="submit"
            disabled={isSubmitting}
            className="h-12 rounded-full bg-primary text-[17px] font-bold text-white hover:bg-primary/90"
          >
            {isSubmitting ? t('auth.loggingIn') : t('auth.logIn')}
          </Button>
        </form>

        <p className="pt-[50px] text-center text-[14px] leading-[21px] text-ink-variant">
          {t('auth.noAccount')}{' '}
          <Link to="/auth/register" className="font-bold text-primary-dark">
            {t('auth.signUp')}
          </Link>
        </p>
      </div>
    </div>
  )
}
