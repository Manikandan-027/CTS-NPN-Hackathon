import { Check, X, Loader2, Minus } from 'lucide-react'
import { PIPELINE_STAGES } from '../../utils/statusMaps'

// The signature UI element of the console: a horizontal spine that
// represents the RCA pipeline. Each stage lights up as it completes.
// completedStages: array of stage keys that are done
// activeStage: stage key currently in progress (optional)
// skippedStages: array of stage keys explicitly skipped (COMPLETELY_NEW path)
export default function PipelineStepper({
  completedStages = [],
  activeStage = null,
  skippedStages = [],
  compact = false,
}) {
  return (
    <div className="w-full overflow-x-auto">
      <div className="flex items-center min-w-[720px]">
        {PIPELINE_STAGES.map((stage, i) => {
          const isDone = completedStages.includes(stage.key)
          const isActive = activeStage === stage.key
          const isSkipped = skippedStages.includes(stage.key)
          const isLast = i === PIPELINE_STAGES.length - 1

          let circleCls =
            'border-border bg-bg-panel2 text-ink-muted'
          let Icon = Minus
          if (isDone) {
            circleCls = 'border-state-success/60 bg-state-success/15 text-state-success'
            Icon = Check
          } else if (isActive) {
            circleCls = 'border-accent-cyan/60 bg-accent-cyan/15 text-accent-cyan animate-pulseSoft'
            Icon = Loader2
          } else if (isSkipped) {
            circleCls = 'border-state-warning/50 bg-state-warning/10 text-state-warning'
            Icon = X
          }

          return (
            <div key={stage.key} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center gap-2 min-w-[84px]">
                <div
                  className={`flex items-center justify-center rounded-full border ${circleCls} ${
                    compact ? 'w-7 h-7' : 'w-9 h-9'
                  } transition-colors`}
                >
                  <Icon size={compact ? 13 : 15} className={isActive ? 'animate-spin' : ''} />
                </div>
                <span
                  className={`text-[10.5px] text-center leading-tight font-mono ${
                    isDone
                      ? 'text-ink-secondary'
                      : isActive
                      ? 'text-accent-cyan'
                      : isSkipped
                      ? 'text-state-warning'
                      : 'text-ink-muted'
                  }`}
                >
                  {stage.label}
                </span>
              </div>
              {!isLast && (
                <div
                  className={`flex-1 h-[2px] mx-1 rounded-full ${
                    isDone ? 'bg-state-success/50' : 'bg-border'
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
