import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Award } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useProduct } from '@/hooks/useProducts'
import { getCompetitorObservations } from '@/lib/api'
import {
  InventoryTab,
  ListingTab,
  PricingTab,
  ReviewsTab,
} from '@/components/intelligence/ModuleTabs'
import {
  AcosTrendChart,
  InventoryTrendChart,
  RankTrendChart,
} from '@/components/charts/ProductTrendChart'

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>()
  const { data: product, isLoading, isError, refetch } = useProduct(productId)
  const [activeTab, setActiveTab] = useState('performance')

  // Fetch competitor offers for the Competition tab
  const { data: competitorObs = [] } = useQuery({
    queryKey: ['competitor_observations', productId],
    queryFn: () => getCompetitorObservations(productId || ''),
    enabled: !!productId,
  })

  if (isLoading || !product) {
    return (
      <AppShell>
        <Topbar title="Loading Product Workspace..." />
        <main className="p-8 max-w-7xl mx-auto w-full">
          <div className="h-64 rounded-xl border border-border bg-card animate-pulse" />
        </main>
      </AppShell>
    )
  }

  if (isError) {
    return (
      <AppShell>
        <Topbar title="Product Not Found" />
        <main className="p-8 max-w-md mx-auto text-center">
          <p className="text-sm text-muted-foreground mb-4">Could not load product with ID: {productId}</p>
          <Button onClick={() => refetch()} size="sm">Retry</Button>
        </main>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <Topbar
        title={product.name}
        actions={
          <div className="flex items-center gap-2">
            <ProvenanceBadge provenance="AMAZON_OFFICIAL" />
            <Link to="/pricing-lab">
              <Button size="sm" variant="outline" className="text-xs h-8">
                Pricing Lab →
              </Button>
            </Link>
          </div>
        }
      />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Workspace Hero Header */}
        <div className="rounded-xl border border-border bg-card p-5 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="size-12 rounded-lg bg-red-50 border border-red-200 dark:bg-red-950/40 dark:border-red-900/50 flex items-center justify-center text-red-600 shrink-0 font-bold text-lg">
              {product.category?.charAt(0) || 'P'}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-red-700 bg-red-50 border border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-900/50 px-2 py-0.5 rounded">
                  {product.category}
                </span>
                <span className="font-mono text-xs text-muted-foreground">ASIN: {product.product_id}</span>
                <span className="text-muted-foreground">·</span>
                <span className="text-xs text-muted-foreground">Store: Amazon India (A21TJRUUN4KGV)</span>
              </div>
              <h2 className="text-lg font-bold text-foreground leading-snug tracking-tight">
                {product.name}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-6 shrink-0 self-end md:self-center border-t md:border-t-0 pt-3 md:pt-0 border-border">
            <div className="flex flex-col text-right">
              <span className="text-xs text-muted-foreground">Base Catalog Price</span>
              <span className="text-xl font-bold font-mono text-slate-900 dark:text-white">
                ${product.base_price.toFixed(2)}
              </span>
            </div>
            <div className="flex flex-col text-right">
              <span className="text-xs text-muted-foreground">Active Signals</span>
              <span className="text-xl font-bold font-mono text-red-600">
                {product.signals.length}
              </span>
            </div>
          </div>
        </div>

        {/* 7 Core Workspace Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 p-1 rounded-lg flex flex-wrap gap-1 h-auto">
            <TabsTrigger value="performance" className="text-xs font-semibold px-3 py-1.5">
              1. Performance
            </TabsTrigger>
            <TabsTrigger value="competition" className="text-xs font-semibold px-3 py-1.5">
              2. Competition ({competitorObs.length})
            </TabsTrigger>
            <TabsTrigger value="pricing" className="text-xs font-semibold px-3 py-1.5">
              3. Pricing Lab
            </TabsTrigger>
            <TabsTrigger value="inventory" className="text-xs font-semibold px-3 py-1.5">
              4. Inventory & Forecast
            </TabsTrigger>
            <TabsTrigger value="reviews" className="text-xs font-semibold px-3 py-1.5">
              5. Customer Voice (VOC)
            </TabsTrigger>
            <TabsTrigger value="listing" className="text-xs font-semibold px-3 py-1.5">
              6. Listing Quality
            </TabsTrigger>
            <TabsTrigger value="evidence" className="text-xs font-semibold px-3 py-1.5">
              7. Evidence & Audit
            </TabsTrigger>
          </TabsList>

          {/* TAB 1: Performance */}
          <TabsContent value="performance" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-lg border border-border bg-card p-4">
                <span className="text-xs text-muted-foreground font-medium block">Total Units Sold (Observed)</span>
                <span className="text-2xl font-bold font-mono text-foreground mt-1 block">
                  {product.metrics.reduce((acc, m) => acc + m.units_sold, 0)}
                </span>
                <span className="text-[11px] text-muted-foreground mt-1 block">Over {product.metrics.length} daily snapshots</span>
              </div>
              <div className="rounded-lg border border-border bg-card p-4">
                <span className="text-xs text-muted-foreground font-medium block">Current Inventory Level</span>
                <span className="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1 block">
                  {product.metrics[product.metrics.length - 1]?.inventory_level ?? '—'}
                </span>
                <span className="text-[11px] text-muted-foreground mt-1 block">FBA Available Stock</span>
              </div>
              <div className="rounded-lg border border-border bg-card p-4">
                <span className="text-xs text-muted-foreground font-medium block">Buy Box Ownership</span>
                <span className="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1 block">
                  {product.metrics[product.metrics.length - 1]?.has_buy_box ? '100% (Winning)' : '0% (Lost)'}
                </span>
                <span className="text-[11px] text-muted-foreground mt-1 block">In latest daily observation</span>
              </div>
            </div>

            {/* Metric Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-lg border border-border bg-card p-5">
                <h3 className="text-sm font-bold text-foreground mb-3">Sales Rank Velocity</h3>
                <RankTrendChart metrics={product.metrics} />
              </div>
              <div className="rounded-lg border border-border bg-card p-5">
                <h3 className="text-sm font-bold text-foreground mb-3">Inventory Stock Level Trajectory</h3>
                <InventoryTrendChart metrics={product.metrics} />
              </div>
              <div className="rounded-lg border border-border bg-card p-5 lg:col-span-2">
                <h3 className="text-sm font-bold text-foreground mb-3">ACOS & Ad Spend Efficiency</h3>
                <AcosTrendChart metrics={product.metrics} />
              </div>
            </div>
          </TabsContent>

          {/* TAB 2: Competition */}
          <TabsContent value="competition" className="space-y-6">
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-foreground">Direct Competitor Offer Ladder</h3>
                  <p className="text-xs text-muted-foreground">
                    Direct median landed prices filter out Tier 3 substitutes to prevent distorted price medians.
                  </p>
                </div>
                <ProvenanceBadge provenance="AMAZON_OFFICIAL" />
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-border text-slate-500 uppercase font-semibold text-[10.5px]">
                    <tr>
                      <th className="p-3">Competitor Seller</th>
                      <th className="p-3">Match Tier</th>
                      <th className="p-3">Landed Price</th>
                      <th className="p-3">Fulfillment</th>
                      <th className="p-3">Buy Box</th>
                      <th className="p-3">Observed Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {competitorObs.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-6 text-center text-muted-foreground">
                          No competitor observations logged for this ASIN yet.
                        </td>
                      </tr>
                    ) : (
                      competitorObs.map((obs: any) => (
                        <tr key={obs.id} className="hover:bg-muted/20">
                          <td className="p-3 font-medium text-foreground">{obs.competitor}</td>
                          <td className="p-3">
                            <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded font-bold">
                              {obs.match_tier}
                            </span>
                          </td>
                          <td className="p-3 font-mono font-bold text-foreground">
                            ${Number(obs.landed_price || obs.price).toFixed(2)}
                          </td>
                          <td className="p-3">{obs.fulfillment_channel || 'FBA'}</td>
                          <td className="p-3">
                            {obs.is_buy_box_winner ? (
                              <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900/50 px-2 py-0.5 rounded font-bold">
                                <Award className="size-3.5" /> Winner
                              </span>
                            ) : (
                              <span className="text-muted-foreground">No</span>
                            )}
                          </td>
                          <td className="p-3 text-muted-foreground">
                            {obs.observed_at ? new Date(obs.observed_at).toLocaleDateString() : 'Recent'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </TabsContent>

          {/* TAB 3: Pricing */}
          <TabsContent value="pricing" className="space-y-6">
            <PricingTab productId={product.product_id} />
          </TabsContent>

          {/* TAB 4: Inventory */}
          <TabsContent value="inventory" className="space-y-6">
            <InventoryTab productId={product.product_id} />
          </TabsContent>

          {/* TAB 5: Reviews / VOC */}
          <TabsContent value="reviews" className="space-y-6">
            <ReviewsTab productId={product.product_id} />
          </TabsContent>

          {/* TAB 6: Listing Quality */}
          <TabsContent value="listing" className="space-y-6">
            <ListingTab productId={product.product_id} />
          </TabsContent>

          {/* TAB 7: Evidence & Audit */}
          <TabsContent value="evidence" className="space-y-6">
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-foreground">Cryptographic Provenance & Audit Trail</h3>
                <ProvenanceBadge provenance="AMAZON_OFFICIAL" />
              </div>
              <p className="text-xs text-muted-foreground mb-4">
                Every calculation, recommendation, and seller input is stamped with a cryptographic SHA-256 payload hash and immutable audit log.
              </p>

              <div className="space-y-3 text-xs">
                {product.activity.map((act, idx) => (
                  <div key={idx} className="p-3 rounded border border-border bg-muted/20">
                    <div className="flex justify-between font-semibold text-foreground mb-1">
                      <span>{act.action}</span>
                      <span className="font-mono text-[10.5px] text-muted-foreground">{act.timestamp}</span>
                    </div>
                    <div className="flex justify-between text-muted-foreground text-[11px]">
                      <span>Agent/Actor: <strong className="text-foreground">{act.agent}</strong></span>
                      <span className="font-mono">Audit Row #{idx + 1}</span>
                    </div>
                  </div>
                ))}
                {product.activity.length === 0 && (
                  <div className="p-6 text-center text-muted-foreground">No activity recorded for this product yet.</div>
                )}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </AppShell>
  )
}
