import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/shared/lib/cn"

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-full font-semibold whitespace-nowrap transition-all duration-200 ease-[var(--ease-out-quint)] outline-none active:scale-[0.97] focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-white shadow-2 hover:-translate-y-0.5 hover:bg-[#1d4ed8] hover:shadow-3",
        destructive:
          "bg-destructive text-white shadow-1 hover:-translate-y-0.5 hover:bg-destructive/90 focus-visible:ring-destructive/20",
        outline:
          "border border-border bg-surface text-ink shadow-1 hover:-translate-y-0.5 hover:bg-panel hover:text-primary",
        secondary:
          "bg-panel text-ink hover:bg-border",
        ghost:
          "text-ink-variant hover:bg-panel hover:text-primary",
        accent:
          "bg-accent text-accent-foreground shadow-1 hover:-translate-y-0.5 hover:brightness-95",
        duo:
          "rounded-2xl bg-[#58cc02] text-white font-extrabold uppercase tracking-[0.8px] border-0 shadow-[0_4px_0_0_#58a700] hover:bg-[#61d20a] active:translate-y-[2px] active:scale-100 active:shadow-[0_2px_0_0_#58a700]",
        "duo-outline":
          "rounded-2xl bg-white text-[#1cb0f6] font-extrabold uppercase tracking-[0.8px] border-2 border-[#e5e5e5] shadow-[0_4px_0_0_#e5e5e5] hover:border-[#d4d4d4] hover:bg-[#f7f7f7] active:translate-y-[2px] active:scale-100 active:shadow-[0_2px_0_0_#e5e5e5]",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-5 py-2 text-sm has-[>svg]:px-4",
        xs: "h-7 gap-1 px-2.5 text-xs has-[>svg]:px-2 [&_svg:not([class*='size-'])]:size-3.5",
        sm: "h-9 gap-1.5 px-4 text-sm has-[>svg]:px-3",
        lg: "h-11 px-6 text-base has-[>svg]:px-5",
        icon: "size-10",
        "icon-xs": "size-7 [&_svg:not([class*='size-'])]:size-3.5",
        "icon-sm": "size-9",
        "icon-lg": "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
