import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, ShieldCheck } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'
import LoadingState from '../components/shared/LoadingState'
import ErrorState from '../components/shared/ErrorState'
import EmptyState from '../components/shared/EmptyState'
import ConfidenceBar from '../components/shared/ConfidenceBar'
import CodeEvidenceCard from '../components/shared/CodeEvidenceCard'
import ValidationPanel from '../components/incident/ValidationPanel'
import StatusBadge from '../components/shared/StatusBadge'
import { getIncidentTypeMeta } from '../utils/statusMaps'

export default function Validation() {
  const [incidents,setIncidents]=useState([]); const [loading,setLoading]=useState(true); const [error,setError]=useState(null)
  const fetchIncidents=async()=>{try{const r=await apiClient.get('/api/support/incidents',{params:{limit:100}});setIncidents(r.data?.incidents||[]);setError(null)}catch(e){setError(apiError(e))}finally{setLoading(false)}}
  useEffect(()=>{fetchIncidents();const id=setInterval(fetchIncidents,3000);return()=>clearInterval(id)},[])

  const pending = useMemo(
    () =>
      (Array.isArray(incidents) ? incidents : []).filter(
        (i) => (i.validation_status || i.validation) === 'PENDING_HUMAN_VALIDATION'
      ),
    [incidents]
  )

  if (loading) return <LoadingState label="Loading pending validations…" />
  if (error) return <ErrorState error={error} onRetry={fetchIncidents} />

  if (pending.length === 0) {
    return (
      <Panel>
        <EmptyState
          icon={ShieldCheck}
          title="Nothing awaiting validation"
          description="Every processed incident with a proposed root cause has already been reviewed by a developer."
        />
      </Panel>
    )
  }

  return (
    <div className="space-y-4">
      {pending.map((incident) => (
        <Panel
          key={incident.incident_id}
          eyebrow={incident.incident_id}
          title={incident.error_message || incident.error_code || incident.incident || 'Incident'}
          action={
            <div className="flex items-center gap-2">
              <StatusBadge meta={getIncidentTypeMeta(incident.incident_status || incident.status)} size="sm" />
              <Link
                to={`/incidents/${incident.incident_id}`}
                className="text-xs text-accent-cyan hover:underline inline-flex items-center gap-1"
              >
                Full detail <ArrowUpRight size={12} />
              </Link>
            </div>
          }
        >
          <div className="grid lg:grid-cols-3 gap-5">
            <div className="lg:col-span-2 space-y-4">
              {incident.root_cause && (
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1">
                    Root cause
                  </div>
                  <p className="text-sm text-ink-primary leading-relaxed">{incident.root_cause}</p>
                </div>
              )}
              {Array.isArray(incident.evidence) && incident.evidence.length > 0 && (
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1.5">
                    Evidence
                  </div>
                  <ul className="space-y-1">
                    {incident.evidence.map((e, i) => (
                      <li key={i} className="text-sm text-ink-secondary flex gap-2">
                        <span className="text-accent-cyan mt-1">•</span>
                        {typeof e === 'string' ? e : JSON.stringify(e)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <CodeEvidenceCard
                filePath={incident.file_path}
                lineStart={incident.line_start}
                lineEnd={incident.line_end}
                snippet={incident.repository_evidence?.context || incident.code_snippet}
                matchedTerms={incident.repository_evidence?.matched_terms}
                score={incident.repository_evidence?.score}
              />
              {incident.suggested_fix && (
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1">
                    Suggested resolution
                  </div>
                  <p className="text-sm text-ink-secondary leading-relaxed">{incident.suggested_fix}</p>
                </div>
              )}
              {incident.prevention && (
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1">
                    Prevention
                  </div>
                  <p className="text-sm text-ink-secondary leading-relaxed">{incident.prevention}</p>
                </div>
              )}
              <ConfidenceBar value={incident.confidence_percent ?? incident.confidence} />
            </div>
            <div>
              <ValidationPanel incidentId={incident.incident_id} onDone={fetchIncidents} />
            </div>
          </div>
        </Panel>
      ))}
    </div>
  )
}
