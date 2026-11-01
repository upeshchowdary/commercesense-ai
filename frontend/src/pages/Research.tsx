import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { postResearch, postAddProduct } from '@/lib/api'
import {
  Search,
  Loader2,
  ExternalLink,
  Sparkles,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Plus,
} from 'lucide-react'

export default function Research() {
  const [params] = useSearchParams()
  const queryClient = useQueryClient()
  const [productName, setProductName] = useState(params.get('product') ?? '')
  const [useCache, setUseCache] = useState(true)
  const [addedSuccess, setAddedSuccess] = useState(false)

  const researchMutation = useMutation({
    mutationFn: (name: string) =>
      postResearch({ product_name: name.trim(), use_cache: useCache, generate_summary: true }),
  })

  const addProductMutation = useMutation({
    mutationFn: (prod: { product_id: string; name: string; category: string; base_price: number; cogs?: number }) =>
      postAddProduct(prod),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      setAddedSuccess(true)
      setTimeout(() => setAddedSuccess(false), 3000)
    },
  })

  const handleRun = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (productName.trim().length < 2) return
    researchMutation.mutate(productName.trim())
  }

  const data = researchMutation.data
  const analysis = data?.analysis
  const bundle = data?.bundle
  const findings: any[] = bundle?.findings ?? []
  const queriesUsed: string[] = bundle?.search_queries_used ?? []

  // Guess approximate price from range or default
  const priceMatches = analysis?.typical_price_range?.match(/\$?(\d+(\.\d+)?)/g)
  const estimatedPrice = priceMatches && priceMatches[0] ? parseFloat(priceMatches[0].replace('$', '')) : 24.99

  const handleAddToPortfolio = () => {
    if (!productName.trim()) return
    const autoId = 'ASIN-' + Math.random().toString(36).substring(2, 8).toUpperCase()
    addProductMutation.mutate({
      product_id: autoId,
      name: productName.trim(),
      category: 'Kitchen',
      base_price: estimatedPrice,
      cogs: Math.round(estimatedPrice * 0.35 * 100) / 100,
    })
  }

  return (
    <AppShell>
      <Topbar title="Product Research Workspace" />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Live Product & Market Discovery
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Real-world product intelligence powered by 9 rotating Gemini keys and live web retrieval. Research any product, brand, or ASIN.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ProvenanceBadge provenance="MODELLED" />
            <ProvenanceBadge provenance="PUBLIC_NEWS" />
          </div>
        </div>

        {/* Search Bar */}
        <div className="bg-card border border-border rounded-xl p-5 mb-8 shadow-xs">
          <form onSubmit={handleRun} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="size-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="Enter any product keyword or ASIN (e.g. Bamboo Cutting Board Set, Sony WH-1000XM5, Silicone Air Fryer Liners)..."
                className="w-full pl-10 pr-4 py-2.5 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-hidden focus:ring-2 focus:ring-red-500"
              />
            </div>
            <Button
              type="submit"
              disabled={researchMutation.isPending || productName.trim().length < 2}
              className="bg-red-600 hover:bg-red-700 text-white px-6 h-10 gap-2 shrink-0 font-medium shadow-xs"
            >
              {researchMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  <span>Gathering Live Market Intelligence...</span>
                </>
              ) : (
                <>
                  <Sparkles className="size-4" />
                  <span>Analyze Product</span>
                </>
              )}
            </Button>
          </form>

          <div className="flex items-center justify-between mt-3 pt-3 border-t border-border text-xs text-muted-foreground">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={useCache}
                onChange={(e) => setUseCache(e.target.checked)}
                className="size-3.5 accent-red-600 rounded"
              />
              <span>Use local cache for repeat queries (faster, preserves Gemini quota)</span>
            </label>

            {data && (
              <span className="font-mono text-[11px]">
                Status: <strong className={data.cache_hit ? "text-amber-600" : "text-red-700 dark:text-red-400"}>
                  {data.cache_hit ? "CACHED SNAPSHOT" : "LIVE WEB RETRIEVAL"}
                </strong>
              </span>
            )}
          </div>
        </div>

        {/* Error State */}
        {researchMutation.isError && (
          <div className="p-4 mb-6 rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/40 text-xs text-red-700 dark:text-red-300 flex items-center gap-2">
            <AlertCircle className="size-4 shrink-0" />
            <span>{(researchMutation.error as Error)?.message || 'Failed to research product. Check API connections.'}</span>
          </div>
        )}

        {/* Loading State */}
        {researchMutation.isPending && (
          <div className="p-12 text-center bg-card border border-border rounded-xl">
            <Loader2 className="size-8 animate-spin text-red-600 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-foreground">Scouting Live E-Commerce Landscape</h3>
            <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
              Gemini is planning targeted search queries, analyzing competitor offers, pricing benchmarks, and synthesizing customer reviews...
            </p>
          </div>
        )}

        {/* Results */}
        {data && (
          <div className="space-y-6">
            {/* Action Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 p-4 rounded-xl">
              <div>
                <h3 className="text-base font-bold text-red-700 dark:text-red-400">
                  Intelligence Brief: {data.product_name}
                </h3>
                <p className="text-xs text-red-900/70 dark:text-red-300/80 mt-0.5">
                  Synthesized from {findings.length} live citations across {queriesUsed.length} queries.
                </p>
              </div>

              <Button
                onClick={handleAddToPortfolio}
                disabled={addProductMutation.isPending || addedSuccess}
                className="bg-red-600 hover:bg-red-700 text-white gap-2 shrink-0 text-xs shadow-xs"
              >
                {addedSuccess ? (
                  <>
                    <CheckCircle className="size-3.5 text-emerald-200" />
                    <span>Added to Portfolio!</span>
                  </>
                ) : (
                  <>
                    <Plus className="size-3.5" />
                    <span>Track in Portfolio</span>
                  </>
                )}
              </Button>
            </div>

            {/* AI Market Overview Cards */}
            {analysis && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Market Overview */}
                <div className="md:col-span-2 rounded-xl border border-border bg-card p-5 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-red-600 uppercase tracking-wider">
                    <TrendingUp className="size-4" />
                    <span>Market Landscape & Positioning</span>
                  </div>
                  <p className="text-sm text-foreground leading-relaxed">
                    {analysis.market_overview}
                  </p>

                  {analysis.strategic_advice && (
                    <div className="p-3 rounded-lg bg-muted/40 border border-border text-xs text-muted-foreground">
                      <strong className="text-foreground block mb-0.5">Strategic Recommendation:</strong>
                      {analysis.strategic_advice}
                    </div>
                  )}
                </div>

                {/* Key Numbers & Competitors */}
                <div className="rounded-xl border border-border bg-card p-5 space-y-4">
                  <div>
                    <span className="text-xs text-muted-foreground font-medium block">Observed Price Range</span>
                    <span className="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1 block">
                      {analysis.typical_price_range || '$19.99 - $34.99'}
                    </span>
                  </div>

                  {analysis.top_competitors && analysis.top_competitors.length > 0 && (
                    <div className="pt-3 border-t border-border">
                      <span className="text-xs font-semibold text-foreground block mb-2">Key Competitors Observed:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {analysis.top_competitors.map((comp: string, i: number) => (
                          <span key={i} className="text-xs bg-muted px-2.5 py-1 rounded-md text-foreground font-medium">
                            {comp}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Pros vs Cons / Customer Sentiment */}
            {analysis && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Selling Points */}
                <div className="rounded-xl border border-border bg-card p-5">
                  <div className="flex items-center gap-2 text-xs font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider mb-3">
                    <CheckCircle className="size-4" />
                    <span>Top Selling Points & Customer Demand</span>
                  </div>
                  <ul className="space-y-2 text-xs">
                    {analysis.key_selling_points?.map((pt: string, i: number) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-emerald-600 font-bold mt-0.5">•</span>
                        <span className="text-foreground">{pt}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Customer Pain Points */}
                <div className="rounded-xl border border-border bg-card p-5">
                  <div className="flex items-center gap-2 text-xs font-bold text-red-600 uppercase tracking-wider mb-3">
                    <AlertCircle className="size-4" />
                    <span>Customer Pain Points & Flaws to Exploit</span>
                  </div>
                  <ul className="space-y-2 text-xs">
                    {analysis.customer_pain_points?.map((pt: string, i: number) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-red-600 font-bold mt-0.5">•</span>
                        <span className="text-foreground">{pt}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Queries & Web Sources */}
            <div className="rounded-xl border border-border bg-card p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-foreground">
                  Grounded Search Angles & Live Findings ({findings.length})
                </h3>
                <ProvenanceBadge provenance="PUBLIC_NEWS" />
              </div>

              {/* Queries Planned */}
              <div className="flex flex-wrap gap-2">
                {queriesUsed.map((q, i) => (
                  <span key={i} className="text-xs border border-border px-2.5 py-1 rounded bg-muted/30 text-foreground font-mono">
                    {q}
                  </span>
                ))}
              </div>

              {/* Findings List */}
              <div className="divide-y divide-border pt-2">
                {findings.map((f: any, i: number) => (
                  <div key={i} className="py-3.5 space-y-1.5">
                    <p className="text-xs text-foreground leading-relaxed">{f.snippet}</p>
                    <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                      {f.source_url ? (
                        <a
                          href={f.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-red-600 hover:text-red-700 hover:underline"
                        >
                          <span className="truncate max-w-md">{f.source_url}</span>
                          <ExternalLink className="size-3 shrink-0" />
                        </a>
                      ) : (
                        <span>Public news observation</span>
                      )}
                      <span>{f.query}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Empty Initial State */}
        {!data && !researchMutation.isPending && (
          <div className="p-12 text-center border border-dashed border-border rounded-xl bg-card">
            <Search className="size-10 text-muted-foreground mx-auto mb-3 opacity-40" />
            <h3 className="text-base font-bold text-foreground">No Research Query Active</h3>
            <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
              Type any product name, brand, or ASIN above to query the market, evaluate competitor pricing, and uncover customer sentiment.
            </p>
          </div>
        )}
      </main>
    </AppShell>
  )
}
