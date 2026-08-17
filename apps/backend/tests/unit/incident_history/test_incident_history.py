from __future__ import annotations

from pathlib import Path

from backend.core.incident_history import IncidentHistoryRepository, IncidentHistoryService


def test_new_incident_is_saved_and_then_reused(tmp_path: Path) -> None:
    repository = IncidentHistoryRepository(tmp_path / "history.db")
    service = IncidentHistoryService(repository)
    incident = "GET /products returns HTTP 429 Too Many Requests immediately for a new user"
    repo = "/sample/project"
    investigation = {
        "root_cause": "Rate limiter quota is too low.",
        "file_path": "src/rate_limiter.py",
        "line_start": 7,
        "line_end": 7,
        "evidence": ["self.max_requests = 2"],
        "suggested_fix": "Increase the production request quota.",
        "prevention": "Validate rate-limit configuration in CI.",
        "confidence": 0.95,
    }
    assert not service.lookup(incident, repo).found
    saved = service.save_new_investigation(incident, repo, investigation)
    match = service.lookup(incident, repo)
    assert match.found
    assert match.match_type == "fingerprint"
    assert match.record is not None
    assert match.record.id == saved.id
    assert match.record.suggested_fix == investigation["suggested_fix"]
    activities = repository.list_activities(saved.id)
    assert any(item["activity_type"] == "NEW_INVESTIGATION_SAVED" for item in activities)
    assert any(item["activity_type"] == "HISTORY_MATCH" for item in activities)


def test_signature_reuses_solution_for_same_repository(tmp_path: Path) -> None:
    repository = IncidentHistoryRepository(tmp_path / "history.db")
    service = IncidentHistoryService(repository)
    service.save_new_investigation(
        "Payment API returns HTTP 500 after deployment",
        "repo-a",
        {
            "root_cause": "Bad configuration.",
            "file_path": "config.py",
            "line_start": 10,
            "line_end": 10,
            "evidence": ["limit = 2"],
            "suggested_fix": "Correct the configuration.",
            "prevention": "Add config validation.",
            "confidence": 0.8,
        },
    )
    result = service.lookup("Payment API returns HTTP 500 after deployment", "repo-a")
    assert result.found
    assert result.record is not None
