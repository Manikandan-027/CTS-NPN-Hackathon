import { useState, useEffect } from 'react'
import { ChevronDown, ChevronRight, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'
import LoadingState from '../components/shared/LoadingState'
import ErrorState from '../components/shared/ErrorState'
import EmptyState from '../components/shared/EmptyState'
import { getLogEventMeta } from '../utils/statusMaps'
import { formatDateTime, formatRelativeTime } from '../utils/format'

export default function Activity() {
  const [data,setData]=useState({activities:[]})
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState(null)
  const fetchLogs=async()=>{try{const r=await apiClient.get('/api/support/logs',{params:{limit:100}});setData(r.data);setError(null)}catch(e){setError(apiError(e))}finally{setLoading(false)}}
  useEffect(()=>{fetchLogs();const id=setInterval(fetchLogs,2000);return()=>clearInterval(id)},[])
  const logs = data?.activities || []
  const list = Array.isArray(logs) ? logs : []

  return (
    <Panel title="Pipeline activity" eyebrow="Chronological">
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState error={error} onRetry={fetchLogs} />
      ) : list.length === 0 ? (
        <EmptyState title="No activity recorded yet" description="Pipeline events will stream here as incidents are processed." />
      ) : (
        <ol className="relative border-l border-border-subtle ml-2">
          {list.map((log, i) => (
            <ActivityRow key={log.id || i} log={log} />
          ))}
        </ol>
      )}
    </Panel>
  )
}

function ActivityRow({ log }) {
  const [open, setOpen] = useState(false)
  const meta = getLogEventMeta(log.event_type || log.event || log.type)
  const isFailure = (log.event_type || log.event) === 'PIPELINE_FAILED'
  const isWarning = (log.event_type || log.event) === 'HISTORY_SAVE_WARNING'
  const isValidationNeeded = (log.event_type || log.event) === 'HUMAN_VALIDATION_REQUIRED'

  const Icon = isFailure ? AlertTriangle : isWarning || isValidationNeeded ? Loader2 : CheckCircle2
  const iconColor = isFailure
    ? 'text-state-danger'
    : isWarning || isValidationNeeded
    ? 'text-state-warning'
    : 'text-state-success'

  const hasMeta = log.metadata || log.details || log.incident_id

  return (
    <li className="mb-1 ml-5">
      <span className={`absolute -left-[9px] flex items-center justify-center w-4 h-4 rounded-full bg-bg-panel border border-border-subtle ${iconColor}`}>
        <Icon size={10} />
      </span>
      <div
        className={`flex items-center justify-between gap-3 py-2.5 ${hasMeta ? 'cursor-pointer' : ''}`}
        onClick={() => hasMeta && setOpen((o) => !o)}
      >
        <div className="flex items-center gap-2 min-w-0">
          {hasMeta && (open ? <ChevronDown size={13} className="text-ink-muted shrink-0" /> : <ChevronRight size={13} className="text-ink-muted shrink-0" />)}
          <span className="text-sm text-ink-primary truncate">{meta.label}</span>
          {log.incident_id && (
            <span className="text-[11px] font-mono text-ink-muted shrink-0">· {log.incident_id}</span>
          )}
        </div>
        <span className="text-[11px] text-ink-muted font-mono shrink-0" title={formatDateTime(log.timestamp || log.created_at)}>
          {formatRelativeTime(log.timestamp || log.created_at)}
        </span>
      </div>
      {open && hasMeta && (
        <pre className="ml-5 mb-2 rounded-lg bg-bg-panel2/70 border border-border-subtle px-3 py-2 text-[11px] font-mono text-ink-secondary overflow-x-auto">
          {JSON.stringify(log.metadata || log.details || { incident_id: log.incident_id }, null, 2)}
        </pre>
      )}
    </li>
  )
}
