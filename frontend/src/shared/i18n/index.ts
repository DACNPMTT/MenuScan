import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { DEFAULT_LANGUAGE, SUPPORTED_LANGUAGE_CODES } from './languages'
import en from './locales/en.json'
import vi from './locales/vi.json'

export const LANGUAGE_STORAGE_KEY = 'menuscan.lang'

// UI ships in vi/en only; anything else falls back to English (fallbackLng).
export const resources = {
  en: { translation: en },
  vi: { translation: vi },
} as const

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: [...SUPPORTED_LANGUAGE_CODES],
    // Treat regional variants (en-US, zh-CN) as their base language.
    nonExplicitSupportedLngs: true,
    load: 'languageOnly',
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      lookupLocalStorage: LANGUAGE_STORAGE_KEY,
      caches: ['localStorage'],
    },
  })

if (!i18n.language) {
  void i18n.changeLanguage(DEFAULT_LANGUAGE)
}

export default i18n
