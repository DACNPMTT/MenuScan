import { useEffect, useState } from 'react'
import { LocateFixed, MapPin, Wallet } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { SectionCard } from '@/shared/components/SectionCard'
import { Button } from '@/shared/components/ui/button'
import { useToast } from '@/app/providers/ToastProvider'
import { describeError } from '@/shared/lib/errors'
import { apiRequest } from '@/shared/lib/api'
import { fetchLocation, setLocation } from '../api'
import type { UserLocation } from '../types'
import { CITY_CENTERS } from '../city-centers'

const PRICE_BAND_OPTIONS: Array<{ value: number | null; key: string }> = [
  { value: 50_000, key: '50k' },
  { value: 100_000, key: '100k' },
  { value: 150_000, key: '150k' },
  { value: 200_000, key: '200k' },
  { value: 300_000, key: '300k' },
  { value: 500_000, key: '500k' },
  { value: null, key: 'any' },
]

interface DiscoverySettingsProps {
  /** Current price band from the user object; null when unset. */
  initialPriceBandCents: number | null
}

/**
 * "Discovery preferences" section on the Profile page.
 *
 * Lets the diner pick a comfortable price band (used by the price-fit scoring
 * term) and set or change their feed location. Self-contained so the host
 * Profile page only renders `<DiscoverySettings />` once.
 */
export function DiscoverySettings({
  initialPriceBandCents,
}: DiscoverySettingsProps) {
  const { t } = useTranslation()
  const toast = useToast()
  const [priceBand, setPriceBand] = useState<number | null>(initialPriceBandCents)
  const [pendingPrice, setPendingPrice] = useState(false)
  const [location, setLocalLocation] = useState<UserLocation | null>(null)
  const [cityId, setCityId] = useState('danang')
  const [pendingLocation, setPendingLocation] = useState(false)

  useEffect(() => {
    void fetchLocation().then(setLocalLocation).catch(() => undefined)
  }, [])

  const savePriceBand = async (value: number | null) => {
    setPriceBand(value)
    setPendingPrice(true)
    try {
      await apiRequest('/api/v1/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({ price_band_cents: value }),
      })
      toast.show({ variant: 'success', title: t('common.saveChanges') })
    } catch (err) {
      toast.show({
        variant: 'error',
        title: describeError(err, t, 'common.saveChanges'),
      })
    } finally {
      setPendingPrice(false)
    }
  }

  const useGeolocation = () => {
    if (!('geolocation' in navigator)) {
      toast.show({ variant: 'error', title: t('feed.locationPrompt.locationDenied') })
      return
    }
    setPendingLocation(true)
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const loc = await setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            source: 'geolocation',
            address_text: null,
          })
          setLocalLocation(loc)
          toast.show({ variant: 'success', title: t('common.saveChanges') })
        } catch (err) {
          toast.show({
            variant: 'error',
            title: describeError(err, t, 'common.saveChanges'),
          })
        } finally {
          setPendingLocation(false)
        }
      },
      () => {
        setPendingLocation(false)
        toast.show({ variant: 'error', title: t('feed.locationPrompt.locationDenied') })
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60_000 },
    )
  }

  const useCity = async () => {
    const city = CITY_CENTERS.find((c) => c.id === cityId)
    if (!city) return
    setPendingLocation(true)
    try {
      const loc = await setLocation({
        lat: city.lat,
        lng: city.lng,
        source: 'manual',
        address_text: city.name,
      })
      setLocalLocation(loc)
      toast.show({ variant: 'success', title: t('common.saveChanges') })
    } catch (err) {
      toast.show({
        variant: 'error',
        title: describeError(err, t, 'common.saveChanges'),
      })
    } finally {
      setPendingLocation(false)
    }
  }

  return (
    <SectionCard
      title={
        <span className="flex items-center gap-2">
          <Wallet className="size-4 text-primary" aria-hidden />
          {t('feed.heroTitle')}
        </span>
      }
      description={t('feed.heroSubtitle')}
    >
      <div className="flex flex-col gap-6">
        {/* Price band */}
        <div className="flex flex-col gap-2">
          <label className="text-[13px] font-bold text-ink-variant">
            {t('feed.card.noPrice')}
          </label>
          <div className="flex flex-wrap gap-2">
            {PRICE_BAND_OPTIONS.map((opt) => {
              const active = priceBand === opt.value
              return (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => savePriceBand(opt.value)}
                  disabled={pendingPrice}
                  className={
                    'rounded-full px-3 py-1 text-[13px] font-bold transition-all ' +
                    (active
                      ? 'bg-primary text-white'
                      : 'border border-border bg-surface text-ink-variant hover:bg-panel')
                  }
                >
                  {opt.value ? `${opt.key}₫` : t('feed.expandRadius')}
                </button>
              )
            })}
          </div>
        </div>

        {/* Location */}
        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-1.5 text-[13px] font-bold text-ink-variant">
            <MapPin className="size-3.5" aria-hidden />
            {t('feed.changeLocation')}
          </label>
          {location && (
            <p className="text-[13px] text-ink-variant">
              {location.address_text ??
                `${location.lat.toFixed(3)}, ${location.lng.toFixed(3)}`}{' '}
              · {location.source === 'geolocation' ? 'GPS' : t('feed.locationPrompt.pickCity')}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={useGeolocation}
              disabled={pendingLocation}
            >
              <LocateFixed className="size-4" aria-hidden />
              {t('feed.locationPrompt.useLocation')}
            </Button>
            <select
              value={cityId}
              onChange={(e) => setCityId(e.target.value)}
              disabled={pendingLocation}
              className="rounded-full border border-border bg-surface px-3 py-1 text-[13px] text-ink"
            >
              {CITY_CENTERS.map((city) => (
                <option key={city.id} value={city.id}>
                  {city.name}
                </option>
              ))}
            </select>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={useCity}
              disabled={pendingLocation}
            >
              {t('common.save')}
            </Button>
          </div>
        </div>
      </div>
    </SectionCard>
  )
}
