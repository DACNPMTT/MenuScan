import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { LANGUAGE_STORAGE_KEY } from '@/shared/i18n'
import { isSupportedLanguage } from '@/shared/i18n/languages'

/**
 * On login, adopt the user's preferred_language as the UI language — but only if
 * they haven't already picked a language in this browser (localStorage). An
 * explicit choice always wins over the stored preference.
 */
export function LanguageSync() {
  const { user } = useAuth()
  const { i18n } = useTranslation()

  useEffect(() => {
    if (!user) return
    const hasExplicitChoice = Boolean(localStorage.getItem(LANGUAGE_STORAGE_KEY))
    if (
      !hasExplicitChoice &&
      isSupportedLanguage(user.preferred_language) &&
      user.preferred_language !== i18n.resolvedLanguage
    ) {
      void i18n.changeLanguage(user.preferred_language)
    }
  }, [user, i18n])

  return null
}
