import {
  CheckCircle2,
  Sparkles,
  AlertTriangle,
  Clock,
  ShieldCheck,
  ShieldX,
  Eye,
  HelpCircle,
} from 'lucide-react'

// Incident type badges — KNOWN / RELATED_NEW / COMPLETELY_NEW
export const INCIDENT_TYPE_META = {
  KNOWN: {
    label: 'Known incident',
    color: 'text-state-success',
    bg: 'bg-state-success/10',
    border: 'border-state-success/30',
    icon: CheckCircle2,
  },
  RELATED_NEW: {
    label: 'Related, new',
    color: 'text-accent-cyan',
    bg: 'bg-accent-cyan/10',
    border: 'border-accent-cyan/30',
    icon: Sparkles,
  },
  COMPLETELY_NEW: {
    label: 'Completely new',
    color: 'text-state-warning',
    bg: 'bg-state-warning/10',
    border: 'border-state-warning/30',
    icon: AlertTriangle,
  },
}

export function getIncidentTypeMeta(status) {
  if (!status) return null
  const key = String(status).toUpperCase()
  return (
    INCIDENT_TYPE_META[key] || {
      label: key.replaceAll('_', ' '),
      color: 'text-ink-secondary',
      bg: 'bg-white/5',
      border: 'border-border',
      icon: HelpCircle,
    }
  )
}

// Validation status badges
export const VALIDATION_META = {
  PENDING_HUMAN_VALIDATION: {
    label: 'Pending validation',
    color: 'text-state-warning',
    bg: 'bg-state-warning/10',
    border: 'border-state-warning/30',
    icon: Clock,
  },
  APPROVED: {
    label: 'Approved',
    color: 'text-state-success',
    bg: 'bg-state-success/10',
    border: 'border-state-success/30',
    icon: ShieldCheck,
  },
  REJECTED: {
    label: 'Rejected',
    color: 'text-state-danger',
    bg: 'bg-state-danger/10',
    border: 'border-state-danger/30',
    icon: ShieldX,
  },
  NEEDS_REVIEW: {
    label: 'Needs review',
    color: 'text-accent-blue',
    bg: 'bg-accent-blue/10',
    border: 'border-accent-blue/30',
    icon: Eye,
  },
}

export function getValidationMeta(status) {
  if (!status) return null
  const key = String(status).toUpperCase()
  return (
    VALIDATION_META[key] || {
      label: key.replaceAll('_', ' '),
      color: 'text-ink-secondary',
      bg: 'bg-white/5',
      border: 'border-border',
      icon: HelpCircle,
    }
  )
}

// Maps raw backend activity codes to human-readable labels + stage grouping.
export const LOG_EVENT_META = {
  INCIDENT_RECEIVED: { label: 'Incident received', stage: 'intake' },
  CUSTOMER_QUERY_SAVED: { label: 'Customer query stored', stage: 'intake' },
  HISTORY_CHECK_STARTED: { label: 'Checking incident history', stage: 'history' },
  HISTORY_MATCH: { label: 'Matching historical incident found', stage: 'history' },
  HISTORY_MISS: { label: 'No exact historical match', stage: 'history' },
  RAG_RETRIEVAL_STARTED: { label: 'Retrieving similar incidents', stage: 'rag' },
  RAG_TOP20_COMPLETED: { label: 'Top 20 candidates retrieved', stage: 'rag' },
  HYBRID_RERANK_STARTED: { label: 'Reranking candidates', stage: 'rerank' },
  HYBRID_RERANK_COMPLETED: { label: 'Top 5 evidence selected', stage: 'rerank' },
  CODE_SCAN_STARTED: { label: 'Investigating repository', stage: 'code' },
  CODE_SCAN_COMPLETED: { label: 'Repository investigation complete', stage: 'code' },
  ROOT_CAUSE_ANALYSIS_COMPLETED: { label: 'Root cause identified', stage: 'rca' },
  QWEN_RESOLUTION_COMPLETED: { label: 'AI resolution drafted (Qwen)', stage: 'qwen' },
  HUMAN_VALIDATION_REQUIRED: { label: 'Awaiting human validation', stage: 'validation' },
  HUMAN_VALIDATION_COMPLETED: { label: 'Human validation recorded', stage: 'validation' },
  HISTORY_SAVE_WARNING: { label: 'Knowledge save warning', stage: 'system' },
  PIPELINE_FAILED: { label: 'Pipeline failed', stage: 'system' },
}

export function getLogEventMeta(eventType) {
  if (!eventType) return { label: 'Activity event', stage: 'system' }
  return (
    LOG_EVENT_META[eventType] || {
      label: String(eventType).replaceAll('_', ' ').toLowerCase(),
      stage: 'system',
    }
  )
}

export const PIPELINE_STAGES = [
  { key: 'intake', label: 'Incident' },
  { key: 'history', label: 'History' },
  { key: 'rag', label: 'RAG Top 20' },
  { key: 'rerank', label: 'Hybrid Top 5' },
  { key: 'code', label: 'Code Investigation' },
  { key: 'rca', label: 'Root Cause' },
  { key: 'qwen', label: 'Qwen' },
  { key: 'validation', label: 'Human Validation' },
]
