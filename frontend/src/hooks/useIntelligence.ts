import { useMutation, useQueryClient } from '@tanstack/react-query'
import { postIntelligence } from '@/lib/api'

export function useIntelligence() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: postIntelligence,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['activity'] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['products'] })
      void variables
    },
  })
}
