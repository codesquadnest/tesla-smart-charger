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

const strategyOptions = [
  {
    value: 'proportional',
    label: 'Proportional — reduce all vehicles equally',
  },
  {
    value: 'priority',
    label: 'Priority — reduce lowest-priority vehicle first',
  },
]

export function Step8CircuitStrategy({ state, update, next, back }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Circuit &amp; Strategy</h2>
        <p className="text-sm text-slate-500 mt-1">
          Configure your home circuit limits and overload response behaviour.
        </p>
      </div>

      <div className="card p-6 space-y-5">
        <Input
          label="Home max amps (A)"
          type="number"
          min={1}
          max={400}
          value={state.homeMaxAmps}
          onChange={(e) => update({ homeMaxAmps: Number(e.target.value) })}
          hint="Your home circuit breaker limit. The app will not let total consumption exceed this."
        />

        <Select
          label="Overload strategy"
          value={state.overloadStrategy}
          onChange={(e) => update({ overloadStrategy: e.target.value })}
          options={strategyOptions}
        />

        <Input
          label="Stabilisation sleep time (seconds)"
          type="number"
          min={5}
          max={300}
          value={state.sleepTimeSecs}
          onChange={(e) => update({ sleepTimeSecs: Number(e.target.value) })}
          hint="How long to wait between adjustment steps during an overload event."
        />

        <Input
          label="Initial downstep multiplier"
          type="number"
          min={0.1}
          max={1.0}
          step={0.05}
          value={state.downStepPercentage}
          onChange={(e) => update({ downStepPercentage: Number(e.target.value) })}
          hint="First response: multiply current charge amps by this factor (e.g. 0.5 = halve)."
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
