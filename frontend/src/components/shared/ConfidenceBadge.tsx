import { Badge } from '@/components/ui/badge'
import type { Confidence } from '@/lib/types'

const VARIANT: Record<Confidence, 'success' | 'warning' | 'outline' | 'secondary'> = {
  high: 'success',
  medium: 'warning',
  low: 'outline',
  none: 'secondary',
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return <Badge variant={VARIANT[confidence]}>{confidence} confidence</Badge>
}
