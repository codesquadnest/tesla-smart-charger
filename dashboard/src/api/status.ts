import { api } from './client'
import type { SystemStatus } from '@/lib/types'

export const statusApi = {
  get: () => api.get<SystemStatus>('/api/v1/status'),
}
