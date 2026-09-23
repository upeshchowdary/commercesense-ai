import {
  CheckCircle2,
  ExternalLink,
  Loader2,
  Sparkles,
  XCircle,
} from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ConfidenceBadge } from '@/components/shared/ConfidenceBadge'
import { SeverityBadge } from '@/components/shared/SeverityBadge'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { SIGNAL_TYPE_LABEL, signalRecommendation, signalSummary } from '@/lib/signalCopy'
import { cn } from '@/lib/utils'
import { useDecision } from '@/hooks/useDecisions'
import { useIntelligence } from '@/hooks/useIntelligence'
import { useProducts } from '@/hooks/useProducts'
import { useResearch } from '@/hooks/useResearch'
import { useRunSignalDetection, useSignals } from '@/hooks/useSignals'

const DEFAULT_PRODUCT = 'Bamboo Cutting Board Set'
const STEP_LABELS = [
  'Product Selected',
  'Research',
  'Evidence',
  'Insight',
  'Signal',
  'Recommendation',
  'Human Decision',
]

export function DemoMode({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const [productName, setProductName] = useState(DEFAULT_PRODUCT)
  const [step, setStep] = useState(0)
  const products = useProducts()
  const research = useResearch()
  const intelligence = useIntelligence()
  const signals = useSignals()
  const runDetection = useRunSignalDetection()
  const decision = useDecision()
  const triggered = useRef(new Set<number>())

  const productSignal = (signals.data ?? []).find((s) => s.product_name === productName)

  useEffect(() => {
    if (!open) {
      setStep(0)
      triggered.current.clear()
      research.reset()
      intelligence.reset()
      decision.reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    if (step === 1 && !triggered.current.has(1)) {
      triggered.current.add(1)
      research.mutate({ product_name: productName, use_cache: true })
    }
    if (step === 3 && !triggered.current.has(3)) {
      triggered.current.add(3)
      intelligence.mutate({ product_name: productName, use_cache: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step])

  function next() {
    setStep((s) => Math.min(s + 1, STEP_LABELS.length - 1))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle>Guided Demo</DialogTitle>
            <StatusBadge status="DEMO" />
          </div>
        </DialogHeader>

        <div className="flex flex-wrap gap-1.5">
          {STEP_LABELS.map((label, i) => (
            <Badge key={label} variant={i === step ? 'default' : i < step ? 'success' : 'secondary'}>
              {i + 1}. {label}
            </Badge>
          ))}
        </div>

        <div className="min-h-[220px]">
          {step === 0 && (
            <div className="flex flex-col gap-4">
              <p className="text-sm text-muted-foreground">
                Pick a synthetic product. Its real name is used for live research too, so LIVE and SYNTHETIC
                data naturally coexist on the same product without ever computationally mixing.
              </p>
              <Select value={productName} onValueChange={setProductName}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(products.data ?? []).map((p) => (
                    <SelectItem key={p.product_id} value={p.name}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {step === 1 && (
            <StepBody
              loading={research.isPending}
              loadingLabel={`Researching "${productName}" live…`}
              done={research.isSuccess}
            >
              {research.data && (
                <div className="flex flex-col gap-2">
                  <StatusBadge status={research.data.cache_hit ? 'CACHED' : 'LIVE'} />
                  <p className="text-sm text-muted-foreground">
                    {research.data.bundle.findings.length} source(s) found across{' '}
                    {research.data.bundle.search_queries_used.length} queries.
                  </p>
                </div>
              )}
            </StepBody>
          )}

          {step === 2 && (
            <div className="flex max-h-64 flex-col gap-2 overflow-y-auto">
              {(research.data?.bundle.findings ?? []).map((f, i) => (
                <div key={i} className="rounded-lg border border-border p-3 text-sm">
                  <p className="text-foreground">{f.snippet}</p>
                  {f.source_url && (
                    <a
                      href={f.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 flex items-center gap-1 text-xs text-accent hover:underline"
                    >
                      {f.source_url} <ExternalLink className="size-3" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}

          {step === 3 && (
            <StepBody
              loading={intelligence.isPending}
              loadingLabel="Generating grounded insight…"
              done={intelligence.isSuccess}
            >
              {intelligence.data && (
                <div className="grid grid-cols-2 gap-2">
                  {intelligence.data.report.insights.map((ins) => (
                    <div key={ins.category} className="rounded-lg border border-border p-2.5 text-xs">
                      <div className="mb-1 flex items-center justify-between">
                        <span className="font-medium capitalize text-foreground">{ins.category}</span>
                        <ConfidenceBadge confidence={ins.confidence} />
                      </div>
                      <p className="text-muted-foreground">{ins.summary ?? 'No reliable data found.'}</p>
                    </div>
                  ))}
                </div>
              )}
            </StepBody>
          )}

          {step === 4 && (
            <div className="flex flex-col gap-3">
              <StatusBadge status="SYNTHETIC" />
              {productSignal ? (
                <div className="flex flex-col gap-2 rounded-lg border border-border p-3">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={productSignal.severity} />
                    <span className="text-sm font-medium text-foreground">
                      {SIGNAL_TYPE_LABEL[productSignal.signal_type]}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{signalSummary(productSignal)}</p>
                </div>
              ) : signals.data ? (
                <div className="flex flex-col gap-2">
                  <p className="text-sm text-muted-foreground">
                    No signal on record for this product yet.
                  </p>
                  <Button
                    size="sm"
                    className="w-fit"
                    onClick={() => runDetection.mutate()}
                    disabled={runDetection.isPending}
                  >
                    {runDetection.isPending && <Loader2 className="size-3.5 animate-spin" />}
                    Run signal detection
                  </Button>
                </div>
              ) : (
                <Loader2 className="size-4 animate-spin text-muted-foreground" />
              )}
            </div>
          )}

          {step === 5 && (
            <p className="text-sm text-muted-foreground">
              {productSignal
                ? signalRecommendation(productSignal.signal_type)
                : 'No signal detected for this product — no action needed right now.'}
            </p>
          )}

          {step === 6 && (
            <div className="flex flex-col gap-3">
              {decision.isSuccess ? (
                <p className="flex items-center gap-2 text-sm text-success">
                  <CheckCircle2 className="size-4" /> Decision recorded. See it on the Product or Decision
                  Center page.
                </p>
              ) : (
                <div className="flex gap-2">
                  <Button
                    disabled={decision.isPending || !productSignal}
                    onClick={() =>
                      productSignal &&
                      decision.mutate({
                        product_name: productName,
                        category: productSignal.signal_type,
                        decision: 'approved',
                        decided_by: 'Demo',
                      })
                    }
                  >
                    <CheckCircle2 className="size-4" /> Approve
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={decision.isPending || !productSignal}
                    onClick={() =>
                      productSignal &&
                      decision.mutate({
                        product_name: productName,
                        category: productSignal.signal_type,
                        decision: 'rejected',
                        decided_by: 'Demo',
                      })
                    }
                  >
                    <XCircle className="size-4" /> Reject
                  </Button>
                </div>
              )}
              {!productSignal && !decision.isSuccess && (
                <p className="text-xs text-muted-foreground">
                  No signal was detected for this product, so there's nothing to decide on — try a product
                  with a planted issue, e.g. {DEFAULT_PRODUCT}.
                </p>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-border pt-4">
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <div className="flex gap-2">
            {step > 0 && (
              <Button variant="outline" size="sm" onClick={() => setStep((s) => s - 1)}>
                Back
              </Button>
            )}
            {step < STEP_LABELS.length - 1 ? (
              <Button
                size="sm"
                onClick={next}
                disabled={
                  (step === 1 && !research.isSuccess) ||
                  (step === 3 && !intelligence.isSuccess)
                }
              >
                Next
              </Button>
            ) : (
              <Button size="sm" asChild>
                <Link to={`/products/${(products.data ?? []).find((p) => p.name === productName)?.product_id ?? ''}`}>
                  <Sparkles className="size-3.5" />
                  View Product
                </Link>
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function StepBody({
  loading,
  loadingLabel,
  done,
  children,
}: {
  loading: boolean
  loadingLabel: string
  done: boolean
  children: ReactNode
}) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        {loadingLabel}
      </div>
    )
  }
  return <div className={cn(!done && 'text-sm text-muted-foreground')}>{done ? children : 'Waiting…'}</div>
}
