// Shared Listing/Pricing/Reviews/Inventory tab bodies (spec §28.2's
// per-product tabs AND §28's Product Bundle View reuse the exact same
// components — one implementation, not two competing UIs). Rendered by
// both pages/ProductIntelligence.tsx (the full bundle view) and
// pages/ProductDetail.tsx (inline tabs on the main product page).
import { CheckCircle2, Loader2, MessageSquarePlus, RefreshCw, Sparkles, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ConfidenceBadge } from '@/components/shared/ConfidenceBadge'
import { ErrorState } from '@/components/shared/ErrorState'
import { CardSkeleton } from '@/components/shared/Skeletons'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { InventoryForecastChart } from '@/components/charts/InventoryForecastChart'
import { WhyPanel, AlternativesPanel } from '@/components/shared/WhyPanel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { formatCurrency, formatCurrencyOrNA, formatPercent, titleCase } from '@/lib/utils'
import type { IntelligenceApproveRequest } from '@/lib/types'
import {
  useInventoryAnalyze,
  useInventoryApprove,
  useInventoryForecast,
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
  useReviewAnalyze,
  useReviewApprove,
  useReviewIntelligence,
} from '@/hooks/useIntelligenceModules'

export function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <Badge variant="secondary">No data</Badge>
  const variant = score >= 80 ? 'success' : score >= 60 ? 'warning' : 'danger'
  return <Badge variant={variant}>{score}/100</Badge>
}

export function DecisionRow({
  onApprove, onReject, onMoreResearch, pending, isError, errorMessage, recordedAction,
}: {
  onApprove: () => void
  onReject: () => void
  onMoreResearch: () => void
  pending: boolean
  isError?: boolean
  errorMessage?: string
  /** Set after a successful decision, e.g. "Approved" -- disables repeat
   * clicks until the underlying data refetches and this goes away. */
  recordedAction?: string | null
}) {
  const disabled = pending || !!recordedAction
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={disabled} onClick={onApprove}>
          <CheckCircle2 className="size-3.5" /> Approve
        </Button>
        <Button size="sm" variant="destructive" disabled={disabled} onClick={onReject}>
          <XCircle className="size-3.5" /> Reject
        </Button>
        <Button size="sm" variant="outline" disabled={disabled} onClick={onMoreResearch}>
          <MessageSquarePlus className="size-3.5" /> Request More Research
        </Button>
      </div>
      {recordedAction && <p className="text-sm text-success">{recordedAction} · recorded</p>}
      {isError && <p className="text-sm text-danger">{errorMessage ?? 'Could not record this decision.'}</p>}
    </div>
  )
}

export function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border p-2 text-center">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold text-foreground">{value}</p>
    </div>
  )
}

/** Simulator inputs are free text (users paste "$16.99" or leave stray
 * whitespace); Number("$16.99") is NaN, which used to get sent as JSON
 * null and silently 422 with no rendered error. Strips currency
 * formatting and requires a finite, positive result. */
function parsePositiveNumber(raw: string): number | null {
  const n = parseFloat(raw.replace(/[$,\s]/g, ''))
  return Number.isFinite(n) && n > 0 ? n : null
}

function approveBody(decision: IntelligenceApproveRequest['decision'], field?: string): IntelligenceApproveRequest {
  return { decision, field, decided_by: 'Demo User' }
}

const DECISION_RECORDED_LABEL: Record<IntelligenceApproveRequest['decision'], string> = {
  approved: 'Approved',
  rejected: 'Rejected',
  more_research_requested: 'More research requested',
}

/** For DecisionRow's recordedAction/isError props: a mutation's own
 * .variables/.error, keyed to the module-specific approve() signature
 * every *Approve hook shares ({ productId, body }). */
