import { useState } from 'react'
import { CalendarIcon } from 'lucide-react'
import { format, isValid, parseISO } from 'date-fns'
import { Button } from '@/shared/components/ui/button'
import { Calendar } from '@/shared/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/components/ui/popover'
import { cn } from '@/shared/lib/cn'

interface DatePickerProps {
  value?: string
  onChange: (iso: string) => void
  placeholder?: string
  min?: string
  max?: string
  disabled?: boolean
  'aria-label'?: string
}

function parseDateSafe(iso: string | undefined): Date | undefined {
  if (!iso) return undefined
  const d = parseISO(iso)
  return isValid(d) ? d : undefined
}

/** ISO date picker built on shadcn Calendar + Popover. Bridges the
 * `YYYY-MM-DD` string contract used by BillsPage to react-day-picker's
 * `Date`-based API. `min`/`max` enforce a selectable range. */
export function DatePicker({
  value,
  onChange,
  placeholder,
  min,
  max,
  disabled,
  'aria-label': ariaLabel,
}: DatePickerProps) {
  const [open, setOpen] = useState(false)
  const selected = parseDateSafe(value)
  const minDate = parseDateSafe(min)
  const maxDate = parseDateSafe(max)

  const matchers: Array<{ before: Date } | { after: Date }> = []
  if (minDate) matchers.push({ before: minDate })
  if (maxDate) matchers.push({ after: maxDate })

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          aria-label={ariaLabel}
          className={cn(
            'h-9 w-[150px] justify-start gap-2 rounded-xl border border-border bg-surface px-3 text-left text-[14px] font-normal text-ink',
            !selected && 'text-ink-variant',
          )}
        >
          <CalendarIcon className="size-4 text-primary" aria-hidden />
          {selected ? format(selected, 'MMM d, yyyy') : (placeholder ?? ariaLabel ?? '—')}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={selected}
          onSelect={(d) => {
            if (d) {
              onChange(format(d, 'yyyy-MM-dd'))
              setOpen(false)
            }
          }}
          disabled={matchers.length > 0 ? matchers : undefined}
        />
      </PopoverContent>
    </Popover>
  )
}
