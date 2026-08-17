from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class IncidentHistoryRecord:
    id: int
    fingerprint: str
    error_signature: str
    incident: str
    repository: str
    source_type: str
    service: str | None
    route: str | None
    root_cause: str
    file_path: str
    line_start: int
    line_end: int
    evidence: list[str]
    suggested_fix: str
    prevention: str
    confidence: float
    status: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class HistoryLookupResult:
    found: bool
    match_type: str | None
    record: IncidentHistoryRecord | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "match_type": self.match_type,
            "record": self.record.to_dict() if self.record else None,
        }
