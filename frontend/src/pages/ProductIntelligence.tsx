import {
  CheckCircle2,
  Loader2,
  MessageSquarePlus,
  RefreshCw,
  Sparkles,
  XCircle,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { ConfidenceBadge } from '@/components/shared/ConfidenceBadge'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { CardSkeleton } from '@/components/shared/Skeletons'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatCurrency, titleCase } from '@/lib/utils'
import type { IntelligenceApproveRequest } from '@/lib/types'
import {
  useInventoryAnalyze,
  useInventoryApprove,
  useInventoryIntelligence,
  useInventorySimulate,
  useListingAnalyze,
  useListingApprove,
  useListingIntelligence,
  useListingRewrite,
  usePricingAnalyze,
  usePricingApprove,
  usePricingIntelligence,
  usePricingSimulate,
  useProductIntelligenceOverview,
  useReviewAnalyze,
  useReviewApprove,
  useReviewIntelligence,
} from '@/hooks/useIntelligenceModules'

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <Badge variant="secondary">No data</Badge>
  const variant = score >= 80 ? 'success' : score >= 60 ? 'warning' : 'danger'
  return <Badge variant={variant}>{score}/100</Badge>
}

function DecisionRow({
  onApprove, onReject, onMoreResearch, pending,
}: {
  onApprove: () => void
  onReject: () => void
  onMoreResearch: () => void
  pending: boolean
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button size="sm" disabled={pending} onClick={onApprove}>
        <CheckCircle2 className="size-3.5" /> Approve
      </Button>
      <Button size="sm" variant="destructive" disabled={pending} onClick={onReject}>
        <XCircle className="size-3.5" /> Reject
      </Button>
      <Button size="sm" variant="outline" disabled={pending} onClick={onMoreResearch}>
        <MessageSquarePlus className="size-3.5" /> Request More Research
      </Button>
    </div>
  )
}

