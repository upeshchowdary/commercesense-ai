import { useQuery } from '@tanstack/react-query'
import { getEvaluation } from '@/lib/api'

export function useEvaluation() {
  return useQuery({ queryKey: ['evaluation'], queryFn: getEvaluation })
}
