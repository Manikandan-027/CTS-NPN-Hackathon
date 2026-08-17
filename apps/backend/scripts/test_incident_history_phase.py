from __future__ import annotations

import json
import tempfile
from pathlib import Path

from backend.core.incident_history import IncidentHistoryRepository, IncidentHistoryService
from backend.core.investigation import IncidentDecisionEngine


def fake_llm_rca(*, incident, historical_evidence, repository_evidence, stack_trace):
    finding = repository_evidence["findings"][0]
    return {
        "root_cause": "The rate limiter allows only two requests per minute, which is too restrictive for the intended endpoint.",
        "file_path": finding["file_path"],
        "line_start": finding["line_start"],
        "line_end": finding["line_end"],
        "evidence": finding["evidence"],
        "suggested_fix": "Increase the request quota to an appropriate production value and validate it before deployment.",
        "prevention": "Add configuration validation and a test for the first request from a new user.",
        "confidence": 0.95,
        "summary": "The rate-limit configuration is the cause of the 429 incident.",
    }


def main() -> None:
    root = Path("apps/sample_code_project").resolve()
    incident = "GET /products returns HTTP 429 Too Many Requests immediately for a new user"
    with tempfile.TemporaryDirectory(prefix="rca-history-test-") as directory:
        history = IncidentHistoryService(IncidentHistoryRepository(Path(directory) / "incident_history.db"))
        engine = IncidentDecisionEngine(history)
        first = engine.handle(
            incident, str(root), service="sample-api", route="/products",
            source_type="local", llm_rca=fake_llm_rca,
        )
        second = engine.handle(
            incident, str(root), service="sample-api", route="/products",
            source_type="local",
            llm_rca=lambda **_: (_ for _ in ()).throw(
                AssertionError("LLM must not run on a history hit")
            ),
        )
        print("=" * 72)
        print("INCIDENT HISTORY + CODE INVESTIGATION DECISION TEST")
        print("=" * 72)
        print("First incident:")
        print(json.dumps(first.to_dict(), indent=2, ensure_ascii=False))
        print("\nSecond identical incident:")
        print(json.dumps(second.to_dict(), indent=2, ensure_ascii=False))
        print("\nResult:")
        print("  First action :", first.action)
        print("  Second action:", second.action)
        print("=" * 72)
        assert first.action == "INVESTIGATE_AND_SAVE"
        assert second.action == "REUSE_PREVIOUS_SOLUTION"


if __name__ == "__main__":
    main()
