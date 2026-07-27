import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Lock, LockOpen } from 'lucide-react'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { authApi } from '@/api/auth'
import { signIn, signOut } from '@/lib/authStore'

interface Props {
  /** Whether the backend has Basic Auth configured. */
  authEnabled: boolean
  /** Whether this tab currently holds credentials. */
  signedIn: boolean
}

/**
 * Gate for the vehicle command controls.
 *
 * The backend fails closed: with Basic Auth unconfigured it refuses commands
 * outright, so there is nothing to sign into and we point at Settings instead.
 */
export function CommandAccess({ authEnabled, signedIn }: Props) {
  if (!authEnabled) {
    return (
      <Alert type="warning" title="Vehicle controls are disabled">
        Wake, charge limit and refresh change your car's physical state, so they
        require HTTP Basic Auth. It is not enabled, and the API refuses these
        commands until it is. Turn it on under{' '}
        <Link to="/settings" className="underline font-medium">
          Settings → Security
        </Link>
        . Note that Basic Auth only covers these commands — the rest of the
        API stays open, so this isn't a substitute for keeping the app off the
        public internet.
      </Alert>
    )
  }

  if (signedIn) return <SignedInBar />

  return <SignInForm />
}

function SignedInBar() {
  return (
    <div className="flex items-center justify-between gap-3 p-3 rounded-lg border border-green-200 bg-green-50 text-sm text-green-800">
      <span className="flex items-center gap-2">
        <LockOpen size={16} />
        Vehicle controls unlocked for this tab.
      </span>
      <Button variant="secondary" size="sm" onClick={signOut}>
        Lock
      </Button>
    </div>
  )
}

function SignInForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = () => {
    setBusy(true)
    setError(null)
    // Verified up front so a typo surfaces here rather than as a failed wake.
    authApi
      .verify(username, password)
      .then(() => signIn(username, password))
      .catch((e: Error) => setError(e.message))
      .finally(() => setBusy(false))
  }

  const canSubmit = username.trim().length > 0 && password.length > 0 && !busy

  return (
    <div className="p-4 rounded-lg border border-slate-200 bg-white space-y-3">
      <p className="flex items-center gap-2 text-sm font-medium text-slate-700">
        <Lock size={16} />
        Sign in to use vehicle controls
      </p>
      <p className="text-xs text-slate-500">
        Wake, charge limit and refresh require your Basic Auth credentials.
        They are kept in this tab only and cleared when you close it.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && canSubmit) submit()
          }}
        />
      </div>
      {error && <Alert type="error">{error}</Alert>}
      <Button size="sm" loading={busy} disabled={!canSubmit} onClick={submit}>
        Unlock controls
      </Button>
    </div>
  )
}
