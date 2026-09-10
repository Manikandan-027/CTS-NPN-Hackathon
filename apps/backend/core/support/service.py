from __future__ import annotations

from typing import Any, Callable

from backend.core.investigation import IncidentDecisionEngine, InvestigationDecision
from .models import SupportResponse


class SupportResponseService:
    """Convert the internal investigation decision into one demo/production-facing response."""

    def __init__(self, decision_engine: IncidentDecisionEngine) -> None:
        self.decision_engine = decision_engine

    def handle(
        self,
        incident: str,
        repository: str,
        *,
        service: str | None = None,
        route: str | None = None,
        stack_trace: str | None = None,
        source_type: str = "local",
        investigator_factory: Callable | None = None,
        llm_rca: Callable[..., dict[str, Any]] | None = None,
        historical_evidence: list[dict[str, Any]] | None = None,
        rag_retriever: Callable[[str, int], list[dict[str, Any]]] | None = None,
        rag_top_k: int = 5,
    ) -> SupportResponse:
        decision = self.decision_engine.handle(
            incident,
            repository,
            service=service,
            route=route,
            stack_trace=stack_trace,
            source_type=source_type,
            investigator_factory=investigator_factory,
            llm_rca=llm_rca,
            historical_evidence=historical_evidence,
            rag_retriever=rag_retriever,
            rag_top_k=rag_top_k,
        )
        return self._build_response(incident, decision)

    @staticmethod
    def _build_response(incident: str, decision: InvestigationDecision) -> SupportResponse:
        result = decision.result
        known = decision.action == "REUSE_PREVIOUS_SOLUTION"
        status = "KNOWN" if known else "NEW"
        if known:
            message = "A previous solution exists for this incident. Repository rescanning was skipped."
            support_message = (
                "Reminder for support engineer: this incident was previously investigated. "
                "Use the stored solution and follow the recorded code location."
            )
        else:
            message = "This is a new incident. The current codebase was investigated and the solution was saved."
            support_message = (
                "Action required: review the suggested fix at the reported code location, "
                "apply the change, test it, and redeploy according to your release process."
            )

        confidence = result.get("confidence")
        if confidence is not None:
            confidence = float(confidence)

        return SupportResponse(
            incident_status=status,
            action=decision.action,
            message=message,
            incident=incident,
            history_id=result.get("history_id"),
            root_cause=result.get("root_cause"),
            file_path=result.get("file_path"),
            line_start=result.get("line_start"),
            line_end=result.get("line_end"),
            evidence=list(result.get("evidence") or []),
            historical_evidence=list(result.get("historical_rag") or []),
            suggested_fix=result.get("suggested_fix"),
            prevention=result.get("prevention"),
            confidence=confidence,
            support_message=support_message,
        )
