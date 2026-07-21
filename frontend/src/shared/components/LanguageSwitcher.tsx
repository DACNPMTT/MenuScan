import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { SUPPORTED_LANGUAGES, isSupportedLanguage } from '@/shared/i18n/languages'
import { cn } from '@/shared/lib/cn'

interface LanguageSwitcherProps {
  className?: string
}

/**
 * UI-language segmented pill. With only two languages (vi/en), showing both
 * options side-by-side is clearer than a toggle (no surprise about what the
 * "other" choice is) and matches the existing pill nav style. Active language
 * gets the primary fill; the other is a muted ghost.
 *
 * Choice is a client-side preference (persisted by the i18next detector); for
 * logged-in users we also mirror vi/en into `preferred_language` so the
 * scan-target default stays in sync.
 */
export function LanguageSwitcher({ className }: LanguageSwitcherProps) {
  const { i18n, t } = useTranslation()
  const { user, updateProfile } = useAuth()

  const current = isSupportedLanguage(i18n.resolvedLanguage) ? i18n.resolvedLanguage : 'vi'

  const handleChange = (code: 'vi' | 'en') => {
    if (code === current) return
    void i18n.changeLanguage(code)
    if (user) {
      void updateProfile({ preferred_language: code }).catch(() => {
        // Best-effort: the UI language still changes even if the sync fails.
      })
    }
  }

  return (
    <div
      role="group"
      aria-label={t('language.label')}
      className={cn(
        'inline-flex items-center gap-0.5 rounded-full bg-panel/80 p-0.5',
        className,
      )}
    >
      {SUPPORTED_LANGUAGES.map((lang) => {
        const isActive = lang.code === current
        return (
          <button
            key={lang.code}
            type="button"
            onClick={() => handleChange(lang.code)}
            aria-pressed={isActive}
            title={lang.label}
            className={cn(
              'flex h-7 items-center gap-1 rounded-full px-2.5 text-[11px] font-extrabold uppercase tracking-wide transition-colors',
              isActive
                ? 'bg-primary text-white shadow-2 shadow-primary/30'
                : 'text-ink-variant hover:text-primary',
            )}
          >
            <span className="text-[13px] leading-none">{lang.flag}</span>
            <span>{lang.code}</span>
          </button>
        )
      })}
    </div>
  )
}
