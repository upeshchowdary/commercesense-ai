import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { useProducts } from '@/hooks/useProducts'
import { getCompetitorObservations, getCompetitorMatches, postReviewCandidateMatch, postSyncCompetitor } from '@/lib/api'
import {
  Check,
  X,
  Award,
  RefreshCw,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Competitors() {
  const queryClient = useQueryClient()
  const { data: products = [] } = useProducts()
  const [selectedProductId, setSelectedProductId] = useState<string>('')
  const [activeTier, setActiveTier] = useState<'ALL' | 'TIER_1_SAME_ASIN' | 'TIER_2_EXACT_EQUIVALENT' | 'TIER_3_SUBSTITUTE' | 'CANDIDATES'>('ALL')

  // Set default product when products load
  const currentProductId = selectedProductId || (products.length > 0 ? products[0].product_id : '')

  // Fetch observations & matches
  const { data: observations = [], isLoading: obsLoading } = useQuery({
    queryKey: ['competitor_observations', currentProductId],
    queryFn: () => getCompetitorObservations(currentProductId),
    enabled: !!currentProductId,
  })

  const { data: candidates = [] } = useQuery({
    queryKey: ['competitor_matches', currentProductId],
    queryFn: () => getCompetitorMatches(currentProductId),
    enabled: !!currentProductId,
  })

  const reviewMutation = useMutation({
    mutationFn: ({ matchId, confirmed }: { matchId: number; confirmed: boolean }) =>
      postReviewCandidateMatch(matchId, confirmed, currentProductId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitor_matches', currentProductId] })
      queryClient.invalidateQueries({ queryKey: ['competitor_observations', currentProductId] })
    },
  })

  const syncMutation = useMutation({
    mutationFn: () => postSyncCompetitor(currentProductId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitor_observations', currentProductId] })
    },
  })

  const selectedProduct = products.find((p) => p.product_id === currentProductId)

  // Unpack observations safely whether backend returns wrapper envelope or raw array
  const obsList: any[] = (observations as any)?.data?.direct_competitors
    ? [
        ...(((observations as any).data.direct_competitors) || []),
        ...(((observations as any).data.substitutes) || []),
      ]
    : Array.isArray(observations)
    ? observations
    : ((observations as any)?.direct_competitors || [])

  const candidateList: any[] = (candidates as any)?.matches
    ? (candidates as any).matches
    : Array.isArray(candidates)
    ? candidates
    : []

  // Filter observations by tier
  const filteredObs = obsList.filter((o) => {
    if (activeTier === 'ALL') return true
    return o.match_tier === activeTier
  })

  return (
    <AppShell>
      <Topbar title="Competitor Watch" />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              3-Tier Competitor Intelligence
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Strict 3-tier hierarchy: Tier 1 (Same ASIN), Tier 2 (Exact Equivalent), Tier 3 (Substitute). Substitutes are strictly excluded from direct competitor medians.
            </p>
          </div>
          <ProvenanceBadge provenance="AMAZON_OFFICIAL" />
        </div>

        {/* Product Selector Dropdown */}
        <div className="mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-card border border-border p-3.5 rounded-lg">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 whitespace-nowrap">
              Focus Product:
            </span>
            <select
              value={currentProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              className="border border-border rounded-md px-3 py-1.5 text-xs bg-background text-foreground w-full sm:w-80"
            >
              {products.map((p) => (
                <option key={p.product_id} value={p.product_id}>
                  {p.name} (${p.base_price.toFixed(2)})
                </option>
              ))}
            </select>
            <Button
              size="sm"
              variant="outline"
              disabled={syncMutation.isPending || !currentProductId}
              onClick={() => syncMutation.mutate()}
              className="text-xs gap-1.5 h-8 whitespace-nowrap"
            >
              <RefreshCw className={cn("size-3.5", syncMutation.isPending && "animate-spin")} />
              <span>{syncMutation.isPending ? 'Syncing...' : 'Sync Offers'}</span>
            </Button>
          </div>

          {selectedProduct && (
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span>ASIN: <strong className="text-foreground font-mono">{selectedProduct.product_id}</strong></span>
              <span>·</span>
              <span>Base Price: <strong className="text-slate-900 dark:text-white font-semibold">${selectedProduct.base_price.toFixed(2)}</strong></span>
            </div>
          )}
        </div>

        {/* Tier Tabs */}
        <div className="flex items-center gap-2 border-b border-border mb-6 overflow-x-auto pb-px">
          {[
            { id: 'ALL', label: 'All Observed Offers' },
            { id: 'TIER_1_SAME_ASIN', label: 'Tier 1: Same ASIN' },
            { id: 'TIER_2_EXACT_EQUIVALENT', label: 'Tier 2: Exact Equivalent' },
            { id: 'TIER_3_SUBSTITUTE', label: 'Tier 3: Substitutes' },
            { id: 'CANDIDATES', label: `Candidate Review (${candidateList.filter((c: any) => c.seller_confirmed === null).length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTier(tab.id as any)}
              className={cn(
                'px-3.5 py-2 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap',
                activeTier === tab.id
                  ? 'border-red-600 text-red-600 dark:border-red-500 dark:text-red-400'
                  : 'border-transparent text-slate-500 hover:text-slate-900 dark:text-slate-400',
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content based on tab */}
        {activeTier === 'CANDIDATES' ? (
          <div className="flex flex-col gap-3">
            {candidateList.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground border border-dashed rounded-lg bg-card">
                No cross-ASIN matching candidates pending review.
              </div>
            ) : (
              candidateList.map((cand: any) => (
                <div
                  key={cand.id}
                  className="rounded-lg border border-border p-4 bg-card flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs font-bold text-foreground">{cand.candidate_asin}</span>
                      <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-muted">
                        {cand.match_method} · {cand.match_confidence} confidence
                      </span>
                    </div>
                    <p className="text-xs font-medium text-foreground">{cand.candidate_title}</p>
                    <div className="flex items-center gap-3 text-[11px] text-muted-foreground mt-1.5">
                      <span>Matched: {cand.matched_fields.join(', ')}</span>
                      {cand.mismatched_fields.length > 0 && (
                        <span className="text-red-600">Mismatched: {cand.mismatched_fields.join(', ')}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                    {cand.seller_confirmed === null ? (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => reviewMutation.mutate({ matchId: cand.id, confirmed: false })}
                          className="text-xs h-8 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 border-red-200 dark:border-red-900/50"
                        >
                          <X className="size-3.5 mr-1" />
                          Reject
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => reviewMutation.mutate({ matchId: cand.id, confirmed: true })}
                          className="text-xs h-8 bg-red-600 hover:bg-red-700 text-white shadow-xs"
                        >
                          <Check className="size-3.5 mr-1" />
                          Confirm Exact Match
                        </Button>
                      </>
                    ) : (
                      <span
                        className={cn(
                          'text-xs font-bold px-2 py-1 rounded',
                          cand.seller_confirmed ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-slate-100 text-slate-600 border border-slate-200',
                        )}
                      >
                        {cand.seller_confirmed ? 'Confirmed Equivalent' : 'Rejected Match'}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-border text-slate-500 uppercase tracking-wider font-semibold text-[10.5px]">
                  <tr>
                    <th className="p-3.5">Competitor Offer</th>
                    <th className="p-3.5">Match Tier</th>
                    <th className="p-3.5">Item Price</th>
                    <th className="p-3.5">Shipping</th>
                    <th className="p-3.5">Landed Price</th>
                    <th className="p-3.5">Fulfillment</th>
                    <th className="p-3.5">Featured Offer</th>
                    <th className="p-3.5">Observed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {obsLoading ? (
                    <tr>
                      <td colSpan={8} className="p-8 text-center text-muted-foreground animate-pulse">
                        Loading competitor offer distribution...
                      </td>
                    </tr>
                  ) : filteredObs.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="p-8 text-center text-muted-foreground">
                        No competitor observations recorded for this tier yet.
                      </td>
                    </tr>
                  ) : (
                    filteredObs.map((obs: any) => (
                      <tr key={obs.id} className="hover:bg-muted/30 transition-colors">
                        <td className="p-3.5 font-medium text-foreground">
                          <div className="flex flex-col">
                            <span>{obs.competitor}</span>
                            {obs.competitor_asin && (
                              <span className="font-mono text-[10px] text-muted-foreground">
                                {obs.competitor_asin}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-3.5">
                          <span
                            className={cn(
                              'px-2 py-0.5 rounded text-[10px] font-bold tracking-tight',
                              obs.match_tier === 'TIER_1_SAME_ASIN' && 'bg-red-50 text-red-700 border border-red-200',
                              obs.match_tier === 'TIER_2_EXACT_EQUIVALENT' && 'bg-slate-100 text-slate-700 border border-slate-200',
                              obs.match_tier === 'TIER_3_SUBSTITUTE' && 'bg-slate-50 text-slate-500',
                            )}
                          >
                            {obs.match_tier?.replace('TIER_', 'T').replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="p-3.5 font-mono">${Number(obs.price).toFixed(2)}</td>
                        <td className="p-3.5 font-mono text-muted-foreground">
                          ${Number(obs.shipping_cost || 0).toFixed(2)}
                        </td>
                        <td className="p-3.5 font-mono font-bold text-foreground">
                          ${Number(obs.landed_price || obs.price).toFixed(2)}
                        </td>
                        <td className="p-3.5">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-muted">
                            {obs.fulfillment_channel || 'FBA'}
                          </span>
                        </td>
                        <td className="p-3.5">
                          {obs.is_buy_box_winner ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900/50 px-2 py-0.5 rounded font-bold text-[11px]">
                              <Award className="size-3.5" /> Buy Box Winner
                            </span>
                          ) : (
                            <span className="text-muted-foreground text-[11px]">No</span>
                          )}
                        </td>
                        <td className="p-3.5 text-muted-foreground text-[11px] whitespace-nowrap">
                          {obs.observed_at ? new Date(obs.observed_at).toLocaleDateString() : 'Recent'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </AppShell>
  )
}
