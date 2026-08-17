import { useMemo, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, FileCode2 } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'
import LoadingState from '../components/shared/LoadingState'
import ErrorState from '../components/shared/ErrorState'
import EmptyState from '../components/shared/EmptyState'
import StatusBadge from '../components/shared/StatusBadge'
import { getIncidentTypeMeta, getValidationMeta } from '../utils/statusMaps'
import { formatDateTime, resolveConfidencePercent, truncate } from '../utils/format'

const TYPE_FILTERS = ['KNOWN', 'RELATED_NEW', 'COMPLETELY_NEW']
const VALIDATION_FILTERS = ['PENDING_HUMAN_VALIDATION', 'APPROVED', 'REJECTED']

export default function Incidents() {
  const navigate = useNavigate()
  const [data, setData] = useState({ incidents: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const fetchIncidents = async () => {
    try { const r = await apiClient.get('/api/support/incidents', { params: { limit: 100 } }); setData(r.data); setError(null) }
    catch (e) { setError(apiError(e)) } finally { setLoading(false) }
  }
  useEffect(() => { fetchIncidents(); const id=setInterval(fetchIncidents,5000); return ()=>clearInterval(id) }, [])
  const [typeFilter, setTypeFilter] = useState(null)
  const [validationFilter, setValidationFilter] = useState(null)

  const incidents = data?.incidents || []

  const filtered = useMemo(() => {
    let list = Array.isArray(incidents) ? incidents : []
    if (typeFilter) {
      list = list.filter((i) => (i.incident_status || i.status) === typeFilter)
    }
    if (validationFilter) {
      list = list.filter((i) => (i.validation_status || i.validation) === validationFilter)
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter((i) =>
        [
          i.incident_id,
          i.error_code,
          i.error_message,
          i.service,
          i.customer_query,
          i.incident,
        ]
          .filter(Boolean)
          .some((f) => String(f).toLowerCase().includes(q))
      )
    }
    return list
  }, [incidents, typeFilter, validationFilter, search])

  return (
    <div className="space-y-4">
      <Panel bodyClassName="!py-3">
        <div className="flex flex-col lg:flex-row lg:items-center gap-3">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by incident ID, error, service, or customer query…"
              className="w-full rounded-lg bg-bg-base/60 border border-border pl-9 pr-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-accent-cyan/50 outline-none"
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {TYPE_FILTERS.map((t) => (
              <FilterChip
                key={t}
                active={typeFilter === t}
                onClick={() => setTypeFilter(typeFilter === t ? null : t)}
                meta={getIncidentTypeMeta(t)}
              />
            ))}
            {VALIDATION_FILTERS.map((v) => (
              <FilterChip
                key={v}
                active={validationFilter === v}
                onClick={() => setValidationFilter(validationFilter === v ? null : v)}
                meta={getValidationMeta(v)}
              />
            ))}
          </div>
        </div>
      </Panel>

      <Panel title={`Incidents (${filtered.length})`}>
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState error={error} onRetry={fetchIncidents} />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={FileCode2}
            title="No incidents match your filters"
            description="Adjust your search or filters, or wait for new incidents from the payment app."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-muted text-xs">
                  <th className="px-3 py-2 font-mono font-medium">Incident ID</th>
                  <th className="px-3 py-2 font-mono font-medium">Error</th>
                  <th className="px-3 py-2 font-mono font-medium">Service</th>
                  <th className="px-3 py-2 font-mono font-medium">Type</th>
                  <th className="px-3 py-2 font-mono font-medium">Confidence</th>
                  <th className="px-3 py-2 font-mono font-medium">Code location</th>
                  <th className="px-3 py-2 font-mono font-medium">Created</th>
                  <th className="px-3 py-2 font-mono font-medium">Validation</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((inc) => {
                  const pct = resolveConfidencePercent(inc)
                  return (
                    <tr
                      key={inc.incident_id}
                      onClick={() => navigate(`/incidents/${inc.incident_id}`)}
                      className="border-t border-border-subtle hover:bg-white/[0.03] cursor-pointer transition-colors"
                    >
                      <td className="px-3 py-2.5 font-mono text-ink-primary whitespace-nowrap">
                        {inc.incident_id}
                      </td>
                      <td className="px-3 py-2.5 text-ink-secondary max-w-[220px] truncate">
                        {truncate(inc.error_message || inc.error_code || inc.incident, 60)}
                      </td>
                      <td className="px-3 py-2.5 text-ink-secondary">{inc.service || '—'}</td>
                      <td className="px-3 py-2.5">
                        <StatusBadge meta={getIncidentTypeMeta(inc.incident_status || inc.status)} size="sm" />
                      </td>
                      <td className="px-3 py-2.5 font-mono mono-num text-ink-secondary">
                        {pct !== null ? `${pct}%` : '—'}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-xs text-ink-muted">
                        {inc.file_path ? `${inc.file_path}${inc.line_start ? `:${inc.line_start}` : ''}` : '—'}
                      </td>
                      <td className="px-3 py-2.5 text-ink-muted text-xs whitespace-nowrap">
                        {formatDateTime(inc.created_at || inc.timestamp)}
                      </td>
                      <td className="px-3 py-2.5">
                        {inc.validation_status ? (
                          <StatusBadge meta={getValidationMeta(inc.validation_status)} size="sm" />
                        ) : (
                          <span className="text-ink-muted text-xs">—</span>
                        )}
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

function FilterChip({ active, onClick, meta }) {
  if (!meta) return null
  const Icon = meta.icon
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors ${
        active
          ? `${meta.color} ${meta.bg} ${meta.border}`
          : 'text-ink-muted border-border-subtle hover:text-ink-secondary'
      }`}
    >
      {Icon && <Icon size={11} />}
      {meta.label}
    </button>
  )
}
