import { AlertTriangle, PlusCircle } from 'lucide-react'
import { formatConfidencePercent } from '../../utils/format'

// The strong warning state required for COMPLETELY_NEW incidents.
// Never fabricates a root cause — only shows the gate the incident
// failed and the manual action required next.
export default function CompletelyNewBanner({ bestSimilarity, threshold, onAddKnowledge }) {
  const simPct = formatConfidencePercent(bestSimilarity)
  const thresholdPct = formatConfidencePercent(threshold)

  return (
    <div className="relative overflow-hidden rounded-2xl border border-state-warning/40 bg-gradient-to-br from-state-warning/[0.08] via-bg-panel to-bg-panel p-6">
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-xl bg-state-warning/15 border border-state-warning/40 flex items-center justify-center shrink-0">
          <AlertTriangle size={22} className="text-state-warning" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[11px] uppercase tracking-[0.14em] font-mono text-state-warning mb-1">
            Completely new incident
          </div>
          <h3 className="font-display text-lg font-semibold text-ink-primary mb-1.5">
            No sufficiently similar historical incident was found
          </h3>
          <p className="text-sm text-ink-secondary max-w-2xl">
            The pipeline did not fabricate a root cause for this incident. Repository
            investigation and Qwen resolution were skipped because there is no
            historical or developer-approved evidence to ground them in.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
            <Stat label="Best similarity" value={simPct !== null ? `${simPct}%` : '—'} tone="warning" />
            <Stat label="Required threshold" value={thresholdPct !== null ? `${thresholdPct}%` : '—'} tone="default" />
            <Stat label="Historical evidence" value="NONE" tone="danger" />
            <Stat label="Developer knowledge" value="NOT FOUND" tone="danger" />
            <Stat label="Repository investigation" value="SKIPPED" tone="warning" />
            <Stat label="Qwen resolution" value="SKIPPED" tone="warning" />
          </div>

          <div className="mt-5 rounded-xl border border-border-subtle bg-white/[0.03] px-4 py-3">
            <div className="text-sm font-medium text-ink-primary">Developer action required</div>
            <p className="text-xs text-ink-muted mt-1">
              Add the verified incident, root cause, resolution and prevention to the
              developer knowledge base so future occurrences resolve automatically.
            </p>
          </div>

          <button
            onClick={onAddKnowledge}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-state-warning text-bg-base font-semibold text-sm px-4 py-2.5 hover:brightness-110 transition-all shadow-[0_0_20px_rgba(243,185,78,0.25)]"
          >
            <PlusCircle size={16} />
            Add verified knowledge
          </button>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, tone }) {
  const toneCls =
    tone === 'warning'
      ? 'text-state-warning'
      : tone === 'danger'
      ? 'text-state-danger'
      : 'text-ink-primary'
  return (
    <div className="rounded-lg bg-bg-panel2/70 border border-border-subtle px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wide text-ink-muted font-mono mb-1">
        {label}
      </div>
      <div className={`text-sm font-semibold font-mono ${toneCls}`}>{value}</div>
    </div>
  )
}
