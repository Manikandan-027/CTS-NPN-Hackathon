import { useLocation } from 'react-router-dom'

const TITLES = {
  '/': { title: 'Dashboard', desc: 'Live pipeline overview and system health' },
  '/chatbot': { title: 'AI Incident RCA Chatbot', desc: 'Describe an incident and get a root cause from the real pipeline' },
  '/incidents': { title: 'Incidents', desc: 'Search and filter every incident the pipeline has processed' },
  '/validation': { title: 'Human Validation', desc: 'Review AI-proposed root causes before they are trusted' },
  '/customer-queries': { title: 'Customer Queries', desc: 'Requests submitted from the payment application' },
  '/activity': { title: 'Pipeline Activity', desc: 'Chronological trace of every RCA run' },
  '/knowledge-base': { title: 'Developer Knowledge Base', desc: 'Approved root causes the pipeline can reuse' },
  '/settings': { title: 'Settings', desc: 'Environment and demo controls' },
}

function resolveTitle(pathname) {
  if (TITLES[pathname]) return TITLES[pathname]
  if (pathname.startsWith('/incidents/')) return { title: 'Incident Detail', desc: 'Full RCA trace for a single incident' }
  if (pathname.startsWith('/knowledge-base/')) return { title: 'Knowledge Base Entry', desc: 'Approved root cause detail' }
  return { title: 'RCA Console', desc: '' }
}

export default function Topbar() {
  const { pathname } = useLocation()
  const { title, desc } = resolveTitle(pathname)

  return (
    <header className="sticky top-0 z-10 backdrop-blur-md bg-bg-base/70 border-b border-border-subtle px-6 py-4 flex items-center justify-between">
      <div>
        <h1 className="font-display text-lg font-semibold text-ink-primary">{title}</h1>
        {desc && <p className="text-xs text-ink-muted mt-0.5">{desc}</p>}
      </div>
      <div className="hidden sm:flex items-center gap-2 text-[11px] text-ink-muted font-mono px-3 py-1.5 rounded-full border border-border-subtle bg-white/[0.02]">
        AI does not auto-apply fixes — human approval required
      </div>
    </header>
  )
}
