/** TypeScript types mirroring the backend feed_recommend Pydantic schemas. */

export interface MealBrief {
  name?: string | null
  price?: number | null
}

export interface ScoreBreakdown {
  distance: number
  quality: number
  price_fit?: number | null
  taste_match?: number | null
  allergy_penalty: number
  total: number
}

export interface RestaurantCard {
  source_id: number
  name: string
  address: string
  lat: number
  lng: number
  avg_price?: number | null
  star?: number | null
  image_url?: string | null
  phone_num?: string | null
  type: string[]
  meals: MealBrief[]
  semantic_text?: string | null
  distance_km?: number | null
  score: number
  score_breakdown: ScoreBreakdown
  match_reasons: string[]
  caution_reasons: string[]
  saved: boolean
  seen_action?: string | null
}

export interface FeedResponse {
  items: RestaurantCard[]
  total_available: number
  location_source?: string | null
  radius_km: number
}

export type LocationSource = 'geolocation' | 'manual'

export interface UserLocation {
  lat: number
  lng: number
  address_text?: string | null
  source: LocationSource
  updated_at: string
}

export interface RestaurantSummary {
  source_id: number
  name: string
  address: string
  lat: number
  lng: number
  maps_url: string
}

/** Google Maps "search by point" deep link for a lat/lng pair. */
export function googleMapsUrl(lat: number, lng: number): string {
  return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`
}
