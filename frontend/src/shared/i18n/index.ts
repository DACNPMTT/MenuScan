import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { DEFAULT_LANGUAGE, SUPPORTED_LANGUAGE_CODES } from './languages'
import en from './locales/en.json'
import vi from './locales/vi.json'
import zh from './locales/zh.json'
import ja from './locales/ja.json'
import ko from './locales/ko.json'
import fr from './locales/fr.json'
import th from './locales/th.json'

export const LANGUAGE_STORAGE_KEY = 'menuscan.lang'

// Untranslated keys fall back to English, so a partially translated locale still
// renders a complete UI instead of showing raw keys.
export const resources = {
  en: { translation: en },
  vi: { translation: vi },
  zh: { translation: zh },
  ja: { translation: ja },
  ko: { translation: ko },
  fr: { translation: fr },
  th: { translation: th },
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
