import { Loader2, BrainCircuit, AlertOctagon, RefreshCw } from 'lucide-react'
import InvestigationProgress from './InvestigationProgress'
import RcaResponse from './RcaResponse'

export default function ChatMessage({ message, onValidated, onRetry }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] sm:max-w-[70%] rounded-2xl rounded-tr-sm bg-accent-blue/15 border border-accent-blue/25 px-4 py-2.5">
          <p className="text-sm text-ink-primary whitespace-pre-line">{message.text}</p>
        </div>
      </div>
    )
  }

  // Assistant messages
  return (
    <div className="flex gap-3 items-start">
      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent-cyan to-accent-blue flex items-center justify-center shrink-0 mt-0.5">
        <BrainCircuit size={14} className="text-bg-base" />
      </div>
      <div className="min-w-0 flex-1 max-w-[92%] space-y-3">
        {message.type === 'loading' && (
          <div className="flex items-center gap-2 text-ink-muted text-sm">
            <Loader2 size={15} className="animate-spin text-accent-cyan" />
            Investigating incident…
          </div>
        )}

        {message.type === 'error' && (
          <div className="flex items-start gap-2 rounded-lg border border-state-danger/30 bg-state-danger/[0.06] px-3.5 py-2.5">
            <AlertOctagon size={15} className="text-state-danger mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-ink-primary">
                {message.error?.message || 'Something went wrong reaching the RCA backend.'}
              </p>
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1 text-xs font-medium text-ink-secondary hover:text-ink-primary hover:border-accent-cyan/40 transition-colors"
                >
                  <RefreshCw size={12} /> Retry
                </button>
              )}
            </div>
          </div>
        )}

        {(message.type === 'text' || message.type === 'rca_result') && message.text && (
          <p className="text-sm text-ink-primary leading-relaxed whitespace-pre-line">
            {message.text}
          </p>
        )}

        {message.type === 'rca_result' && message.incident && (
          <>
            <InvestigationProgress incident={message.incident} />
            <RcaResponse incident={message.incident} onValidated={onValidated} />
          </>
        )}
      </div>
    </div>
  )
}
