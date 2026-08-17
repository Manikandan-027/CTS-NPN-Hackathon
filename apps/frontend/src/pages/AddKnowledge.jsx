import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, PlusCircle, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'

const EMPTY_EVIDENCE = 'Developer verified the issue.'

export default function AddKnowledge() {
  const navigate = useNavigate()
  const location = useLocation()
  const prefill = location.state || {}
  const [isPending,setPending]=useState(false)
  const [isSuccess,setSuccess]=useState(false)
  const [isError,setIsError]=useState(false)
  const [error,setError]=useState(null)
  const [data,setData]=useState(null)

  const [form, setForm] = useState({
    incident: prefill.incident || '',
    root_cause: '',
    resolution: '',
    prevention: '',
    file_path: '',
    line_start: '',
    line_end: '',
    evidence: EMPTY_EVIDENCE,
    service: prefill.service || '',
    route: prefill.route || '',
    repository: prefill.repository || '',
    validated_by: 'developer',
    source_incident_id: prefill.source_incident_id || '',
    confidence: '1.0',
  })
  const [submitted, setSubmitted] = useState(false)

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (submitted) return // prevent duplicate submissions
    setSubmitted(true); setPending(true); setIsError(false); setError(null)
    const payload={incident:form.incident,root_cause:form.root_cause,resolution:form.resolution,prevention:form.prevention||'',file_path:form.file_path||null,line_start:form.line_start?Number(form.line_start):null,line_end:form.line_end?Number(form.line_end):null,evidence:form.evidence?form.evidence.split('\n').map(s=>s.trim()).filter(Boolean):[],service:form.service||'demo-payment-service',route:form.route||'/api/demo/payment',repository:form.repository||null,validated_by:form.validated_by||'developer',source_incident_id:form.source_incident_id||null,confidence:form.confidence?Number(form.confidence):1.0}
    apiClient.post('/api/knowledge-base/incidents',payload).then(r=>{setData(r.data);setSuccess(true)}).catch(e=>{setIsError(true);setError(apiError(e));setSubmitted(false)}).finally(()=>setPending(false))
  }

  const resultState = data?.status || data?.result

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary transition-colors"
      >
        <ArrowLeft size={13} /> Back
      </button>

      <Panel title="Add verified knowledge" eyebrow="Developer knowledge base">
        {isSuccess ? (
          <div className="flex flex-col items-center text-center gap-3 py-8">
            <CheckCircle2 size={28} className="text-state-success" />
            <div>
              <div className="text-sm font-medium text-ink-primary">
                {resultState === 'ALREADY_EXISTS'
                  ? 'This entry already exists in the knowledge base.'
                  : resultState === 'PENDING_REPAIR'
                  ? 'Saved — pending repair before it becomes reusable.'
                  : 'Knowledge base entry added.'}
              </div>
              <p className="text-xs text-ink-muted mt-1 max-w-sm">
                Future incidents matching this signature can now resolve automatically
                through historical / developer knowledge retrieval.
              </p>
            </div>
            <button
              onClick={() => navigate('/knowledge-base')}
              className="mt-2 inline-flex items-center gap-2 rounded-lg bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 px-4 py-2 text-sm font-semibold hover:bg-accent-cyan/25 transition-colors"
            >
              View knowledge base
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {isError && (
              <div className="flex items-center gap-2 rounded-lg bg-state-danger/10 border border-state-danger/30 px-3 py-2.5 text-xs text-state-danger">
                <AlertTriangle size={14} />
                {error?.message || 'Could not save this entry. Please try again.'}
              </div>
            )}

            <Field label="Incident" required>
              <textarea
                required
                rows={2}
                value={form.incident}
                onChange={(e) => update('incident', e.target.value)}
                className={inputCls}
                placeholder="Describe the incident exactly as it occurred."
              />
            </Field>

            <Field label="Root cause" required>
              <textarea
                required
                rows={2}
                value={form.root_cause}
                onChange={(e) => update('root_cause', e.target.value)}
                className={inputCls}
                placeholder="The verified root cause."
              />
            </Field>

            <Field label="Resolution" required>
              <textarea
                required
                rows={2}
                value={form.resolution}
                onChange={(e) => update('resolution', e.target.value)}
                className={inputCls}
                placeholder="How this was fixed."
              />
            </Field>

            <Field label="Prevention">
              <textarea
                rows={2}
                value={form.prevention}
                onChange={(e) => update('prevention', e.target.value)}
                className={inputCls}
                placeholder="How to prevent recurrence."
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Service">
                <input value={form.service} onChange={(e) => update('service', e.target.value)} className={inputCls} />
              </Field>
              <Field label="Route">
                <input value={form.route} onChange={(e) => update('route', e.target.value)} className={inputCls} />
              </Field>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <Field label="File path">
                <input value={form.file_path} onChange={(e) => update('file_path', e.target.value)} className={inputCls} placeholder="src/payment/payment_service.py" />
              </Field>
              <Field label="Line start">
                <input type="number" value={form.line_start} onChange={(e) => update('line_start', e.target.value)} className={inputCls} />
              </Field>
              <Field label="Line end">
                <input type="number" value={form.line_end} onChange={(e) => update('line_end', e.target.value)} className={inputCls} />
              </Field>
            </div>

            <Field label="Evidence (one item per line)">
              <textarea
                rows={2}
                value={form.evidence}
                onChange={(e) => update('evidence', e.target.value)}
                className={inputCls}
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Validated by">
                <input value={form.validated_by} onChange={(e) => update('validated_by', e.target.value)} className={inputCls} />
              </Field>
              <Field label="Confidence (0–1)">
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={form.confidence}
                  onChange={(e) => update('confidence', e.target.value)}
                  className={inputCls}
                />
              </Field>
            </div>

            <button
              type="submit"
              disabled={isPending}
              className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-accent-cyan text-bg-base font-semibold text-sm px-4 py-2.5 hover:brightness-110 transition-all disabled:opacity-50"
            >
              {isPending ? <Loader2 size={15} className="animate-spin" /> : <PlusCircle size={15} />}
              {isPending ? 'Saving…' : 'Add to knowledge base'}
            </button>
          </form>
        )}
      </Panel>
    </div>
  )
}

const inputCls =
  'w-full rounded-lg bg-bg-base/60 border border-border px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-accent-cyan/50 outline-none resize-none'

function Field({ label, required, children }) {
  return (
    <div>
      <label className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1.5 block">
        {label} {required && <span className="text-state-danger">*</span>}
      </label>
      {children}
    </div>
  )
}
