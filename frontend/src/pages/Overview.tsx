import {
  Activity as ActivityIcon,
  Boxes,
  FlaskConical,
  Gavel,
  Search,
  TriangleAlert,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { AgentActivityChart } from '@/components/charts/AgentActivityChart'
import { SignalDistributionChart } from '@/components/charts/SignalDistributionChart'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { KpiCard } from '@/components/shared/KpiCard'
import { CardSkeleton, KpiSkeleton } from '@/components/shared/Skeletons'
import { findDecision } from '@/lib/decisions'
import { formatRelativeTime, titleCase } from '@/lib/utils'
import { useActivity } from '@/hooks/useActivity'
import { useEvaluation } from '@/hooks/useEvaluation'
import { useProducts } from '@/hooks/useProducts'
import { useSignals } from '@/hooks/useSignals'

export default function Overview() {
  const products = useProducts()
  const signals = useSignals()
  const activity = useActivity({ limit: 100 })
  const evaluation = useEvaluation()

  const loading = products.isLoading || signals.isLoading || activity.isLoading
  const anyError = products.isError || signals.isError || activity.isError

  if (anyError) {
    return (
      <AppShell title="Overview">
        <ErrorState
          description="Couldn't reach the API. Make sure the backend is running (uvicorn api.main:app --port 8000)."
          onRetry={() => {
            products.refetch()
            signals.refetch()
            activity.refetch()
          }}
        />
      </AppShell>
    )
  }

  const productList = products.data ?? []
  const signalList = signals.data ?? []
  const activityList = activity.data ?? []

  const highSeverity = signalList.filter((s) => s.severity === 'high')
  const researchRuns = activityList.filter((e) => e.agent === 'research_agent')
  const pending = signalList.filter(
    (s) => s.severity && !findDecision(activityList, s.product_name ?? '', s.signal_type),
  )
  const opportunities = (evaluation.data?.results ?? []).filter(
    (r) => r.expected && r.detected && !r.false_positive,
  )

  const recent = activityList.slice(0, 8)

  return (
    <AppShell title="Overview">
      <div className="flex flex-col gap-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            AI Commerce Intelligence
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Monitor products. Research markets. Detect signals. Understand why they matter.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => <KpiSkeleton key={i} />)
          ) : (
            <>
              <KpiCard label="Products Monitored" value={productList.length} icon={Boxes} />
              <KpiCard label="Active Signals" value={signalList.length} icon={TriangleAlert} />
              <KpiCard
                label="High Priority"
                value={highSeverity.length}
                icon={TriangleAlert}
                tone={highSeverity.length > 0 ? 'danger' : 'default'}
              />
              <KpiCard
                label="Opportunities Detected"
                value={opportunities.length}
                icon={FlaskConical}
                tone="success"
                hint="Synthetic eval"
              />
              <KpiCard label="Research Runs" value={researchRuns.length} icon={Search} />
              <KpiCard
                label="Pending Decisions"
                value={pending.length}
                icon={Gavel}
                tone={pending.length > 0 ? 'accent' : 'default'}
              />
            </>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Signal Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <CardSkeleton /> : <SignalDistributionChart signals={signalList} />}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Agent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <CardSkeleton /> : <AgentActivityChart activity={activityList} />}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Recent Intelligence</CardTitle>
            <Link to="/activity" className="text-xs font-medium text-accent hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent>
            {loading ? (
              <CardSkeleton lines={5} />
            ) : recent.length === 0 ? (
              <EmptyState
                icon={ActivityIcon}
                title="No activity yet"
                description="Run signal detection or a live research query to see events here."
              />
            ) : (
              <ul className="flex flex-col divide-y divide-border">
                {recent.map((e, i) => (
                  <li key={i} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                    <div className="flex min-w-0 items-center gap-3">
                      <Badge variant="outline" className="shrink-0">
                        {titleCase(e.agent)}
                      </Badge>
                      <span className="truncate text-foreground">{titleCase(e.action)}</span>
                      <span className="truncate text-muted-foreground">· {e.product_name}</span>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {formatRelativeTime(e.timestamp)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
