import { useState } from 'react'
import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Spinner'
import { configApi } from '@/api/config'
import { vehiclesApi } from '@/api/vehicles'
import { authApi } from '@/api/auth'
import { CheckCircle, Zap } from 'lucide-react'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

export function Step10Done({ state, back, finish }: Props) {
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  const applyConfig = async () => {
    setSaving(true)
    setError('')
    try {
      // 1. Save system config
      await configApi.update({
        homeMaxAmps: state.homeMaxAmps,
        voltage: state.voltage,
        region: state.region as 'eu' | 'na' | 'ap',
        energyMonitorIp: state.energyMonitorIp,
        energyMonitorType: state.energyMonitorType,
        sleepTimeSecs: state.sleepTimeSecs,
        downStepPercentage: state.downStepPercentage,
        overloadStrategy: state.overloadStrategy as 'proportional' | 'priority',
        configured: true,
      } as Parameters<typeof configApi.update>[0])

      // 2. Add each selected vehicle
      for (const [idx, v] of state.selectedTeslaVehicles.entries()) {
        const settings = state.vehicleSettings[v.id] ?? {
          chargerMaxAmps: 25,
          chargerMinAmps: 6,
          priority: idx + 1,
        }
        await vehiclesApi.add({
          name: v.display_name,
          vin: v.vin,
          teslaVehicleId: String(v.id),
          teslaAccessToken: state.accessToken,
          teslaRefreshToken: state.refreshToken,
          teslaHttpProxy: state.proxyUrl,
          teslaClientId: state.clientId,
          chargerMaxAmps: settings.chargerMaxAmps,
          chargerMinAmps: settings.chargerMinAmps,
          priority: settings.priority,
        })
      }

      // 3. Configure auth if enabled
      if (state.authEnabled) {
        await authApi.setupBasicAuth({
          enabled: true,
          username: state.authUsername,
          password: state.authPassword,
        })
      }

      setDone(true)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Setup failed. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {!done ? (
        <>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Review &amp; Finish</h2>
            <p className="text-sm text-slate-500 mt-1">
              Everything is configured. Click &ldquo;Apply&rdquo; to save your settings.
            </p>
          </div>

          <div className="card p-5 space-y-3 text-sm">
            <Row label="Region" value={state.region.toUpperCase()} />
            <Row label="Voltage" value={`${state.voltage}V`} />
            <Row label="Home max amps" value={`${state.homeMaxAmps}A`} />
            <Row label="Overload strategy" value={state.overloadStrategy} />
            <Row label="Energy monitor" value={`${state.energyMonitorType} @ ${state.energyMonitorIp}`} />
            <Row
              label="Vehicles"
              value={state.selectedTeslaVehicles.map((v) => v.display_name).join(', ')}
            />
            <Row label="Auth" value={state.authEnabled ? `Enabled (${state.authUsername})` : 'Disabled'} />
          </div>

          {error && <Alert type="error">{error}</Alert>}

          <div className="flex gap-3">
            <Button variant="secondary" onClick={back}>
              Back
            </Button>
            <Button onClick={applyConfig} loading={saving} className="flex-1">
              Apply &amp; Launch Dashboard
            </Button>
          </div>
        </>
      ) : (
        <div className="text-center space-y-6 py-4">
          <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto">
            <CheckCircle size={40} className="text-green-500" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-900">You&apos;re all set!</h2>
            <p className="text-slate-500 mt-2">
              Tesla Smart Charger is configured and ready to protect your home circuit.
            </p>
          </div>
          <Button onClick={finish} size="lg" className="w-full">
            <Zap size={18} />
            Go to Dashboard
          </Button>
        </div>
      )}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-900 text-right">{value || '—'}</span>
    </div>
  )
}
