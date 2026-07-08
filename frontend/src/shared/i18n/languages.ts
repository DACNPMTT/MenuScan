// Supported UI (interface) languages — only the ones with a full translation
// catalog. This is intentionally just vi/en; the *scan target* language is
// separate and open-ended (any language the model can translate to).
export const SUPPORTED_LANGUAGES = [
  { code: 'vi', label: 'Tiếng Việt', flag: '🇻🇳' },
  { code: 'en', label: 'English', flag: '🇬🇧' },
] as const

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]['code']

export const SUPPORTED_LANGUAGE_CODES = SUPPORTED_LANGUAGES.map((l) => l.code)

export const DEFAULT_LANGUAGE: LanguageCode = 'vi'

export function isSupportedLanguage(code: string | null | undefined): code is LanguageCode {
  return !!code && SUPPORTED_LANGUAGE_CODES.includes(code as LanguageCode)
}
