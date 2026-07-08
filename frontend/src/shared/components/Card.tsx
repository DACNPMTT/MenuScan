import type { HTMLAttributes, PropsWithChildren } from 'react'
import { cn } from '@/shared/lib/cn'

type CardProps = PropsWithChildren<HTMLAttributes<HTMLElement>>

export function Card({ children, className, ...articleProps }: CardProps) {
  return (
    <article {...articleProps} className={cn('card', className)}>
      {children}
    </article>
  )
}