function decisionRowProps(approve: {
  isSuccess: boolean
  isError: boolean
  error: unknown
  variables?: { body: IntelligenceApproveRequest }
}) {
  return {
    recordedAction: approve.isSuccess ? DECISION_RECORDED_LABEL[approve.variables!.body.decision] : null,
    isError: approve.isError,
    errorMessage: approve.error instanceof Error ? approve.error.message : undefined,
  }
}

// ------------------------------------------------------------------ Listing

export function ListingTab({ productId }: { productId: string }) {
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
          {(data.failed_rules.length > 0 || data.warnings.length > 0) && (
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
                    {['top_issue_1', 'top_issue_2', 'top_issue_3']
                      .map((k) => String(analyze.data!.ai_diagnosis!.data?.[k] ?? '').trim())
                      .filter(Boolean)
                      .map((issue) => (
                        <li key={issue}>{issue}</li>
                      ))}
                  </ul>
                </>
              ) : (
                <p className="text-muted-foreground">{analyze.data.ai_diagnosis.message}</p>
              )}
            </div>
          )}
          <WhyPanel
            what={`Listing Health Score is ${data.score}/100, built from ${Object.keys(data.category_scores).length} weighted categories (CommerceSense heuristic, not an official Amazon score).`}
            why="A weak score means the listing is more likely to under-convert or be harder for shoppers to find — even if the product itself is fine."
            evidence={data.failed_rules.length > 0 ? `Failed checks: ${data.failed_rules.join(', ')}` : 'No failed checks — only warnings, if any, apply.'}
            calculation={`Category scores: ${Object.entries(data.category_scores).map(([k, v]) => `${titleCase(k)} ${v}`).join(', ')}.`}
            ifNothing="The listing keeps whatever discoverability/conversion drag these failed checks cause."
            proposedAction="Use Propose Rewrite below for a grounded title revision, or address the failed checks directly."
          />
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
            {...decisionRowProps(approve)}
          />
        </CardContent>
      </Card>
    </div>
  )
}

// ------------------------------------------------------------------ Pricing

