import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useConfig, useUpdateConfig } from '@/hooks/useConfig'
import { toNum } from '@/lib/utils'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Spinner'
import { authApi } from '@/api/auth'
import { Save, ShieldCheck, ShieldOff } from 'lucide-react'
import type { SystemConfig } from '@/lib/types'

export default function SettingsPage() {
  const { data: config, isLoading } = useConfig()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size={32} />
      </div>
    )
  }

  if (!config) return null

  return (
    <div className="p-8 space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 text-sm mt-1">System-wide configuration.</p>
      </div>

      <SystemSection config={config} />
      <EnergyMonitorSection config={config} />
      <SolarSection config={config} />
      <CircuitSection config={config} />
      <SecuritySection config={config} />
    </div>
  )
}

function SystemSection({ config }: { config: SystemConfig }) {
  const update = useUpdateConfig()
  const [form, setForm] = useState({
    region: config.region,
    voltage: config.voltage,
    hostIp: config.hostIp,
    apiPort: config.apiPort,
  })
  const [saved, setSaved] = useState(false)

  const save = async () => {
    await update.mutateAsync(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const regionOpts = [
    { value: 'eu', label: 'Europe (EU)' },
    { value: 'na', label: 'North America (NA)' },
    { value: 'ap', label: 'Asia Pacific (AP)' },
  ]

  return (
    <Card>
      <p className="text-base font-semibold text-slate-900 mb-4">System</p>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Region"
            info="Tesla Fleet API region matching your vehicle's market (EU, North America, or Asia Pacific)."
            value={form.region}
            onChange={(e) => setForm((f) => ({ ...f, region: e.target.value as 'eu' | 'na' | 'ap' }))}
            options={regionOpts}
          />
          <Input
            label="Grid voltage (V)"
            info="Your home's nominal grid voltage. Used to convert power (watts) to current (amps)."
            type="number"
            value={form.voltage}
            onChange={(e) => setForm((f) => ({ ...f, voltage: toNum(e.target.valueAsNumber, f.voltage) }))}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Server host IP"
            info="IP address the API server binds to."
            value={form.hostIp}
            onChange={(e) => setForm((f) => ({ ...f, hostIp: e.target.value }))}
          />
          <Input
            label="API port"
            info="TCP port the API server listens on."
            type="number"
            value={form.apiPort}
            onChange={(e) => setForm((f) => ({ ...f, apiPort: toNum(e.target.valueAsNumber, f.apiPort) }))}
          />
        </div>
      </div>
      <SaveRow saving={update.isPending} saved={saved} onSave={save} error={update.error} />
    </Card>
  )
}

function EnergyMonitorSection({ config }: { config: SystemConfig }) {
  const update = useUpdateConfig()
  const [form, setForm] = useState({
    energyMonitorType: config.energyMonitorType,
    energyMonitorIp: config.energyMonitorIp,
  })
  const [saved, setSaved] = useState(false)

  const save = async () => {
    await update.mutateAsync(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const emTypes = [{ value: 'shelly_em', label: 'Shelly EM' }]

  return (
    <Card>
      <p className="text-base font-semibold text-slate-900 mb-4">Energy Monitor</p>
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Type"
          info="Energy monitor hardware model. Currently only Shelly EM is supported."
          value={form.energyMonitorType}
          onChange={(e) => setForm((f) => ({ ...f, energyMonitorType: e.target.value }))}
          options={emTypes}
        />
        <Input
          label="IP address"
          info="IP address of the energy monitor device on the local network."
          value={form.energyMonitorIp}
          onChange={(e) => setForm((f) => ({ ...f, energyMonitorIp: e.target.value }))}
        />
      </div>
      <SaveRow saving={update.isPending} saved={saved} onSave={save} error={update.error} />
    </Card>
  )
}

function SolarSection({ config }: { config: SystemConfig }) {
  const update = useUpdateConfig()
  const [form, setForm] = useState({
    solarSurplusEnabled: config.solarSurplusEnabled,
    solarTargetAmps: config.solarTargetAmps,
  })
  const [saved, setSaved] = useState(false)

  const save = async () => {
    await update.mutateAsync(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <Card>
      <p className="text-base font-semibold text-slate-900 mb-4">Solar Surplus</p>
      <div className="space-y-4">
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={form.solarSurplusEnabled}
            onChange={(e) =>
              setForm((f) => ({ ...f, solarSurplusEnabled: e.target.checked }))
            }
            className="rounded border-slate-300"
          />
          <span className="font-medium">Enable solar surplus charging</span>
        </label>
        <p className="text-xs text-slate-400">
          With solar panels, the energy monitor reads your grid feed-in. When
          it shows an export (surplus), the charger ramps up to absorb it
          instead of selling it back. When there's no surplus, each car idles at
          its minimum amps. Requires the energy monitor CT to be clamped on the
          grid feed-in point.
        </p>
        {form.solarSurplusEnabled && (
          <Input
            label="Grid import target (A)"
            info="How much grid import to tolerate while in solar mode. 0 = export nothing, use every surplus amp for charging. A small buffer around 1A avoids flapping between import/export."
            type="number"
            step={0.5}
            min={0}
            max={config.homeMaxAmps}
            value={form.solarTargetAmps}
            onChange={(e) =>
              setForm((f) => ({ ...f, solarTargetAmps: toNum(e.target.valueAsNumber, f.solarTargetAmps) }))
            }
          />
        )}
      </div>
      <SaveRow saving={update.isPending} saved={saved} onSave={save} error={update.error} />
    </Card>
  )
}

function CircuitSection({ config }: { config: SystemConfig }) {
  const update = useUpdateConfig()
  const [form, setForm] = useState({
    homeMaxAmps: config.homeMaxAmps,
    sleepTimeSecs: config.sleepTimeSecs,
    downStepPercentage: config.downStepPercentage,
    upStepPercentage: config.upStepPercentage,
    overloadStrategy: config.overloadStrategy,
    maxSessionDuration: config.maxSessionDuration,
  })
  const [saved, setSaved] = useState(false)

  const save = async () => {
    await update.mutateAsync(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const strategyOpts = [
    { value: 'proportional', label: 'Proportional' },
    { value: 'priority', label: 'Priority' },
  ]

  return (
    <Card>
      <p className="text-base font-semibold text-slate-900 mb-4">Circuit &amp; Strategy</p>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Home max amps (A)"
          info="Your main breaker or circuit limit. The app will not let total consumption exceed this."
          type="number"
          value={form.homeMaxAmps}
          onChange={(e) => setForm((f) => ({ ...f, homeMaxAmps: toNum(e.target.valueAsNumber, f.homeMaxAmps) }))}
        />
        <Select
          label="Overload strategy"
          info="How to distribute load reduction across vehicles when overload is detected."
          value={form.overloadStrategy}
          onChange={(e) =>
            setForm((f) => ({
              ...f,
              overloadStrategy: e.target.value as 'proportional' | 'priority',
            }))
          }
          options={strategyOpts}
        />
        <Input
          label="Sleep time (seconds)"
          info="Seconds between adjustment steps during an overload event. Lower values react faster but may cause more API calls."
          type="number"
          value={form.sleepTimeSecs}
          onChange={(e) => setForm((f) => ({ ...f, sleepTimeSecs: toNum(e.target.valueAsNumber, f.sleepTimeSecs) }))}
        />
        <Input
          label="Down step multiplier"
          info="First response when overload is detected. Current charge amps are multiplied by this factor (e.g. 0.5 = halve)."
          type="number"
          step={0.05}
          min={0.1}
          max={1}
          value={form.downStepPercentage}
          onChange={(e) => setForm((f) => ({ ...f, downStepPercentage: toNum(e.target.valueAsNumber, f.downStepPercentage) }))}
        />
        <Input
          label="Max session duration (seconds)"
          info="Maximum time a supervised overload session can run before ending. Prevents the car from staying stuck at a reduced limit if overload persists."
          type="number"
          step={30}
          min={60}
          max={3600}
          value={form.maxSessionDuration}
          onChange={(e) => setForm((f) => ({ ...f, maxSessionDuration: toNum(e.target.valueAsNumber, f.maxSessionDuration) }))}
        />
      </div>
      <SaveRow saving={update.isPending} saved={saved} onSave={save} error={update.error} />
    </Card>
  )
}

function SecuritySection({ config }: { config: SystemConfig }) {
  const qc = useQueryClient()
  const [mode, setMode] = useState<'view' | 'edit'>('view')
  const [form, setForm] = useState({
    enabled: config.auth.enabled,
    username: config.auth.username,
    password: '',
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      await authApi.setupBasicAuth(form)
      // Refresh config so the Security view reflects the new auth state.
      await qc.invalidateQueries({ queryKey: ['config'] })
      await qc.invalidateQueries({ queryKey: ['status'] })
      setSaved(true)
      setMode('view')
      setTimeout(() => setSaved(false), 2000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <p className="text-base font-semibold text-slate-900">Security</p>
        {mode === 'view' ? (
          <Button variant="secondary" size="sm" onClick={() => setMode('edit')}>
            Edit
          </Button>
        ) : null}
      </div>

      {mode === 'view' ? (
        <div className="flex items-center gap-3 text-sm">
          {config.auth.enabled ? (
            <>
              <ShieldCheck size={20} className="text-green-500" />
              <span className="text-slate-900">
                Basic auth enabled (user: <strong>{config.auth.username}</strong>)
              </span>
            </>
          ) : (
            <>
              <ShieldOff size={20} className="text-slate-400" />
              <span className="text-slate-500">
                Authentication disabled — vehicle controls (wake, charge limit,
                refresh) are locked until you enable it.
              </span>
            </>
          )}
        </div>
      ) : null}

      {mode === 'view' && (
        <p className="text-xs text-slate-400 mt-3">
          Basic Auth only covers the wake / charge-limit / refresh commands —
          the dashboard and the rest of the API stay open to anyone who can
          reach this port. Don't expose this app directly to the internet; put
          it behind a firewall, VPN, or a reverse proxy with its own auth.
        </p>
      )}

      {mode === 'edit' && (
        <div className="space-y-4">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
              className="rounded border-slate-300"
            />
            <span className="font-medium">Enable Basic Auth</span>
          </label>
          {form.enabled && (
            <>
              <Input
                label="Username"
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              />
              <Input
                label="New password"
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                hint="Leave blank to keep the existing password."
              />
            </>
          )}
          {error && <Alert type="error">{error}</Alert>}
          {saved && <Alert type="success">Saved!</Alert>}
          <div className="flex gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setForm({
                  enabled: config.auth.enabled,
                  username: config.auth.username,
                  password: '',
                })
                setMode('view')
              }}
            >
              Cancel
            </Button>
            <Button size="sm" onClick={save} loading={saving}>
              <Save size={14} />
              Save
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}

function SaveRow({
  saving,
  saved,
  onSave,
  error,
}: {
  saving: boolean
  saved: boolean
  onSave: () => void
  error: unknown
}) {
  return (
    <div className="flex items-center gap-4 mt-4">
      <Button onClick={onSave} loading={saving} size="sm">
        <Save size={14} />
        Save
      </Button>
      {saved && <span className="text-sm text-green-600">Saved!</span>}
      {Boolean(error) && (
        <span className="text-sm text-red-600">
          {error instanceof Error ? error.message : String(error)}
        </span>
      )}
    </div>
  )
}
