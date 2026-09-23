import { useMutation, useQueryClient } from '@tanstack/react-query'
import { postDecision } from '@/lib/api'

export function useDecision() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: postDecision,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activity'] })
    },
  })
}
