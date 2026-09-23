import { useMutation, useQueryClient } from '@tanstack/react-query'
import { postResearch } from '@/lib/api'

export function useResearch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: postResearch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activity'] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}
