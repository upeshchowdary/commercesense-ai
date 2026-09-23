import {
  Clock,
  ExternalLink,
  FlaskConical,
  Gavel,
  Loader2,
  Search,
  Sparkles,
  TriangleAlert,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { AcosTrendChart, InventoryTrendChart, RankTrendChart } from '@/components/charts/ProductTrendChart'
import { ConfidenceBadge } from '@/components/shared/ConfidenceBadge'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { SeverityBadge } from '@/components/shared/SeverityBadge'
import { CardSkeleton } from '@/components/shared/Skeletons'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { decisionLabel, decisionTone } from '@/lib/decisions'
import { SIGNAL_TYPE_LABEL } from '@/lib/signalCopy'
import { formatCurrency, formatDateTime, formatRelativeTime, formatSecondsAge, titleCase } from '@/lib/utils'
import { useProduct } from '@/hooks/useProducts'
import { useResearch } from '@/hooks/useResearch'
import { useIntelligence } from '@/hooks/useIntelligence'

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>()
  const { data: product, isLoading, isError, refetch } = useProduct(productId)
  const research = useResearch()
  const intelligence = useIntelligence()
  const [useCache, setUseCache] = useState(true)

  if (isError) {
    return (
      <AppShell title="Product">
        <ErrorState description="Couldn't load this product." onRetry={() => refetch()} />
      </AppShell>
    )
  }

  if (isLoading || !product) {
    return (
      <AppShell title="Product">
        <CardSkeleton lines={6} />
      </AppShell>
    )
  }

  const humanDecisions = product.activity.filter((e) => e.agent === 'human')
  const researchActivity = product.activity.filter(
    (e) => e.agent === 'research_agent' || e.agent === 'insight_agent' || e.agent === 'orchestrator',
  )
  const hasResearched = researchActivity.length > 0 || research.data !== undefined

  return (
    <AppShell title={product.name}>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold text-foreground">{product.name}</h2>
              <StatusBadge status="SYNTHETIC" />
              {product.planted_issue && (
                <Badge variant="outline" title="Ground-truth label from the synthetic data generator">
                  Ground truth: {SIGNAL_TYPE_LABEL[product.planted_issue]}
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              {product.category} · {formatCurrency(product.base_price)}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {product.signals.length > 0 ? (
              <SeverityBadge severity={product.signals[0].severity} />
            ) : (
              <SeverityBadge severity={null} />
            )}
            <Button size="sm" asChild>
              <Link to={`/products/${product.product_id}/intelligence`}>
                <Sparkles className="size-3.5" />
                Full Intelligence
              </Link>
            </Button>
          </div>
        </div>

        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="signals">Signals ({product.signals.length})</TabsTrigger>
            <TabsTrigger value="research">Research</TabsTrigger>
            <TabsTrigger value="evidence">Evidence</TabsTrigger>
            <TabsTrigger value="insights">Insights</TabsTrigger>
            <TabsTrigger value="decisions">Decision History ({humanDecisions.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Card className="p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Signals</p>
                <p className="mt-1 text-xl font-semibold text-foreground">{product.signals.length}</p>
              </Card>
              <Card className="p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Latest Severity</p>
                <div className="mt-1.5">
                  <SeverityBadge severity={product.signals[0]?.severity ?? null} />
                </div>
              </Card>
              <Card className="p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Research Status</p>
                <div className="mt-1.5">
                  {hasResearched ? (
                    <StatusBadge status="LIVE" />
                  ) : (
                    <span className="text-sm text-muted-foreground">Not researched yet</span>
                  )}
                </div>
              </Card>
            </div>
            {product.metrics.length === 0 ? (
              <EmptyState title="No metric history" description="This product has no daily metrics." />
            ) : (
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Sales Rank</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <RankTrendChart metrics={product.metrics} />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>Inventory</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <InventoryTrendChart metrics={product.metrics} />
                  </CardContent>
                </Card>
                <Card className="lg:col-span-2">
                  <CardHeader>
                    <CardTitle>ACOS</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <AcosTrendChart metrics={product.metrics} />
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          <TabsContent value="signals" className="flex flex-col gap-3">
            {product.signals.length === 0 ? (
              <EmptyState
                icon={TriangleAlert}
                title="No signals detected"
                description="Run signal detection from the Signals page to check this product."
              />
            ) : (
              product.signals.map((s) => (
                <Link key={s.id} to={`/signals/${s.id}`}>
                  <Card className="flex flex-col gap-2 p-4 transition-colors hover:border-primary/40 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-3">
                      <SeverityBadge severity={s.severity} />
                      <span className="text-sm font-medium text-foreground">
                        {SIGNAL_TYPE_LABEL[s.signal_type]}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">Detected {formatDateTime(s.detected_at)}</span>
                  </Card>
                </Link>
              ))
            )}
          </TabsContent>

          <TabsContent value="research" className="flex flex-col gap-4">
            <Card className="flex flex-col gap-3 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <label className="flex items-center gap-1.5">
                    <input
                      type="checkbox"
                      checked={useCache}
                      onChange={(e) => setUseCache(e.target.checked)}
                      className="size-3.5 accent-[var(--primary)]"
                    />
                    Use cache when available
                  </label>
                </div>
                <Button
                  onClick={() => research.mutate({ product_name: product.name, use_cache: useCache })}
                  disabled={research.isPending}
                >
                  {research.isPending ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
                  Run live research
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                This calls the live Research Agent (Gemini + Tavily). With caching on, repeat runs within the
                cache window are free and instant; a genuinely new run spends real, metered API quota.
              </p>
              {research.isError && (
                <p className="text-xs text-danger">{(research.error as Error)?.message ?? 'Research failed.'}</p>
              )}
            </Card>

            {research.data && (
              <Card className="flex flex-col gap-3 p-4">
                <div className="flex items-center gap-2">
                  <StatusBadge status={research.data.cache_hit ? 'CACHED' : 'LIVE'} />
                  {research.data.cache_hit && research.data.cache_age_seconds !== null && (
                    <span className="text-xs text-muted-foreground">
                      Age: {formatSecondsAge(research.data.cache_age_seconds)}
                    </span>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {research.data.bundle.findings.length} source(s)
                  </span>
                </div>
                <div className="flex flex-col gap-2">
                  {research.data.bundle.search_queries_used.map((q, i) => (
                    <Badge key={i} variant="outline" className="w-fit normal-case">
                      {q}
                    </Badge>
                  ))}
                </div>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="evidence" className="flex flex-col gap-3">
            {!research.data && !intelligence.data ? (
              <EmptyState
                icon={FlaskConical}
                title="No evidence yet"
                description="Run research or generate an insight to see cited findings here."
              />
            ) : (
              (research.data?.bundle.findings ?? intelligence.data?.bundle.findings ?? []).map((f, i) => (
                <Card key={i} className="flex flex-col gap-1.5 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-muted-foreground">Query: {f.query}</span>
                    <span className="text-xs text-muted-foreground">{formatRelativeTime(f.retrieved_at)}</span>
                  </div>
                  <p className="text-sm text-foreground">{f.snippet}</p>
                  {f.source_url && (
                    <a
                      href={f.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-xs text-accent hover:underline"
                    >
                      {f.source_url}
                      <ExternalLink className="size-3" />
                    </a>
                  )}
                </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="insights" className="flex flex-col gap-4">
            <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
              <p className="text-xs text-muted-foreground">
                Generates grounded insights (pricing, trend, risk, opportunity) from live research. Every
                confident insight must cite a real snippet from the findings above — anything the model can't
                back up is shown as "no reliable data found."
              </p>
              <Button
                onClick={() => intelligence.mutate({ product_name: product.name, use_cache: useCache })}
                disabled={intelligence.isPending}
              >
                {intelligence.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Sparkles className="size-4" />
                )}
                Generate insight
              </Button>
            </Card>
            {intelligence.isError && (
              <p className="text-xs text-danger">
                {(intelligence.error as Error)?.message ?? 'Insight generation failed.'}
              </p>
            )}
            {intelligence.data ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {intelligence.data.report.insights.map((insight) => (
                  <Card key={insight.category} className="flex flex-col gap-2 p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-foreground">{titleCase(insight.category)}</span>
                      <ConfidenceBadge confidence={insight.confidence} />
                    </div>
                    {insight.summary ? (
                      <>
                        <p className="text-sm text-muted-foreground">{insight.summary}</p>
                        {insight.source_snippet && (
                          <blockquote className="rounded-md border-l-2 border-primary/40 bg-muted/50 px-3 py-2 text-xs italic text-muted-foreground">
                            "{insight.source_snippet}"
                          </blockquote>
                        )}
                        {insight.source_url && (
                          <a
                            href={insight.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-1 text-xs text-accent hover:underline"
                          >
                            Source <ExternalLink className="size-3" />
                          </a>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">No reliable data found.</p>
                    )}
                  </Card>
                ))}
              </div>
            ) : (
              <EmptyState icon={Sparkles} title="No insights generated yet" />
            )}
          </TabsContent>

          <TabsContent value="decisions" className="flex flex-col gap-3">
            {humanDecisions.length === 0 ? (
              <EmptyState icon={Gavel} title="No decisions recorded for this product yet" />
            ) : (
              humanDecisions.map((d, i) => (
                <Card key={i} className="flex items-center justify-between gap-3 p-4">
                  <div className="flex items-center gap-3">
                    <Badge variant={decisionTone(d.action)}>{decisionLabel(d.action)}</Badge>
                    <span className="text-sm text-foreground">
                      {(d.detail as { category?: string })?.category ?? ''}
                    </span>
                    {(d.detail as { reason?: string })?.reason && (
                      <span className="text-sm text-muted-foreground">
                        — {(d.detail as { reason?: string }).reason}
                      </span>
                    )}
                  </div>
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="size-3" />
                    {formatDateTime(d.timestamp)}
                  </span>
                </Card>
              ))
            )}
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}
