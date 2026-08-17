import { FileCode2, FileX2 } from 'lucide-react'

// Renders exactly the code evidence returned by the backend.
// Never invents code — if no snippet/context is present, shows only
// the file/line reference (or the "unavailable" state entirely).
export default function CodeEvidenceCard({
  filePath,
  lineStart,
  lineEnd,
  snippet,
  matchedTerms = [],
  score,
}) {
  if (!filePath) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-border-subtle bg-bg-panel2/60 px-4 py-4">
        <FileX2 size={18} className="text-ink-muted shrink-0" />
        <span className="text-sm text-ink-muted">
          Code-level evidence unavailable.
        </span>
      </div>
    )
  }

  const lineLabel =
    lineStart && lineEnd
      ? lineStart === lineEnd
        ? `Line ${lineStart}`
        : `Lines ${lineStart}–${lineEnd}`
      : lineStart
      ? `Line ${lineStart}`
      : null

  const lines = snippet ? snippet.split('\n') : []
  const highlightLine = lineStart

  return (
    <div className="rounded-xl border border-border-subtle overflow-hidden bg-bg-panel2/60">
      <div className="flex items-center justify-between gap-3 px-4 py-2.5 bg-white/[0.03] border-b border-border-subtle">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode2 size={15} className="text-accent-cyan shrink-0" />
          <span className="text-sm font-mono text-ink-primary truncate">{filePath}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {lineLabel && (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/25">
              {lineLabel}
            </span>
          )}
          {score !== undefined && score !== null && (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-white/5 text-ink-muted border border-border-subtle">
              score {typeof score === 'number' ? score.toFixed(2) : score}
            </span>
          )}
        </div>
      </div>

      {lines.length > 0 ? (
        <pre className="text-[12.5px] leading-6 font-mono overflow-x-auto px-0 py-2">
          {lines.map((line, idx) => {
            const lineNumber = (lineStart || 1) + idx
            const isHighlighted =
              highlightLine !== undefined &&
              highlightLine !== null &&
              lineNumber === Number(highlightLine)
            return (
              <div
                key={idx}
                className={`flex px-4 ${
                  isHighlighted ? 'bg-accent-cyan/10 border-l-2 border-accent-cyan' : 'border-l-2 border-transparent'
                }`}
              >
                <span className="w-10 text-right pr-4 select-none text-ink-muted/60">
                  {lineNumber}
                </span>
                <span className={isHighlighted ? 'text-ink-primary' : 'text-ink-secondary'}>
                  {line}
                </span>
              </div>
            )
          })}
        </pre>
      ) : (
        <div className="px-4 py-3 text-xs text-ink-muted">
          Location identified; source snippet not included by the backend.
        </div>
      )}

      {matchedTerms?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-4 py-2.5 border-t border-border-subtle bg-white/[0.02]">
          {matchedTerms.map((term, i) => (
            <span
              key={i}
              className="text-[10.5px] font-mono px-2 py-0.5 rounded-full bg-state-qwen/10 text-state-qwen border border-state-qwen/25"
            >
              {term}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
