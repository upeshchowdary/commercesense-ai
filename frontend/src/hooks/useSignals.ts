import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getSignal, getSignals, runSignalDetection } from '@/lib/api'

export function useSignals(filters?: { severity?: string; type?: string; product_id?: string }) {
  return useQuery({
    queryKey: ['signals', filters],
    queryFn: () => getSignals(filters),
  })
}

export function useSignal(id: number | undefined) {
  return useQuery({
    queryKey: ['signals', 'detail', id],
    queryFn: () => getSignal(id!),
    enabled: id !== undefined,
  })
}

export function useRunSignalDetection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: runSignalDetection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] })
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['evaluation'] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}
