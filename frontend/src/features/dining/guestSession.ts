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

export interface GuestSelectionDraftLine {
  quantity: number
  note: string
}

const KEY_PREFIX = 'dining_guest_'
const PREFS_KEY_PREFIX = 'dining_guest_prefs_'
const SELECTIONS_KEY_PREFIX = 'dining_guest_selections_'

function keyFor(token: string): string {
  return `${KEY_PREFIX}${token}`
}

function selectionsKeyFor(token: string, menuId: string): string {
  return `${SELECTIONS_KEY_PREFIX}${token}_${menuId}`
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

/** Keep an in-progress dish basket on this device. The server remains the
 * source of truth once the guest confirms their selection. */
export function saveGuestSelectionDraft(
  token: string,
  menuId: string,
  lines: Record<string, GuestSelectionDraftLine>,
): void {
  try {
    localStorage.setItem(selectionsKeyFor(token, menuId), JSON.stringify(lines))
  } catch {
    // Non-fatal: a guest can still select and confirm dishes normally.
  }
}

export function loadGuestSelectionDraft(
  token: string,
  menuId: string,
): Record<string, GuestSelectionDraftLine> | null {
  try {
    const raw = localStorage.getItem(selectionsKeyFor(token, menuId))
    if (!raw) return null

    const parsed = JSON.parse(raw) as Record<string, Partial<GuestSelectionDraftLine>>
    const lines = Object.entries(parsed).reduce<Record<string, GuestSelectionDraftLine>>(
      (validLines, [itemId, line]) => {
        if (
          typeof line.quantity === 'number' &&
          Number.isInteger(line.quantity) &&
          line.quantity >= 0 &&
          line.quantity <= 99 &&
          typeof line.note === 'string'
        ) {
          validLines[itemId] = { quantity: line.quantity, note: line.note }
        }
        return validLines
      },
      {},
    )
    return lines
  } catch {
    return null
  }
}
