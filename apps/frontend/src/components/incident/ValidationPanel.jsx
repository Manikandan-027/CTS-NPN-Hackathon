import { useState } from 'react'
import { ShieldCheck, ShieldX, Eye, Loader2, ShieldAlert } from 'lucide-react'
import { apiClient, apiError } from '../../api/client'

// Human-in-the-loop control. AI never auto-applies a fix — this is the
// only path that changes an incident's validation status.
export default function ValidationPanel({ incidentId, onDone }) {
  const [comments, setComments] = useState('')
  const [validatedBy, setValidatedBy] = useState('developer')
  const [pendingDecision, setPendingDecision] = useState(null)
  const [error, setError] = useState(null)

  async function submit(decision) {
    setPendingDecision(decision); setError(null)
    try {
      await apiClient.post(`/api/support/validate/${encodeURIComponent(incidentId)}`, { decision, comments, validated_by: validatedBy || 'developer' })
      setComments(''); onDone?.()
    } catch (e) { setError(apiError(e)) } finally { setPendingDecision(null) }
  }
  const isPending = !!pendingDecision

  return (
    <div className="rounded-xl border border-border-subtle bg-bg-panel2/60 p-4 space-y-4">
      <div className="flex items-start gap-2 rounded-lg bg-accent-blue/10 border border-accent-blue/25 px-3 py-2.5">
        <ShieldAlert size={15} className="text-accent-blue mt-0.5 shrink-0" />
        <p className="text-xs text-ink-secondary">
          The AI never applies this fix automatically. Approving here only marks the
          root cause and resolution as developer-verified.
        </p>
      </div>

      <div>
        <label className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1.5 block">
          Validated by
        </label>
        <input
          value={validatedBy}
          onChange={(e) => setValidatedBy(e.target.value)}
          placeholder="developer"
          className="w-full rounded-lg bg-bg-base/60 border border-border px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-accent-cyan/50 outline-none"
        />
      </div>

      <div>
        <label className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1.5 block">
          Comments
        </label>
        <textarea
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          rows={3}
          placeholder="Verified the RCA against production logs."
          className="w-full rounded-lg bg-bg-base/60 border border-border px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-accent-cyan/50 outline-none resize-none"
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <ActionButton
          label="Approve"
          icon={ShieldCheck}
          tone="success"
          loading={isPending && pendingDecision === 'APPROVE'}
          disabled={isPending}
          onClick={() => submit('APPROVE')}
        />
        <ActionButton
          label="Reject"
          icon={ShieldX}
          tone="danger"
          loading={isPending && pendingDecision === 'REJECT'}
          disabled={isPending}
          onClick={() => submit('REJECT')}
        />
        <ActionButton
          label="Needs review"
          icon={Eye}
          tone="blue"
          loading={isPending && pendingDecision === 'NEEDS_REVIEW'}
          disabled={isPending}
          onClick={() => submit('NEEDS_REVIEW')}
        />
      </div>

      {error && (
        <p className="text-xs text-state-danger">
          {error?.message || 'Could not submit validation decision.'}
        </p>
      )}
    </div>
  )
}

function ActionButton({ label, icon: Icon, tone, onClick, disabled, loading }) {
  const toneCls = {
    success: 'bg-state-success/15 text-state-success border-state-success/35 hover:bg-state-success/25',
    danger: 'bg-state-danger/15 text-state-danger border-state-danger/35 hover:bg-state-danger/25',
    blue: 'bg-accent-blue/15 text-accent-blue border-accent-blue/35 hover:bg-accent-blue/25',
  }[tone]

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1.5 rounded-lg border px-3.5 py-2 text-xs font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${toneCls}`}
    >
      {loading ? <Loader2 size={13} className="animate-spin" /> : <Icon size={13} />}
      {label}
    </button>
  )
}
