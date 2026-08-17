import { useNavigate, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ArrowLeft, Wrench, ShieldAlert, BrainCircuit } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'
import LoadingState from '../components/shared/LoadingState'
import ErrorState from '../components/shared/ErrorState'
import StatusBadge from '../components/shared/StatusBadge'
import ConfidenceBar from '../components/shared/ConfidenceBar'
import PipelineStepper from '../components/shared/PipelineStepper'
import CodeEvidenceCard from '../components/shared/CodeEvidenceCard'
import CompletelyNewBanner from '../components/incident/CompletelyNewBanner'
import HistoricalMatchCard from '../components/incident/HistoricalMatchCard'
import RetrievalTable from '../components/incident/RetrievalTable'
import ValidationPanel from '../components/incident/ValidationPanel'
import { getIncidentTypeMeta, getValidationMeta } from '../utils/statusMaps'
import { formatDateTime, resolveConfidencePercent } from '../utils/format'
import { derivePipelineState } from '../utils/pipelineState'

export default function IncidentDetail() {
  const { incidentId } = useParams()
  const navigate = useNavigate()
  const [incident, setIncident] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const fetchIncident = async () => {
    try { const r=await apiClient.post(`/api/support/incidents/${encodeURIComponent(incidentId)}`); setIncident(r.data); setError(null) }
    catch(e){ setError(apiError(e)) } finally { setLoading(false) }
  }
  useEffect(() => { fetchIncident(); const id=setInterval(fetchIncident,5000); return ()=>clearInterval(id) }, [incidentId])

  if (loading) return <LoadingState label="Loading incident detail…" />
  if (error) return <ErrorState error={error} onRetry={fetchIncident} />
  if (!incident) return <ErrorState error={{ message: 'Incident not found.' }} />

  const status = (incident.incident_status || incident.status || '').toUpperCase()
  const isCompletelyNew = status === 'COMPLETELY_NEW'
  const pipeline = derivePipelineState(incident)
  const confidencePct = resolveConfidencePercent(incident)

  return (
    <div className="space-y-5">
      <button
        onClick={() => navigate('/incidents')}
        className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary transition-colors"
      >
        <ArrowLeft size={13} /> Back to incidents
      </button>

      {/* 1. Incident summary */}
      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <h2 className="font-display text-xl font-semibold text-ink-primary font-mono">
                {incident.incident_id}
              </h2>
              <StatusBadge meta={getIncidentTypeMeta(status)} />
              {incident.validation_status && (
                <StatusBadge meta={getValidationMeta(incident.validation_status)} />
              )}
            </div>
            <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-muted">
              {incident.service && <span>Service: <span className="text-ink-secondary">{incident.service}</span></span>}
              {incident.route && <span>Route: <span className="text-ink-secondary">{incident.route}</span></span>}
              {incident.error_code && <span>Error code: <span className="text-ink-secondary font-mono">{incident.error_code}</span></span>}
              {incident.customer_email && <span>Customer: <span className="text-ink-secondary">{incident.customer_email}</span></span>}
              <span>Created: <span className="text-ink-secondary">{formatDateTime(incident.created_at || incident.timestamp)}</span></span>
            </div>
            {incident.error_message && (
              <p className="text-sm text-ink-secondary mt-3 max-w-2xl">{incident.error_message}</p>
            )}
            {incident.customer_query && (
              <div className="mt-3 rounded-lg bg-white/[0.03] border border-border-subtle px-3 py-2.5 max-w-2xl">
                <div className="text-[10.5px] uppercase tracking-wide text-ink-muted font-mono mb-1">
                  Customer query
                </div>
                <p className="text-sm text-ink-secondary italic">"{incident.customer_query}"</p>
              </div>
            )}
          </div>
        </div>

        <div className="mt-5">
          <PipelineStepper
            completedStages={pipeline.completed}
            activeStage={pipeline.active}
            skippedStages={pipeline.skipped}
          />
        </div>
      </Panel>

      {isCompletelyNew ? (
        <CompletelyNewBanner
          bestSimilarity={incident.best_similarity ?? incident.similarity}
          threshold={incident.required_threshold ?? incident.similarity_threshold}
          onAddKnowledge={() =>
            navigate('/knowledge-base/add', {
              state: {
                incident: incident.incident || incident.error_message,
                service: incident.service,
                route: incident.route,
                repository: incident.repository,
                source_incident_id: incident.incident_id,
              },
            })
          }
        />
      ) : (
        <>
          {/* 2. Historical match */}
          {(incident.historical_match || status === 'KNOWN') && (
            <Panel title="Historical match" eyebrow="Section 2">
              <HistoricalMatchCard match={incident.historical_match || incident} />
            </Panel>
          )}

          {/* 3. Similarity / evidence gate */}
          {(incident.best_similarity !== undefined || incident.similarity !== undefined) && (
            <Panel title="Similarity / evidence gate" eyebrow="Section 3">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <MiniStat label="Best similarity" value={fmtPct(incident.best_similarity ?? incident.similarity)} />
                <MiniStat label="Required threshold" value={fmtPct(incident.required_threshold ?? incident.similarity_threshold)} />
                <MiniStat label="Gate result" value={status.replaceAll('_', ' ')} />
              </div>
            </Panel>
          )}

          {/* 4 & 5. Top 20 / Hybrid Top 5 */}
          {(incident.top_20 || incident.retrieval_top20 || incident.top_5 || incident.hybrid_top5 || incident.evidence_top5) && (
            <Panel title="Retrieval detail" eyebrow="Sections 4 & 5">
              <div className="space-y-3">
                <RetrievalTable
                  title="Top 20 historical / semantic candidates"
                  items={incident.top_20 || incident.retrieval_top20 || incident.rag_top20}
                />
                <RetrievalTable
                  title="Hybrid reranked Top 5 evidence"
                  items={incident.top_5 || incident.hybrid_top5 || incident.evidence_top5}
                />
              </div>
            </Panel>
          )}

          {/* 6 & 7. Root cause + evidence */}
          {(incident.root_cause || incident.evidence) && (
            <Panel title="Root cause & evidence" eyebrow="Sections 6 & 7">
              <div className="space-y-4">
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
                    <ul className="space-y-1.5">
                      {incident.evidence.map((e, i) => (
                        <li key={i} className="text-sm text-ink-secondary flex gap-2">
                          <span className="text-accent-cyan mt-1">•</span>
                          <span>{typeof e === 'string' ? e : JSON.stringify(e)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Panel>
          )}

          {/* 8 & 9. Repository investigation + Code location */}
          <Panel title="Repository investigation & code location" eyebrow="Sections 8 & 9">
            <CodeEvidenceCard
              filePath={incident.file_path}
              lineStart={incident.line_start}
              lineEnd={incident.line_end}
              snippet={incident.repository_evidence?.context || incident.code_snippet}
              matchedTerms={incident.repository_evidence?.matched_terms}
              score={incident.repository_evidence?.score}
            />
          </Panel>

          {/* 10. Confidence */}
          {confidencePct !== null && (
            <Panel title="Confidence" eyebrow="Section 10">
              <ConfidenceBar value={incident.confidence_percent ?? incident.confidence} />
            </Panel>
          )}

          {/* 11 & 12. Resolution + prevention */}
          {(incident.suggested_fix || incident.prevention) && (
            <Panel title="Suggested resolution & prevention" eyebrow="Sections 11 & 12">
              <div className="grid md:grid-cols-2 gap-5">
                {incident.suggested_fix && (
                  <InfoBlock icon={Wrench} tone="cyan" label="Suggested resolution" text={incident.suggested_fix} />
                )}
                {incident.prevention && (
                  <InfoBlock icon={ShieldAlert} tone="qwen" label="Prevention" text={incident.prevention} />
                )}
              </div>
              <div className="mt-3 flex items-center gap-1.5 text-[11px] text-ink-muted">
                <BrainCircuit size={12} className="text-state-qwen" />
                AI-drafted resolution — requires human validation before it is trusted.
              </div>
            </Panel>
          )}
        </>
      )}

      {/* 13. Human validation */}
      {!isCompletelyNew && (
        <Panel title="Human validation" eyebrow="Section 13">
          {incident.validation_status && incident.validation_status !== 'PENDING_HUMAN_VALIDATION' ? (
            <div className="flex items-center gap-3">
              <StatusBadge meta={getValidationMeta(incident.validation_status)} />
              {incident.validated_by && (
                <span className="text-xs text-ink-muted">by {incident.validated_by}</span>
              )}
              {incident.validation_comments && (
                <span className="text-xs text-ink-secondary italic">"{incident.validation_comments}"</span>
              )}
            </div>
          ) : (
            <ValidationPanel incidentId={incident.incident_id} onDone={fetchIncident} />
          )}
        </Panel>
      )}

      {/* 14. Developer knowledge base status */}
      <Panel title="Developer knowledge base status" eyebrow="Section 14">
        {incident.knowledge_base_status ? (
          <div className="text-sm text-ink-secondary">{JSON.stringify(incident.knowledge_base_status)}</div>
        ) : (
          <p className="text-sm text-ink-muted">
            {isCompletelyNew
              ? 'Not yet added — use "Add verified knowledge" above once this incident has a confirmed root cause.'
              : incident.validation_status === 'APPROVED'
              ? 'Approved RCAs are eligible for reuse as historical/developer knowledge.'
              : 'This incident will become reusable knowledge once a developer approves it.'}
          </p>
        )}
      </Panel>
    </div>
  )
}

function fmtPct(v) {
  if (v === null || v === undefined) return '—'
  const num = Number(v)
  if (Number.isNaN(num)) return String(v)
  const pct = num <= 1 ? num * 100 : num
  return `${Math.round(pct * 10) / 10}%`
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-lg bg-bg-panel2/70 border border-border-subtle px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wide text-ink-muted font-mono mb-1">{label}</div>
      <div className="text-sm font-semibold font-mono text-ink-primary">{value}</div>
    </div>
  )
}

function InfoBlock({ icon: Icon, tone, label, text }) {
  const toneCls = tone === 'qwen' ? 'text-state-qwen' : 'text-accent-cyan'
  return (
    <div>
      <div className={`flex items-center gap-1.5 text-[11px] uppercase tracking-wide font-mono mb-1.5 ${toneCls}`}>
        <Icon size={12} /> {label}
      </div>
      <p className="text-sm text-ink-secondary leading-relaxed whitespace-pre-line">{text}</p>
    </div>
  )
}