export default function ProductIntelligence() {
  const { productId } = useParams<{ productId: string }>()
  const overview = useProductIntelligenceOverview(productId)

  if (overview.isError) {
    return (
      <AppShell title="Product Intelligence">
        <ErrorState description="Couldn't load this product's intelligence overview." onRetry={() => overview.refetch()} />
      </AppShell>
    )
  }
  if (overview.isLoading || !overview.data) {
    return (
      <AppShell title="Product Intelligence">
        <CardSkeleton lines={6} />
      </AppShell>
    )
  }

  const data = overview.data

  return (
    <AppShell title={data.product.name}>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold text-foreground">{data.product.name}</h2>
              <StatusBadge status="SYNTHETIC" />
              <Link to={`/products/${productId}`} className="text-xs text-accent hover:underline">
                Full product page →
              </Link>
            </div>
            <p className="text-sm text-muted-foreground">
              {data.product.category} · {formatCurrency(data.product.base_price)}
            </p>
          </div>
          <Card className="p-4 text-center">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Attention Score</p>
            <p className={`text-3xl font-bold ${data.attention_score >= 50 ? 'text-danger' : data.attention_score >= 20 ? 'text-warning' : 'text-success'}`}>
              {data.attention_score}
              <span className="text-base text-muted-foreground">/100</span>
            </p>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Attention Summary</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {Object.entries(data.components).map(([key, value]) => (
              <div key={key} className="rounded-lg border border-border p-3 text-center">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{titleCase(key)}</p>
                <p className="mt-1 text-lg font-semibold text-foreground">{value}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Issues</CardTitle>
          </CardHeader>
          <CardContent>
            {data.top_issues.length === 0 ? (
              <EmptyState title="No urgent issues detected" className="border-none py-6" />
            ) : (
              <ul className="flex flex-col gap-2">
                {data.top_issues.map((issue, i) => (
                  <li key={i} className="rounded-lg border border-border px-3 py-2 text-sm text-foreground">
                    {issue}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Tabs defaultValue="listing">
          <TabsList>
            <TabsTrigger value="listing">
              Listing <ScoreBadge score={data.listing_score} />
            </TabsTrigger>
            <TabsTrigger value="pricing">Pricing</TabsTrigger>
            <TabsTrigger value="reviews">Reviews</TabsTrigger>
            <TabsTrigger value="inventory">Inventory</TabsTrigger>
          </TabsList>

          <TabsContent value="listing">
            <ListingTab productId={productId!} />
          </TabsContent>
          <TabsContent value="pricing">
            <PricingTab productId={productId!} />
          </TabsContent>
          <TabsContent value="reviews">
            <ReviewsTab productId={productId!} />
          </TabsContent>
          <TabsContent value="inventory">
            <InventoryTab productId={productId!} />
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}

function approveBody(decision: IntelligenceApproveRequest['decision'], field?: string): IntelligenceApproveRequest {
  return { decision, field, decided_by: 'Demo User' }
}

// ------------------------------------------------------------------ Listing

function ListingTab({ productId }: { productId: string }) {
  const { data, isLoading, isError, refetch } = useListingIntelligence(productId)
  const analyze = useListingAnalyze()
  const rewrite = useListingRewrite()
  const approve = useListingApprove()

  if (isError) return <ErrorState description="No listing data available." onRetry={() => refetch()} />
  if (isLoading || !data) return <CardSkeleton lines={5} />

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Listing Health — {data.score}/100</CardTitle>
          <Button size="sm" onClick={() => analyze.mutate(productId)} disabled={analyze.isPending}>
            {analyze.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
            Analyze
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            {Object.entries(data.category_scores).map(([cat, score]) => (
              <div key={cat} className="rounded-lg border border-border p-2 text-center text-xs">
                <p className="text-muted-foreground">{titleCase(cat)}</p>
                <p className="font-semibold text-foreground">{score}</p>
              </div>
            ))}
          </div>
          {data.failed_rules.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {data.failed_rules.map((r) => <Badge key={r} variant="danger">{titleCase(r)}</Badge>)}
              {data.warnings.map((r) => <Badge key={r} variant="warning">{titleCase(r)}</Badge>)}
            </div>
          )}
          {analyze.data?.ai_diagnosis && (
            <div className="rounded-lg border border-border bg-muted/40 p-3 text-sm">
              {analyze.data.ai_diagnosis.available ? (
                <>
                  <p className="text-foreground">{String(analyze.data.ai_diagnosis.data?.diagnosis ?? '')}</p>
                  <ul className="mt-2 list-inside list-disc text-muted-foreground">
                    {['top_issue_1', 'top_issue_2', 'top_issue_3'].map((k) => (
                      <li key={k}>{String(analyze.data!.ai_diagnosis!.data?.[k] ?? '')}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="text-muted-foreground">{analyze.data.ai_diagnosis.message}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>AI Title Rewrite</CardTitle>
          <Button size="sm" variant="outline" onClick={() => rewrite.mutate(productId)} disabled={rewrite.isPending}>
            {rewrite.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
            Propose Rewrite
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Current Title</p>
            <p className="text-sm text-foreground">{data.listing.title}</p>
          </div>
          {rewrite.data && (
            <>
              {rewrite.data.proposed_title ? (
                <>
                  <div className="flex items-center gap-2">
                    <StatusBadge status="LIVE" />
                    <span className="text-xs text-muted-foreground">Grounded: {rewrite.data.grounding?.grounded ? 'yes' : 'no'}</span>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Proposed Title</p>
                    <p className="text-sm font-medium text-foreground">{rewrite.data.proposed_title}</p>
                  </div>
                  {rewrite.data.changes && (
                    <ul className="list-inside list-disc text-xs text-muted-foreground">
                      {rewrite.data.changes.map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">{rewrite.data.message}</p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Decision</CardTitle></CardHeader>
        <CardContent>
          <DecisionRow
            pending={approve.isPending}
            onApprove={() => approve.mutate({ productId, body: approveBody('approved', 'title') })}
            onReject={() => approve.mutate({ productId, body: approveBody('rejected', 'title') })}
            onMoreResearch={() => approve.mutate({ productId, body: approveBody('more_research_requested', 'title') })}
          />
          {approve.isSuccess && <p className="mt-2 text-xs text-success">Decision recorded.</p>}
        </CardContent>
      </Card>
    </div>
  )
}

// ------------------------------------------------------------------ Pricing

function PricingTab({ productId }: { productId: string }) {
  const { data, isLoading, isError, refetch } = usePricingIntelligence(productId)
  const analyze = usePricingAnalyze()
  const simulate = usePricingSimulate()
  const approve = usePricingApprove()
  const [simPrice, setSimPrice] = useState('')

  if (isError) return <ErrorState description="No pricing data available." onRetry={() => refetch()} />
  if (isLoading || !data) return <CardSkeleton lines={5} />

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Pricing — {data.price_state.replace(/_/g, ' ')}</CardTitle>
          <Button size="sm" onClick={() => analyze.mutate({ productId })} disabled={analyze.isPending}>
            {analyze.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
            Analyze
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Stat label="Current Price" value={formatCurrency(data.current_price)} />
            <Stat label="Variable Cost" value={formatCurrency(data.contribution.variable_cost)} />
            <Stat label="Contribution" value={formatCurrency(data.contribution.contribution)} />
            <Stat label="Margin" value={data.contribution.margin_pct !== null ? `${(data.contribution.margin_pct * 100).toFixed(1)}%` : 'N/A'} />
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Recommended Range</p>
            {data.recommendation.low !== null ? (
              <>
                <p className="text-lg font-semibold text-foreground">
                  {formatCurrency(data.recommendation.low)} – {formatCurrency(data.recommendation.high!)}
                </p>
                <ul className="mt-1 list-inside list-disc text-xs text-muted-foreground">
                  {data.recommendation.reasoning.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">{data.recommendation.reasoning[0]}</p>
            )}
          </div>
          {data.observations.length > 0 && (
            <div>
              <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Competitor Observations</p>
              <div className="flex flex-wrap gap-1.5">
                {data.observations.map((o) => (
                  <Badge key={o.id} variant="outline" className="normal-case">
                    {o.competitor}: {formatCurrency(o.price)}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Price Simulator</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex gap-2">
            <Input value={simPrice} onChange={(e) => setSimPrice(e.target.value)} placeholder="New price, e.g. 19.99" className="max-w-40" />
            <Button
              size="sm"
              disabled={simulate.isPending || !simPrice}
              onClick={() => simulate.mutate({ productId, newPrice: Number(simPrice), adSpendLevels: [0, 1, 2] })}
            >
              Simulate
            </Button>
          </div>
          {simulate.data && (
            <div className="rounded-lg border border-border p-3 text-sm">
              <StatusBadge status="SYNTHETIC" />
              <p className="mt-2 text-xs text-muted-foreground">This is a scenario simulation, not a sales forecast.</p>
              <pre className="mt-2 overflow-x-auto text-xs text-muted-foreground">{JSON.stringify(simulate.data, null, 2)}</pre>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Decision</CardTitle></CardHeader>
        <CardContent>
          <DecisionRow
            pending={approve.isPending}
            onApprove={() => approve.mutate({ productId, body: approveBody('approved', 'price_range') })}
            onReject={() => approve.mutate({ productId, body: approveBody('rejected', 'price_range') })}
            onMoreResearch={() => approve.mutate({ productId, body: approveBody('more_research_requested', 'price_range') })}
          />
          {approve.isSuccess && <p className="mt-2 text-xs text-success">Decision recorded.</p>}
        </CardContent>
      </Card>
    </div>
  )
}

// ------------------------------------------------------------------- Review

function ReviewsTab({ productId }: { productId: string }) {
  const { data, isLoading, isError, refetch } = useReviewIntelligence(productId)
  const analyze = useReviewAnalyze()
  const approve = useReviewApprove()

  if (isError) return <ErrorState description="No review data available." onRetry={() => refetch()} />
  if (isLoading || !data) return <CardSkeleton lines={5} />

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Reviews — {data.rating_stats.avg_rating ?? 'N/A'} ★ ({data.rating_stats.total_reviews})</CardTitle>
          <Button size="sm" onClick={() => analyze.mutate(productId)} disabled={analyze.isPending}>
            {analyze.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
            Analyze
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Stat label="Negative %" value={`${data.rating_stats.negative_pct ?? 0}%`} />
            <Stat label="30d Velocity" value={data.velocity.trend} />
            <Stat label="Current / Prev" value={`${data.velocity.current_count} / ${data.velocity.previous_count}`} />
            <Stat label="Total Available" value={String(data.total_reviews_available)} />
          </div>

          {data.emerging_issues.length > 0 && (
            <div className="rounded-lg border border-danger/30 bg-danger/5 p-3">
              <p className="text-xs font-semibold uppercase text-danger">Emerging Issues</p>
              {data.emerging_issues.map((e, i) => (
                <p key={i} className="mt-1 text-sm text-foreground">{e.explanation}</p>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-2">
            {data.themes.slice(0, 5).map((t) => (
              <div key={t.theme} className="rounded-lg border border-border p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-foreground">{titleCase(t.theme)}</span>
                  <span className="text-xs text-muted-foreground">
                    {t.mentions} mentions · {t.negative} negative / {t.positive} positive
                  </span>
                </div>
                {t.evidence[0] && <p className="mt-1 text-xs italic text-muted-foreground">"{t.evidence[0].review_text}"</p>}
              </div>
            ))}
          </div>

          {analyze.data?.ai_summary && (
            <div className="rounded-lg border border-border bg-muted/40 p-3 text-sm">
              {analyze.data.ai_summary.available ? (
                <>
                  <p className="text-foreground">{String(analyze.data.ai_summary.data?.sentiment_summary ?? '')}</p>
                  <p className="mt-1 text-muted-foreground">
                    Suggested: {String(analyze.data.ai_summary.data?.suggested_investigation ?? '')}
                  </p>
                </>
              ) : (
                <p className="text-muted-foreground">{analyze.data.ai_summary.message}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Decision</CardTitle></CardHeader>
        <CardContent>
          <DecisionRow
            pending={approve.isPending}
            onApprove={() => approve.mutate({ productId, body: approveBody('approved', 'review_theme') })}
            onReject={() => approve.mutate({ productId, body: approveBody('rejected', 'review_theme') })}
            onMoreResearch={() => approve.mutate({ productId, body: approveBody('more_research_requested', 'review_theme') })}
          />
          {approve.isSuccess && <p className="mt-2 text-xs text-success">Decision recorded.</p>}
        </CardContent>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------- Inventory

function InventoryTab({ productId }: { productId: string }) {
  const { data, isLoading, isError, refetch } = useInventoryIntelligence(productId)
  const analyze = useInventoryAnalyze()
  const simulate = useInventorySimulate()
  const approve = useInventoryApprove()
  const [reorderQty, setReorderQty] = useState('')

  if (isError) return <ErrorState description="No inventory data available." onRetry={() => refetch()} />
  if (isLoading || !data) return <CardSkeleton lines={5} />

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Inventory — {data.category.replace(/_/g, ' ')}</CardTitle>
          <Button size="sm" onClick={() => analyze.mutate(productId)} disabled={analyze.isPending}>
            {analyze.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
            Analyze
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Stat label="Current Inventory" value={String(data.current_inventory)} />
            <Stat label="Days of Cover" value={data.days_of_cover !== null ? String(data.days_of_cover) : 'N/A'} />
            <Stat label="Reorder Point" value={String(data.reorder_point)} />
            <Stat label="Suggested Reorder" value={String(data.suggested_reorder_quantity)} />
          </div>
          {data.projected_stockout_date && (
            <p className="text-sm text-danger">Projected stockout date: {data.projected_stockout_date}</p>
          )}
          {analyze.data?.ai_explanation && (
            <div className="rounded-lg border border-border bg-muted/40 p-3 text-sm">
              {analyze.data.ai_explanation.available ? (
                <div className="flex items-start justify-between gap-2">
                  <p className="text-foreground">{String(analyze.data.ai_explanation.data?.diagnosis ?? '')}</p>
                  <ConfidenceBadge confidence={(analyze.data.ai_explanation.data?.confidence as 'none' | 'low' | 'medium' | 'high') ?? 'none'} />
                </div>
              ) : (
                <p className="text-muted-foreground">{analyze.data.ai_explanation.message}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Reorder Scenario</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex gap-2">
            <Input value={reorderQty} onChange={(e) => setReorderQty(e.target.value)} placeholder="Reorder quantity, e.g. 500" className="max-w-48" />
            <Button
              size="sm"
              disabled={simulate.isPending || !reorderQty}
              onClick={() => simulate.mutate({ productId, reorderQuantity: Number(reorderQty) })}
            >
              Simulate
            </Button>
          </div>
          {simulate.data && (
            <div className="rounded-lg border border-border p-3 text-sm">
              <StatusBadge status="SYNTHETIC" />
              <p className="mt-2 text-xs text-muted-foreground">
                Post-replenishment inventory: {simulate.data.post_replenishment_inventory} · Days of cover after: {simulate.data.days_of_cover_after_replenishment ?? 'N/A'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Decision</CardTitle></CardHeader>
        <CardContent>
          <DecisionRow
            pending={approve.isPending}
            onApprove={() => approve.mutate({ productId, body: approveBody('approved', 'reorder_quantity') })}
            onReject={() => approve.mutate({ productId, body: approveBody('rejected', 'reorder_quantity') })}
            onMoreResearch={() => approve.mutate({ productId, body: approveBody('more_research_requested', 'reorder_quantity') })}
          />
          {approve.isSuccess && <p className="mt-2 text-xs text-success">Decision recorded.</p>}
        </CardContent>
      </Card>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border p-2 text-center">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold text-foreground">{value}</p>
    </div>
  )
}
