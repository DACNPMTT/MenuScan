import { useState } from 'react'
import { LocateFixed, MapPin } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence } from 'motion/react'
import { useToast } from '@/app/providers/ToastProvider'
import { setLocation } from '../api'
import { CITY_CENTERS } from '../city-centers'
import type { UserLocation } from '../types'

interface LocationPromptProps {
  open: boolean
  /** Called with the persisted location, regardless of how it was obtained. */
  onSettled: (location: UserLocation) => void
  onClose: () => void
}

/**
 * Modal shown on first feed open (or when the user taps "change location").
 *
 * Two paths:
 * - "Use my location": `navigator.geolocation` (only after the user taps the
 *   button — never on page load).
 * - "Pick a city": a `<select>` of static city centers, so diners at a desktop
 *   planning a trip can still get a feed without a geocode service.
 */
export function LocationPrompt({ open, onSettled, onClose }: LocationPromptProps) {
  const { t } = useTranslation()
  const toast = useToast()
  const [pending, setPending] = useState(false)
  const [cityId, setCityId] = useState<string>('danang')

  const persist = async (lat: number, lng: number, source: 'geolocation' | 'manual', address_text: string | null) => {
    setPending(true)
    try {
      const location = await setLocation({ lat, lng, source, address_text })
      onSettled(location)
    } catch (err) {
      toast.show({
        variant: 'error',
        title: t('feed.locationPrompt.title'),
        description: err instanceof Error ? err.message : undefined,
      })
    } finally {
      setPending(false)
    }
  }

  const handleGeolocation = () => {
    if (!('geolocation' in navigator)) {
      toast.show({
        variant: 'error',
        title: t('feed.locationPrompt.locationDenied'),
      })
      return
    }
    setPending(true)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        void persist(
          position.coords.latitude,
          position.coords.longitude,
          'geolocation',
          null,
        ).finally(() => setPending(false))
      },
      () => {
        setPending(false)
        toast.show({
          variant: 'error',
          title: t('feed.locationPrompt.locationDenied'),
        })
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60_000 },
    )
  }

  const handleCity = () => {
    const city = CITY_CENTERS.find((c) => c.id === cityId)
    if (!city) return
    void persist(city.lat, city.lng, 'manual', city.name)
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 px-4 py-6 backdrop-blur-sm sm:items-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          role="dialog"
          aria-modal="true"
        >
          <motion.div
            initial={{ y: 24, scale: 0.98 }}
            animate={{ y: 0, scale: 1 }}
            exit={{ y: 24, scale: 0.98 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="w-full max-w-md rounded-3xl bg-surface p-6 shadow-pop"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-col gap-2 text-center">
              <span className="mx-auto flex size-14 items-center justify-center rounded-3xl bg-primary/10 text-primary">
                <MapPin className="size-7" aria-hidden />
              </span>
              <h2 className="text-[20px] font-bold text-ink">
                {t('feed.locationPrompt.title')}
              </h2>
              <p className="text-[14px] text-ink-variant">
                {t('feed.locationPrompt.subtitle')}
              </p>
            </div>

            <div className="mt-6 flex flex-col gap-3">
              <button
                type="button"
                onClick={handleGeolocation}
                disabled={pending}
                className="flex items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-3 text-[14px] font-bold text-white transition-all hover:bg-primary-dark disabled:opacity-60"
              >
                <LocateFixed className="size-4" aria-hidden />
                {t('feed.locationPrompt.useLocation')}
              </button>

              <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-ink-variant/70">
                <span className="h-px flex-1 bg-border" />
                {t('feed.locationPrompt.pickCity')}
                <span className="h-px flex-1 bg-border" />
              </div>

              <select
                value={cityId}
                onChange={(e) => setCityId(e.target.value)}
                disabled={pending}
                className="w-full rounded-2xl border border-border bg-surface px-4 py-3 text-[14px] text-ink focus:border-primary focus:outline-none"
              >
                {CITY_CENTERS.map((city) => (
                  <option key={city.id} value={city.id}>
                    {city.name}
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={handleCity}
                disabled={pending}
                className="rounded-2xl border border-border bg-surface px-4 py-3 text-[14px] font-bold text-ink transition-all hover:bg-panel disabled:opacity-60"
              >
                {t('feed.locationPrompt.pickCity')}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
