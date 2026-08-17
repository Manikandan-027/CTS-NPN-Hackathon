import { AlertOctagon, RefreshCw, WifiOff } from 'lucide-react'

export default function ErrorState({ error, onRetry, compact = false }) {
  const status = error?.status
  const isOffline = status === 0
  const message = error?.message || 'Something went wrong loading this data.'

  return (
    <div
      className={`flex flex-col items-center justify-center text-center gap-3 ${
        compact ? 'py-8' : 'py-16'
      }`}
    >
      {isOffline ? (
        <WifiOff size={28} className="text-state-danger" />
      ) : (
        <AlertOctagon size={28} className="text-state-danger" />
      )}
      <div>
        <div className="text-sm font-medium text-ink-primary">
          {isOffline ? 'Backend unreachable' : `Request failed${status ? ` (${status})` : ''}`}
        </div>
        <div className="text-xs text-ink-muted mt-1 max-w-sm">{message}</div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-ink-secondary hover:text-ink-primary hover:border-accent-cyan/40 transition-colors"
        >
          <RefreshCw size={13} /> Retry
        </button>
      )}
    </div>
  )
}
