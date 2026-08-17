import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import {
  LayoutGrid,
  ListTree,
  ShieldCheck,
  MessageSquareText,
  Activity,
  BrainCircuit,
  Settings,
  Radio,
  Bot,
} from 'lucide-react'
import { apiClient } from '../../api/client'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutGrid, end: true },
  { to: '/chatbot', label: 'AI RCA Chatbot', icon: Bot },
  { to: '/incidents', label: 'Incidents', icon: ListTree },
  { to: '/validation', label: 'Validation', icon: ShieldCheck },
  { to: '/customer-queries', label: 'Customer Queries', icon: MessageSquareText },
  { to: '/activity', label: 'Activity', icon: Activity },
  { to: '/knowledge-base', label: 'Knowledge Base', icon: BrainCircuit },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  const [health,setHealth]=useState(null); const [isError,setIsError]=useState(false)
  const fetchHealth=async()=>{try{const r=await apiClient.get('/health');setHealth(r.data);setIsError(false)}catch{setIsError(true)}}
  useEffect(()=>{fetchHealth();const id=setInterval(fetchHealth,10000);return()=>clearInterval(id)},[])
  const isUp=!isError && !!health

  return (
    <aside className="hidden md:flex md:flex-col w-64 shrink-0 h-screen sticky top-0 border-r border-border-subtle bg-bg-panel/60 backdrop-blur-sm">
      <div className="px-5 py-5 flex items-center gap-2.5 border-b border-border-subtle">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-cyan to-accent-blue flex items-center justify-center shadow-glow">
          <BrainCircuit size={17} className="text-bg-base" />
        </div>
        <div>
          <div className="font-display font-semibold text-sm leading-tight text-ink-primary">
            RCA Console
          </div>
          <div className="text-[10.5px] text-ink-muted font-mono">
            Incident Intelligence
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/25'
                  : 'text-ink-secondary hover:text-ink-primary hover:bg-white/[0.04] border border-transparent'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-border-subtle">
        <div className="flex items-center gap-2 text-xs">
          <Radio
            size={13}
            className={isUp ? 'text-state-success animate-pulseSoft' : 'text-state-danger'}
          />
          <span className={isUp ? 'text-state-success' : 'text-state-danger'}>
            {isUp ? 'Backend online' : 'Backend unreachable'}
          </span>
        </div>
        <div className="text-[10.5px] text-ink-muted font-mono mt-1 truncate">
          {import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}
        </div>
      </div>
    </aside>
  )
}
