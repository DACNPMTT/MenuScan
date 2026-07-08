import type {
  ButtonHTMLAttributes,
  MouseEvent,
  PropsWithChildren,
} from 'react'
import type { LinkProps } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { cn } from '@/shared/lib/cn'

type ButtonVariant = 'primary' | 'secondary'

type ButtonBaseProps = PropsWithChildren<{
  className?: string
  variant?: ButtonVariant
}>

type NativeButtonProps = ButtonBaseProps &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    as?: 'button'
  }

type LinkButtonProps = ButtonBaseProps &
  LinkProps & {
    as: 'link'
    disabled?: boolean
  }

type ButtonProps = NativeButtonProps | LinkButtonProps

export function Button(props: ButtonProps) {
  const variant = props.variant ?? 'primary'
  const className = cn(
    'button',
    `button--${variant}`,
    props.className,
    props.disabled && 'button--disabled',
  )

  if (props.as === 'link') {
    const { as, children, disabled, variant, ...linkProps } = props
    void as
    void variant

    const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
      if (disabled) {
        event.preventDefault()
        return
      }

      linkProps.onClick?.(event)
    }

    return (
      <Link
        {...linkProps}
        aria-disabled={disabled ? true : undefined}
        className={className}
        onClick={handleClick}
        tabIndex={disabled ? -1 : linkProps.tabIndex}
      >
        {children}
      </Link>
    )
  }

  const { as, children, variant: _variant, ...buttonProps } = props
  void as
  void _variant

  return (
    <button {...buttonProps} className={className}>
      {children}
    </button>
  )
}
