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
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vehicles'] }),
  })
}

export function useUpdateVehicle(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<Vehicle>) => vehiclesApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vehicles'] })
      qc.invalidateQueries({ queryKey: ['vehicles', id] })
    },
  })
}

export function useRemoveVehicle() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => vehiclesApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vehicles'] }),
  })
}
