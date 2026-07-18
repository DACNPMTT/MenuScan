/**
 * A guest's foothold in a dining session, kept in localStorage so the dish
 * picker survives a reload and a guest is not asked to re-join every time.
 *
 * Keyed by the invite token — that is the one thing a guest always has in the
 * URL, and it is what every public dining endpoint is gated on. There is no
 * auth here: a guest is an anonymous participant identified only by the id the
 * join endpoint handed back.
 */

import type { FoodProfilePreferenceDraft } from '@/features/food-profile/preferences'

export interface GuestSession {
  token: string
  sessionId: string
  participantId: string
  displayName: string
}

const KEY_PREFIX = 'dining_guest_'
const PREFS_KEY_PREFIX = 'dining_guest_prefs_'

function keyFor(token: string): string {
  return `${KEY_PREFIX}${token}`
}

/** The guest's declared preferences, kept alongside their identity so the "edit
 * preferences" screen can prefill instead of wiping what they already chose. */
export function saveGuestPrefsDraft(
  token: string,
  draft: FoodProfilePreferenceDraft,
): void {
  try {
    localStorage.setItem(`${PREFS_KEY_PREFIX}${token}`, JSON.stringify(draft))
  } catch {
    // Non-fatal: the edit screen just starts from empty.
  }
}

export function loadGuestPrefsDraft(
  token: string,
): FoodProfilePreferenceDraft | null {
  try {
    const raw = localStorage.getItem(`${PREFS_KEY_PREFIX}${token}`)
    return raw ? (JSON.parse(raw) as FoodProfilePreferenceDraft) : null
  } catch {
    return null
  }
}

export function saveGuestSession(value: GuestSession): void {
  try {
    localStorage.setItem(keyFor(value.token), JSON.stringify(value))
  } catch {
    // Private-mode / storage-full: the picker will simply ask them to re-join.
  }
}

export function loadGuestSession(token: string): GuestSession | null {
  try {
    const raw = localStorage.getItem(keyFor(token))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<GuestSession>
    if (
      typeof parsed.participantId === 'string' &&
      typeof parsed.sessionId === 'string' &&
      typeof parsed.token === 'string'
    ) {
      return {
        token: parsed.token,
        sessionId: parsed.sessionId,
        participantId: parsed.participantId,
        displayName: parsed.displayName ?? '',
      }
    }
    return null
  } catch {
    return null
  }
}
