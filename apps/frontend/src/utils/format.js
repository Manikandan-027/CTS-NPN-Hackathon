// Formats a confidence value that may arrive as a 0-1 fraction or an
// already-scaled percentage. Never renders "0.95%" for a 95% confidence.
export function formatConfidencePercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return null
  }
  const num = Number(value)
  const pct = num <= 1 ? num * 100 : num
  return Math.round(pct * 10) / 10
}

export function formatPercentLabel(value) {
  const pct = formatConfidencePercent(value)
  if (pct === null) return '—'
  return `${pct}%`
}

// Prefers a pre-computed confidence_percent field, falls back to
// deriving it from a 0-1 confidence field.
export function resolveConfidencePercent(obj) {
  if (!obj) return null
  if (obj.confidence_percent !== undefined && obj.confidence_percent !== null) {
    // confidence_percent might itself be 0-1 or already 0-100
    return formatConfidencePercent(obj.confidence_percent)
  }
  if (obj.confidence !== undefined && obj.confidence !== null) {
    return formatConfidencePercent(obj.confidence)
  }
  return null
}

export function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatRelativeTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  const diffMs = Date.now() - d.getTime()
  const diffSec = Math.round(diffMs / 1000)
  if (diffSec < 5) return 'just now'
  if (diffSec < 60) return `${diffSec}s ago`
  const diffMin = Math.round(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.round(diffHr / 24)
  return `${diffDay}d ago`
}

export function formatCurrency(amountMinorUnits, currency = 'USD') {
  if (amountMinorUnits === null || amountMinorUnits === undefined) return '—'
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
    }).format(Number(amountMinorUnits) / 100)
  } catch {
    return String(amountMinorUnits)
  }
}

export function truncate(str, len = 80) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len - 1) + '…' : str
}
