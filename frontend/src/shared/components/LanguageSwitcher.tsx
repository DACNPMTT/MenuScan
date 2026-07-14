import { ChevronDown, Globe } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { SUPPORTED_LANGUAGES, isSupportedLanguage } from '@/shared/i18n/languages'
import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu'

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
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          className={cn('gap-1 text-ink-variant', className)}
          title={t('language.select')}
          aria-label={t('language.select')}
        >
          <Globe className="size-4" aria-hidden />
          <ChevronDown className="size-3" aria-hidden />
          <span className="sr-only">{t('language.select')}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {SUPPORTED_LANGUAGES.map((lang) => (
          <DropdownMenuItem
            key={lang.code}
            onSelect={() => handleChange(lang.code)}
            className={cn(lang.code === current && 'font-bold text-primary')}
          >
            {lang.flag} {lang.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
