import { Check, X, Loader2 } from 'lucide-react'
import { derivePipelineState } from '../../utils/pipelineState'

// Chat-native version of the dashboard's PipelineStepper: a vertical
// checklist. Every line is driven by derivePipelineState(incident), the
// same util IncidentDetail/Dashboard use, so a step only shows ✓ if the
// backend response actually contains the fields that stage produces, and
// only shows "skipped" if the backend's own state says so.
const CHECKLIST = [
  { stageKeys: ['intake'], label: 'Incident understood' },
  { stageKeys: ['history', 'rag', 'rerank'], label: 'Historical evidence retrieved' },
  { stageKeys: ['code'], label: 'Repository analyzed' },
  { stageKeys: ['rca', 'qwen'], label: 'RCA generated' },
]

export default function InvestigationProgress({ incident, pending = false }) {
  if (!incident && !pending) return null

  const pipeline = incident ? derivePipelineState(incident) : { completed: [], active: null, skipped: [] }

  return (
    <div className="space-y-1.5">
      {CHECKLIST.map(({ stageKeys, label }) => {
        const isDone = stageKeys.some((k) => pipeline.completed.includes(k))
        const isSkipped = !isDone && stageKeys.some((k) => pipeline.skipped.includes(k))
        const isActive = !isDone && !isSkipped && pending && stageKeys.some((k) => pipeline.active === k)

        let Icon = Loader2
        let cls = 'text-ink-muted'
        if (isDone) {
          Icon = Check
          cls = 'text-state-success'
        } else if (isSkipped) {
          Icon = X
          cls = 'text-state-warning'
        } else if (isActive) {
          cls = 'text-accent-cyan animate-spin'
        }

        return (
          <div key={label} className={`flex items-center gap-2 text-xs font-mono ${cls}`}>
            <Icon size={13} className={isActive ? 'animate-spin' : ''} />
            <span className={isDone ? 'text-ink-secondary' : isSkipped ? 'text-state-warning' : 'text-ink-muted'}>
              {label}
              {isSkipped ? ' — skipped' : ''}
            </span>
          </div>
        )
      })}
    </div>
  )
}
