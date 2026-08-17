from __future__ import annotations

from pathlib import Path

from backend.core.incident_history import IncidentHistoryRepository, IncidentHistoryService
from backend.core.investigation import IncidentDecisionEngine
from backend.core.support import SupportResponseService


def _service(tmp_path: Path) -> SupportResponseService:
    history = IncidentHistoryService(IncidentHistoryRepository(tmp_path / "history.db"))
    return SupportResponseService(IncidentDecisionEngine(history))


def _fake_investigator(repo: str, source_type: str):
    class FakeResult:
        def to_dict(self):
            return {
                "available": True,
                "source_type": "local",
                "repository": repo,
                "scanned_files": 1,
                "findings": [
                    {
                        "file_path": "src/rate_limiter.py",
                        "line_start": 7,
                        "line_end": 7,
                        "score": 68,
                        "matched_terms": ["suspicious-limit-value"],
                        "evidence": ["Suspicious low limit value: self.max_requests = 2"],
                        "context": "7: self.max_requests = 2",
                    }
                ],
            }

    class FakeInvestigator:
        def investigate(self, incident, stack_trace=None):
            return FakeResult()

    return FakeInvestigator()


def _fake_llm(**kwargs):
    return {
        "root_cause": "Rate limiter is configured with max_requests = 2.",
        "file_path": "src/rate_limiter.py",
        "line_start": 7,
        "line_end": 7,
        "evidence": ["Suspicious low limit value: self.max_requests = 2"],
        "suggested_fix": "Increase the production request quota.",
        "prevention": "Validate rate-limit configuration during deployment.",
        "confidence": 0.95,
        "summary": "The low rate limit causes the incident.",
    }


def test_new_incident_returns_unified_support_response(tmp_path: Path):
    service = _service(tmp_path)
    response = service.handle(
        "GET /products returns HTTP 429 Too Many Requests",
        "sample-repo",
        service="sample-api",
        route="/products",
        investigator_factory=_fake_investigator,
        llm_rca=_fake_llm,
        historical_evidence=[{"id": "RCA-1", "similarity": 0.8}],
    )

    assert response.incident_status == "NEW"
    assert response.action == "INVESTIGATE_AND_SAVE"
    assert response.history_id == 1
    assert response.file_path == "src/rate_limiter.py"
    assert response.line_start == 7
    assert response.historical_evidence


def test_known_incident_returns_reminder_without_investigation(tmp_path: Path):
    service = _service(tmp_path)
    kwargs = dict(
        incident="GET /products returns HTTP 429 Too Many Requests",
        repository="sample-repo",
        service="sample-api",
        route="/products",
        investigator_factory=_fake_investigator,
        llm_rca=_fake_llm,
    )
    first = service.handle(**kwargs)
    second = service.handle(**kwargs)

    assert first.action == "INVESTIGATE_AND_SAVE"
    assert second.incident_status == "KNOWN"
    assert second.action == "REUSE_PREVIOUS_SOLUTION"
    assert second.history_id == first.history_id
    assert "Reminder" in second.support_message
