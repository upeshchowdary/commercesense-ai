import { CheckCircle2, ChevronDown, Gavel, MessageSquarePlus, XCircle } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { EmptyState } from '@/components/shared/EmptyState'
import { SeverityBadge } from '@/components/shared/SeverityBadge'
import { CardSkeleton } from '@/components/shared/Skeletons'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn, titleCase } from '@/lib/utils'
import { decisionLabel, findDecision } from '@/lib/decisions'
import { SIGNAL_TYPE_LABEL, signalRecommendation, signalSummary } from '@/lib/signalCopy'
import { useActivity } from '@/hooks/useActivity'
import { useDecision } from '@/hooks/useDecisions'
import { useProduct, useProducts } from '@/hooks/useProducts'
import { useSignals } from '@/hooks/useSignals'

export default function DecisionCenter() {
  const signals = useSignals()
  const activity = useActivity({ agent: 'human' })
  const decision = useDecision()

  const pending = useMemo(() => {
    return (signals.data ?? []).filter(
      (s) => !findDecision(activity.data, s.product_name ?? '', s.signal_type),
    )
  }, [signals.data, activity.data])

  const isLoading = signals.isLoading || activity.isLoading

  return (
    <AppShell title="Decision Center">
      <div className="flex flex-col gap-8">
        <section className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">Pending Recommendations</h2>
            <Badge variant={pending.length > 0 ? 'warning' : 'success'}>{pending.length} awaiting</Badge>
          </div>
          {isLoading ? (
            <CardSkeleton lines={4} />
          ) : pending.length === 0 ? (
            <EmptyState icon={Gavel} title="Nothing pending" description="Every detected signal has been reviewed." />
          ) : (
            <div className="flex flex-col gap-3">
              {pending.map((s) => (
                <Card key={s.id} className="flex flex-col gap-3 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <SeverityBadge severity={s.severity} />
                      <div>
                        <p className="text-sm font-semibold text-foreground">
                          {SIGNAL_TYPE_LABEL[s.signal_type]}
                        </p>
                        <Link to={`/products/${s.product_id}`} className="text-xs text-accent hover:underline">
                          {s.product_name}
                        </Link>
                      </div>
                    </div>
                    <StatusBadge status="SYNTHETIC" />
                  </div>
                  <p className="text-sm text-muted-foreground">{signalSummary(s)}</p>
                  <p className="text-xs text-muted-foreground">
                    <strong className="text-foreground">Recommendation:</strong>{' '}
                    {signalRecommendation(s.signal_type)}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      disabled={decision.isPending}
                      onClick={() =>
                        decision.mutate({
                          product_name: s.product_name ?? '',
                          category: s.signal_type,
                          decision: 'approved',
                        })
                      }
                    >
                      <CheckCircle2 className="size-3.5" />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={decision.isPending}
                      onClick={() =>
                        decision.mutate({
                          product_name: s.product_name ?? '',
                          category: s.signal_type,
                          decision: 'rejected',
                        })
                      }
                    >
                      <XCircle className="size-3.5" />
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={decision.isPending}
                      onClick={() =>
                        decision.mutate({
                          product_name: s.product_name ?? '',
                          category: s.signal_type,
                          decision: 'more_research_requested',
                        })
                      }
                    >
                      <MessageSquarePlus className="size-3.5" />
                      Request More Research
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold text-foreground">Decision Trace</h2>
          <DecisionTrace />
        </section>
      </div>
    </AppShell>
  )
}

function DecisionTrace() {
  const products = useProducts()
  const [productId, setProductId] = useState<string | undefined>(undefined)
  const product = useProduct(productId)

  const stages = useMemo(() => {
    if (!product.data) return []
    const p = product.data
    const researchEvents = p.activity.filter((e) => e.agent === 'research_agent')
    const insightEvents = p.activity.filter((e) => e.agent === 'insight_agent')
    const humanEvents = p.activity.filter((e) => e.agent === 'human')
    return [
      { label: 'Product', detail: `${p.name} (${p.category}, $${p.base_price})` },
      {
        label: 'Research',
        detail:
          researchEvents.length > 0
            ? `${researchEvents.length} research event(s) — most recent: ${titleCase(researchEvents[0].action)}`
            : 'No live research run yet',
      },
      {
        label: 'Cache State',
        detail: researchEvents.some((e) => e.action === 'cache_hit') ? 'Served from cache at least once' : 'No cache hits recorded',
      },
      {
        label: 'Insight',
        detail:
          insightEvents.length > 0
            ? `${insightEvents.length} insight event(s) — most recent: ${titleCase(insightEvents[0].action)}`
            : 'No insight generated yet',
      },
      {
        label: 'Signal',
        detail: p.signals.length > 0 ? `${p.signals.length} synthetic signal(s) detected` : 'No signals detected',
      },
      {
        label: 'Evidence',
        detail: 'See the Evidence tab on the product page for cited findings',
      },
      {
        label: 'Recommendation',
        detail: p.signals[0] ? signalRecommendation(p.signals[0].signal_type) : 'No recommendation yet',
      },
      {
        label: 'Human Decision',
        detail:
          humanEvents.length > 0
            ? `${humanEvents.length} decision(s) recorded — latest: ${decisionLabel(humanEvents[0].action)}`
            : 'No human decision recorded yet',
      },
    ]
  }, [product.data])

  return (
    <Card className="flex flex-col gap-4 p-5">
      <Select value={productId} onValueChange={setProductId}>
        <SelectTrigger className="w-full sm:w-80">
          <SelectValue placeholder="Select a product to trace…" />
        </SelectTrigger>
        <SelectContent>
          {(products.data ?? []).map((p) => (
            <SelectItem key={p.product_id} value={p.product_id}>
              {p.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {!productId ? (
        <EmptyState title="Pick a product to see its full decision trace" className="border-none py-8" />
      ) : product.isLoading ? (
        <CardSkeleton lines={6} />
      ) : (
        <ol className="flex flex-col">
          {stages.map((stage, i) => (
            <TraceStage key={stage.label} index={i} last={i === stages.length - 1} {...stage} />
          ))}
        </ol>
      )}
    </Card>
  )
}

function TraceStage({
  label,
  detail,
  index,
  last,
}: {
  label: string
  detail: string
  index: number
  last: boolean
}) {
  const [open, setOpen] = useState(false)
  return (
    <li className="relative flex gap-3 pb-4">
      {!last && <span className="absolute left-[11px] top-6 h-[calc(100%-6px)] w-px bg-border" />}
      <div className="z-10 flex size-[22px] shrink-0 items-center justify-center rounded-full border border-primary/40 bg-panel text-[10px] font-semibold text-primary">
        {index + 1}
      </div>
      <div className="flex-1">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-2 text-left"
        >
          <span className="text-sm font-medium text-foreground">{label}</span>
          <ChevronDown className={cn('size-4 text-muted-foreground transition-transform', open && 'rotate-180')} />
        </button>
        {open && <p className="mt-1 max-w-md text-xs text-muted-foreground">{detail}</p>}
      </div>
    </li>
  )
}
