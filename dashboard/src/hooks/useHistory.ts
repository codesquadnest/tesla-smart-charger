import { useQuery } from '@tanstack/react-query'
import { historyApi } from '@/api/history'

interface HistoryParams {
  limit?: number
  vehicle_id?: string
  from_date?: string
  to_date?: string
}

export function useHistory(params?: HistoryParams) {
  return useQuery({
    queryKey: ['history', params],
    queryFn: () => historyApi.get(params),
  })
}
