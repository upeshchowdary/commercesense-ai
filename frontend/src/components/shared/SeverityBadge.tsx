import { Badge } from '@/components/ui/badge'
import type { Severity } from '@/lib/types'

export function SeverityBadge({ severity }: { severity: Severity | null }) {
  if (severity === 'high') return <Badge variant="danger">High</Badge>
  if (severity === 'medium') return <Badge variant="warning">Medium</Badge>
  return <Badge variant="success">Healthy</Badge>
}
