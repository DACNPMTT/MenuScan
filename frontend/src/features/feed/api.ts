/** Typed API wrappers for the `/feed` endpoints.
 *
 * All functions go through the shared `apiRequest` wrapper which attaches the
 * bearer token and unwraps the `{ success, data }` envelope. Paths include
 * the `/api/v1` prefix per the convention used across the app. */

import { apiRequest } from '@/shared/lib/api'
import type {
  FeedResponse,
  LocationSource,
  RestaurantCard,
  UserLocation,
} from './types'

export interface SetLocationPayload {
  lat: number
  lng: number
  address_text?: string | null
  source: LocationSource
}

/** Top-N scored restaurant cards, excluding already-saved and already-seen. */
export function fetchFeed(radiusKm = 5, limit = 20): Promise<FeedResponse> {
  const params = new URLSearchParams({
    radius_km: String(radiusKm),
    limit: String(limit),
  })
  return apiRequest<FeedResponse>(`/api/v1/feed?${params.toString()}`)
}

/** Mark a restaurant as seen (skip or view). Idempotent. */
export function markSeen(
  sourceId: number,
  action: 'skip' | 'view',
): Promise<{ ok: true }> {
  return apiRequest<{ ok: true }>(`/api/v1/feed/${sourceId}/seen`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  })
}

/** Bookmark a restaurant. Also marks it seen so it leaves the feed. */
export function saveRestaurant(sourceId: number): Promise<RestaurantCard> {
  return apiRequest<RestaurantCard>(`/api/v1/feed/saves/${sourceId}`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

/** Remove a restaurant from saved. Idempotent — 204 either way. */
export async function unsaveRestaurant(sourceId: number): Promise<void> {
  await apiRequest<null>(`/api/v1/feed/saves/${sourceId}`, { method: 'DELETE' })
}

/** All saved restaurants for the current user, newest save first. */
export function fetchSaved(): Promise<RestaurantCard[]> {
  return apiRequest<RestaurantCard[]>('/api/v1/feed/saves')
}

/** Full restaurant detail (with per-user score and saved flag). */
export function fetchRestaurantDetail(sourceId: number): Promise<RestaurantCard> {
  return apiRequest<RestaurantCard>(`/api/v1/feed/restaurants/${sourceId}`)
}

/** Return the user's saved location, or null if not yet set. */
export function fetchLocation(): Promise<UserLocation | null> {
  return apiRequest<UserLocation | null>('/api/v1/feed/me/location')
}

/** Insert or replace the user's location (geolocation or manual). */
export function setLocation(payload: SetLocationPayload): Promise<UserLocation> {
  return apiRequest<UserLocation>('/api/v1/feed/me/location', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

/** Group-bridge: create a dining session tagged with a restaurant. */
export function createDiningSessionFromRestaurant(
  sourceId: number,
): Promise<{
  session: {
    id: string
    restaurant_source_id?: number | null
    restaurant?: {
      source_id: number
      name: string
      address: string
      maps_url: string
    } | null
  }
  invite_token: string
}> {
  return apiRequest('/api/v1/dining/sessions', {
    method: 'POST',
    body: JSON.stringify({ mode: 'GROUP', restaurant_source_id: sourceId }),
  })
}
