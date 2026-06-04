import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

const regionOptions = [
  { value: 'eu', label: 'Europe (EU)' },
  { value: 'na', label: 'North America (NA)' },
  { value: 'ap', label: 'Asia Pacific (AP)' },
]

export function Step2RegionVoltage({ state, update, next, back }: Props) {
  const voltagePresets = state.region === 'na' ? 120 : 230

  const handleRegionChange = (r: string) => {
    update({ region: r, voltage: r === 'na' ? 120 : 230 })
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Region &amp; Voltage</h2>
        <p className="text-sm text-slate-500 mt-1">
          Select your Tesla Fleet API region and your home grid voltage.
        </p>
      </div>

      <div className="card p-6 space-y-5">
        <Select
          label="Tesla Fleet API region"
          value={state.region}
          onChange={(e) => handleRegionChange(e.target.value)}
          options={regionOptions}
        />

        <Input
          label="Home grid voltage (V)"
          type="number"
          min={100}
          max={480}
          step={10}
          value={state.voltage}
          onChange={(e) => update({ voltage: Number(e.target.value) })}
          hint={`Preset for ${state.region.toUpperCase()}: ${voltagePresets}V`}
        />
      </div>

      <div className="flex gap-3">
        <Button variant="secondary" onClick={back}>
          Back
        </Button>
        <Button onClick={next} className="flex-1">
          Continue
        </Button>
      </div>
    </div>
  )
}
