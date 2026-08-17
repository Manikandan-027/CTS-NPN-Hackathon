import StatusBadge from '../shared/StatusBadge'
import ValidationPanel from '../incident/ValidationPanel'
import { getValidationMeta } from '../../utils/statusMaps'

// Mirrors the "Human validation" section on IncidentDetail so the same
// approve/reject/needs-review flow — and the same live validation API —
// is available directly inside the chat, without duplicating logic.
export default function HumanValidation({ incident, onDone }) {
  if (!incident?.incident_id) return null

  const alreadyDecided =
    incident.validation_status && incident.validation_status !== 'PENDING_HUMAN_VALIDATION'

  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-ink-muted font-mono mb-1.5">
        Human validation
      </div>
      {alreadyDecided ? (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border-subtle bg-bg-panel2/60 px-3 py-2.5">
          <StatusBadge meta={getValidationMeta(incident.validation_status)} />
          {incident.validated_by && (
            <span className="text-xs text-ink-muted">by {incident.validated_by}</span>
          )}
          {incident.validation_comments && (
            <span className="text-xs text-ink-secondary italic">
              "{incident.validation_comments}"
            </span>
          )}
        </div>
      ) : (
        <ValidationPanel incidentId={incident.incident_id} onDone={onDone} />
      )}
    </div>
  )
}
