import { useState } from 'react'
import { Wrench, ShieldAlert, BrainCircuit, History, PlusCircle, Loader2 } from 'lucide-react'
import StatusBadge from '../shared/StatusBadge'
import ConfidenceBar from '../shared/ConfidenceBar'
import CodeLocalization from './CodeLocalization'
import EvidenceSection from './EvidenceSection'
import HumanValidation from './HumanValidation'
import { getIncidentTypeMeta } from '../../utils/statusMaps'
import { resolveConfidencePercent } from '../../utils/format'
import { derivePipelineState } from '../../utils/pipelineState'
import { apiClient, apiError } from '../../api/client'

// The structured "INCIDENT RCA" panel that appears inside an AI chat
// message. Every value is read straight off the incident object the
// backend returned — nothing here is hardcoded or generated client-side.
export default function RcaResponse({ incident, onValidated }) {
  if (!incident) return null

  const status = (incident.incident_status || incident.status || '').toUpperCase()
  const isKnown = status === 'KNOWN'
  const isCompletelyNew = status === 'COMPLETELY_NEW'
  const confidencePct = resolveConfidencePercent(incident)
  const pipeline = derivePipelineState(incident)

  const agreementCount =
    incident.agreement_count ?? incident.evidence_agreement?.count ?? null
  const agreementTotal =
    incident.total_historical ?? incident.evidence_agreement?.total ?? null
  const hasAgreement =
    agreementCount !== null && agreementCount !== undefined && agreementTotal

  const summary = incident.rca_summary || incident.summary || incident.ai_summary

  return (
    <div className="rounded-xl border border-border-subtle bg-bg-panel2/60 overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 bg-white/[0.03] border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <span className="font-display text-sm font-semibold text-ink-primary">
            INCIDENT RCA
          </span>
          {incident.incident_id && (
            <span className="text-[11px] font-mono text-ink-muted">{incident.incident_id}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isKnown && (
            <span className="inline-flex items-center gap-1 text-[11px] font-mono text-state-success">
              <History size={11} /> Reused previous RCA
            </span>
          )}
          <StatusBadge meta={getIncidentTypeMeta(status)} size="sm" />
        </div>
      </div>

      <div className="px-4 py-4 space-y-4">
        {isCompletelyNew ? (
          <NewIncidentKnowledgeForm incident={incident} />
        ) : (
          <>
            {/* Root cause */}
            {incident.root_cause && (
              <Field label="Root cause" value={incident.root_cause} />
            )}

            {/* Confidence + Evidence agreement */}
            <div className="grid sm:grid-cols-2 gap-4">
              {confidencePct !== null && (
                <ConfidenceBar value={incident.confidence_percent ?? incident.confidence} />
              )}
              {hasAgreement && (
                <div>
                  <div className="text-xs text-ink-muted font-mono mb-1">Evidence agreement</div>
                  <div className="text-sm font-semibold font-mono text-ink-primary">
                    {agreementCount} / {agreementTotal}{' '}
                    <span className="text-ink-muted font-normal">historical incidents</span>
                  </div>
                </div>
              )}
            </div>

            {/* Resolution */}
            {(incident.suggested_fix || incident.prevention) && (
              <div className="border-t border-border-subtle pt-3 space-y-3">
                <SectionTitle>Resolution</SectionTitle>
                <div className="grid sm:grid-cols-2 gap-4">
                  {incident.suggested_fix && (
                    <InfoBlock icon={Wrench} tone="cyan" label="Recommended resolution" text={incident.suggested_fix} />
                  )}
                  {incident.prevention && (
                    <InfoBlock icon={ShieldAlert} tone="qwen" label="Prevention" text={incident.prevention} />
                  )}
                </div>
                <div className="flex items-center gap-1.5 text-[11px] text-ink-muted">
                  <BrainCircuit size={12} className="text-state-qwen" />
                  AI-drafted resolution — requires human validation before it is trusted.
                </div>
              </div>
            )}

            {/* Code localization */}
            {(incident.file_path || incident.repository) && (
              <div className="border-t border-border-subtle pt-3 space-y-2">
                <SectionTitle>Code localization</SectionTitle>
                <CodeLocalization incident={incident} />
              </div>
            )}

            {/* Evidence */}
            <div className="border-t border-border-subtle pt-3">
              <SectionTitle>Evidence</SectionTitle>
              <div className="mt-2">
                <EvidenceSection incident={incident} />
              </div>
            </div>

            {/* RCA summary */}
            {summary && (
              <div className="border-t border-border-subtle pt-3">
                <SectionTitle>RCA summary</SectionTitle>
                <p className="text-sm text-ink-secondary leading-relaxed whitespace-pre-line mt-1.5">
                  {summary}
                </p>
              </div>
            )}
          </>
        )}

        {/* Human validation */}
        {!isCompletelyNew && (
          <div className="border-t border-border-subtle pt-3">
            <HumanValidation incident={incident} onDone={onValidated} />
          </div>
        )}

        {isKnown && pipeline.skipped.length > 0 && (
          <div className="text-[11px] text-ink-muted font-mono space-y-0.5 pt-1">
            <div>History match found</div>
            {pipeline.skipped.includes('code') && <div>Repository analysis skipped</div>}
            {pipeline.skipped.includes('qwen') && <div>LLM analysis skipped</div>}
          </div>
        )}
      </div>
    </div>
  )
}

function NewIncidentKnowledgeForm({ incident }) {
  const [rootCause, setRootCause] = useState('')
  const [resolution, setResolution] = useState('')
  const [prevention, setPrevention] = useState('')
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)

  async function addKnowledge() {
    if (!rootCause.trim() || !resolution.trim()) {
      setStatus({ type: 'error', text: 'Root cause and resolution are required.' })
      return
    }
    setBusy(true); setStatus(null)
    try {
      const r = await apiClient.post('/api/knowledge-base/incidents', {
        incident: incident.incident || incident.error_message || '',
        root_cause: rootCause.trim(),
        resolution: resolution.trim(),
        prevention: prevention.trim(),
        file_path: incident.file_path || null,
        line_start: incident.line_start || null,
        line_end: incident.line_end || null,
        evidence: Array.isArray(incident.evidence) ? incident.evidence : [],
        service: incident.service || 'demo-payment-service',
        route: incident.route || '/api/demo/payment',
        repository: incident.repository || null,
        validated_by: 'developer',
        source_incident_id: incident.incident_id,
        confidence: 1.0,
      })
      setStatus({ type: 'success', text: r.data?.message || 'Developer knowledge added.' })
    } catch (e) {
      setStatus({ type: 'error', text: apiError(e).message })
    } finally { setBusy(false) }
  }

  return <div className="rounded-lg border border-state-warning/30 bg-state-warning/[0.06] p-4 space-y-3">
    <div>
      <div className="text-sm font-medium text-ink-primary">Completely new incident</div>
      <p className="text-xs text-ink-muted mt-1">No sufficiently similar historical evidence was found. Repository investigation and Qwen were skipped.</p>
    </div>
    <div className="grid gap-2">
      <textarea value={rootCause} onChange={e=>setRootCause(e.target.value)} rows={2} placeholder="Developer-verified root cause" className="w-full rounded-lg bg-bg-base/60 border border-border px-3 py-2 text-sm text-ink-primary outline-none" />
      <textarea value={resolution} onChange={e=>setResolution(e.target.value)} rows={2} placeholder="Developer-verified resolution" className="w-full rounded-lg bg-bg-base/60 border border-border px-3 py-2 text-sm text-ink-primary outline-none" />
      <textarea value={prevention} onChange={e=>setPrevention(e.target.value)} rows={2} placeholder="Prevention (optional)" className="w-full rounded-lg bg-bg-base/60 border border-border px-3 py-2 text-sm text-ink-primary outline-none" />
    </div>
    <button disabled={busy} onClick={addKnowledge} className="inline-flex items-center gap-2 rounded-lg bg-state-warning text-bg-base font-semibold text-xs px-3.5 py-2 disabled:opacity-50">
      {busy ? <Loader2 size={13} className="animate-spin"/> : <PlusCircle size={13}/>} {busy ? 'Saving…' : 'Add verified knowledge'}
    </button>
    {status && <div className={`text-xs ${status.type==='error'?'text-state-danger':'text-state-success'}`}>{status.text}</div>}
  </div>
}

function SectionTitle({ children }) {
  return (
    <div className="text-[11px] uppercase tracking-[0.12em] text-ink-muted font-mono">
      {children}
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1">{label}</div>
      <p className="text-sm text-ink-primary leading-relaxed">{value}</p>
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
