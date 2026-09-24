import { Boxes, Search, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { SeverityBadge } from '@/components/shared/SeverityBadge'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { ListSkeleton } from '@/components/shared/Skeletons'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatCurrency } from '@/lib/utils'
import type { ProductSummary } from '@/lib/types'
import { useProducts } from '@/hooks/useProducts'

// Spec §32 filter syntax: listing:needs-attention, pricing:below-margin,
// reviews:emerging, inventory:stockout-risk — parsed client-side out of
// the free-text search box, no dedicated backend search API.
const MODULE_FILTER_PATTERN = /(listing|pricing|reviews|inventory):(\S+)/gi

function moduleFilterMatches(p: ProductSummary, module: string, value: string): boolean {
  switch (module) {
    case 'listing':
      return value === 'needs-attention' ? (p.listing_score ?? 100) < 70 : true
    case 'pricing':
      return value === 'below-margin' ? p.price_state === 'BELOW_MARGIN_FLOOR' : true
    case 'reviews':
      return value === 'emerging' ? p.review_has_emerging_issue : true
    case 'inventory':
      return value === 'stockout-risk' ? p.inventory_category === 'STOCKOUT_RISK' : true
    default:
      return true
  }
}

export default function Products() {
  const navigate = useNavigate()
  const { data, isLoading, isError, refetch } = useProducts()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('all')
  const [severity, setSeverity] = useState('all')

  const categories = useMemo(
    () => Array.from(new Set((data ?? []).map((p) => p.category))).sort(),
    [data],
  )

  const { moduleFilters, freeText } = useMemo(() => {
    const filters: { module: string; value: string }[] = []
    let rest = query
    for (const m of query.matchAll(MODULE_FILTER_PATTERN)) {
      filters.push({ module: m[1].toLowerCase(), value: m[2].toLowerCase() })
      rest = rest.replace(m[0], '')
    }
    return { moduleFilters: filters, freeText: rest.trim() }
  }, [query])

  const filtered = useMemo(() => {
    return (data ?? []).filter((p) => {
      if (freeText && !p.name.toLowerCase().includes(freeText.toLowerCase())) return false
      if (category !== 'all' && p.category !== category) return false
      if (severity === 'flagged' && p.signal_count === 0) return false
      if (severity === 'high' && p.highest_severity !== 'high') return false
      if (severity === 'healthy' && p.signal_count > 0) return false
      if (moduleFilters.some((f) => !moduleFilterMatches(p, f.module, f.value))) return false
      return true
    })
  }, [data, freeText, category, severity, moduleFilters])

  return (
    <AppShell title="Products">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, or filter: listing:needs-attention pricing:below-margin reviews:emerging inventory:stockout-risk"
              className="pl-8"
            />
          </div>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="w-full sm:w-44">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {categories.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger className="w-full sm:w-44">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All products</SelectItem>
              <SelectItem value="flagged">Flagged</SelectItem>
              <SelectItem value="high">High severity</SelectItem>
              <SelectItem value="healthy">Healthy</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {isError ? (
          <ErrorState description="Couldn't load products." onRetry={() => refetch()} />
        ) : isLoading ? (
          <ListSkeleton rows={8} />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={Boxes}
            title="No products match"
            description={
              (data ?? []).length === 0
                ? 'No products yet. Run `python data/generate_synthetic_data.py` from the project root.'
                : 'Try a different search or filter.'
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((p) => (
              <Link key={p.product_id} to={`/products/${p.product_id}`}>
                <Card className="flex h-full flex-col gap-3 p-4 transition-colors hover:border-primary/40">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-semibold text-foreground">{p.name}</span>
                      <span className="text-xs text-muted-foreground">{p.category}</span>
                    </div>
                    <StatusBadge status="SYNTHETIC" />
                  </div>
                  <IntelligenceBadgeRow product={p} />
                  <div className="mt-auto flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground">
                      {formatCurrency(p.base_price)}
                    </span>
                    <div className="flex items-center gap-2">
                      {p.signal_count > 0 && (
                        <span className="text-xs text-muted-foreground">
                          {p.signal_count} signal{p.signal_count === 1 ? '' : 's'}
                        </span>
                      )}
                      <SeverityBadge severity={p.highest_severity} />
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-1 w-full"
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      navigate(`/products/${p.product_id}/intelligence`)
                    }}
                  >
                    <Sparkles className="size-3.5" />
                    Full Intelligence
                  </Button>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}

// Spec §28.3 Intelligence Overview Cards, condensed onto the Products
// list. Each dot is a quick module-health read; the full breakdown lives
// on the Product Bundle View one click away.
function IntelligenceBadgeRow({ product }: { product: ProductSummary }) {
  const badges: { label: string; tone: 'success' | 'warning' | 'danger' }[] = [
    {
      label: `Listing ${product.listing_score ?? '–'}`,
      tone: product.listing_score === null ? 'warning' : product.listing_score >= 70 ? 'success' : 'danger',
    },
    {
      label: 'Pricing',
      tone: product.price_state === 'BELOW_MARGIN_FLOOR' ? 'danger'
        : product.price_state === 'HEALTHY_RANGE' ? 'success' : 'warning',
    },
    {
      label: 'Reviews',
      tone: product.review_has_emerging_issue ? 'danger'
        : (product.review_negative_pct ?? 0) >= 15 ? 'warning' : 'success',
    },
    {
      label: 'Inventory',
      tone: product.inventory_category === 'STOCKOUT_RISK' ? 'danger'
        : product.inventory_category === 'LOW_COVER' || product.inventory_category === 'OVERSTOCK' ? 'warning' : 'success',
    },
  ]
  return (
    <div className="flex flex-wrap gap-1">
      {badges.map((b) => (
        <span
          key={b.label}
          className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
            b.tone === 'success' ? 'bg-success/10 text-success'
              : b.tone === 'danger' ? 'bg-danger/10 text-danger' : 'bg-warning/10 text-warning'
          }`}
        >
          {b.label}
        </span>
      ))}
    </div>
  )
}
