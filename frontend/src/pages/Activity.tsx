import { Activity as ActivityIcon, Bot, FlaskConical, Gavel, Search, Sparkles, Waypoints } from 'lucide-react'
import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { ListSkeleton } from '@/components/shared/Skeletons'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatDateTime, titleCase } from '@/lib/utils'
import { useActivity } from '@/hooks/useActivity'

const AGENT_ICONS: Record<string, typeof Search> = {
  research_agent: Search,
  insight_agent: Sparkles,
  inventory_signal: FlaskConical,
  ppc_waste_signal: FlaskConical,
  rank_bb_signal: FlaskConical,
  orchestrator: Waypoints,
  human: Gavel,
}

const AGENT_OPTIONS = [
  'research_agent',
  'insight_agent',
  'orchestrator',
  'inventory_signal',
  'ppc_waste_signal',
  'rank_bb_signal',
  'human',
]

export default function Activity() {
  const [agent, setAgent] = useState('all')
  const [product, setProduct] = useState('')
  const { data, isLoading, isError, refetch } = useActivity({
    agent: agent === 'all' ? undefined : agent,
    product_name: product || undefined,
    limit: 300,
  })

  return (
    <AppShell title="Activity Feed">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row">
          <Select value={agent} onValueChange={setAgent}>
            <SelectTrigger className="w-full sm:w-56">
              <SelectValue placeholder="Agent" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All agents</SelectItem>
              {AGENT_OPTIONS.map((a) => (
                <SelectItem key={a} value={a}>
                  {titleCase(a)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            placeholder="Filter by exact product name…"
            className="flex-1"
          />
        </div>

        {isError ? (
          <ErrorState description="Couldn't load activity." onRetry={() => refetch()} />
        ) : isLoading ? (
          <ListSkeleton rows={10} />
        ) : (data ?? []).length === 0 ? (
          <EmptyState icon={ActivityIcon} title="No activity found" />
        ) : (
          <Card className="divide-y divide-border">
            {(data ?? []).map((e, i) => {
              const Icon = AGENT_ICONS[e.agent] ?? Bot
              return (
                <div key={i} className="flex items-start gap-3 px-4 py-3">
                  <div className="mt-0.5 rounded-md border border-border bg-muted p-1.5">
                    <Icon className="size-3.5 text-primary" />
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{titleCase(e.agent)}</Badge>
                      <span className="text-sm font-medium text-foreground">{titleCase(e.action)}</span>
                      <span className="text-sm text-muted-foreground">{e.product_name}</span>
                      <span className="ml-auto text-xs text-muted-foreground">{formatDateTime(e.timestamp)}</span>
                    </div>
                    {Object.keys(e.detail ?? {}).length > 0 && (
                      <details className="text-xs text-muted-foreground">
                        <summary className="cursor-pointer select-none">Detail</summary>
                        <pre className="mt-1 overflow-x-auto rounded-md bg-muted/50 p-2 text-[11px]">
                          {JSON.stringify(e.detail, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              )
            })}
          </Card>
        )}
      </div>
    </AppShell>
  )
}
