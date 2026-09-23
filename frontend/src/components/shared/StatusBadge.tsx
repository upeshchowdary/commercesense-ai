import { Database, FlaskConical, Sparkles, Zap, type LucideIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export type DataStatus = 'LIVE' | 'CACHED' | 'SYNTHETIC' | 'DEMO'

const CONFIG: Record<DataStatus, { variant: 'live' | 'cached' | 'synthetic' | 'demo'; icon: LucideIcon; label: string }> = {
  LIVE: { variant: 'live', icon: Zap, label: 'Live' },
  CACHED: { variant: 'cached', icon: Database, label: 'Cache Hit' },
  SYNTHETIC: { variant: 'synthetic', icon: FlaskConical, label: 'Synthetic' },
  DEMO: { variant: 'demo', icon: Sparkles, label: 'Demo' },
}

export function StatusBadge({ status, className }: { status: DataStatus; className?: string }) {
  const { variant, icon: Icon, label } = CONFIG[status]
  return (
    <Badge variant={variant} className={cn(className)}>
      <Icon className="size-3" />
      {label}
    </Badge>
  )
}
