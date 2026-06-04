import { useState, useEffect } from 'react'
import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Spinner'
import { authApi } from '@/api/auth'
import type { TeslaVehicle } from '@/lib/types'
import { Car, CheckCircle } from 'lucide-react'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

export function Step5SelectVehicles({ state, update, next, back }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [vehicles, setVehicles] = useState<TeslaVehicle[]>([])

  const fetchVehicles = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await authApi.listVehicles(state.accessToken, state.proxyUrl)
      setVehicles(res.vehicles)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fetch vehicles.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (state.accessToken) fetchVehicles()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (v: TeslaVehicle) => {
    const already = state.selectedTeslaVehicles.find((s) => s.id === v.id)
    if (already) {
      update({
        selectedTeslaVehicles: state.selectedTeslaVehicles.filter((s) => s.id !== v.id),
      })
    } else {
      update({
        selectedTeslaVehicles: [
          ...state.selectedTeslaVehicles,
          { id: v.id, vin: v.vin, display_name: v.display_name },
        ],
      })
    }
  }

  const isSelected = (id: number) => state.selectedTeslaVehicles.some((s) => s.id === id)
  const canContinue = state.selectedTeslaVehicles.length > 0

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Select Vehicles</h2>
        <p className="text-sm text-slate-500 mt-1">
          Choose which vehicles you want to manage. You can add more later.
        </p>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner size={32} />
        </div>
      ) : (
        <div className="space-y-3">
          {vehicles.length === 0 && !loading && !error && (
            <Alert type="warning">
              No vehicles found on this Tesla account.{' '}
              <button onClick={fetchVehicles} className="underline font-medium">
                Retry
              </button>
            </Alert>
          )}
          {vehicles.map((v) => {
            const selected = isSelected(v.id)
            return (
              <button
                key={v.id}
                onClick={() => toggle(v)}
                className={`w-full text-left card p-4 flex items-center gap-4 transition-colors ${
                  selected
                    ? 'border-brand-500 bg-brand-50'
                    : 'hover:bg-slate-50'
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                    selected ? 'bg-brand-100' : 'bg-slate-100'
                  }`}
                >
                  <Car size={20} className={selected ? 'text-brand-600' : 'text-slate-500'} />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-slate-900">{v.display_name}</p>
                  <p className="text-xs text-slate-500">VIN: {v.vin}</p>
                  <p className="text-xs text-slate-400">
                    {v.state === 'online' ? (
                      <span className="text-green-600">● Online</span>
                    ) : (
                      <span className="text-slate-400">● {v.state}</span>
                    )}
                  </p>
                </div>
                {selected && <CheckCircle size={20} className="text-brand-600 shrink-0" />}
              </button>
            )
          })}
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="secondary" onClick={back}>
          Back
        </Button>
        <Button onClick={next} disabled={!canContinue} className="flex-1">
          Continue ({state.selectedTeslaVehicles.length} selected)
        </Button>
      </div>
    </div>
  )
}
