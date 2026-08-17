import { useNavigate, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'
import LoadingState from '../components/shared/LoadingState'
import ErrorState from '../components/shared/ErrorState'
import ConfidenceBar from '../components/shared/ConfidenceBar'
import CodeEvidenceCard from '../components/shared/CodeEvidenceCard'
import { formatDateTime } from '../utils/format'

export default function KnowledgeBaseEntry() {
  const { kbId } = useParams()
  const navigate = useNavigate()
  const [entry,setEntry]=useState(null)
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState(null)
  const fetchEntry=async()=>{try{const r=await apiClient.get(`/api/knowledge-base/incidents/${encodeURIComponent(kbId)}`);setEntry(r.data);setError(null)}catch(e){setError(apiError(e))}finally{setLoading(false)}}
  useEffect(()=>{fetchEntry()},[kbId])

  return (
    <div className="space-y-4">
      <button
        onClick={() => navigate('/knowledge-base')}
        className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary transition-colors"
      >
        <ArrowLeft size={13} /> Back to knowledge base
      </button>

      {loading ? (
        <LoadingState label="Loading entry…" />
      ) : error ? (
        <ErrorState error={error} onRetry={fetchEntry} />
      ) : !entry ? (
        <ErrorState error={{ message: 'Knowledge base entry not found.' }} />
      ) : (
        <>
          <Panel>
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <h2 className="font-display text-lg font-semibold font-mono text-ink-primary">
                {entry.kb_id || kbId}
              </h2>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-state-success/10 text-state-success border border-state-success/30">
                {entry.status || 'APPROVED'}
              </span>
            </div>
            <div className="text-xs text-ink-muted flex flex-wrap gap-x-5 gap-y-1">
              {entry.service && <span>Service: <span className="text-ink-secondary">{entry.service}</span></span>}
              {entry.route && <span>Route: <span className="text-ink-secondary">{entry.route}</span></span>}
              {entry.validated_by && <span>Validated by: <span className="text-ink-secondary">{entry.validated_by}</span></span>}
              <span>Created: <span className="text-ink-secondary">{formatDateTime(entry.created_at || entry.timestamp)}</span></span>
            </div>
          </Panel>

          <Panel title="Incident">
            <p className="text-sm text-ink-primary leading-relaxed">{entry.incident}</p>
          </Panel>

          <Panel title="Root cause">
            <p className="text-sm text-ink-primary leading-relaxed">{entry.root_cause}</p>
          </Panel>

          <Panel title="Resolution">
            <p className="text-sm text-ink-secondary leading-relaxed">{entry.resolution}</p>
          </Panel>

          {entry.prevention && (
            <Panel title="Prevention">
              <p className="text-sm text-ink-secondary leading-relaxed">{entry.prevention}</p>
            </Panel>
          )}

          {(entry.file_path || entry.evidence) && (
            <Panel title="Evidence">
              <div className="space-y-3">
                <CodeEvidenceCard
                  filePath={entry.file_path}
                  lineStart={entry.line_start}
                  lineEnd={entry.line_end}
                />
                {Array.isArray(entry.evidence) && entry.evidence.length > 0 && (
                  <ul className="space-y-1">
                    {entry.evidence.map((e, i) => (
                      <li key={i} className="text-sm text-ink-secondary flex gap-2">
                        <span className="text-accent-cyan mt-1">•</span>
                        {typeof e === 'string' ? e : JSON.stringify(e)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Panel>
          )}

          {entry.confidence !== undefined && (
            <Panel title="Confidence">
              <ConfidenceBar value={entry.confidence} />
            </Panel>
          )}
        </>
      )}
    </div>
  )
}
