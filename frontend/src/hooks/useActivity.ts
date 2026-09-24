import { useQuery } from '@tanstack/react-query'
import { getActivity, getActivityStats } from '@/lib/api'

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

export function useActivityStats() {
  return useQuery({
    queryKey: ['activity', 'stats'],
    queryFn: getActivityStats,
  })
}
