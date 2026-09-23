import { useQuery } from '@tanstack/react-query'
import { getProduct, getProducts } from '@/lib/api'

export function useProducts() {
  return useQuery({ queryKey: ['products'], queryFn: getProducts })
}

export function useProduct(productId: string | undefined) {
  return useQuery({
    queryKey: ['products', productId],
    queryFn: () => getProduct(productId!),
    enabled: !!productId,
  })
}
