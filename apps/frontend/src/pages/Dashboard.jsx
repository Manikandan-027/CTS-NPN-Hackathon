import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Layers, CheckCircle2, Sparkles, AlertTriangle, Clock, BrainCircuit, ArrowUpRight } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'
import MetricCard from '../components/shared/MetricCard'
import LoadingState from '../components/shared/LoadingState'
import ErrorState from '../components/shared/ErrorState'
import EmptyState from '../components/shared/EmptyState'
import StatusBadge from '../components/shared/StatusBadge'
import ConfidenceBar from '../components/shared/ConfidenceBar'
import PipelineStepper from '../components/shared/PipelineStepper'
import CodeEvidenceCard from '../components/shared/CodeEvidenceCard'
import { getIncidentTypeMeta, getValidationMeta } from '../utils/statusMaps'
import { formatDateTime, resolveConfidencePercent } from '../utils/format'
import { derivePipelineState } from '../utils/pipelineState'

export default function Dashboard() {
  const [incidents, setIncidents] = useState([])
  const [latest, setLatest] = useState(null)
  const [kb, setKb] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = async () => {
    try {
      const [i, l, k] = await Promise.all([
        apiClient.get('/api/support/incidents', { params: { limit: 50 } }),
        apiClient.get('/api/support/latest'),
        apiClient.get('/api/knowledge-base/status'),
      ])
      setIncidents(i.data?.incidents || [])
      setLatest(l.data?.response || null)
      setKb(k.data)
      setError(null)
    } catch (e) { setError(apiError(e)) } finally { setLoading(false) }
  }

  useEffect(() => { fetchData(); const id = setInterval(fetchData, 3000); return () => clearInterval(id) }, [])

  const metrics = useMemo(() => {
    const list = Array.isArray(incidents) ? incidents : []
    const count = (p) => list.filter(p).length
    return { total: list.length, known: count(i => (i.incident_status || i.status) === 'KNOWN'), relatedNew: count(i => (i.incident_status || i.status) === 'RELATED_NEW'), completelyNew: count(i => (i.incident_status || i.status) === 'COMPLETELY_NEW'), pending: count(i => (i.validation_status || i.validation) === 'PENDING_HUMAN_VALIDATION') }
  }, [incidents])

  if (loading && !latest) return <LoadingState label="Loading RCA console…" />
  if (error && !latest) return <ErrorState error={error} onRetry={fetchData} />

  const latestPipeline = latest ? derivePipelineState(latest) : null

  return <div className="space-y-6">
    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
      <MetricCard label="Total incidents" value={metrics.total} icon={Layers} tone="cyan" />
      <MetricCard label="Known" value={metrics.known} icon={CheckCircle2} tone="success" />
      <MetricCard label="Related, new" value={metrics.relatedNew} icon={Sparkles} tone="cyan" />
      <MetricCard label="Completely new" value={metrics.completelyNew} icon={AlertTriangle} tone="warning" />
      <MetricCard label="Pending validation" value={metrics.pending} icon={Clock} tone="warning" />
      <MetricCard label="Approved KB entries" value={kb?.count ?? '—'} icon={BrainCircuit} tone="qwen" />
    </div>
    <Panel title="Latest incident" eyebrow="Live" action={latest?.incident_id && <Link to={`/incidents/${latest.incident_id}`} className="text-xs text-accent-cyan hover:underline inline-flex items-center gap-1">Full detail <ArrowUpRight size={12}/></Link>}>
      {!latest ? <EmptyState title="No incidents yet" description="Trigger a payment failure or send an incident to the backend."/> : <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono text-sm text-ink-primary">{latest.incident_id || '—'}</span>
          {latest.error_code && <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-white/5 text-ink-muted border border-border-subtle">{latest.error_code}</span>}
          {latest.service && <span className="text-xs text-ink-muted">service: {latest.service}</span>}
          <StatusBadge meta={getIncidentTypeMeta(latest.incident_status)} size="sm" />
          {latest.validation_status && <StatusBadge meta={getValidationMeta(latest.validation_status)} size="sm" />}
          <span className="text-xs text-ink-muted ml-auto">Updated {formatDateTime(latest.updated_at || latest.timestamp)}</span>
        </div>
        {latestPipeline && <PipelineStepper completedStages={latestPipeline.completed} activeStage={latestPipeline.active} skippedStages={latestPipeline.skipped}/>}
        <div className="grid md:grid-cols-2 gap-5">
          <div className="space-y-3">
            {latest.root_cause ? <div><div className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1">Root cause</div><p className="text-sm text-ink-primary leading-relaxed">{latest.root_cause}</p></div> : <div className="text-sm text-ink-muted">No root cause generated for this incident.</div>}
            {resolveConfidencePercent(latest) !== null && <ConfidenceBar value={latest.confidence_percent ?? latest.confidence}/>}
          </div>
          <CodeEvidenceCard filePath={latest.file_path} lineStart={latest.line_start} lineEnd={latest.line_end} snippet={latest.repository_evidence?.context || latest.code_snippet} matchedTerms={latest.repository_evidence?.matched_terms} score={latest.repository_evidence?.score}/>
        </div>
      </div>}
    </Panel>
    <Panel title="Recent incidents" action={<Link to="/incidents" className="text-xs text-accent-cyan hover:underline">View all</Link>}>
      {incidents.length===0 ? <EmptyState title="No incidents recorded yet"/> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-ink-muted text-xs"><th className="px-3 py-2">Incident</th><th className="px-3 py-2">Service</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">Confidence</th><th className="px-3 py-2">Created</th></tr></thead><tbody>{incidents.slice(0,8).map((inc, idx)=><tr key={`${inc.incident_id}-${idx}`} onClick={()=>window.location.assign(`/incidents/${inc.incident_id}`)} className="border-t border-border-subtle hover:bg-white/[0.03] cursor-pointer"><td className="px-3 py-2.5 font-mono text-ink-primary">{inc.incident_id}</td><td className="px-3 py-2.5 text-ink-secondary">{inc.service || '—'}</td><td className="px-3 py-2.5"><StatusBadge meta={getIncidentTypeMeta(inc.incident_status || inc.status)} size="sm"/></td><td className="px-3 py-2.5 font-mono">{resolveConfidencePercent(inc) ?? '—'}%</td><td className="px-3 py-2.5 text-ink-muted text-xs">{formatDateTime(inc.created_at || inc.timestamp)}</td></tr>)}</tbody></table></div>}
    </Panel>
  </div>
}
