from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SupportResponse:
    """Stable, support-engineer-facing result of the incident workflow."""

    incident_status: str
    action: str
    message: str
    incident: str
    history_id: int | None
    root_cause: str | None
    file_path: str | None
    line_start: int | None
    line_end: int | None
    evidence: list[str]
    historical_evidence: list[dict[str, Any]]
    suggested_fix: str | None
    prevention: str | None
    confidence: float | None
    support_message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
