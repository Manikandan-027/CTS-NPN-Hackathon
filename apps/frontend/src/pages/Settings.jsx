import { useState } from 'react'
import { AlertTriangle, RotateCcw, Loader2, CheckCircle2 } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'

export default function Settings() {
   const [confirming, setConfirming] = useState(false)
  const [state, setState] = useState('idle') // idle | pending | done | error
  const [error, setError] = useState(null)

  async function handleReset() {
    setState('pending')
    setError(null)
    try {
      await apiClient.post('/api/demo/reset')
      setState('done')
      setConfirming(false)
    } catch (e) {
      setError(apiError(e))
      setState('error')
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <Panel title="Environment" eyebrow="Configuration">
        <div className="text-sm text-ink-secondary space-y-1.5">
          <div>
            Backend API base URL:{' '}
            <span className="font-mono text-accent-cyan">
              {import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}
            </span>
          </div>
          <div className="text-xs text-ink-muted">
            Set via <span className="font-mono">VITE_API_BASE_URL</span> in your <span className="font-mono">.env</span> file.
          </div>
        </div>
      </Panel>

      <Panel title="Demo controls" eyebrow="Destructive">
        <div className="rounded-xl border border-state-danger/30 bg-state-danger/[0.04] p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} className="text-state-danger shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm font-medium text-ink-primary">Reset demo data</div>
              <p className="text-xs text-ink-muted mt-1">
                Clears incidents, activity logs, customer queries, and knowledge base entries
                on the backend so you can re-run the demo from a clean state. This cannot be undone.
              </p>

              {state === 'done' ? (
                <div className="mt-3 flex items-center gap-2 text-xs text-state-success">
                  <CheckCircle2 size={14} /> Demo data reset.
                </div>
              ) : !confirming ? (
                <button
                  onClick={() => setConfirming(true)}
                  className="mt-3 inline-flex items-center gap-2 rounded-lg border border-state-danger/40 text-state-danger px-3 py-1.5 text-xs font-semibold hover:bg-state-danger/10 transition-colors"
                >
                  <RotateCcw size={13} /> Reset demo data
                </button>
              ) : (
                <div className="mt-3 flex items-center gap-2">
                  <button
                    onClick={handleReset}
                    disabled={state === 'pending'}
                    className="inline-flex items-center gap-2 rounded-lg bg-state-danger text-bg-base font-semibold px-3 py-1.5 text-xs hover:brightness-110 transition-all disabled:opacity-50"
                  >
                    {state === 'pending' ? <Loader2 size={13} className="animate-spin" /> : <RotateCcw size={13} />}
                    Confirm reset
                  </button>
                  <button
                    onClick={() => setConfirming(false)}
                    className="text-xs text-ink-muted hover:text-ink-primary"
                  >
                    Cancel
                  </button>
                </div>
              )}
              {state === 'error' && (
                <p className="text-xs text-state-danger mt-2">{error?.message}</p>
              )}
            </div>
          </div>
        </div>
      </Panel>
    </div>
  )
}
