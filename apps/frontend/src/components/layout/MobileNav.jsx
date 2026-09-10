import { NavLink } from 'react-router-dom'
import { LayoutGrid, ListTree, ShieldCheck, Activity, Bot } from 'lucide-react'

const ITEMS = [
  { to: '/', label: 'Home', icon: LayoutGrid, end: true },
  { to: '/chatbot', label: 'Chat', icon: Bot },
  { to: '/incidents', label: 'Incidents', icon: ListTree },
  { to: '/validation', label: 'Validate', icon: ShieldCheck },
  { to: '/activity', label: 'Activity', icon: Activity },
]

export default function MobileNav() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-20 bg-bg-panel/95 backdrop-blur-md border-t border-border-subtle flex items-center justify-around py-2">
      {ITEMS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `flex flex-col items-center gap-1 px-2 py-1 text-[10px] font-medium ${
              isActive ? 'text-accent-cyan' : 'text-ink-muted'
            }`
          }
        >
          <Icon size={18} />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
