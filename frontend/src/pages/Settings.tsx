import { CheckCircle2, XCircle } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { ErrorState } from '@/components/shared/ErrorState'
import { CardSkeleton } from '@/components/shared/Skeletons'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useHealth } from '@/hooks/useHealth'

export default function Settings() {
  const { data, isLoading, isError, refetch } = useHealth()

  return (
    <AppShell title="Settings">
      <div className="mx-auto flex max-w-2xl flex-col gap-5">
        <Card>
          <CardHeader>
            <CardTitle>Backend Connectivity</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {isError ? (
              <ErrorState description="Couldn't reach the API." onRetry={() => refetch()} />
            ) : isLoading ? (
              <CardSkeleton lines={2} />
            ) : (
              <>
                <KeyRow label="GEMINI_API_KEY" set={!!data?.gemini_api_key_set} />
                <KeyRow label="TAVILY_API_KEY" set={!!data?.tavily_api_key_set} />
                <p className="text-xs text-muted-foreground">
                  Only whether each key is configured is ever shown here — never the value itself.
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Data Sources</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <StatusBadge status="SYNTHETIC" />
              <span>3 deterministic signal detectors reading locally generated fake seller data. No live calls, runs automatically.</span>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status="LIVE" />
              <span>Research Agent (Tavily) and Insight Agent (Gemini) — real API calls, human-triggered only.</span>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status="CACHED" />
              <span>A live research result served from the 6-hour local cache instead of a new API call.</span>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status="DEMO" />
              <span>Data shown as part of the guided Demo Mode walkthrough.</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>About</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Sydon-1 — Amazon Seller Copilot. A CUBE Buildathon practice build (Sydon AI / CodeQuesters, 2026).
            The synthetic and live sides of this app are kept intentionally separate — see the README in the
            repository for the full architecture.
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}

function KeyRow({ label, set }: { label: string; set: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
      <span className="font-mono text-sm text-foreground">{label}</span>
      {set ? (
        <span className="flex items-center gap-1.5 text-sm text-success">
          <CheckCircle2 className="size-4" /> Set
        </span>
      ) : (
        <span className="flex items-center gap-1.5 text-sm text-danger">
          <XCircle className="size-4" /> Not set
        </span>
      )}
    </div>
  )
}
