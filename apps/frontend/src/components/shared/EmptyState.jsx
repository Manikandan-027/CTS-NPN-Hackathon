import { Inbox } from 'lucide-react'

export default function EmptyState({ icon: Icon = Inbox, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center gap-2 py-14">
      <Icon size={26} className="text-ink-muted mb-1" />
      <div className="text-sm font-medium text-ink-primary">{title}</div>
      {description && (
        <div className="text-xs text-ink-muted max-w-sm">{description}</div>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
