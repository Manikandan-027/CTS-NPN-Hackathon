from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.core.code_investigation import LocalRepositorySource, RepositoryInvestigator
from backend.core.incident_history import IncidentHistoryService, HistoryLookupResult


@dataclass(frozen=True)
class InvestigationDecision:
    action: str
    history_match: HistoryLookupResult
    result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "history_match": self.history_match.to_dict(),
            "result": self.result,
        }


class IncidentDecisionEngine:
    """Decide whether to reuse a previous solution or investigate current source code."""

    def __init__(self, history: IncidentHistoryService) -> None:
        self.history = history

    def handle(
        self,
        incident: str,
        repository: str,
        *,
        service: str | None = None,
        route: str | None = None,
        stack_trace: str | None = None,
        source_type: str = "local",
        investigator_factory: Callable[[str, str], RepositoryInvestigator] | None = None,
        llm_rca: Callable[..., dict[str, Any]] | None = None,
        historical_evidence: list[dict[str, Any]] | None = None,
        rag_retriever: Callable[[str, int], list[dict[str, Any]]] | None = None,
        rag_top_k: int = 5,
    ) -> InvestigationDecision:
        history_match = self.history.lookup(incident, repository, service, route)
        rag_results = historical_evidence
        if rag_results is None and rag_retriever is not None:
            rag_results = rag_retriever(incident, rag_top_k)
        rag_results = rag_results or []
        if history_match.found and history_match.record:
            record = history_match.record
            return InvestigationDecision(
                action="REUSE_PREVIOUS_SOLUTION",
                history_match=history_match,
                result={
                    "message": "A previous solution exists. Remind the support engineer instead of rescanning the repository.",
                    "root_cause": record.root_cause,
                    "file_path": record.file_path,
                    "line_start": record.line_start,
                    "line_end": record.line_end,
                    "evidence": record.evidence,
                    "suggested_fix": record.suggested_fix,
                    "prevention": record.prevention,
                    "confidence": record.confidence,
                    "history_id": record.id,
                    "historical_rag": rag_results,
                },
            )

        if investigator_factory is None:
            investigator_factory = lambda repo, kind: RepositoryInvestigator(LocalRepositorySource(repo))
        investigator = investigator_factory(repository, source_type)
        evidence = investigator.investigate(incident, stack_trace).to_dict()
        if not evidence.get("findings"):
            raise RuntimeError("No relevant repository evidence found for a new incident.")
        if llm_rca is None:
            raise ValueError("llm_rca is required for a new incident.")

        investigation = llm_rca(
            incident=incident,
            historical_evidence=rag_results,
            repository_evidence=evidence,
            stack_trace=stack_trace,
        )
        saved = self.history.save_new_investigation(
            incident,
            repository,
            investigation,
            service=service,
            route=route,
            source_type=source_type,
        )
        return InvestigationDecision(
            action="INVESTIGATE_AND_SAVE",
            history_match=history_match,
            result={
                **investigation,
                "history_id": saved.id,
                "historical_rag": rag_results,
                "message": "New issue investigated in the current codebase and the solution was saved for future incidents.",
            },
        )
