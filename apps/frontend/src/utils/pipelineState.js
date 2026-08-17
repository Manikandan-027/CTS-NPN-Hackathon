// Derives which pipeline stages are complete/active/skipped for the
// PipelineStepper, based purely on fields the backend actually returned.
// Never assumes a stage ran just because a later one did.
export function derivePipelineState(incident) {
  if (!incident) {
    return { completed: [], active: 'intake', skipped: [] }
  }

  const status = (incident.incident_status || incident.status || '').toUpperCase()
  const completed = ['intake']
  const skipped = []

  const hasHistoryInfo =
    incident.historical_match || incident.history_status || status === 'KNOWN' || status === 'RELATED_NEW' || status === 'COMPLETELY_NEW'
  if (hasHistoryInfo) completed.push('history')

  const hasTop20 = incident.top_20 || incident.retrieval_top20 || incident.rag_top20
  const hasTop5 = incident.top_5 || incident.hybrid_top5 || incident.evidence_top5

  if (status === 'COMPLETELY_NEW') {
    if (hasTop20) completed.push('rag')
    else if (hasHistoryInfo) skipped.push('rag')
    skipped.push('rerank', 'code', 'rca', 'qwen')
    if (incident.validation_status) {
      completed.push('validation')
    }
    return { completed, active: null, skipped }
  }

  if (hasTop20) completed.push('rag')
  if (hasTop5) completed.push('rerank')
  if (incident.repository_evidence || incident.file_path) completed.push('code')
  if (incident.root_cause) completed.push('rca')
  if (incident.suggested_fix || incident.prevention || incident.qwen_resolution) completed.push('qwen')

  let active = null
  const order = ['intake', 'history', 'rag', 'rerank', 'code', 'rca', 'qwen', 'validation']
  const lastCompletedIdx = Math.max(...order.map((s, i) => (completed.includes(s) ? i : -1)))

  if (incident.validation_status === 'APPROVED' || incident.validation_status === 'REJECTED') {
    completed.push('validation')
  } else if (incident.validation_status === 'PENDING_HUMAN_VALIDATION' || completed.includes('qwen')) {
    active = 'validation'
  } else if (lastCompletedIdx >= 0 && lastCompletedIdx < order.length - 2) {
    active = order[lastCompletedIdx + 1]
  }

  return { completed, active, skipped }
}
