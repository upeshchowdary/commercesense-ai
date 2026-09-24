import { Link, useParams } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { CardSkeleton } from '@/components/shared/Skeletons'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { titleCase, formatCurrency } from '@/lib/utils'
import { useProductIntelligenceOverview } from '@/hooks/useIntelligenceModules'
import {
  InventoryTab,
  ListingTab,
  PricingTab,
  ReviewsTab,
  ScoreBadge,
} from '@/components/intelligence/ModuleTabs'

export default function ProductIntelligence() {
  const { productId } = useParams<{ productId: string }>()
  const overview = useProductIntelligenceOverview(productId)

  if (overview.isError) {
    return (
      <AppShell title="Product Intelligence">
        <ErrorState description="Couldn't load this product's intelligence overview." onRetry={() => overview.refetch()} />
      </AppShell>
    )
  }
  if (overview.isLoading || !overview.data) {
    return (
      <AppShell title="Product Intelligence">
        <CardSkeleton lines={6} />
      </AppShell>
    )
  }

  const data = overview.data

  return (
    <AppShell title={data.product.name}>
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold text-foreground">{data.product.name}</h2>
              <StatusBadge status="SYNTHETIC" />
              <Link to={`/products/${productId}`} className="text-xs text-accent hover:underline">
                Full product page →
              </Link>
            </div>
            <p className="text-sm text-muted-foreground">
              {data.product.category} · {formatCurrency(data.product.base_price)}
            </p>
          </div>
          <Card className="p-4 text-center">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Attention Score</p>
            <p className={`text-3xl font-bold ${data.attention_score >= 50 ? 'text-danger' : data.attention_score >= 20 ? 'text-warning' : 'text-success'}`}>
              {data.attention_score}
              <span className="text-base text-muted-foreground">/100</span>
            </p>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Attention Summary</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {Object.entries(data.components).map(([key, value]) => (
              <div key={key} className="rounded-lg border border-border p-3 text-center">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{titleCase(key)}</p>
                <p className="mt-1 text-lg font-semibold text-foreground">{value}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Issues</CardTitle>
          </CardHeader>
          <CardContent>
            {data.top_issues.length === 0 ? (
              <EmptyState title="No urgent issues detected" className="border-none py-6" />
            ) : (
              <ul className="flex flex-col gap-2">
                {data.top_issues.map((issue, i) => (
                  <li key={i} className="rounded-lg border border-border px-3 py-2 text-sm text-foreground">
                    {issue}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Tabs defaultValue="listing">
          <TabsList>
            <TabsTrigger value="listing">
              Listing <ScoreBadge score={data.listing_score} />
            </TabsTrigger>
            <TabsTrigger value="pricing">Pricing</TabsTrigger>
            <TabsTrigger value="reviews">Reviews</TabsTrigger>
            <TabsTrigger value="inventory">Inventory</TabsTrigger>
          </TabsList>

          <TabsContent value="listing">
            <ListingTab productId={productId!} />
          </TabsContent>
          <TabsContent value="pricing">
            <PricingTab productId={productId!} />
          </TabsContent>
          <TabsContent value="reviews">
            <ReviewsTab productId={productId!} />
          </TabsContent>
          <TabsContent value="inventory">
            <InventoryTab productId={productId!} />
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}
