import { CheckCircle2, Clock, Gavel, Info, MessageSquarePlus, XCircle } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { SeverityBadge } from '@/components/shared/SeverityBadge'
import { CardSkeleton } from '@/components/shared/Skeletons'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { decisionLabel, decisionTone, findDecision } from '@/lib/decisions'
import { SIGNAL_TYPE_LABEL, signalRecommendation, signalSummary, signalWhyItMatters } from '@/lib/signalCopy'
import { formatDateTime, titleCase } from '@/lib/utils'
import { useActivity } from '@/hooks/useActivity'
import { useDecision } from '@/hooks/useDecisions'
import { useSignal } from '@/hooks/useSignals'

export default function SignalDetail() {
  const { signalId } = useParams<{ signalId: string }>()
  const id = signalId ? Number(signalId) : undefined
  const { data: signal, isLoading, isError, refetch } = useSignal(id)
  const activity = useActivity({ product_name: signal?.product_name })
  const decision = useDecision()
  const [reason, setReason] = useState('')

  if (isError) {
    return (
      <AppShell title="Signal">
        <ErrorState description="Couldn't load this signal." onRetry={() => refetch()} />
      </AppShell>
    )
  }

  if (isLoading || !signal) {
    return (
      <AppShell title="Signal">
        <CardSkeleton lines={6} />
      </AppShell>
    )
  }

  const existingDecision = findDecision(activity.data, signal.product_name ?? '', signal.signal_type)

  return (
    <AppShell title={SIGNAL_TYPE_LABEL[signal.signal_type]}>
      <div className="mx-auto flex max-w-3xl flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <SeverityBadge severity={signal.severity} />
            <h2 className="text-xl font-semibold text-foreground">{SIGNAL_TYPE_LABEL[signal.signal_type]}</h2>
          </div>
          <Link
            to={`/products/${signal.product_id}`}
            className="text-sm font-medium text-accent hover:underline"
          >
            {signal.product_name} →
          </Link>
        </div>

        <Card className="p-5">
          <CardHeader className="p-0 pb-3">
            <CardTitle>Signal Summary</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 p-0">
            <p className="text-sm text-foreground">{signalSummary(signal)}</p>
            <span className="text-xs text-muted-foreground">
              Detected {formatDateTime(signal.detected_at)} · as of {signal.date}
            </span>
          </CardContent>
        </Card>

        <Card className="p-5">
          <CardHeader className="p-0 pb-3">
            <CardTitle>Why It Matters</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <p className="text-sm text-muted-foreground">{signalWhyItMatters(signal.signal_type)}</p>
          </CardContent>
        </Card>

        <Card className="p-5">
          <CardHeader className="flex-row items-center justify-between p-0 pb-3">
            <CardTitle>Evidence</CardTitle>
            <div className="flex items-center gap-2">
              <StatusBadge status="SYNTHETIC" />
              <span className="flex items-center gap-1 text-xs text-muted-foreground" title="Deterministic rule-based detector, not an AI judgment">
                <Info className="size-3" />
                Rule-based
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
              {Object.entries(signal.evidence).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between gap-3 border-b border-border py-1.5 text-sm sm:justify-start sm:gap-2">
                  <dt className="text-muted-foreground">{titleCase(key)}</dt>
                  <dd className="font-medium text-foreground">{String(value)}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <Card className="p-5">
          <CardHeader className="p-0 pb-3">
            <CardTitle>Recommendation</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <p className="text-sm text-muted-foreground">{signalRecommendation(signal.signal_type)}</p>
          </CardContent>
        </Card>

        <Card className="p-5">
          <CardHeader className="p-0 pb-3">
            <CardTitle>Decision</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 p-0">
            {existingDecision ? (
              <div className="flex items-center gap-3">
                <Badge variant={decisionTone(existingDecision.action)}>
                  {decisionLabel(existingDecision.action)}
                </Badge>
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="size-3" />
                  {formatDateTime(existingDecision.timestamp)}
                </span>
              </div>
            ) : (
              <>
                <Input
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Reason (optional)"
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    disabled={decision.isPending}
                    onClick={() =>
                      decision.mutate({
                        product_name: signal.product_name ?? '',
                        category: signal.signal_type,
                        decision: 'approved',
                        reason: reason || undefined,
                      })
                    }
                  >
                    <CheckCircle2 className="size-4" />
                    Approve
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={decision.isPending}
                    onClick={() =>
                      decision.mutate({
                        product_name: signal.product_name ?? '',
                        category: signal.signal_type,
                        decision: 'rejected',
                        reason: reason || undefined,
                      })
                    }
                  >
                    <XCircle className="size-4" />
                    Reject
                  </Button>
                  <Button
                    variant="outline"
                    disabled={decision.isPending}
                    onClick={() =>
                      decision.mutate({
                        product_name: signal.product_name ?? '',
                        category: signal.signal_type,
                        decision: 'more_research_requested',
                        reason: reason || undefined,
                      })
                    }
                  >
                    <MessageSquarePlus className="size-4" />
                    Request More Research
                  </Button>
                </div>
                {decision.isSuccess && (
                  <p className="text-xs text-success">Decision recorded.</p>
                )}
                {decision.isError && <p className="text-xs text-danger">Couldn't record the decision.</p>}
              </>
            )}
          </CardContent>
        </Card>

        {!signal.product_name && (
          <EmptyState icon={Gavel} title="No product context" description="This signal has no linked product name." />
        )}
      </div>
    </AppShell>
  )
}
