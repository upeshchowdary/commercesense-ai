import { Loader2, RefreshCw, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { SeverityBadge } from '@/components/shared/SeverityBadge'
import { ListSkeleton } from '@/components/shared/Skeletons'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { findDecision } from '@/lib/decisions'
import { SIGNAL_TYPE_LABEL } from '@/lib/signalCopy'
import { formatDateTime } from '@/lib/utils'
import { useActivity } from '@/hooks/useActivity'
import { useRunSignalDetection, useSignals } from '@/hooks/useSignals'

const SEVERITY_FILTERS = ['all', 'high', 'medium'] as const
const TYPE_FILTERS = ['all', 'inventory_stockout', 'ppc_waste', 'rank_drop'] as const
const STATUS_FILTERS = ['all', 'new', 'reviewed'] as const

export default function Signals() {
  const [severity, setSeverity] = useState<(typeof SEVERITY_FILTERS)[number]>('all')
  const [type, setType] = useState<(typeof TYPE_FILTERS)[number]>('all')
  const [status, setStatus] = useState<(typeof STATUS_FILTERS)[number]>('all')

  const { data, isLoading, isError, refetch } = useSignals({
    severity: severity === 'all' ? undefined : severity,
    type: type === 'all' ? undefined : type,
  })
  const activity = useActivity({ agent: 'human' })
  const runDetection = useRunSignalDetection()

  const filtered = useMemo(() => {
    const rows = data ?? []
    if (status === 'all') return rows
    return rows.filter((s) => {
      const decided = !!findDecision(activity.data, s.product_name ?? '', s.signal_type)
      return status === 'reviewed' ? decided : !decided
    })
  }, [data, status, activity.data])

  return (
    <AppShell
      title="Signal Center"
      actions={
        <Button size="sm" onClick={() => runDetection.mutate()} disabled={runDetection.isPending}>
          {runDetection.isPending ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <RefreshCw className="size-3.5" />
          )}
          Run signal detection
        </Button>
      }
    >
      <div className="flex flex-col gap-4">
        {runDetection.data && (
          <Card className="flex flex-wrap items-center gap-4 p-3 text-xs text-muted-foreground">
            <span>
              Flagged <strong className="text-foreground">{runDetection.data.total_flagged}</strong> this run
            </span>
            <span>Inventory: {runDetection.data.inventory_stockout_flagged}</span>
            <span>PPC waste: {runDetection.data.ppc_waste_flagged}</span>
            <span>Rank drop: {runDetection.data.rank_drop_flagged}</span>
          </Card>
        )}

        <div className="flex flex-wrap gap-3">
          <Select value={severity} onValueChange={(v) => setSeverity(v as typeof severity)}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              <SelectItem value="high">Critical / High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
            </SelectContent>
          </Select>
          <Select value={type} onValueChange={(v) => setType(v as typeof type)}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Signal type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              <SelectItem value="inventory_stockout">Inventory Stockout</SelectItem>
              <SelectItem value="ppc_waste">PPC Waste</SelectItem>
              <SelectItem value="rank_drop">Ranking / Buy Box</SelectItem>
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={(v) => setStatus(v as typeof status)}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="new">New</SelectItem>
              <SelectItem value="reviewed">Reviewed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {isError ? (
          <ErrorState description="Couldn't load signals." onRetry={() => refetch()} />
        ) : isLoading ? (
          <ListSkeleton rows={8} />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={TriangleAlert}
            title="No signals match"
            description={
              (data ?? []).length === 0
                ? 'No signals detected yet — click "Run signal detection" above.'
                : 'Try different filters.'
            }
          />
        ) : (
          <div className="flex flex-col gap-2.5">
            {filtered.map((s) => {
              const decided = !!findDecision(activity.data, s.product_name ?? '', s.signal_type)
              return (
                <Link key={s.id} to={`/signals/${s.id}`}>
                  <Card className="flex flex-col gap-2 p-4 transition-colors hover:border-primary/40 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-3">
                      <SeverityBadge severity={s.severity} />
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-foreground">
                          {SIGNAL_TYPE_LABEL[s.signal_type]}
                        </span>
                        <span className="text-xs text-muted-foreground">{s.product_name}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant={decided ? 'secondary' : 'outline'}>
                        {decided ? 'Reviewed' : 'Awaiting Decision'}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{formatDateTime(s.detected_at)}</span>
                    </div>
                  </Card>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </AppShell>
  )
}
