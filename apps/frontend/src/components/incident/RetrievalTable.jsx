import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

// Collapsible technical detail table for Top 20 / Hybrid Top 5 retrieval
// results, so the primary RCA narrative isn't cluttered by default.
export default function RetrievalTable({ title, items, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)

  if (!items || items.length === 0) {
    return (
      <div className="rounded-xl border border-border-subtle px-4 py-3 text-xs text-ink-muted">
        {title}: no candidates returned.
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border-subtle overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
      >
        <span className="text-sm font-medium text-ink-primary flex items-center gap-2">
          {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
          {title}
        </span>
        <span className="text-[11px] font-mono text-ink-muted">{items.length} candidates</span>
      </button>
      {open && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-ink-muted border-t border-border-subtle">
                <th className="px-4 py-2 font-mono font-medium">#</th>
                <th className="px-4 py-2 font-mono font-medium">Incident / Snippet</th>
                <th className="px-4 py-2 font-mono font-medium">Score</th>
                <th className="px-4 py-2 font-mono font-medium">Source</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} className="border-t border-border-subtle/60 hover:bg-white/[0.02]">
                  <td className="px-4 py-2 text-ink-muted font-mono">{i + 1}</td>
                  <td className="px-4 py-2 text-ink-secondary max-w-md truncate">
                    {item.incident || item.text || item.summary || JSON.stringify(item).slice(0, 80)}
                  </td>
                  <td className="px-4 py-2 font-mono mono-num text-accent-cyan">
                    {typeof item.score === 'number' ? item.score.toFixed(3) : item.score ?? '—'}
                  </td>
                  <td className="px-4 py-2 text-ink-muted">{item.source || item.type || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
