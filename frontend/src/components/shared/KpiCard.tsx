import type { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export function KpiCard({
  label,
  value,
  icon: Icon,
  tone = 'default',
  hint,
  className,
}: {
  label: string
  value: string | number
  icon?: LucideIcon
  tone?: 'default' | 'danger' | 'success' | 'accent'
  hint?: string
  className?: string
}) {
  const toneClass = {
    default: 'text-foreground',
    danger: 'text-danger',
    success: 'text-success',
    accent: 'text-accent',
  }[tone]

  return (
    <Card className={cn('animate-slide-up', className)}>
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="flex flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
          <span className={cn('text-2xl font-semibold tabular-nums', toneClass)}>{value}</span>
          {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
        </div>
        {Icon && (
          <div className="rounded-lg border border-border bg-muted p-2">
            <Icon className={cn('size-4', toneClass)} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
