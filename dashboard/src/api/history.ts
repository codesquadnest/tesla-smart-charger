import { api } from './client'
import type { OverloadEvent } from '@/lib/types'

interface HistoryResponse {
  data: OverloadEvent[]
  count: number
}

export const historyApi = {
  get: (params?: {
    limit?: number
    vehicle_id?: string
    from_date?: string
    to_date?: string
  }) => {
    const qs = new URLSearchParams()
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.vehicle_id) qs.set('vehicle_id', params.vehicle_id)
    if (params?.from_date) qs.set('from_date', params.from_date)
    if (params?.to_date) qs.set('to_date', params.to_date)
    const query = qs.toString()
    return api.get<HistoryResponse>(`/api/v1/history${query ? `?${query}` : ''}`)
  },
}
