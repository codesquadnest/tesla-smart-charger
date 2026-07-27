import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { vehiclesApi } from '@/api/vehicles'
import type { Vehicle } from '@/lib/types'

export function useVehicles() {
  return useQuery({
    queryKey: ['vehicles'],
    queryFn: vehiclesApi.list,
  })
}

export function useVehicle(id: string) {
  return useQuery({
    queryKey: ['vehicles', id],
    queryFn: () => vehiclesApi.get(id),
    enabled: !!id,
  })
}

export function useAddVehicle() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<Vehicle>) => vehiclesApi.add(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vehicles'] })
      qc.invalidateQueries({ queryKey: ['status'] })
    },
  })
}

export function useUpdateVehicle(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<Vehicle>) => vehiclesApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vehicles'] })
      qc.invalidateQueries({ queryKey: ['vehicles', id] })
      qc.invalidateQueries({ queryKey: ['status'] })
    },
  })
}

export function useRemoveVehicle() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => vehiclesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vehicles'] })
      qc.invalidateQueries({ queryKey: ['status'] })
    },
  })
}

/**
 * Force a telemetry refetch for one vehicle.
 *
 * The backend refresh is non-blocking, so the invalidated status query first
 * comes back with `refreshing: true` and the real data lands on a later poll.
 */
export function useRefreshVehicle() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => vehiclesApi.refresh(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['status'] }),
  })
}

export function useWakeVehicle() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => vehiclesApi.wake(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['status'] }),
  })
}

export function useSetChargeLimit(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (percent: number) => vehiclesApi.setChargeLimit(id, percent),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['status'] }),
  })
}
