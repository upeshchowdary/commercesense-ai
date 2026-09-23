import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getInventoryIntelligence,
  getListingIntelligence,
  getPricingIntelligence,
  getProductIntelligenceOverview,
  getReviewIntelligence,
  postInventoryAnalyze,
  postInventoryApprove,
  postInventoryForecast,
  postInventorySimulate,
  postListingAnalyze,
  postListingApprove,
  postListingRewrite,
  postPricingAnalyze,
  postPricingApprove,
  postPricingSimulate,
  postReviewAnalyze,
  postReviewApprove,
} from '@/lib/api'

export function useProductIntelligenceOverview(productId: string | undefined) {
  return useQuery({
    queryKey: ['intelligence', 'overview', productId],
    queryFn: () => getProductIntelligenceOverview(productId!),
    enabled: !!productId,
  })
}

// --- Listing ---
export function useListingIntelligence(productId: string | undefined) {
  return useQuery({
    queryKey: ['intelligence', 'listing', productId],
    queryFn: () => getListingIntelligence(productId!),
    enabled: !!productId,
  })
}
export function useListingAnalyze() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (productId: string) => postListingAnalyze(productId),
    onSuccess: (_d, productId) => qc.invalidateQueries({ queryKey: ['intelligence', 'listing', productId] }),
  })
}
export function useListingRewrite() {
  return useMutation({ mutationFn: (productId: string) => postListingRewrite(productId, true) })
}
export function useListingApprove() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, body }: { productId: string; body: Parameters<typeof postListingApprove>[1] }) =>
      postListingApprove(productId, body),
    onSuccess: (_d, { productId }) => qc.invalidateQueries({ queryKey: ['intelligence', 'overview', productId] }),
  })
}

// --- Pricing ---
export function usePricingIntelligence(productId: string | undefined) {
  return useQuery({
    queryKey: ['intelligence', 'pricing', productId],
    queryFn: () => getPricingIntelligence(productId!),
    enabled: !!productId,
  })
}
export function usePricingAnalyze() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, useLiveResearch }: { productId: string; useLiveResearch?: boolean }) =>
      postPricingAnalyze(productId, useLiveResearch),
    onSuccess: (_d, { productId }) => qc.invalidateQueries({ queryKey: ['intelligence', 'pricing', productId] }),
  })
}
export function usePricingSimulate() {
  return useMutation({
    mutationFn: ({ productId, newPrice, adSpendLevels }: { productId: string; newPrice: number; adSpendLevels?: number[] }) =>
      postPricingSimulate(productId, newPrice, adSpendLevels),
  })
}
export function usePricingApprove() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, body }: { productId: string; body: Parameters<typeof postPricingApprove>[1] }) =>
      postPricingApprove(productId, body),
    onSuccess: (_d, { productId }) => qc.invalidateQueries({ queryKey: ['intelligence', 'overview', productId] }),
  })
}

// --- Review ---
export function useReviewIntelligence(productId: string | undefined) {
  return useQuery({
    queryKey: ['intelligence', 'review', productId],
    queryFn: () => getReviewIntelligence(productId!),
    enabled: !!productId,
  })
}
export function useReviewAnalyze() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (productId: string) => postReviewAnalyze(productId),
    onSuccess: (_d, productId) => qc.invalidateQueries({ queryKey: ['intelligence', 'review', productId] }),
  })
}
export function useReviewApprove() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, body }: { productId: string; body: Parameters<typeof postReviewApprove>[1] }) =>
      postReviewApprove(productId, body),
    onSuccess: (_d, { productId }) => qc.invalidateQueries({ queryKey: ['intelligence', 'overview', productId] }),
  })
}

// --- Inventory ---
export function useInventoryIntelligence(productId: string | undefined) {
  return useQuery({
    queryKey: ['intelligence', 'inventory', productId],
    queryFn: () => getInventoryIntelligence(productId!),
    enabled: !!productId,
  })
}
export function useInventoryAnalyze() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (productId: string) => postInventoryAnalyze(productId),
    onSuccess: (_d, productId) => qc.invalidateQueries({ queryKey: ['intelligence', 'inventory', productId] }),
  })
}
export function useInventoryForecast() {
  return useMutation({
    mutationFn: ({ productId, daysAhead }: { productId: string; daysAhead?: number }) => postInventoryForecast(productId, daysAhead),
  })
}
export function useInventorySimulate() {
  return useMutation({
    mutationFn: ({ productId, reorderQuantity, leadTimeDays }: { productId: string; reorderQuantity: number; leadTimeDays?: number }) =>
      postInventorySimulate(productId, reorderQuantity, leadTimeDays),
  })
}
export function useInventoryApprove() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, body }: { productId: string; body: Parameters<typeof postInventoryApprove>[1] }) =>
      postInventoryApprove(productId, body),
    onSuccess: (_d, { productId }) => qc.invalidateQueries({ queryKey: ['intelligence', 'overview', productId] }),
  })
}
