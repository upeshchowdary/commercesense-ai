import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  Download,
  ArrowRight,
  Plus,
  X,
} from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { postAddProduct } from '@/lib/api'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { useProducts } from '@/hooks/useProducts'
import { cn } from '@/lib/utils'

export default function Products() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: products = [], isLoading } = useProducts()
  const [modalOpen, setModalOpen] = useState(false)
  const [newProd, setNewProd] = useState({
    product_id: '',
    name: '',
    category: 'Kitchen',
    base_price: 29.99,
    cogs: 8.50,
  })

  const addMutation = useMutation({
    mutationFn: postAddProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      setModalOpen(false)
      setNewProd({ product_id: '', name: '', category: 'Kitchen', base_price: 29.99, cogs: 8.50 })
    },
  })

  const [query, setQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('ALL')
  const [selectedStockStatus] = useState('ALL')

  const categories = useMemo(
    () => ['ALL', ...Array.from(new Set(products.map((p) => p.category))).sort()],
    [products],
  )

  const filtered = useMemo(() => {
    return products.filter((p) => {
      const matchQuery =
        p.name.toLowerCase().includes(query.toLowerCase()) ||
        p.product_id.toLowerCase().includes(query.toLowerCase()) ||
        p.category.toLowerCase().includes(query.toLowerCase())

      const matchCat = selectedCategory === 'ALL' || p.category === selectedCategory
      const matchStock =
        selectedStockStatus === 'ALL' ||
        (selectedStockStatus === 'RISK' &&
          (p.inventory_category === 'STOCKOUT_RISK' || p.inventory_category === 'LOW_COVER')) ||
        (selectedStockStatus === 'HEALTHY' && p.inventory_category === 'HEALTHY') ||
        (selectedStockStatus === 'OVERSTOCK' && p.inventory_category === 'OVERSTOCK')

      return matchQuery && matchCat && matchStock
    })
  }, [products, query, selectedCategory, selectedStockStatus])

  const exportCsv = () => {
    const headers = ['Product ID', 'Name', 'Category', 'Base Price', 'Inventory State', 'Pricing State', 'Attention Score']
    const rows = filtered.map((p) => [
      p.product_id,
      `"${p.name.replace(/"/g, '""')}"`,
      p.category,
      p.base_price.toFixed(2),
      p.inventory_category || 'HEALTHY',
      p.price_state || 'HEALTHY_RANGE',
      p.attention_score || 0,
    ])
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `commercesense_portfolio_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <AppShell>
      <Topbar
        title="Product Portfolio"
        actions={
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={() => setModalOpen(true)}
              className="gap-1.5 text-xs h-8 bg-red-600 hover:bg-red-700 text-white shadow-xs"
            >
              <Plus className="size-3.5" />
              <span>Add Real Product</span>
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={exportCsv}
              className="gap-1.5 text-xs h-8"
            >
              <Download className="size-3.5" />
              <span>Export CSV</span>
            </Button>
          </div>
        }
      />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Amazon Seller Portfolio Grid
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Multi-metric inventory cover, landed price states, review sentiment risks, and attention scores across your catalog.
            </p>
          </div>
          <ProvenanceBadge provenance="AMAZON_OFFICIAL" />
        </div>

        {/* Filter Controls Bar */}
        <div className="mb-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search product title or ASIN..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-border rounded-md bg-card text-foreground"
            />
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={cn(
                  'px-3 py-1 rounded-md text-xs font-semibold border transition-colors whitespace-nowrap',
                  selectedCategory === cat
                    ? 'border-red-600 bg-red-50 text-red-700 dark:bg-red-950/40 dark:border-red-500 dark:text-red-400'
                    : 'border-border bg-card text-muted-foreground hover:text-foreground',
                )}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Data Grid Table */}
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-900 border-b border-border text-slate-600 dark:text-slate-400 uppercase font-semibold text-[10.5px]">
                <tr>
                  <th className="p-3.5">Product Title</th>
                  <th className="p-3.5">Category</th>
                  <th className="p-3.5">Price</th>
                  <th className="p-3.5">Stock Condition</th>
                  <th className="p-3.5">Price State</th>
                  <th className="p-3.5">Negative VOC</th>
                  <th className="p-3.5">Attention Score</th>
                  <th className="p-3.5">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {isLoading ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-muted-foreground animate-pulse">
                      Loading product catalog...
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-muted-foreground">
                      No products matching query.
                    </td>
                  </tr>
                ) : (
                  filtered.map((p) => (
                    <tr
                      key={p.product_id}
                      onClick={() => navigate(`/products/${encodeURIComponent(p.product_id)}`)}
                      className="hover:bg-muted/30 cursor-pointer transition-colors"
                    >
                      <td className="p-3.5 font-medium text-foreground max-w-xs">
                        <div className="flex flex-col">
                          <span className="truncate">{p.name}</span>
                          <span className="font-mono text-[10px] text-muted-foreground">
                            {p.product_id}
                          </span>
                        </div>
                      </td>
                      <td className="p-3.5 text-muted-foreground">{p.category}</td>
                      <td className="p-3.5 font-mono font-bold">${p.base_price.toFixed(2)}</td>
                      <td className="p-3.5">
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded text-[10px] font-bold tracking-tight',
                            p.inventory_category === 'STOCKOUT_RISK' && 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400',
                            p.inventory_category === 'LOW_COVER' && 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400',
                            p.inventory_category === 'HEALTHY' && 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400',
                            p.inventory_category === 'OVERSTOCK' && 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
                          )}
                        >
                          {p.inventory_category || 'HEALTHY'}
                        </span>
                      </td>
                      <td className="p-3.5 font-mono text-[11px] text-muted-foreground">
                        {p.price_state || 'HEALTHY_RANGE'}
                      </td>
                      <td className="p-3.5">
                        {p.review_negative_pct !== null && p.review_negative_pct !== undefined ? (
                          <span
                            className={cn(
                              'font-mono text-xs font-semibold',
                              p.review_negative_pct > 20 ? 'text-red-600' : 'text-muted-foreground',
                            )}
                          >
                            {p.review_negative_pct.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-[11px]">—</span>
                        )}
                      </td>
                      <td className="p-3.5 font-mono font-bold">
                        <span
                          className={cn(
                            'px-1.5 py-0.5 rounded text-[11px]',
                            (p.attention_score || 0) > 60
                              ? 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400'
                              : (p.attention_score || 0) > 30
                              ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400'
                              : 'text-muted-foreground',
                          )}
                        >
                          {p.attention_score || 0}
                        </span>
                      </td>
                      <td className="p-3.5">
                        <span className="text-xs font-semibold text-red-600 hover:underline flex items-center gap-1">
                          Workspace <ArrowRight className="size-3" />
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl p-6 max-w-md w-full shadow-lg">
            <div className="flex items-center justify-between pb-3 border-b border-border mb-4">
              <h3 className="text-base font-bold text-foreground">Add Real Product / ASIN</h3>
              <button onClick={() => setModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="size-4" />
              </button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); addMutation.mutate(newProd); }} className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold block text-foreground mb-1">ASIN / Product ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. B08N5WRWNW or SKU-001"
                  value={newProd.product_id}
                  onChange={(e) => setNewProd({ ...newProd, product_id: e.target.value.trim() })}
                  className="w-full px-3 py-1.5 text-xs border rounded bg-background"
                />
              </div>
              <div>
                <label className="text-xs font-semibold block text-foreground mb-1">Product Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Stainless Steel Garlic Press with Cleaning Brush"
                  value={newProd.name}
                  onChange={(e) => setNewProd({ ...newProd, name: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs border rounded bg-background"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold block text-foreground mb-1">Category</label>
                  <select
                    value={newProd.category}
                    onChange={(e) => setNewProd({ ...newProd, category: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-xs border rounded bg-background"
                  >
                    <option value="Kitchen">Kitchen</option>
                    <option value="Electronics">Electronics</option>
                    <option value="Office">Office</option>
                    <option value="Beauty">Beauty</option>
                    <option value="Sports">Sports</option>
                    <option value="Home & Garden">Home & Garden</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold block text-foreground mb-1">Base Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={newProd.base_price}
                    onChange={(e) => setNewProd({ ...newProd, base_price: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-1.5 text-xs border rounded bg-background"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold block text-foreground mb-1">Unit COGS ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={newProd.cogs}
                  onChange={(e) => setNewProd({ ...newProd, cogs: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-1.5 text-xs border rounded bg-background"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t border-border mt-4">
                <Button type="button" variant="outline" size="sm" onClick={() => setModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={addMutation.isPending} className="bg-red-600 hover:bg-red-700 text-white shadow-xs">
                  {addMutation.isPending ? 'Saving...' : 'Save Product'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>

  )
}
