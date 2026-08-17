import { History, FileSearch2, Database } from 'lucide-react'
import HistoricalMatchCard from '../incident/HistoricalMatchCard'
import RetrievalTable from '../incident/RetrievalTable'

// Renders the three evidence categories the backend pipeline actually
// produces. Every sub-section is conditional on real data being present —
// nothing here is fabricated when the backend omits a field.
export default function EvidenceSection({ incident }) {
  if (!incident) return null

  const historicalMatch = incident.historical_match
  const top5 =
    incident.top_5 || incident.hybrid_top5 || incident.evidence_top5 || null
  const top20 =
    incident.top_20 || incident.retrieval_top20 || incident.rag_top20 || null
  const repoEvidence = incident.repository_evidence

  const hasHistorical = historicalMatch || (Array.isArray(top5) && top5.length > 0)
  const hasRepo = repoEvidence && (repoEvidence.context || repoEvidence.evidence || incident.file_path)
  const hasRetrieval = Array.isArray(top20) && top20.length > 0

  if (!hasHistorical && !hasRepo && !hasRetrieval) return null

  return (
    <div className="space-y-4">
      {hasHistorical && (
        <div>
          <SectionLabel icon={History} label="Historical evidence" />
          {historicalMatch ? (
            <HistoricalMatchCard match={historicalMatch} />
          ) : (
            <ul className="space-y-2">
              {top5.map((item, i) => (
                <li
                  key={i}
                  className="rounded-lg border border-border-subtle bg-bg-panel2/60 px-3 py-2.5 text-sm"
                >
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-mono text-ink-muted mb-1">
                    {(item.incident_id || item.id) && (
                      <span>ID: {item.incident_id || item.id}</span>
                    )}
                    {typeof item.score === 'number' && (
                      <span className="text-accent-cyan">
                        relevance {item.score.toFixed(3)}
                      </span>
                    )}
                    {typeof item.similarity === 'number' && (
                      <span className="text-accent-cyan">
                        similarity {item.similarity.toFixed(3)}
                      </span>
                    )}
                  </div>
                  {(item.root_cause || item.incident) && (
                    <p className="text-ink-primary">{item.root_cause || item.incident}</p>
                  )}
                  {item.resolution && (
                    <p className="text-ink-secondary mt-1">{item.resolution}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {hasRepo && (
        <div>
          <SectionLabel icon={FileSearch2} label="Repository evidence" />
          <div className="rounded-lg border border-border-subtle bg-bg-panel2/60 px-3 py-2.5 space-y-1.5 text-sm">
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] font-mono text-ink-muted">
              {incident.file_path && <span>{incident.file_path}</span>}
              {incident.line_start && (
                <span>
                  Line{incident.line_end && incident.line_end !== incident.line_start ? 's' : ''}{' '}
                  {incident.line_start}
                  {incident.line_end && incident.line_end !== incident.line_start
                    ? `–${incident.line_end}`
                    : ''}
                </span>
              )}
            </div>
            {(repoEvidence?.evidence || repoEvidence?.context) && (
              <p className="text-ink-secondary leading-relaxed whitespace-pre-line">
                {repoEvidence.evidence || repoEvidence.context}
              </p>
            )}
          </div>
        </div>
      )}

      {hasRetrieval && (
        <div>
          <SectionLabel icon={Database} label="Retrieval evidence" />
          <RetrievalTable title="Top 20 semantic candidates" items={top20} />
        </div>
      )}
    </div>
  )
}

function SectionLabel({ icon: Icon, label }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1.5">
      <Icon size={12} /> {label}
    </div>
  )
}
