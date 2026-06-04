import { useState } from 'react'
import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'
import { CheckCircle } from 'lucide-react'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

const emTypes = [{ value: 'shelly_em', label: 'Shelly EM' }]

export function Step7EnergyMonitor({ state, update, next, back }: Props) {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<'ok' | 'fail' | null>(null)

  const canContinue = state.energyMonitorIp.trim().length > 0

  const testConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await fetch(`http://${state.energyMonitorIp}/status/`, {
        signal: AbortSignal.timeout(5000),
      })
      setTestResult(res.ok ? 'ok' : 'fail')
    } catch {
      setTestResult('fail')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Energy Monitor</h2>
        <p className="text-sm text-slate-500 mt-1">
          Configure the device that measures your home&apos;s total power consumption.
        </p>
      </div>

      <div className="card p-6 space-y-5">
        <Select
          label="Energy monitor type"
          value={state.energyMonitorType}
          onChange={(e) => update({ energyMonitorType: e.target.value })}
          options={emTypes}
        />

        <Input
          label="Energy monitor IP address"
          placeholder="192.168.1.100"
          value={state.energyMonitorIp}
          onChange={(e) => update({ energyMonitorIp: e.target.value })}
        />

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={testConnection}
            loading={testing}
            disabled={!canContinue}
          >
            Test connection
          </Button>
          {testResult === 'ok' && (
            <span className="flex items-center gap-1 text-sm text-green-600">
              <CheckCircle size={16} /> Connected
            </span>
          )}
          {testResult === 'fail' && (
            <span className="text-sm text-red-600">Connection failed</span>
          )}
        </div>
      </div>

      <Alert type="info">
        The app will poll your energy monitor every 15 seconds. Make sure it&apos;s
        reachable from the server running this application.
      </Alert>

      <div className="flex gap-3">
        <Button variant="secondary" onClick={back}>
          Back
        </Button>
        <Button onClick={next} disabled={!canContinue} className="flex-1">
          Continue
        </Button>
      </div>
    </div>
  )
}
