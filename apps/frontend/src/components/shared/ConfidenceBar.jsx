import { formatConfidencePercent } from '../../utils/format'

function bandColor(pct) {
  if (pct === null) return 'bg-ink-muted'
  if (pct >= 80) return 'bg-state-success'
  if (pct >= 50) return 'bg-state-warning'
  return 'bg-state-danger'
}

export default function ConfidenceBar({ value, size = 'md', showLabel = true }) {
  const pct = formatConfidencePercent(value)
  const barH = size === 'sm' ? 'h-1.5' : 'h-2'

  if (pct === null) {
    return <span className="text-xs text-ink-muted">No confidence score</span>
  }

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1">
        {showLabel && (
          <span className="text-xs text-ink-muted font-mono">Confidence</span>
        )}
        <span className="text-sm font-semibold font-mono mono-num text-ink-primary">
          {pct}%
        </span>
      </div>
      <div className={`w-full rounded-full bg-white/5 overflow-hidden ${barH}`}>
        <div
          className={`${barH} rounded-full ${bandColor(pct)} transition-all duration-700 ease-out`}
          style={{ width: `${Math.min(100, Math.max(2, pct))}%` }}
        />
      </div>
    </div>
  )
}
