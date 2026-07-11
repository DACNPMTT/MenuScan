// Personalized dish ranking. Reuses `assessDish` for the risk signal and layers
// a positive favorites / negative dislikes signal on top, so dishes that fit the
// diner float to the top and risky dishes sink. Pure and side-effect free.
//
// Note: `favorites`/`dislikes` on the profile are optional and empty until the
// profile UI ships. Until then ranking still works off the risk signal alone
// (risky dishes sink), and the "recommended" flag simply stays off — no
// fabricated recommendations.
import {
  assessDish,
  hasRisk,
  type DietProfile,
  type DishDietary,
} from '@/features/menu-scan/dietary'

const RISK_PENALTY = 1000
const FAVORITE_BONUS = 10
const DISLIKE_PENALTY = 10

export interface DishScore {
  /** Higher means a better fit. Risky dishes take a large negative penalty. */
  score: number
  /** True when the dish positively matches a taste preference and has no risk. */
  recommended: boolean
}

/** True when the profile carries any signal worth ranking by. With an empty
 * profile we leave the menu in its original order. */
export function isProfileActive(profile: DietProfile): boolean {
  return (
    (profile.allergies?.length ?? 0) > 0 ||
    (profile.dietary_preferences?.length ?? 0) > 0 ||
    (profile.favorites?.length ?? 0) > 0 ||
    (profile.dislikes?.length ?? 0) > 0
  )
}

/** Score a single dish against the diner's profile. */
export function scoreDish(item: DishDietary, profile: DietProfile): DishScore {
  const risky = hasRisk(assessDish(item, profile))
  const tags = new Set(item.dietary_tags ?? [])
  const favorites = (profile.favorites ?? []).filter((code) => tags.has(code)).length
  const dislikes = (profile.dislikes ?? []).filter((code) => tags.has(code)).length

  const score =
    (risky ? -RISK_PENALTY : 0) +
    favorites * FAVORITE_BONUS -
    dislikes * DISLIKE_PENALTY

  return { score, recommended: !risky && favorites > 0 }
}

/** Return a new array of dishes ordered best-fit first. Stable: dishes with the
 * same score keep their original order, so the menu layout is preserved within
 * a tier. */
export function rankDishes<T extends DishDietary>(
  items: T[],
  profile: DietProfile,
): T[] {
  return items
    .map((item, index) => ({ item, index, score: scoreDish(item, profile).score }))
    .sort((a, b) => b.score - a.score || a.index - b.index)
    .map((entry) => entry.item)
}
