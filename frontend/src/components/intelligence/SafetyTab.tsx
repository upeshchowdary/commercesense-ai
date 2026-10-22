// Safety tab: on-demand US CPSC recall check (free, no API key). It only
// calls the backend when the user clicks the button -- never on mount -- and
// every hit is shown as a *possible* name match with its CPSC link, using the
// backend's own disclaimer text. See providers/recalls.py for the rules.
import { ExternalLink, Loader2, ShieldAlert } from 'lucide-react'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { EmptyState } from '@/components/shared/EmptyState'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useRecallCheck } from '@/hooks/useIntelligenceModules'

export function SafetyTab({ productId }: { productId: string }) {
  const check = useRecallCheck()
  const result = check.data

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2">
            <ShieldAlert className="size-4" /> Product recall check (US CPSC)
          </CardTitle>
          {result?.available && <StatusBadge status={result.provenance === 'CACHED' ? 'CACHED' : 'LIVE'} />}
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <p className="text-muted-foreground">
            Searches the US Consumer Product Safety Commission's public recall database by product name. Free, no API key.
            Runs only when you click.
          </p>
          <div>
            <Button size="sm" disabled={check.isPending} onClick={() => check.mutate(productId)}>
              {check.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <ShieldAlert className="size-3.5" />}
              {result ? 'Check again' : 'Check recalls'}
            </Button>
          </div>

          {check.isError && (
            <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-danger">
              Couldn't run the check: {check.error instanceof Error ? check.error.message : 'unknown error'}
            </p>
          )}

          {result && !result.available && (
            <p className="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-warning">
              CPSC could not be reached, so this product has NOT been checked. This is not a "no recalls" result.
              {result.error ? ` (${result.error})` : ''}
            </p>
          )}

          {result?.available && (
            <>
              <p className="text-xs text-muted-foreground">
                Searched for: {result.queried_terms.map((t) => `"${t}"`).join(', ')}. {result.disclaimer}
              </p>
              {result.matches.length === 0 ? (
                <EmptyState title="No possible matches in CPSC's database" className="border-none py-6" />
              ) : (
                <ul className="flex flex-col gap-2">
                  {result.matches.map((m) => (
                    <li key={m.recall_id ?? m.url} className="flex flex-col gap-1 rounded-lg border border-border px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-foreground">{m.title ?? 'Untitled recall'}</span>
                        {m.brand_match && <Badge variant="warning">Brand also matches</Badge>}
                        {m.recall_date && <span className="text-xs text-muted-foreground">{m.recall_date}</span>}
                      </div>
                      {m.hazards.length > 0 && <p className="text-xs text-muted-foreground">Hazard: {m.hazards.join('; ')}</p>}
                      {m.remedies.length > 0 && <p className="text-xs text-muted-foreground">Remedy: {m.remedies.join('; ')}</p>}
                      {m.url && (
                        <a href={m.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-primary hover:underline">
                          Open on cpsc.gov <ExternalLink className="size-3" />
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
