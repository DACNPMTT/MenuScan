import { Globe } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { SUPPORTED_LANGUAGES, isSupportedLanguage } from '@/shared/i18n/languages'
import { cn } from '@/shared/lib/cn'

interface LanguageSwitcherProps {
  className?: string
}

/**
 * UI-language selector. The choice is a client-side preference (persisted to
 * localStorage by the i18next detector) so all seven languages are available.
 * For logged-in users we also mirror vi/en into preferred_language — the only
 * values the backend accepts — so the scan-target default stays in sync.
 */
export function LanguageSwitcher({ className }: LanguageSwitcherProps) {
  const { i18n, t } = useTranslation()
  const { user, updateProfile } = useAuth()

  const current = isSupportedLanguage(i18n.resolvedLanguage)
    ? i18n.resolvedLanguage
    : 'vi'

  const handleChange = (code: string) => {
    void i18n.changeLanguage(code)
    if (user && (code === 'vi' || code === 'en')) {
      void updateProfile({ preferred_language: code }).catch(() => {
        // Best-effort: the UI language still changes even if the sync fails.
      })
    }
  }

  return (
    <label
      className={cn(
        'inline-flex items-center gap-1.5 rounded-[8px] border border-hairline bg-canvas px-2 py-1.5 text-ink-variant',
        className,
      )}
      title={t('language.select')}
    >
      <Globe className="size-4 shrink-0" aria-hidden />
      <span className="sr-only">{t('language.select')}</span>
      <select
        value={current}
        onChange={(event) => handleChange(event.target.value)}
        aria-label={t('language.select')}
        className="cursor-pointer bg-transparent text-[13px] font-medium text-ink outline-none"
      >
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.flag} {lang.label}
          </option>
        ))}
      </select>
    </label>
  )
}
