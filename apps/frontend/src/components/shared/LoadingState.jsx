import { Loader2 } from 'lucide-react'

export default function LoadingState({ label = 'Loading data…', compact = false }) {
  return (
    <div
      className={`flex items-center justify-center gap-3 text-ink-muted ${
        compact ? 'py-6' : 'py-16'
      }`}
    >
      <Loader2 size={18} className="animate-spin text-accent-cyan" />
      <span className="text-sm font-body">{label}</span>
    </div>
  )
}

export function SkeletonRow({ className = '' }) {
  return (
    <div
      className={`h-4 rounded bg-white/5 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.06),transparent)] bg-[length:200%_100%] animate-shimmer ${className}`}
    />
  )
}
