import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search, BrainCircuit, PlusCircle } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'
import MetricCard from '../components/shared/MetricCard'
import LoadingState from '../components/shared/LoadingState'
import ErrorState from '../components/shared/ErrorState'
import EmptyState from '../components/shared/EmptyState'
import ConfidenceBar from '../components/shared/ConfidenceBar'
import { formatDateTime, truncate } from '../utils/format'

export default function KnowledgeBase() {
  const navigate = useNavigate()
  const [status,setStatus]=useState(null)
  const [entries,setEntries]=useState([])
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState(null)
  const [search,setSearch]=useState('')
  const fetchKb=async()=>{try{const [s,e]=await Promise.all([apiClient.get('/api/knowledge-base/status'),apiClient.get('/api/knowledge-base/incidents',{params:{limit:100}})]);setStatus(s.data);setEntries(e.data?.incidents||[]);setError(null)}catch(e){setError(apiError(e))}finally{setLoading(false)}}
  useEffect(()=>{fetchKb();const id=setInterval(fetchKb,5000);return()=>clearInterval(id)},[]) 

  const list = Array.isArray(entries) ? entries : []
  const filtered = search.trim()
    ? list.filter((e) =>
        [e.incident, e.root_cause, e.service, e.kb_id, e.id]
          .filter(Boolean)
          .some((f) => String(f).toLowerCase().includes(search.trim().toLowerCase()))
      )
    : list

 
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <MetricCard label="Total entries" value={status?.count ?? status?.total ?? list.length} icon={BrainCircuit} tone="qwen" />
        <MetricCard label="Approved" value={status?.approved_count ?? '—'} tone="success" />
        <MetricCard
          label="Latest incident"
          value={status?.latest_incident_id ? truncate(status.latest_incident_id, 16) : '—'}
          tone="cyan"
        />
      </div>

      <Panel
        title="Developer-approved knowledge"
        action={
          <button
            onClick={() => navigate('/knowledge-base/add')}
            className="inline-flex items-center gap-1.5 rounded-lg bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 px-3 py-1.5 text-xs font-semibold hover:bg-accent-cyan/25 transition-colors"
          >
            <PlusCircle size={13} /> Add knowledge
          </button>
        }
      >
        <div className="relative mb-4">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search knowledge base…"
            className="w-full max-w-md rounded-lg bg-bg-base/60 border border-border pl-9 pr-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-accent-cyan/50 outline-none"
          />
        </div>

        {loading ? (
          <LoadingState compact />
        ) : entriesQuery.isError ? (
          <ErrorState error={normalizeError(entriesQuery.error)} onRetry={entriesQuery.refetch} compact />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={BrainCircuit}
            title="No knowledge base entries yet"
            description="Completely new incidents that are verified by a developer will appear here."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-muted text-xs">
                  <th className="px-3 py-2 font-mono font-medium">KB ID</th>
                  <th className="px-3 py-2 font-mono font-medium">Incident</th>
                  <th className="px-3 py-2 font-mono font-medium">Root cause</th>
                  <th className="px-3 py-2 font-mono font-medium">Resolution</th>
                  <th className="px-3 py-2 font-mono font-medium">Service</th>
                  <th className="px-3 py-2 font-mono font-medium">Confidence</th>
                  <th className="px-3 py-2 font-mono font-medium">Validated by</th>
                  <th className="px-3 py-2 font-mono font-medium">Status</th>
                  <th className="px-3 py-2 font-mono font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e, i) => {
                  const kbId = e.kb_id || e.id || i
                  return (
                    <tr
                      key={kbId}
                      onClick={() => navigate(`/knowledge-base/${kbId}`)}
                      className="border-t border-border-subtle hover:bg-white/[0.03] cursor-pointer transition-colors"
                    >
                      <td className="px-3 py-2.5 font-mono text-ink-primary">{kbId}</td>
                      <td className="px-3 py-2.5 text-ink-secondary max-w-[200px] truncate">{truncate(e.incident, 50)}</td>
                      <td className="px-3 py-2.5 text-ink-secondary max-w-[200px] truncate">{truncate(e.root_cause, 50)}</td>
                      <td className="px-3 py-2.5 text-ink-secondary max-w-[200px] truncate">{truncate(e.resolution, 50)}</td>
                      <td className="px-3 py-2.5 text-ink-secondary">{e.service || '—'}</td>
                      <td className="px-3 py-2.5 w-28">
                        <ConfidenceBar value={e.confidence} size="sm" showLabel={false} />
                      </td>
                      <td className="px-3 py-2.5 text-ink-secondary">{e.validated_by || '—'}</td>
                      <td className="px-3 py-2.5 text-ink-muted text-xs">{e.status || 'APPROVED'}</td>
                      <td className="px-3 py-2.5 text-ink-muted text-xs whitespace-nowrap">
                        {formatDateTime(e.created_at || e.timestamp)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}
