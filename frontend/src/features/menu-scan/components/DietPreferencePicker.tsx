import { useTranslation } from 'react-i18next'
import { ALLERGENS, DIET_PREFERENCES } from '@/features/menu-scan/dietary'
import { cn } from '@/shared/lib/cn'

export interface DietPreferenceValue {
  allergies: string[]
  dietary_preferences: string[]
}

interface DietPreferencePickerProps {
  value: DietPreferenceValue
  onChange: (next: DietPreferenceValue) => void
  disabled?: boolean
  sections?: Array<'allergies' | 'dietary_preferences'>
}

function toggle(list: string[], code: string): string[] {
  return list.includes(code) ? list.filter((item) => item !== code) : [...list, code]
}

/** Chip multi-selects for allergies + dietary preferences. Reused by the profile
 * editor and (later) the registration onboarding step. */
export function DietPreferencePicker({
  value,
  onChange,
  disabled,
  sections = ['allergies', 'dietary_preferences'],
}: DietPreferencePickerProps) {
  const { t } = useTranslation()
  const showAllergies = sections.includes('allergies')
  const showDietaryPreferences = sections.includes('dietary_preferences')

  const chip = (active: boolean) =>
    cn(
      'h-8 rounded-full border px-3 text-[13px] font-medium transition-all duration-200 ease-[var(--ease-spring)] hover:scale-[1.04] active:scale-95 disabled:cursor-not-allowed disabled:opacity-50',
      active
        ? 'border-primary bg-primary text-white shadow-sm shadow-primary/25'
        : 'border-hairline bg-canvas text-primary-dark hover:bg-surface-muted',
    )

  return (
    <div className="flex flex-col gap-4">
      {showAllergies ? (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
            {t('diet.allergiesLabel')}
          </legend>
          <div className="flex flex-wrap gap-2">
            {ALLERGENS.map((code) => {
              const active = value.allergies.includes(code)
              return (
                <button
                  key={code}
                  type="button"
                  disabled={disabled}
                  aria-pressed={active}
                  onClick={() =>
                    onChange({ ...value, allergies: toggle(value.allergies, code) })
                  }
                  className={chip(active)}
                >
                  {t(`diet.allergens.${code}`)}
                </button>
              )
            })}
          </div>
        </fieldset>
      ) : null}

      {showDietaryPreferences ? (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
            {t('diet.preferencesLabel')}
          </legend>
          <div className="flex flex-wrap gap-2">
            {DIET_PREFERENCES.map((code) => {
              const active = value.dietary_preferences.includes(code)
              return (
                <button
                  key={code}
                  type="button"
                  disabled={disabled}
                  aria-pressed={active}
                  onClick={() =>
                    onChange({
                      ...value,
                      dietary_preferences: toggle(value.dietary_preferences, code),
                    })
                  }
                  className={chip(active)}
                >
                  {t(`diet.preferences.${code}`)}
                </button>
              )
            })}
          </div>
        </fieldset>
      ) : null}
    </div>
  )
}
