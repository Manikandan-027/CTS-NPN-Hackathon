import { Folder, FunctionSquare } from 'lucide-react'
import CodeEvidenceCard from '../shared/CodeEvidenceCard'

// Adds Repository / Function context around the existing CodeEvidenceCard,
// which already handles File / Lines / snippet rendering. Only ever
// displays fields the backend actually returned — never invents a
// repository or function name.
export default function CodeLocalization({ incident }) {
  if (!incident) return null

  const repository = incident.repository || incident.repo || incident.repository_evidence?.repository
  const functionName =
    incident.function_name ||
    incident.function ||
    incident.repository_evidence?.function ||
    incident.repository_evidence?.function_name

  const hasAnyContext = repository || functionName || incident.file_path

  if (!hasAnyContext) return null

  return (
    <div className="space-y-2.5">
      {(repository || functionName) && (
        <div className="flex flex-wrap gap-4 text-xs">
          {repository && (
            <span className="inline-flex items-center gap-1.5 text-ink-secondary">
              <Folder size={13} className="text-ink-muted" />
              Repository: <span className="text-ink-primary font-mono">{repository}</span>
            </span>
          )}
          {functionName && (
            <span className="inline-flex items-center gap-1.5 text-ink-secondary">
              <FunctionSquare size={13} className="text-ink-muted" />
              Function: <span className="text-ink-primary font-mono">{functionName}</span>
            </span>
          )}
        </div>
      )}
      <CodeEvidenceCard
        filePath={incident.file_path}
        lineStart={incident.line_start}
        lineEnd={incident.line_end}
        snippet={incident.repository_evidence?.context || incident.code_snippet}
        matchedTerms={incident.repository_evidence?.matched_terms}
        score={incident.repository_evidence?.score}
      />
    </div>
  )
}
