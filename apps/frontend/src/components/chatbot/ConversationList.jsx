import { Plus, MessageSquare } from 'lucide-react'
import { useEffect, useState } from 'react'
import { apiClient, apiError } from '../../api/client'
import StatusBadge from '../shared/StatusBadge'
import LoadingState from '../shared/LoadingState'
import ErrorState from '../shared/ErrorState'
import EmptyState from '../shared/EmptyState'
import { getIncidentTypeMeta } from '../../utils/statusMaps'
import { formatRelativeTime, truncate } from '../../utils/format'

// Shows real past incidents (from the same /api/support/incidents the
// Incidents page uses) as reopenable conversations. No fake history.
export default function ConversationList({ activeIncidentId, onSelect, onNewInvestigation }) {
  const [incidents,setIncidents]=useState([]); const [loading,setLoading]=useState(true); const [error,setError]=useState(null)
  const fetchIncidents=async()=>{try{const r=await apiClient.get('/api/support/incidents',{params:{limit:30}});setIncidents(r.data?.incidents||[]);setError(null)}catch(e){setError(apiError(e))}finally{setLoading(false)}}
  useEffect(()=>{fetchIncidents();const id=setInterval(fetchIncidents,5000);return()=>clearInterval(id)},[])

  return (
    <aside className="hidden lg:flex lg:flex-col w-72 shrink-0 border-r border-border-subtle bg-bg-panel/40">
      <div className="p-3 border-b border-border-subtle">
        <button
          onClick={onNewInvestigation}
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 px-3 py-2.5 text-sm font-semibold hover:bg-accent-cyan/25 transition-colors"
        >
          <Plus size={15} /> New Investigation
        </button>
      </div>

      <div className="px-3 py-2 text-[11px] uppercase tracking-wide text-ink-muted font-mono">
        Recent incidents
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-1">
        {loading && <LoadingState label="Loading conversations…" compact />}
        {error && <ErrorState error={error} onRetry={fetchIncidents} compact />}
        {!loading && !error && incidents.length === 0 && (
          <EmptyState
            icon={MessageSquare}
            title="No incidents yet"
            description="Start an investigation below."
          />
        )}
        {!loading &&
          !error &&
          incidents.map((inc) => {
            const isActive = inc.incident_id === activeIncidentId
            return (
              <button
                key={inc.incident_id}
                onClick={() => onSelect(inc.incident_id)}
                className={`w-full text-left rounded-lg px-3 py-2.5 border transition-colors ${
                  isActive
                    ? 'bg-accent-cyan/10 border-accent-cyan/25'
                    : 'border-transparent hover:bg-white/[0.04]'
                }`}
              >
                <div className="text-sm text-ink-primary truncate">
                  {truncate(inc.error_message || inc.error_code || inc.incident || inc.incident_id, 42)}
                </div>
                <div className="flex items-center justify-between mt-1.5 gap-2">
                  <StatusBadge meta={getIncidentTypeMeta(inc.incident_status || inc.status)} size="sm" />
                  <span className="text-[10.5px] text-ink-muted font-mono shrink-0">
                    {formatRelativeTime(inc.updated_at || inc.created_at || inc.timestamp)}
                  </span>
                </div>
              </button>
            )
          })}
      </div>
    </aside>
  )
}
