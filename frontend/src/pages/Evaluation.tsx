import { FlaskConical } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { KpiSkeleton } from '@/components/shared/Skeletons'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { SIGNAL_TYPE_LABEL } from '@/lib/signalCopy'
import { useEvaluation } from '@/hooks/useEvaluation'
import type { SignalType } from '@/lib/types'

export default function Evaluation() {
  const { data, isLoading, isError, refetch } = useEvaluation()

  if (isError) {
    return (
      <AppShell title="Evaluation Center">
        <ErrorState description="Couldn't load evaluation results." onRetry={() => refetch()} />
      </AppShell>
    )
  }

  return (
    <AppShell title="Evaluation Center">
      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-2">
          <StatusBadge status="SYNTHETIC" />
          <span className="text-sm text-muted-foreground">
            Compares the ground-truth labels planted by the synthetic data generator against whatever the
            detectors currently have flagged — computed live, never hardcoded.
          </span>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <KpiSkeleton key={i} />
            ))}
          </div>
        ) : !data?.signals_have_been_run ? (
          <EmptyState
            icon={FlaskConical}
            title="Signal detection hasn't been run yet"
            description="Run signal detection from the Signals page first, then come back here to see live evaluation results."
          />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
              <Stat label="Products Tested" value={data.products_tested} />
              <Stat label="Days Simulated" value={data.days_simulated} />
              <Stat label="Random Seed" value={data.seed} />
              <Stat label="Planted Cases" value={data.planted_cases} />
              <Stat label="Detected Cases" value={data.detected_cases} />
              <Stat
                label="False Positives"
                value={data.false_positives}
                tone={data.false_positives > 0 ? 'text-danger' : 'text-success'}
              />
            </div>

            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Product</TableHead>
                    <TableHead>Signal</TableHead>
                    <TableHead>Expected</TableHead>
                    <TableHead>Detected</TableHead>
                    <TableHead>False Positive</TableHead>
                    <TableHead>Result</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.results.map((row) => (
                    <TableRow key={row.product_id}>
                      <TableCell className="font-medium text-foreground">{row.product}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {row.signal ? SIGNAL_TYPE_LABEL[row.signal as SignalType] : '—'}
                      </TableCell>
                      <TableCell>{row.expected ? 'Yes' : 'No'}</TableCell>
                      <TableCell>{row.detected ? 'Yes' : 'No'}</TableCell>
                      <TableCell>{row.false_positive ? 'Yes' : 'No'}</TableCell>
                      <TableCell>
                        <Badge variant={row.result === 'PASS' ? 'success' : 'danger'}>{row.result}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${tone ?? 'text-foreground'}`}>{value}</p>
    </Card>
  )
}
