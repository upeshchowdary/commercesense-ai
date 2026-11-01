import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { getOpportunities, postEvaluateOpportunity } from '@/lib/api'
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Plus,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Opportunities() {
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')

  // Form state for evaluating new opportunity
  const [form, setForm] = useState({
    keyword: '',
    category: 'Kitchen',
    projected_selling_price: 29.99,
    estimated_cogs: 8.50,
    search_volume: 15000,
    search_growth_rate: 15.0,
    active_competitor_count: 8,
    top_competitor_reviews: 450,
    estimated_moq: 500,
    cpsc_recall_count: 0,
  })

  const { data: opportunities = [], isLoading, refetch } = useQuery({
    queryKey: ['opportunities', selectedCategory],
    queryFn: () => getOpportunities(selectedCategory === 'ALL' ? undefined : selectedCategory),
  })

  const oppList: any[] = Array.isArray(opportunities)
    ? opportunities
    : ((opportunities as any)?.opportunities ?? [])

  const evaluateMutation = useMutation({
    mutationFn: postEvaluateOpportunity,
    onSuccess: () => {
      refetch()
      setModalOpen(false)
    },
  })

  const handleEvaluate = (e: React.FormEvent) => {
    e.preventDefault()
    evaluateMutation.mutate(form)
  }

  return (
    <AppShell>
      <Topbar
        title="Product Opportunities"
        actions={
          <Button
            size="sm"
            onClick={() => setModalOpen(true)}
            className="gap-1.5 bg-red-600 hover:bg-red-700 text-white shadow-xs"
          >
            <Plus className="size-3.5" />
            <span>Score New Opportunity</span>
          </Button>
        }
      />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              6-Dimension Opportunity Radar
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Deterministic scoring across Demand, Competition, Unit Margin, Capital, Seasonality, and Policy. Margin floor breach forces an inviolable NO_GO verdict.
            </p>
          </div>
          <ProvenanceBadge provenance="CALCULATED" />
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-1">
          {['ALL', 'Kitchen', 'Electronics', 'Sports', 'Home & Garden'].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={cn(
                'px-3 py-1.5 rounded-md text-xs font-medium border transition-colors whitespace-nowrap',
                selectedCategory === cat
                  ? 'border-red-600 bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400 dark:border-red-800'
                  : 'border-border bg-card text-muted-foreground hover:text-foreground',
              )}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Opportunities Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {isLoading ? (
            [1, 2, 3].map((i) => (
              <div key={i} className="h-56 rounded-lg border border-border bg-card animate-pulse" />
            ))
          ) : oppList.length === 0 ? (
            <div className="col-span-full p-12 text-center text-xs text-muted-foreground border border-dashed rounded-lg bg-card">
              No opportunity scorecards recorded for this filter. Click "Score New Opportunity" to evaluate a candidate product.
            </div>
          ) : (
            oppList.map((opp: any, oppIdx: number) => {
              const verdict = opp.verdict
              const oppId = opp.product_id || opp.id || `opp-${oppIdx}`
              const oppCategory = opp.category || (opp.dimensions?.policy_risk?.details?.includes('Category') ? 'Retail' : 'Catalog')
              return (
                <div
                  key={oppId}
                  className="rounded-lg border border-border bg-card p-5 hover:shadow-xs transition-shadow flex flex-col justify-between"
                >
                  <div>
                    {/* Verdict Pill */}
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[10.5px] font-bold uppercase tracking-wider text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {oppCategory}
                      </span>
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold tracking-tight',
                          verdict === 'GO' && 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400',
                          verdict === 'CONDITIONAL_GO' && 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400',
                          verdict === 'NO_GO' && 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/40 dark:text-red-400',
                          verdict === 'INSUFFICIENT_EVIDENCE' && 'bg-muted text-muted-foreground',
                        )}
                      >
                        {verdict === 'GO' ? (
                          <CheckCircle2 className="size-3.5" />
                        ) : verdict === 'NO_GO' ? (
                          <XCircle className="size-3.5" />
                        ) : (
                          <AlertTriangle className="size-3.5" />
                        )}
                        <span>{verdict?.replace(/_/g, ' ')}</span>
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-foreground tracking-tight">
                      {opp.keyword || opp.product_name}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {opp.rationale || opp.primary_recommendation}
                    </p>

                    {/* Dimension Mini Bars */}
                    {(opp.dimensions || opp.dimension_scores) && (
                      <div className="mt-4 space-y-2 border-t border-border pt-3">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground">Demand Momentum:</span>
                          <span className="font-semibold">
                            {opp.dimensions?.demand_momentum?.score ?? opp.dimension_scores?.demand_momentum ?? 15}/25
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground">Unit Margin Feasibility:</span>
                          <span className="font-semibold">
                            {opp.dimensions?.margin_feasibility?.score ?? opp.dimension_scores?.margin_feasibility ?? 0}/25
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground">Competition Density:</span>
                          <span className="font-semibold">
                            {opp.dimensions?.competition_moat?.score ?? opp.dimension_scores?.competition_density ?? 16}/20
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground">Capital / MOQ Fit:</span>
                          <span className="font-semibold">
                            {opp.dimensions?.capital_moq?.score ?? opp.dimension_scores?.capital_moq ?? 10}/10
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-xs">
                    <span className="font-bold text-foreground">Score: {opp.total_score}/100</span>
                    <ProvenanceBadge provenance="CALCULATED" className="text-[9.5px] py-0" />
                  </div>
                </div>
              )
            })
          )}
        </div>
      </main>

      {/* Evaluate Opportunity Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              Score Product Opportunity Idea
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleEvaluate} className="space-y-3 py-2 text-xs">
            <div>
              <label className="block font-semibold mb-1">Product / Search Keyword:</label>
              <input
                type="text"
                required
                value={form.keyword}
                onChange={(e) => setForm({ ...form, keyword: e.target.value })}
                placeholder="e.g. Stainless Steel Garlic Press"
                className="w-full border border-border rounded px-2.5 py-1.5 bg-card text-foreground"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold mb-1">Category:</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className="w-full border border-border rounded px-2 py-1.5 bg-card text-foreground"
                >
                  <option value="Kitchen">Kitchen</option>
                  <option value="Electronics">Electronics</option>
                  <option value="Sports">Sports</option>
                  <option value="Home & Garden">Home & Garden</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-1">Projected Price ($):</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={form.projected_selling_price}
                  onChange={(e) => setForm({ ...form, projected_selling_price: Number(e.target.value) })}
                  className="w-full border border-border rounded px-2.5 py-1.5 bg-card text-foreground"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold mb-1">Estimated Unit COGS ($):</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={form.estimated_cogs}
                  onChange={(e) => setForm({ ...form, estimated_cogs: Number(e.target.value) })}
                  className="w-full border border-border rounded px-2.5 py-1.5 bg-card text-foreground"
                />
              </div>

              <div>
                <label className="block font-semibold mb-1">Monthly Search Vol:</label>
                <input
                  type="number"
                  value={form.search_volume}
                  onChange={(e) => setForm({ ...form, search_volume: Number(e.target.value) })}
                  className="w-full border border-border rounded px-2.5 py-1.5 bg-card text-foreground"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold mb-1">Competitor Count:</label>
                <input
                  type="number"
                  value={form.active_competitor_count}
                  onChange={(e) => setForm({ ...form, active_competitor_count: Number(e.target.value) })}
                  className="w-full border border-border rounded px-2.5 py-1.5 bg-card text-foreground"
                />
              </div>

              <div>
                <label className="block font-semibold mb-1">Supplier MOQ:</label>
                <input
                  type="number"
                  value={form.estimated_moq}
                  onChange={(e) => setForm({ ...form, estimated_moq: Number(e.target.value) })}
                  className="w-full border border-border rounded px-2.5 py-1.5 bg-card text-foreground"
                />
              </div>
            </div>

            <DialogFooter className="mt-4 pt-3 border-t border-border">
              <Button type="button" variant="outline" size="sm" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={evaluateMutation.isPending}
                className="bg-red-600 hover:bg-red-700 text-white shadow-xs"
              >
                Compute Scorecard
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
