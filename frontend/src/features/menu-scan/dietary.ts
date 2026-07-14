// Dietary taxonomy + matching. Mirrors the backend taxonomy AND the backend
// matching rules (src/modules/dining/service.py) so the badges shown on the
// scan/bill screens agree with the server's verdicts:
//   - an allergy to `seafood` also matches a dish tagged `shellfish` / `fish`
//   - `vegetarian` / `vegan` are judged from the dish's POSITIVE veg tags, not
//     from an incomplete meat denylist (which used to miss chicken, duck, etc.)

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

/** True when the dish carries the diner's allergen `code`. Mirrors the backend:
 * an allergy to the broad `seafood` category also matches the narrower
 * `shellfish` / `fish` tags a dish may carry. */
function dishHasAllergen(code: string, dishAllergens: Set<string>): boolean {
  if (dishAllergens.has(code)) return true
  if (code === 'seafood') {
    return dishAllergens.has('shellfish') || dishAllergens.has('fish')
  }
  return false
}

/** Assess a dish against a diner's profile. Allergen matching only flags on
 * positive dish signals; diet-preference matching mirrors the backend so a
 * dish that is NOT positively tagged vegetarian/vegan counts as violating a
 * vegetarian/vegan rule (safe direction, and consistent with the server). */
export function assessDish(item: DishDietary, profile: DietProfile): DishRisk {
  const itemAllergens = new Set(item.allergens ?? [])
  const itemTags = new Set(item.dietary_tags ?? [])

  const allergens = (profile.allergies ?? []).filter((code) =>
    dishHasAllergen(code, itemAllergens),
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
  switch (preference) {
    case 'no_pork':
      return tags.has('contains_pork')
    case 'no_beef':
      return tags.has('contains_beef')
    case 'no_alcohol':
      return tags.has('contains_alcohol')
    case 'no_seafood':
      return (
        tags.has('contains_seafood') ||
        allergens.has('seafood') ||
        allergens.has('shellfish') ||
        allergens.has('fish')
      )
    case 'vegetarian':
      // A dish counts as vegetarian only if positively tagged vegetarian or
      // vegan; anything else (incl. chicken/duck with no veg tag) violates.
      return !tags.has('vegetarian') && !tags.has('vegan')
    case 'vegan':
      return !tags.has('vegan')
    default:
      return false
  }
}
