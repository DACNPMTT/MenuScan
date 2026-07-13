// Personalized dish ranking. Uses `assessDish` for the allergy/diet risk signal
// so risky dishes sink and the rest keep their menu order. Pure and side-effect
// free.
//
// Taste personalization (favorites / dislikes such as "spicy", "noodles") is
// intentionally NOT done here: a dish's `dietary_tags` only carry the shared
// allergen/diet vocabulary, not taste tags, so client-side taste matching can't
// fire. Authoritative taste ranking is server-side via the advisor verdicts —
// see `rankByVerdict` below and the backend `_matches_preference`.
import {
  assessDish,
  hasRisk,
  type DietProfile,
  type DishDietary,
  type DishRisk,
} from '@/features/menu-scan/dietary'

const RISK_PENALTY = 1000

export interface DishScore {
  /** Higher means a better fit. Risky dishes take a large negative penalty. */
  score: number
}

/** True when the profile carries any signal worth ranking by. With an empty
 * profile we leave the menu in its original order. */
export function isProfileActive(profile: DietProfile): boolean {
  return (
    (profile.allergies?.length ?? 0) > 0 ||
    (profile.dietary_preferences?.length ?? 0) > 0
  )
}

/** Score a single dish against the diner's profile. */
export function scoreDish(item: DishDietary, profile: DietProfile): DishScore {
  const risky = hasRisk(assessDish(item, profile))
  return { score: risky ? -RISK_PENALTY : 0 }
}

/** A single at-a-glance verdict for a dish. `neutral` means nothing worth
 * flagging (no verdict banner shown). */
export type Verdict = 'good' | 'caution' | 'avoid' | 'neutral'

/** Summarize a dish's risk into one verdict. Allergen risk always wins (safety
 * first), then diet mismatch. This is the rule-based fallback; the LLM advisor
 * can supply a richer verdict via `rankByVerdict`. */
export function dishVerdict(risk: DishRisk): Verdict {
  if (risk.allergens.length > 0) return 'avoid'
  if (risk.dietFlags.length > 0) return 'caution'
  return 'neutral'
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

/** The four verdict levels the backend scores a dish at, best first. */
export const VERDICT_LEVELS = ['RECOMMENDED', 'OK', 'CAUTION', 'AVOID'] as const
export type VerdictLevel = (typeof VERDICT_LEVELS)[number]

interface Recommended {
  recommendation?: { verdict: VerdictLevel; score?: number | null } | null
}

/** True once at least one dish carries a verdict — i.e. the diner has a food
 * profile AND the menu has been analysed. Until then there is nothing to sort by
 * and we must not pretend otherwise. */
export function hasVerdicts(items: Recommended[]): boolean {
  return items.some((item) => item.recommendation != null)
}

/** Tier index for a verdict; an unknown/missing verdict sinks to the bottom
 * instead of sorting above RECOMMENDED (which a raw indexOf of -1 would do). */
function verdictTier(verdict: VerdictLevel | undefined): number {
  if (verdict === undefined) return VERDICT_LEVELS.length
  const tier = VERDICT_LEVELS.indexOf(verdict)
  return tier === -1 ? VERDICT_LEVELS.length : tier
}

/** Order dishes by the advice: recommended first, avoid last, score breaking ties.
 *
 * Dishes with no verdict sink below the ones that have one — not because they are
 * bad, but because we know nothing about them, and a dish we have advice for is
 * more useful to put in front of someone deciding what to eat. Stable within a
 * tier, so the menu's own order survives. */
export function rankByVerdict<T extends Recommended>(items: T[]): T[] {
  return items
    .map((item, index) => ({
      item,
      index,
      tier: verdictTier(item.recommendation?.verdict),
      score: item.recommendation?.score ?? 0,
    }))
    .sort((a, b) => a.tier - b.tier || b.score - a.score || a.index - b.index)
    .map((entry) => entry.item)
}
