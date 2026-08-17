export default function Panel({ title, eyebrow, action, children, className = '', bodyClassName = '' }) {
  return (
    <section className={`glass-panel rounded-2xl shadow-glass ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-4 px-5 pt-5 pb-3 border-b border-border-subtle">
          <div>
            {eyebrow && (
              <div className="text-[11px] uppercase tracking-[0.14em] text-ink-muted font-mono mb-1">
                {eyebrow}
              </div>
            )}
            {title && (
              <h2 className="font-display text-[15px] font-semibold text-ink-primary">
                {title}
              </h2>
            )}
          </div>
          {action}
        </div>
      )}
      <div className={`px-5 py-4 ${bodyClassName}`}>{children}</div>
    </section>
  )
}
