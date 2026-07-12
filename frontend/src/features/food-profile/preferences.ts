import type {
  FoodProfilePreference,
  FoodProfilePreferenceInput,
} from '@/app/providers/AuthProvider'
import { ALLERGENS, DIET_PREFERENCES } from '@/features/menu-scan/dietary'

export const FOOD_PROFILE_LIKES = [
  'spicy',
  'mild_spicy',
  'savory',
  'sour',
  'fresh',
  'grilled',
  'soup',
  'noodles',
  'rice',
  'vegetables',
] as const

export const FOOD_PROFILE_AVOIDS = [
  'too_spicy',
  'too_sweet',
  'too_oily',
  'fish_sauce',
  'strong_smell',
  'raw_food',
  'organ_meat',
  'bitter',
  'heavy_cream',
  'deep_fried',
] as const

export type FoodProfilePreferenceSection =
  | 'allergies'
  | 'dietary_preferences'
  | 'likes'
  | 'avoids'

export interface FoodProfilePreferenceDraft {
  allergies: string[]
  dietary_preferences: string[]
  likes: string[]
  avoids: string[]
}

export const EMPTY_FOOD_PROFILE_DRAFT: FoodProfilePreferenceDraft = {
  allergies: [],
  dietary_preferences: [],
  likes: [],
  avoids: [],
}

export function createEmptyFoodProfileDraft(): FoodProfilePreferenceDraft {
  return {
    allergies: [],
    dietary_preferences: [],
    likes: [],
    avoids: [],
  }
}

export function foodProfileDraftToPreferences(
  value: FoodProfilePreferenceDraft,
): FoodProfilePreferenceInput[] {
  return [
    ...value.allergies.map((code) => ({
      code,
      category: 'allergen',
      preference_type: 'ALLERGY' as const,
      importance: 5,
    })),
    ...value.dietary_preferences.map((code) => ({
      code,
      category: 'dietary',
      preference_type: 'DIETARY_RULE' as const,
      importance: 4,
    })),
    ...value.likes.map((code) => ({
      code,
      category: 'preference',
      preference_type: 'LIKE' as const,
      importance: 3,
    })),
    ...value.avoids.map((code) => ({
      code,
      category: 'preference',
      preference_type: 'AVOID' as const,
      importance: 4,
    })),
  ]
}

export function profilePreferencesToDraft(
  preferences: FoodProfilePreference[] = [],
): FoodProfilePreferenceDraft {
  return preferences.reduce<FoodProfilePreferenceDraft>(
    (value, item) => {
      if (item.preference_type === 'ALLERGY') {
        value.allergies.push(item.code)
      }
      if (item.preference_type === 'DIETARY_RULE') {
        value.dietary_preferences.push(item.code)
      }
      if (item.preference_type === 'LIKE') {
        value.likes.push(item.code)
      }
      if (item.preference_type === 'AVOID' || item.preference_type === 'DISLIKE') {
        value.avoids.push(item.code)
      }
      return value
    },
    createEmptyFoodProfileDraft(),
  )
}

export function preferenceOptionsForSection(
  section: FoodProfilePreferenceSection,
): readonly string[] {
  switch (section) {
    case 'allergies':
      return ALLERGENS
    case 'dietary_preferences':
      return DIET_PREFERENCES
    case 'likes':
      return FOOD_PROFILE_LIKES
    case 'avoids':
      return FOOD_PROFILE_AVOIDS
  }
}

export function valuesForSection(
  value: FoodProfilePreferenceDraft,
  section: FoodProfilePreferenceSection,
): string[] {
  return value[section]
}

export function updateSectionValues(
  value: FoodProfilePreferenceDraft,
  section: FoodProfilePreferenceSection,
  nextValues: string[],
): FoodProfilePreferenceDraft {
  return { ...value, [section]: nextValues }
}

export function normalizeCustomPreferenceCode(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

export function labelPreferenceCode(code: string): string {
  return code
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}
