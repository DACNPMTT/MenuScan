import { useState, type FormEvent } from 'react'
import { Plus, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { cn } from '@/shared/lib/cn'
import {
  labelPreferenceCode,
  normalizeCustomPreferenceCode,
  preferenceOptionsForSection,
  updateSectionValues,
  valuesForSection,
  type FoodProfilePreferenceDraft,
  type FoodProfilePreferenceSection,
} from '@/features/food-profile/preferences'

const DEFAULT_SECTIONS: FoodProfilePreferenceSection[] = [
  'allergies',
  'dietary_preferences',
  'likes',
  'avoids',
]

interface FoodProfilePreferencePickerProps {
  value: FoodProfilePreferenceDraft
  onChange: (next: FoodProfilePreferenceDraft) => void
  disabled?: boolean
  sections?: FoodProfilePreferenceSection[]
}

function toggle(list: string[], code: string): string[] {
  return list.includes(code) ? list.filter((item) => item !== code) : [...list, code]
}

function mergeOptions(options: readonly string[], selected: string[]): string[] {
  const merged = [...options]
  selected.forEach((code) => {
    if (!merged.includes(code)) merged.push(code)
  })
  return merged
}

export function FoodProfilePreferencePicker({
  value,
  onChange,
  disabled,
  sections = DEFAULT_SECTIONS,
}: FoodProfilePreferencePickerProps) {
  const { t } = useTranslation()
  const [customInputs, setCustomInputs] = useState<Record<string, string>>({})

  const chip = (active: boolean) =>
    cn(
      'inline-flex min-h-8 items-center gap-1.5 rounded-full border px-3 py-1 text-[13px] font-medium transition-all duration-200 ease-[var(--ease-spring)] hover:scale-[1.04] active:scale-95 disabled:cursor-not-allowed disabled:opacity-50',
      active
        ? 'border-primary bg-primary text-white shadow-sm shadow-primary/25'
        : 'border-hairline bg-canvas text-primary-dark hover:bg-surface-muted',
    )

  const labelFor = (section: FoodProfilePreferenceSection, code: string) => {
    const fallback = labelPreferenceCode(code)
    if (section === 'allergies') {
      return t(`diet.allergens.${code}`, { defaultValue: fallback })
    }
    if (section === 'dietary_preferences') {
      return t(`diet.preferences.${code}`, { defaultValue: fallback })
    }
    return t(`foodProfile.preferenceLabels.${code}`, { defaultValue: fallback })
  }

  const updateCustomInput = (section: FoodProfilePreferenceSection, next: string) => {
    setCustomInputs((current) => ({ ...current, [section]: next }))
  }

  const toggleCode = (section: FoodProfilePreferenceSection, code: string) => {
    const selected = valuesForSection(value, section)
    onChange(updateSectionValues(value, section, toggle(selected, code)))
  }

  const addCustom = (event: FormEvent<HTMLFormElement>, section: FoodProfilePreferenceSection) => {
    event.preventDefault()
    const code = normalizeCustomPreferenceCode(customInputs[section] ?? '')
    if (!code) return
    const selected = valuesForSection(value, section)
    const nextSelected = selected.includes(code) ? selected : [...selected, code]
    onChange(updateSectionValues(value, section, nextSelected))
    setCustomInputs((current) => ({ ...current, [section]: '' }))
  }

  return (
    <div className="flex flex-col gap-5">
      {sections.map((section) => {
        const selected = valuesForSection(value, section)
        const options = mergeOptions(preferenceOptionsForSection(section), selected)
        return (
          <fieldset key={section} className="flex flex-col gap-2">
            <legend className="mb-1 text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
              {t(`foodProfile.sections.${section}`)}
            </legend>
            <div className="flex flex-wrap gap-2">
              {options.map((code) => {
                const active = selected.includes(code)
                return (
                  <button
                    key={code}
                    type="button"
                    disabled={disabled}
                    aria-pressed={active}
                    onClick={() => toggleCode(section, code)}
                    className={chip(active)}
                  >
                    <span>{labelFor(section, code)}</span>
                    {active && !preferenceOptionsForSection(section).includes(code) ? (
                      <X className="size-3" aria-hidden />
                    ) : null}
                  </button>
                )
              })}
            </div>
            <form
              onSubmit={(event) => addCustom(event, section)}
              className="mt-1 grid gap-2 sm:grid-cols-[1fr_auto]"
            >
              <Input
                value={customInputs[section] ?? ''}
                onChange={(event) => updateCustomInput(section, event.target.value)}
                disabled={disabled}
                placeholder={t('foodProfile.otherPlaceholder')}
                aria-label={t('foodProfile.otherLabel', {
                  section: t(`foodProfile.sections.${section}`),
                })}
                className="h-10 rounded-xl"
              />
              <Button
                type="submit"
                variant="outline"
                disabled={disabled || !normalizeCustomPreferenceCode(customInputs[section] ?? '')}
                className="h-10 rounded-full transition-all duration-200 ease-[var(--ease-spring)] hover:bg-surface-muted hover:text-primary-dark active:scale-95"
              >
                <Plus className="size-4" aria-hidden />
                {t('foodProfile.addOther')}
              </Button>
            </form>
          </fieldset>
        )
      })}
    </div>
  )
}
