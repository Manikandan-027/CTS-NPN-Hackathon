from __future__ import annotations

from backend.core.investigation import IncidentDecisionEngine
from backend.core.incident_history.models import HistoryLookupResult


class FakeHistory:
    def __init__(self, found: bool = False):
        self.found = found

    def lookup(self, *args, **kwargs):
        return HistoryLookupResult(False, None, None)

    def save_new_investigation(self, *args, **kwargs):
        class Saved:
            id = 42
        return Saved()


class FakeEvidence:
    def to_dict(self):
        return {
            "available": True,
            "findings": [{"file_path": "src/a.py", "line_start": 2, "line_end": 2}],
        }


class FakeInvestigator:
    def investigate(self, *args, **kwargs):
        return FakeEvidence()


def test_rag_evidence_reaches_llm_and_is_returned():
    captured = {}

    def rag(query, top_k):
        assert query == "HTTP 500 payment failure"
        assert top_k == 3
        return [{"id": "RCA-1", "root_cause": "database timeout", "similarity": 0.91}]

    def llm_rca(**kwargs):
        captured.update(kwargs)
        return {
            "root_cause": "code issue",
            "file_path": "src/a.py",
            "line_start": 2,
            "line_end": 2,
            "evidence": ["bad code"],
            "suggested_fix": "fix it",
            "prevention": "test it",
            "confidence": 0.8,
            "summary": "summary",
        }

    engine = IncidentDecisionEngine(FakeHistory())
    decision = engine.handle(
        "HTTP 500 payment failure",
        "sample",
        investigator_factory=lambda *_: FakeInvestigator(),
        llm_rca=llm_rca,
        rag_retriever=rag,
        rag_top_k=3,
    )

    assert captured["historical_evidence"][0]["id"] == "RCA-1"
    assert decision.result["historical_rag"][0]["id"] == "RCA-1"
