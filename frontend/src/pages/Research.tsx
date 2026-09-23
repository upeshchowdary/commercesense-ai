import { ExternalLink, Loader2, Search } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { EmptyState } from '@/components/shared/EmptyState'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { formatRelativeTime, formatSecondsAge } from '@/lib/utils'
import type { ResearchResult } from '@/lib/types'
import { useResearch } from '@/hooks/useResearch'

interface HistoryEntry extends ResearchResult {
  productName: string
  at: number
}

export default function Research() {
  const [params] = useSearchParams()
  const [productName, setProductName] = useState(params.get('product') ?? '')
  const [useCache, setUseCache] = useState(true)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const research = useResearch()

  function run() {
    if (productName.trim().length < 2) return
    research.mutate(
      { product_name: productName.trim(), use_cache: useCache },
      {
        onSuccess: (data) => {
          setHistory((h) => [{ ...data, productName: productName.trim(), at: Date.now() }, ...h].slice(0, 10))
        },
      },
    )
  }

  const state = research.isPending ? 'running' : research.isError ? 'failed' : research.data ? 'completed' : 'idle'

  return (
    <AppShell title="Research Workspace">
      <div className="mx-auto flex max-w-3xl flex-col gap-5">
        <Card className="flex flex-col gap-3 p-5">
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()}
              placeholder="e.g. Bamboo Cutting Board Set, or any real product"
              className="flex-1"
            />
            <Button onClick={run} disabled={research.isPending || productName.trim().length < 2}>
              {research.isPending ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
              Research
            </Button>
          </div>
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={useCache}
              onChange={(e) => setUseCache(e.target.checked)}
              className="size-3.5 accent-[var(--primary)]"
            />
            Use cache when available (recommended — avoids spending live API quota on repeats)
          </label>
        </Card>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Status:</span>
          <Badge variant={state === 'failed' ? 'danger' : state === 'completed' ? 'success' : 'outline'}>
            {state.toUpperCase()}
          </Badge>
        </div>

        {research.isError && (
          <p className="text-sm text-danger">{(research.error as Error)?.message ?? 'Research failed.'}</p>
        )}

        {research.data && (
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Results for {productName}</CardTitle>
              <div className="flex items-center gap-2">
                <StatusBadge status={research.data.cache_hit ? 'CACHED' : 'LIVE'} />
                {research.data.cache_hit && research.data.cache_age_seconds !== null && (
                  <span className="text-xs text-muted-foreground">
                    Age: {formatSecondsAge(research.data.cache_age_seconds)}
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-2">
                {research.data.bundle.search_queries_used.map((q, i) => (
                  <Badge key={i} variant="outline" className="normal-case">
                    {q}
                  </Badge>
                ))}
              </div>
              <div className="flex flex-col gap-3">
                {research.data.bundle.findings.map((f, i) => (
                  <div key={i} className="rounded-lg border border-border p-3">
                    <p className="text-sm text-foreground">{f.snippet}</p>
                    <div className="mt-2 flex items-center justify-between">
                      {f.source_url ? (
                        <a
                          href={f.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-xs text-accent hover:underline"
                        >
                          {f.source_url}
                          <ExternalLink className="size-3" />
                        </a>
                      ) : (
                        <span className="text-xs text-muted-foreground">No source URL</span>
                      )}
                      <span className="text-xs text-muted-foreground">{formatRelativeTime(f.retrieved_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <div>
          <h3 className="mb-2 text-sm font-medium text-foreground">Session History</h3>
          {history.length === 0 ? (
            <EmptyState title="No queries run yet this session" />
          ) : (
            <div className="flex flex-col gap-2">
              {history.map((h, i) => (
                <Card key={i} className="flex items-center justify-between gap-3 p-3 text-sm">
                  <span className="text-foreground">{h.productName}</span>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={h.cache_hit ? 'CACHED' : 'LIVE'} />
                    <span className="text-xs text-muted-foreground">{h.bundle.findings.length} sources</span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
