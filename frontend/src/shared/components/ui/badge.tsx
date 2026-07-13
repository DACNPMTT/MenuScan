import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/shared/lib/cn"

const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border border-transparent px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 aria-invalid:border-destructive aria-invalid:ring-destructive/20 [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      variant: {
        default: "bg-primary text-white [a&]:hover:bg-primary/90",
        primary: "bg-primary/10 text-primary [a&]:hover:bg-primary/20",
        accent: "bg-accent/30 text-accent-foreground [a&]:hover:bg-accent/50",
        success: "bg-success/10 text-success [a&]:hover:bg-success/20",
        secondary:
          "bg-panel text-ink-variant [a&]:hover:bg-border",
        destructive:
          "bg-destructive/10 text-destructive focus-visible:ring-destructive/20 [a&]:hover:bg-destructive/20",
        outline:
          "border-border text-ink-variant [a&]:hover:bg-panel",
        ghost: "text-ink-variant [a&]:hover:bg-panel",
        link: "text-primary underline-offset-4 [a&]:hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "span"

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
