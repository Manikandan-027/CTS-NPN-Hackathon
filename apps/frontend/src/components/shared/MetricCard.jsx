export default function MetricCard({ label, value, icon: Icon, tone = 'default', hint }) {
  const toneMap = {
    default: 'text-ink-primary',
    cyan: 'text-accent-cyan',
    success: 'text-state-success',
    warning: 'text-state-warning',
    danger: 'text-state-danger',
    qwen: 'text-state-qwen',
  }
  return (
    <div className="glass-panel rounded-2xl p-4 flex flex-col gap-3 shadow-glass hover:border-white/15 transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-[0.1em] text-ink-muted font-mono">
          {label}
        </span>
        {Icon && <Icon size={15} className={toneMap[tone]} />}
      </div>
      <div className={`font-display text-2xl font-semibold mono-num ${toneMap[tone]}`}>
        {value === null || value === undefined ? '—' : value}
      </div>
      {hint && <div className="text-[11px] text-ink-muted">{hint}</div>}
    </div>
  )
}
