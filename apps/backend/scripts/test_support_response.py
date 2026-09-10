from __future__ import annotations

import tempfile
from pathlib import Path

from backend.core.incident_history import IncidentHistoryRepository, IncidentHistoryService
from backend.core.investigation import IncidentDecisionEngine
from backend.core.support import SupportResponseService


def fake_investigator(repo: str, source_type: str):
    class Result:
        def to_dict(self):
            return {
                "available": True,
                "source_type": "local",
                "repository": repo,
                "scanned_files": 1,
                "findings": [{
                    "file_path": "src/rate_limiter.py", "line_start": 7, "line_end": 7,
                    "score": 68, "matched_terms": ["suspicious-limit-value"],
                    "evidence": ["Suspicious low limit value: self.max_requests = 2"],
                    "context": "7: self.max_requests = 2",
                }],
            }

    class Investigator:
        def investigate(self, incident, stack_trace=None):
            return Result()
    return Investigator()


def fake_llm(**kwargs):
    return {
        "root_cause": "Rate limiter is configured with max_requests = 2.",
        "file_path": "src/rate_limiter.py", "line_start": 7, "line_end": 7,
        "evidence": ["Suspicious low limit value: self.max_requests = 2"],
        "suggested_fix": "Increase the production request quota.",
        "prevention": "Validate rate-limit configuration during deployment.",
        "confidence": 0.95,
        "summary": "The low rate limit causes the incident.",
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        db = Path(temp) / "history.db"
        history = IncidentHistoryService(IncidentHistoryRepository(db))
        service = SupportResponseService(IncidentDecisionEngine(history))
        kwargs = dict(
            incident="GET /products returns HTTP 429 Too Many Requests immediately for a new user",
            repository="sample-code-project",
            service="sample-api",
            route="/products",
            investigator_factory=fake_investigator,
            llm_rca=fake_llm,
            historical_evidence=[{"id": "RCA-07162", "similarity": 0.72, "root_cause": "API configuration issue"}],
        )
        first = service.handle(**kwargs)
        second = service.handle(**kwargs)
        assert first.action == "INVESTIGATE_AND_SAVE"
        assert first.incident_status == "NEW"
        assert second.action == "REUSE_PREVIOUS_SOLUTION"
        assert second.incident_status == "KNOWN"
        assert second.history_id == first.history_id
        print("Unified support response phase: PASS")
        print("First :", first.to_dict())
        print("Second:", second.to_dict())


if __name__ == "__main__":
    main()
