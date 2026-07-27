import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
}

export function Step9Security({ state, update, next, back }: Props) {
  const valid =
    !state.authEnabled ||
    (state.authUsername.trim().length > 0 && state.authPassword.trim().length >= 8)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Security</h2>
        <p className="text-sm text-slate-500 mt-1">
          Optionally protect the dashboard and API with a username and password.
        </p>
      </div>

      <Alert type="warning" title="Vehicle controls require authentication">
        Wake, charge limit and refresh change your car's physical state, so the
        API refuses them unless Basic Auth is enabled. Leave it off and those
        controls stay locked in the dashboard — the energy monitor and automatic
        overload handling keep working either way. You can enable it later under
        Settings → Security.
      </Alert>

      <Alert type="info">
        Basic Auth here only protects the wake / charge-limit / refresh
        commands above — the dashboard and the rest of the API stay open to
        anyone who can reach this port. Don't expose this app directly to the
        internet; put it behind a firewall, VPN, or a reverse proxy that adds
        its own authentication.
      </Alert>

      <div className="card p-6 space-y-5">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            checked={state.authEnabled}
            onChange={(e) => update({ authEnabled: e.target.checked })}
          />
          <span className="text-sm font-medium text-slate-700">
            Enable HTTP Basic Auth
          </span>
        </label>

        {state.authEnabled && (
          <>
            <Input
              label="Username"
              info="HTTP Basic Auth username. Used to access the dashboard and API."
              value={state.authUsername}
              onChange={(e) => update({ authUsername: e.target.value.trim() })}
            />
            <Input
              label="Password"
              info="HTTP Basic Auth password. Minimum 8 characters recommended."
              type="password"
              value={state.authPassword}
              onChange={(e) => update({ authPassword: e.target.value.trim() })}
              hint="Minimum 8 characters."
              error={
                state.authPassword.trim().length > 0 &&
                state.authPassword.trim().length < 8
                  ? 'Password must be at least 8 characters.'
                  : undefined
              }
            />
          </>
        )}
      </div>

      <div className="flex gap-3">
        <Button variant="secondary" onClick={back}>
          Back
        </Button>
        <Button onClick={next} disabled={!valid} className="flex-1">
          Continue
        </Button>
      </div>
    </div>
  )
}
