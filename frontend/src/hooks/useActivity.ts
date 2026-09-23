import { useQuery } from '@tanstack/react-query'
import { getActivity } from '@/lib/api'

export function useActivity(filters?: {
  product_name?: string
  agent?: string
  action?: string
  limit?: number
}) {
  return useQuery({
    queryKey: ['activity', filters],
    queryFn: () => getActivity(filters),
  })
}
