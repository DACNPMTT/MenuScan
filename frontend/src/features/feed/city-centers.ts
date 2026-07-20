/** Static lat/lng of major Vietnamese city centers.
 *
 * Used as the manual-entry fallback when geolocation is rejected or
 * unavailable — a diner at a desktop planning tomorrow's trip picks a city
 * from this list rather than typing a full address (no geocode service in v1).
 */

export interface CityCenter {
  id: string
  /** Display name in Vietnamese (UI may localize further). */
  name: string
  lat: number
  lng: number
}

export const CITY_CENTERS: readonly CityCenter[] = [
  { id: 'hanoi', name: 'Hà Nội', lat: 21.0285, lng: 105.8542 },
  { id: 'hcmc', name: 'TP. Hồ Chí Minh', lat: 10.7626, lng: 106.6602 },
  { id: 'danang', name: 'Đà Nẵng', lat: 16.0544, lng: 108.2022 },
  { id: 'hue', name: 'Huế', lat: 16.4637, lng: 107.5909 },
  { id: 'hoian', name: 'Hội An', lat: 15.8801, lng: 108.338 },
  { id: 'nhatrang', name: 'Nha Trang', lat: 12.2388, lng: 109.1967 },
] as const

export function findCityCenter(id: string): CityCenter | undefined {
  return CITY_CENTERS.find((city) => city.id === id)
}
