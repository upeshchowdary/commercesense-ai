import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center justify-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide whitespace-nowrap transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-primary/15 text-primary border-primary/30',
        secondary: 'bg-secondary text-secondary-foreground border-border',
        outline: 'text-foreground border-border',
        success: 'bg-success/15 text-success border-success/30',
        warning: 'bg-warning/15 text-warning border-warning/30',
        danger: 'bg-danger/15 text-danger border-danger/30',
        live: 'bg-live-soft text-live border-live/30',
        cached: 'bg-cached-soft text-cached border-cached/30',
        synthetic: 'bg-synthetic-soft text-synthetic border-synthetic/30',
        demo: 'bg-demo-soft text-demo border-demo/30',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<'span'> & VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : 'span'
  return <Comp data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
