import type { InputHTMLAttributes } from 'react'
import { useId } from 'react'
import { cn } from '@/shared/lib/cn'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  error?: string
  helperText?: string
  label: string
}

export function Input({
  className,
  error,
  helperText,
  id,
  label,
  ...inputProps
}: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const messageId = `${inputId}-message`
  const message = error ?? helperText

  return (
    <label className="field" htmlFor={inputId}>
      <span className="field__label">{label}</span>
      <input
        {...inputProps}
        aria-describedby={message ? messageId : undefined}
        aria-invalid={error ? true : undefined}
        className={cn('field__input', error && 'field__input--invalid', className)}
        id={inputId}
      />
      {message ? (
        <span className="field__message" id={messageId}>
          {message}
        </span>
      ) : null}
    </label>
  )
}
