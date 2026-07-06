import { useState } from 'react'
import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Alert'
import { authApi } from '@/api/auth'
import { Input } from '@/components/ui/Input'
import { ExternalLink, CheckCircle, ClipboardPaste } from 'lucide-react'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

export function Step4TeslaAuth({ state, update, next, back }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showManual, setShowManual] = useState(false)
  const [callbackUrl, setCallbackUrl] = useState('')
  const [manualLoading, setManualLoading] = useState(false)
  const authorized = !!state.accessToken

  const handleAuthorize = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await authApi.start({
        client_id: state.clientId,
        client_secret: state.clientSecret,
        redirect_uri: state.redirectUri,
        proxy_url: state.proxyUrl,
        region: state.region,
      })

      // Open Tesla auth in a popup window
      const popup = window.open(
        res.auth_url,
        'tesla-auth',
        'width=600,height=700,scrollbars=yes'
      )
      if (!popup) {
        setError('Popup blocked by browser. Please allow popups and try again.')
        setLoading(false)
        return
      }

      // The callback page is served from our own origin (redirectUri).
      const expectedOrigin = new URL(state.redirectUri).origin
      let tokensReceived = false
      const finishFromPopup = (access_token: string, refresh_token: string) => {
        tokensReceived = true
        window.clearInterval(closedTimer)
        window.removeEventListener('message', handler)
        window.removeEventListener('hashchange', hashHandler)
        update({ accessToken: access_token, refreshToken: refresh_token })
        popup.close()
        setLoading(false)
        // Clear the hash so tokens don't linger in the address bar / browser history
        window.history.replaceState(null, '', window.location.pathname + window.location.search)
      }

      // Poll for hash fallback (popup writes tokens to opener location.hash).
      const tryHashFallback = () => {
        try {
          const hash = window.location.hash
          if (hash.startsWith('#tsc-oauth=')) {
            const raw = decodeURIComponent(hash.slice('#tsc-oauth='.length))
            const data = JSON.parse(raw)
            if (data.access_token && data.refresh_token) {
              finishFromPopup(data.access_token, data.refresh_token)
              return true
            }
          }
        } catch {
          /* ignore */
        }
        return false
      }

      // Reset loading if the user closes the popup without completing.
      const closedTimer = window.setInterval(() => {
        if (popup.closed) {
          // Try hash fallback before giving up
          if (!tryHashFallback() && !tokensReceived) {
            setShowManual(true)
          }
          window.clearInterval(closedTimer)
          window.removeEventListener('message', handler)
          window.removeEventListener('hashchange', hashHandler)
          setLoading(false)
        }
      }, 500)

      // Listen for the callback result — validate origin, not event.source,
      // since the popup navigates cross-origin (Tesla → our server) and the
      // browser may return a different WindowProxy for event.source after
      // those navigations.
      const handler = (event: MessageEvent) => {
        if (event.origin !== expectedOrigin) return
        if (event.data?.type === 'tesla-auth-callback') {
          const { access_token, refresh_token } = event.data
          if (access_token && refresh_token) {
            finishFromPopup(access_token, refresh_token)
          } else {
            setError('Authorization failed — no tokens received.')
          }
        }
      }
      window.addEventListener('message', handler)

      // Hash-change fallback for when postMessage is not delivered (some
      // reverse-proxy / browser combinations block cross-origin messaging).
      const hashHandler = () => tryHashFallback()
      window.addEventListener('hashchange', hashHandler)
      // Keep `loading` true until the callback fires or the popup closes.
    } catch (e: unknown) {
      setShowManual(true)
      setError(e instanceof Error ? e.message : 'Failed to start authorization.')
      setLoading(false)
    }
  }

  const handleManualSubmit = async () => {
    setManualLoading(true)
    setError('')
    try {
      const url = new URL(callbackUrl)
      const code = url.searchParams.get('code')
      const state = url.searchParams.get('state')
      const issuer = url.searchParams.get('issuer') || undefined
      if (!code || !state) {
        setError('Could not find "code" and "state" in the pasted URL.')
        setManualLoading(false)
        return
      }
      const res = await authApi.exchange(code, state, issuer)
      if (res.access_token && res.refresh_token) {
        update({ accessToken: res.access_token, refreshToken: res.refresh_token })
        setShowManual(false)
      } else {
        setError('Server returned incomplete data.')
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to retrieve tokens.')
      setManualLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Authorize with Tesla</h2>
        <p className="text-sm text-slate-500 mt-1">
          Connect your Tesla account so the app can read vehicle data and send
          charging commands.
        </p>
      </div>

      {authorized ? (
        <div className="card p-6 flex items-center gap-3">
          <CheckCircle size={24} className="text-green-500 shrink-0" />
          <div>
            <p className="font-medium text-slate-900">Authorization successful!</p>
            <p className="text-sm text-slate-500">Tokens received and stored in memory.</p>
          </div>
        </div>
      ) : (
        <div className="card p-6 space-y-4">
          <p className="text-sm text-slate-600">
            Clicking the button below will open Tesla&apos;s sign-in page in a popup.
            After you approve access, you&apos;ll be redirected back here automatically.
          </p>

          {error && <Alert type="error">{error}</Alert>}

          <Button
            onClick={handleAuthorize}
            loading={loading}
            size="lg"
            className="w-full"
          >
            <ExternalLink size={16} />
            Connect with Tesla
          </Button>

          {showManual && (
            <div className="border-t border-slate-200 pt-4 mt-2">
              <p className="text-sm font-medium text-slate-700 mb-2">
                Or paste the callback URL here
              </p>
              <p className="text-xs text-slate-500 mb-3">
                Copy the full URL from the popup&apos;s address bar after
                authorizing and paste it below.
              </p>
              <div className="flex gap-2">
                <Input
                  value={callbackUrl}
                  onChange={(e) => setCallbackUrl(e.target.value)}
                  placeholder="https://tesla.nalgascorp.org/done.html?code=..."
                />
                <Button
                  onClick={handleManualSubmit}
                  loading={manualLoading}
                  variant="secondary"
                  className="shrink-0"
                >
                  <ClipboardPaste size={16} />
                  Verify
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="secondary" onClick={back}>
          Back
        </Button>
        <Button onClick={next} disabled={!authorized} className="flex-1">
          Continue
        </Button>
      </div>
    </div>
  )
}
