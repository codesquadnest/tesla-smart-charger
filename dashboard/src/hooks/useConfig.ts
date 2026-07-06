import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { configApi } from '@/api/config'
import type { SystemConfig } from '@/lib/types'

export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: configApi.get,
  })
}

export function useUpdateConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<SystemConfig>) => configApi.update(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] })
      qc.invalidateQueries({ queryKey: ['status'] })
    },
  })
}
