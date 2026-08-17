import { History, Percent } from 'lucide-react'
import ConfidenceBar from '../shared/ConfidenceBar'

// Shown for KNOWN incidents — surfaces the exact prior occurrence.
export default function HistoricalMatchCard({ match }) {
  if (!match) return null
  const {
    incident,
    previous_incident,
    root_cause,
    previous_root_cause,
    resolution,
    previous_resolution,
    evidence,
    previous_evidence,
    confidence,
    similarity,
  } = match

  const incidentText = previous_incident || incident
  const rootCause = previous_root_cause || root_cause
  const resolutionText = previous_resolution || resolution
  const evidenceList = previous_evidence || evidence

  return (
    <div className="rounded-xl border border-state-success/25 bg-state-success/[0.04] p-4 space-y-3">
      <div className="flex items-center gap-2 text-state-success text-xs font-mono uppercase tracking-wide">
        <History size={13} /> Previous occurrence
      </div>

      {incidentText && (
        <Field label="Previous incident" value={incidentText} />
      )}
      {rootCause && <Field label="Previous root cause" value={rootCause} />}
      {resolutionText && <Field label="Previous resolution" value={resolutionText} />}

      {Array.isArray(evidenceList) && evidenceList.length > 0 && (
        <div>
          <div className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1.5">
            Previous evidence
          </div>
          <ul className="space-y-1">
            {evidenceList.map((e, i) => (
              <li key={i} className="text-sm text-ink-secondary flex gap-2">
                <span className="text-state-success mt-1">•</span>
                <span>{typeof e === 'string' ? e : JSON.stringify(e)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 pt-1">
        {confidence !== undefined && confidence !== null && (
          <ConfidenceBar value={confidence} size="sm" />
        )}
        {similarity !== undefined && similarity !== null && (
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <Percent size={13} />
            Similarity: <span className="text-ink-primary font-mono">{similarity}</span>
          </div>
        )}
      </div>
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1">
        {label}
      </div>
      <div className="text-sm text-ink-primary leading-relaxed">{value}</div>
    </div>
  )
}