export function PricingTab({ productId }: { productId: string }) {
  const { data, isLoading, isError, refetch } = usePricingIntelligence(productId)
  const analyze = usePricingAnalyze()
  const simulate = usePricingSimulate()
  const approve = usePricingApprove()
  const [simPrice, setSimPrice] = useState('')
  const [simPriceError, setSimPriceError] = useState<string | null>(null)

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
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Recommended Range</p>
              {data.recommendation.confidence !== 'none' && (
                <ConfidenceBadge confidence={data.recommendation.confidence as 'low' | 'medium' | 'high'} />
              )}
            </div>
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
          {analyze.data?.ai_explanation && (
            <div className="rounded-lg border border-border bg-muted/40 p-3 text-sm">
              {analyze.data.ai_explanation.available ? (
                <div className="flex flex-col gap-1.5">
                  <p className="text-foreground">{String(analyze.data.ai_explanation.data?.interpretation ?? '')}</p>
                  <p className="text-muted-foreground">{String(analyze.data.ai_explanation.data?.trade_offs ?? '')}</p>
                </div>
              ) : (
                <p className="text-muted-foreground">{analyze.data.ai_explanation.message}</p>
              )}
            </div>
          )}
          {data.observations.length > 0 && (
            <div>
              <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Competitor Observations</p>
              <div className="flex flex-wrap gap-1.5">
                {data.observations.map((o) => (
                  <Badge key={o.id} variant="outline" className="normal-case">
                    {o.competitor}: {formatCurrency(o.price)} ({o.is_verified ? 'verified' : 'observed on web'})
                  </Badge>
                ))}
              </div>
              {data.observations.length > 1 && (
                <p className="mt-1.5 text-xs text-muted-foreground">
                  {data.observations.length} observed prices, median {formatCurrencyOrNA(data.price_distribution.median)} —
                  shown as a range, not a single silently-chosen number.
                </p>
              )}
            </div>
          )}
          <WhyPanel
            what={`Price state is ${data.price_state.replace(/_/g, ' ').toLowerCase()} at a current price of ${formatCurrency(data.current_price)}.`}
            why="Margin, competitor position, and inventory health together determine whether this price is sustainable — not competitor price alone."
            evidence={data.observations.length > 0 ? `${data.observations.length} competitor observation(s), median ${formatCurrencyOrNA(data.price_distribution.median)}.` : 'No competitor observations on file yet.'}
            calculation={`Contribution ${formatCurrency(data.contribution.contribution)} = price − variable cost. Breakeven ${formatCurrencyOrNA(data.breakeven_price)}. Target-margin price ${formatCurrencyOrNA(data.target_margin_price)}.`}
            ifNothing={data.price_state === 'BELOW_MARGIN_FLOOR' ? 'Every unit sold continues to erode margin below the target floor.' : 'Price stays as-is; no immediate financial exposure detected from this data.'}
            proposedAction={data.recommendation.low !== null ? `Consider a price in ${formatCurrency(data.recommendation.low)}–${formatCurrency(data.recommendation.high!)}.` : 'Gather more cost/competitor data before recommending a change.'}
          />
          <AlternativesPanel
            options={[
              { label: 'Keep current price', detail: `Stays at ${formatCurrency(data.current_price)}. No pricing action taken.` },
              { label: 'Reduce toward competitive median', detail: data.price_distribution.median !== null ? `Move toward ${formatCurrency(data.price_distribution.median)} (observed median).` : 'No competitor median available to reduce toward.' },
              { label: 'Increase toward target margin', detail: `Move toward ${formatCurrency(data.target_margin_price ?? data.current_price)} (target-margin price).` },
            ]}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Price Simulator</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex gap-2">
            <Input
              type="number" min="0.01" step="0.01"
              value={simPrice} onChange={(e) => setSimPrice(e.target.value)}
              placeholder="New price, e.g. 19.99" className="max-w-40"
            />
            <Button
              size="sm"
              disabled={simulate.isPending || !simPrice}
              onClick={() => {
                const price = parsePositiveNumber(simPrice)
                if (price === null) {
                  setSimPriceError('Enter a price greater than 0.')
                  return
                }
                setSimPriceError(null)
                simulate.mutate({ productId, newPrice: price, adSpendLevels: [0, 1, 2] })
              }}
            >
              Simulate
            </Button>
          </div>
          {simPriceError && <p className="text-sm text-danger">{simPriceError}</p>}
          {simulate.isError && (
            <p className="text-sm text-danger">{simulate.error instanceof Error ? simulate.error.message : 'Simulation failed.'}</p>
          )}
          {simulate.data && (
            <div className="rounded-lg border border-border p-3 text-sm">
              <StatusBadge status="SYNTHETIC" />
              <p className="mt-2 text-xs text-muted-foreground">This is a scenario simulation, not a sales forecast.</p>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <div><p className="text-xs text-muted-foreground">Price</p><p className="font-semibold">{formatCurrency(simulate.data.price)}</p></div>
                <div><p className="text-xs text-muted-foreground">Contribution / unit</p><p className={`font-semibold ${simulate.data.base.contribution < 0 ? 'text-destructive' : ''}`}>{formatCurrency(simulate.data.base.contribution)}</p></div>
                <div><p className="text-xs text-muted-foreground">Margin</p><p className="font-semibold">{formatPercent(simulate.data.base.margin_pct, 1)}</p></div>
              </div>
              {simulate.data.ad_spend_scenarios.length > 0 && (
                <table className="mt-3 w-full text-xs">
                  <thead className="text-muted-foreground">
                    <tr><th className="text-left font-medium">Ad cost / unit</th><th className="text-right font-medium">Variable cost</th><th className="text-right font-medium">Contribution</th><th className="text-right font-medium">Margin</th></tr>
                  </thead>
                  <tbody>
                    {simulate.data.ad_spend_scenarios.map((s) => (
                      <tr key={s.ad_cost_per_unit ?? 0} className="border-t border-border">
                        <td className="py-1">{formatCurrency(s.ad_cost_per_unit ?? 0)}</td>
                        <td className="py-1 text-right">{formatCurrency(s.variable_cost)}</td>
                        <td className={`py-1 text-right ${s.contribution < 0 ? 'text-destructive' : ''}`}>{formatCurrency(s.contribution)}</td>
                        <td className="py-1 text-right">{formatPercent(s.margin_pct, 1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
            onApprove={() => approve.mutate({ productId, body: approveBody('approved', 'price_range') })}
            onReject={() => approve.mutate({ productId, body: approveBody('rejected', 'price_range') })}
            onMoreResearch={() => approve.mutate({ productId, body: approveBody('more_research_requested', 'price_range') })}
            {...decisionRowProps(approve)}
          />
        </CardContent>
      </Card>
    </div>
  )
}

// ------------------------------------------------------------------- Review

export function ReviewsTab({ productId }: { productId: string }) {
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
            <Stat
              label="30d Velocity"
              value={
                data.velocity.pct_change !== null
                  ? `${titleCase(data.velocity.trend)} (${data.velocity.pct_change >= 0 ? '+' : ''}${data.velocity.pct_change.toFixed(1)}%)`
                  : titleCase(data.velocity.trend)
              }
            />
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

          {data.semantic_themes_available && (
            <div>
              <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
                Semantic Clusters <Badge variant="outline" className="ml-1 normal-case">local ML, optional</Badge>
              </p>
              <div className="flex flex-col gap-1.5">
                {data.semantic_themes.map((c, i) => (
                  <div key={i} className="rounded-lg border border-border p-2 text-xs">
                    <span className="font-medium text-foreground">{titleCase(c.cluster_label)}</span>
                    <span className="ml-2 text-muted-foreground">{c.size} reviews · avg {c.avg_rating}★</span>
                  </div>
                ))}
              </div>
            </div>
          )}

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
          <WhyPanel
            what={`Average rating ${data.rating_stats.avg_rating ?? 'N/A'}★ across ${data.rating_stats.total_reviews} reviews; ${data.emerging_issues.length} emerging issue(s) detected.`}
            why="A stable average rating can hide a fast-rising specific complaint — trend and theme data catch what the headline number doesn't."
            evidence={data.themes[0] ? `Top theme "${data.themes[0].theme}": ${data.themes[0].mentions} mentions (${data.themes[0].negative} negative).` : 'No theme mentions found in the available review text.'}
            calculation={`Velocity: ${data.velocity.current_count} reviews this window vs ${data.velocity.previous_count} previous (${data.velocity.trend}).`}
            ifNothing={data.emerging_issues.length > 0 ? 'The emerging complaint keeps accumulating unaddressed.' : 'No emerging issue currently requires action.'}
            proposedAction={data.emerging_issues.length > 0 ? `Investigate "${data.emerging_issues[0].theme}".` : 'Continue routine monitoring.'}
          />
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
            {...decisionRowProps(approve)}
          />
        </CardContent>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------- Inventory

export function InventoryTab({ productId }: { productId: string }) {
  const { data, isLoading, isError, refetch } = useInventoryIntelligence(productId)
  const analyze = useInventoryAnalyze()
  const simulate = useInventorySimulate()
  const forecast = useInventoryForecast()
  const approve = useInventoryApprove()
  const [reorderQty, setReorderQty] = useState('')
  const [reorderQtyError, setReorderQtyError] = useState<string | null>(null)

  // Deterministic/SYNTHETIC, no LLM or external call -- safe to load on
  // mount, same as the rest of this tab's data.
  useEffect(() => {
    forecast.mutate({ productId, daysAhead: 30 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId])

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
            <Stat label="Current Inventory" value={`${Math.ceil(data.current_inventory)} units`} />
            <Stat label="Days of Cover" value={data.days_of_cover !== null ? String(data.days_of_cover) : 'N/A'} />
            <Stat label="Reorder Point" value={`${Math.ceil(data.reorder_point)} units`} />
            <Stat label="Suggested Reorder" value={`${Math.ceil(data.suggested_reorder_quantity)} units`} />
          </div>
          {data.current_inventory <= 0 ? (
            <p className="rounded-md bg-danger/10 px-3 py-2 text-sm font-semibold text-danger">Out of stock now</p>
          ) : (
            data.projected_stockout_date && (
              <p className="text-sm text-danger">Projected stockout date: {data.projected_stockout_date}</p>
            )
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
          <WhyPanel
            what={`Category ${data.category.replace(/_/g, ' ').toLowerCase()}, ${data.days_of_cover ?? 'N/A'} days of cover remaining.`}
            why="Days of cover below lead time means a stockout is likely before a reorder can arrive — lost sales and rank damage follow."
            evidence={`Weighted average daily demand: ${data.demand.weighted_avg}. Current inventory: ${data.current_inventory}.`}
            calculation={`Reorder point ${Math.ceil(data.reorder_point)} units = lead-time demand + safety stock (${Math.ceil(data.safety_stock)} units). Suggested reorder ${Math.ceil(data.suggested_reorder_quantity)} units = target stock − projected available.`}
            ifNothing={
              data.current_inventory <= 0
                ? 'Already out of stock — every day without a reorder is lost sales.'
                : data.projected_stockout_date
                  ? `Projected stockout around ${data.projected_stockout_date} if nothing changes.`
                  : 'No stockout currently projected from this data.'
            }
            proposedAction={`Consider reordering ${data.suggested_reorder_quantity} units.`}
          />
          <AlternativesPanel
            options={[
              { label: 'Do nothing', detail: 'No reorder placed. Risk accepted as-is.' },
              { label: `Order suggested quantity (${data.suggested_reorder_quantity})`, detail: 'Matches the deterministic reorder-point calculation above.' },
              { label: 'Order a larger batch', detail: 'Reduces reorder frequency but increases holding cost/overstock risk — test in the simulator below.' },
            ]}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>30-Day Inventory Forecast</CardTitle>
          <StatusBadge status="SYNTHETIC" />
        </CardHeader>
        <CardContent>
          {forecast.isPending && !forecast.data ? (
            <CardSkeleton lines={4} />
          ) : (
            <InventoryForecastChart rows={forecast.data?.rows ?? []} reorderPoint={data.reorder_point} />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Reorder Scenario</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex gap-2">
            <Input
              type="number" min="1" step="1"
              value={reorderQty} onChange={(e) => setReorderQty(e.target.value)}
              placeholder="Reorder quantity, e.g. 500" className="max-w-48"
            />
            <Button
              size="sm"
              disabled={simulate.isPending || !reorderQty}
              onClick={() => {
                const qty = parsePositiveNumber(reorderQty)
                if (qty === null) {
                  setReorderQtyError('Enter a quantity greater than 0.')
                  return
                }
                setReorderQtyError(null)
                const roundedQty = Math.round(qty)
                simulate.mutate({ productId, reorderQuantity: roundedQty })
                // Re-run the forecast with this reorder arriving after
                // the configured lead time, so the chart shows its
                // effect on the projected stockout.
                forecast.mutate({
                  productId, daysAhead: 30,
                  inbound: [{ day_offset: data.config.lead_time_days, quantity: roundedQty }],
                })
              }}
            >
              Simulate
            </Button>
          </div>
          {reorderQtyError && <p className="text-sm text-danger">{reorderQtyError}</p>}
          {simulate.isError && (
            <p className="text-sm text-danger">{simulate.error instanceof Error ? simulate.error.message : 'Simulation failed.'}</p>
          )}
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
            {...decisionRowProps(approve)}
          />
        </CardContent>
      </Card>
    </div>
  )
}
