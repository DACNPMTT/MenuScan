// Dietary taxonomy + matching. Mirrors the backend taxonomy: the LLM tags each
// dish with `allergens` / `dietary_tags`, the diner declares `allergies` /
// `dietary_preferences`, and we flag a dish when they intersect.

export const ALLERGENS = [
  'seafood',
  'shellfish',
  'fish',
  'peanut',
  'tree_nut',
  'egg',
  'dairy',
  'gluten',
  'soy',
  'sesame',
] as const

export const DIET_PREFERENCES = [
  'vegetarian',
  'vegan',
  'no_pork',
  'no_beef',
  'no_alcohol',
] as const

export type Allergen = (typeof ALLERGENS)[number]
export type DietPreference = (typeof DIET_PREFERENCES)[number]

export interface DietProfile {
  allergies?: string[] | null
  dietary_preferences?: string[] | null
}

export interface DishDietary {
  allergens?: string[] | null
  dietary_tags?: string[] | null
}

export interface DishRisk {
  /** The diner's allergens that this dish contains. */
  allergens: string[]
  /** The diner's diet preferences this dish violates. */
  dietFlags: string[]
}

/** Assess a dish against a diner's profile. Only flags on POSITIVE dish signals,
 * so an untagged dish is never wrongly flagged. */
export function assessDish(item: DishDietary, profile: DietProfile): DishRisk {
  const itemAllergens = new Set(item.allergens ?? [])
  const itemTags = new Set(item.dietary_tags ?? [])

  const allergens = (profile.allergies ?? []).filter((code) =>
    itemAllergens.has(code),
  )
  const dietFlags = (profile.dietary_preferences ?? []).filter((pref) =>
    violates(pref, itemTags, itemAllergens),
  )
  return { allergens, dietFlags }
}

export function hasRisk(risk: DishRisk): boolean {
  return risk.allergens.length > 0 || risk.dietFlags.length > 0
}

function violates(
  preference: string,
  tags: Set<string>,
  allergens: Set<string>,
): boolean {
  const hasMeatOrSeafood =
    tags.has('contains_pork') ||
    tags.has('contains_beef') ||
    tags.has('contains_seafood')
  switch (preference) {
    case 'no_pork':
      return tags.has('contains_pork')
    case 'no_beef':
      return tags.has('contains_beef')
    case 'no_alcohol':
      return tags.has('contains_alcohol')
    case 'vegetarian':
      return hasMeatOrSeafood
    case 'vegan':
      return hasMeatOrSeafood || allergens.has('dairy') || allergens.has('egg')
    default:
      return false
  }
}
