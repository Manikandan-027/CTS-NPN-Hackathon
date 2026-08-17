export default function StatusBadge({ meta, size = 'md' }) {
  if (!meta) return null
  const Icon = meta.icon
  const sizeCls =
    size === 'sm' ? 'text-[11px] px-2 py-0.5 gap-1' : 'text-xs px-2.5 py-1 gap-1.5'
  return (
    <span
      className={`inline-flex items-center rounded-full border font-medium ${meta.color} ${meta.bg} ${meta.border} ${sizeCls}`}
    >
      {Icon && <Icon size={size === 'sm' ? 11 : 13} />}
      {meta.label}
    </span>
  )
}
