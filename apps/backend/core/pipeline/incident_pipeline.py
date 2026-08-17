from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from backend.core.retrieval.keyword_retrieval import (
    keyword_retrieve_incidents,
)

from backend.core.retrieval.keyword_reranker import (
    rerank_keyword_incidents,
)

from backend.core.retrieval.semantic_retrieval import (
    retrieve_similar_incidents,
)

from backend.core.hybrid_retrieval.reranker import (
    rerank_incidents,
)

from backend.core.rca.root_cause_analyzer import (
    analyze_root_cause,
)

from backend.core.evidence.evidence_extractor import (
    extract_evidence,
)

from backend.core.confidence.confidence_score import (
    calculate_confidence,
)

from backend.core.resolution.resolution_recommender import (
    recommend_resolution,
)

from backend.core.prevention.prevention_recommender import (
    recommend_prevention,
)

from backend.core.recurrence.recurring_incident_detector import (
    detect_recurring_incident,
)

from backend.core.code_investigation import (
    LocalRepositorySource,
    RepositoryInvestigator,
)

from backend.core.llm.code_aware_rca import (
    generate_code_aware_rca,
)


DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
    / "processed_incidents.jsonl"
)


# =========================================================
# DEVELOPER KNOWLEDGE BASE / NOVELTY GATE
# =========================================================

DEVELOPER_KB_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "knowledge_base.json"
)

VECTOR_RELEVANCE_THRESHOLD = float(
    os.getenv(
        "RCA_VECTOR_RELEVANCE_THRESHOLD",
        "0.70",
    )
)

DEVELOPER_KB_RELEVANCE_THRESHOLD = float(
    os.getenv(
        "RCA_KB_RELEVANCE_THRESHOLD",
        "0.38",
    )
)

GENERIC_STOP_WORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in",
    "on", "at", "is", "was", "were", "with", "when", "then",
    "this", "that", "from", "api", "request", "requests",
    "service", "application", "error", "failed", "failure",
    "customer", "user", "users", "incident",
}


# =========================================================
# LOAD HISTORICAL INCIDENTS
# =========================================================

def load_incidents() -> list[dict[str, Any]]:

    if not DATA_PATH.exists():

        raise FileNotFoundError(
            f"Incident dataset not found: {DATA_PATH}"
        )

    incidents = []

    with DATA_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

            line = line.strip()

            if line:
                incidents.append(
                    json.loads(line)
                )

    return incidents



# =========================================================
# DEVELOPER KNOWLEDGE BASE HELPERS
# =========================================================

def _kb_tokens(text: str) -> set[str]:
    tokens = re.findall(
        r"[a-z0-9]+",
        str(text).lower(),
    )
    return {
        token
        for token in tokens
        if len(token) >= 3
        and token not in GENERIC_STOP_WORDS
    }


def _kb_similarity(
    query: str,
    candidate: str,
) -> float:
    q_tokens = _kb_tokens(query)
    c_tokens = _kb_tokens(candidate)

    jaccard = 0.0
    if q_tokens and c_tokens:
        jaccard = len(
            q_tokens & c_tokens
        ) / len(
            q_tokens | c_tokens
        )

    sequence = SequenceMatcher(
        None,
        query.lower().strip(),
        candidate.lower().strip(),
    ).ratio()

    return round(
        0.70 * jaccard + 0.30 * sequence,
        6,
    )


def load_developer_knowledge_base() -> list[dict[str, Any]]:
    if not DEVELOPER_KB_PATH.exists():
        return []

    try:
        data = json.loads(
            DEVELOPER_KB_PATH.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError):
        return []

    return data if isinstance(data, list) else []


def retrieve_developer_knowledge(
    incident: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for record in load_developer_knowledge_base():

        if str(
            record.get("status", "")
        ).upper() not in {
            "APPROVED",
            "SOLVED",
            "VALIDATED",
        }:
            continue

        text = str(
            record.get("incident", "")
        ).strip()

        if not text:
            continue

        score = _kb_similarity(
            incident,
            text,
        )

        candidates.append(
            {
                "incident_id":
                    record.get("incident_id"),

                "id":
                    record.get("incident_id"),

                "similarity":
                    score,

                "final_score":
                    score,

                "source":
                    "developer_knowledge_base",

                "incident_description":
                    text,

                "metadata": {
                    "root_cause":
                        record.get("root_cause"),

                    "resolution":
                        record.get("resolution"),

                    "preventive_action":
                        record.get(
                            "prevention",
                            record.get(
                                "preventive_action"
                            ),
                        ),

                    "service":
                        record.get("service"),

                    "category":
                        record.get(
                            "category",
                            "Developer Knowledge",
                        ),

                    "status":
                        "Approved",

                    "source_type":
                        "DeveloperKnowledgeBase",

                    "repository":
                        record.get("repository"),

                    "file_path":
                        record.get("file_path"),

                    "line_start":
                        record.get("line_start"),

                    "line_end":
                        record.get("line_end"),
                },
            }
        )

    candidates.sort(
        key=lambda item: (
            -float(
                item.get("similarity", 0.0)
            ),
            str(
                item.get(
                    "incident_id",
                    "",
                )
            ),
        )
    )

    return candidates[:top_k]


def merge_historical_candidates(
    vector_candidates: list[dict[str, Any]],
    developer_candidates: list[dict[str, Any]],
    top_k: int = 20,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for item in [
        *vector_candidates,
        *developer_candidates,
    ]:
        key = str(
            item.get(
                "incident_id",
                item.get("id", ""),
            )
        )

        if not key:
            continue

        existing = merged.get(key)

        if existing is None:
            merged[key] = item
            continue

        existing_score = float(
            existing.get("similarity", 0.0)
        )
        new_score = float(
            item.get("similarity", 0.0)
        )

        if new_score > existing_score:
            merged[key] = item

    result = list(
        merged.values()
    )

    result.sort(
        key=lambda item: (
            -float(
                item.get("similarity", 0.0)
            ),
            str(
                item.get(
                    "incident_id",
                    item.get("id", ""),
                )
            ),
        )
    )

    return result[:top_k]


def _candidate_has_evidence(
    item: dict[str, Any],
) -> bool:
    metadata = (
        item.get("metadata", {})
        or {}
    )

    root_cause = (
        metadata.get("root_cause")
        or item.get("root_cause")
    )

    resolution = (
        metadata.get("resolution")
        or item.get("resolution")
    )

    prevention = (
        metadata.get("preventive_action")
        or item.get("preventive_action")
    )

    return bool(
        root_cause
        and (resolution or prevention)
    )


def assess_historical_relevance(
    incident: str,
    top20: list[dict[str, Any]],
    query_metadata: dict[str, str],
) -> dict[str, Any]:
    """
    The vector store can always return nearest neighbors.
    Non-empty Top-20 therefore does NOT imply historical evidence.

    A vector candidate is accepted only when:
      1. similarity passes the absolute threshold,
      2. it contains validated historical evidence, and
      3. the incident is in the known payment/domain context OR
         the metadata service matches.

    Developer-approved KB entries use a separate lexical threshold.
    """

    best_vector = 0.0
    best_kb = 0.0
    meaningful_count = 0
    accepted_count = 0
    service_match_count = 0

    query_service = str(
        query_metadata.get(
            "service",
            "",
        )
    ).lower()

    incident_lower = incident.lower()

    payment_domain = any(
        term in incident_lower
        for term in (
            "payment",
            "checkout",
            "transaction",
            "card",
            "gateway",
        )
    )

    for item in top20:

        score = float(
            item.get(
                "similarity",
                0.0,
            )
            or 0.0
        )

        source = str(
            item.get(
                "source",
                "",
            )
        ).lower()

        metadata = (
            item.get(
                "metadata",
                {}
            )
            or {}
        )

        if source == "developer_knowledge_base":

            best_kb = max(
                best_kb,
                score,
            )

            if (
                score >=
                DEVELOPER_KB_RELEVANCE_THRESHOLD
                and _candidate_has_evidence(item)
            ):
                meaningful_count += 1
                accepted_count += 1

            continue

        best_vector = max(
            best_vector,
            score,
        )

        evidence_available = (
            _candidate_has_evidence(item)
        )

        if evidence_available:
            meaningful_count += 1

        candidate_service = str(
            metadata.get(
                "service",
                item.get(
                    "affected_service",
                    "",
                ),
            )
            or ""
        ).lower()

        service_match = bool(
            query_service
            and candidate_service
            and query_service == candidate_service
        )

        if service_match:
            service_match_count += 1

        domain_match = (
            payment_domain
            and (
                "payment" in candidate_service
                or "payment" in str(
                    metadata.get(
                        "category",
                        "",
                    )
                ).lower()
            )
        )

        if (
            score >= VECTOR_RELEVANCE_THRESHOLD
            and evidence_available
            and (
                service_match
                or domain_match
            )
        ):
            accepted_count += 1

    vector_relevant = (
        best_vector >= VECTOR_RELEVANCE_THRESHOLD
        and accepted_count > 0
    )

    kb_relevant = (
        best_kb >= DEVELOPER_KB_RELEVANCE_THRESHOLD
        and any(
            str(
                item.get(
                    "source",
                    "",
                )
            ).lower()
            == "developer_knowledge_base"
            and float(
                item.get(
                    "similarity",
                    0.0,
                )
            )
            >= DEVELOPER_KB_RELEVANCE_THRESHOLD
            and _candidate_has_evidence(item)
            for item in top20
        )
    )

    is_relevant = (
        vector_relevant
        or kb_relevant
    )

    if is_relevant:
        reason = (
            "Historical evidence passed the relevance gate."
        )
    elif meaningful_count == 0:
        reason = (
            "Candidates were returned, but no meaningful "
            "validated historical evidence was found."
        )
    else:
        reason = (
            "Historical candidates did not meet the minimum "
            "relevance/domain threshold."
        )

    return {
        "is_relevant":
            is_relevant,

        "reason":
            reason,

        "best_vector_similarity":
            round(best_vector, 6),

        "best_developer_kb_similarity":
            round(best_kb, 6),

        "vector_threshold":
            VECTOR_RELEVANCE_THRESHOLD,

        "developer_kb_threshold":
            DEVELOPER_KB_RELEVANCE_THRESHOLD,

        "meaningful_evidence_count":
            meaningful_count,

        "accepted_count":
            accepted_count,

        "service_match_count":
            service_match_count,

        "candidate_count":
            len(top20),
    }


# =========================================================
# QUERY METADATA
# =========================================================

def _extract_query_metadata(
    incident: str,
) -> dict[str, str]:

    text = incident.lower()

    service = ""
    category = ""
    severity = ""

    if "payment" in text:
        service = "Payment API"

    elif "customer api" in text:
        service = "Customer API"

    elif "inventory api" in text:
        service = "Inventory API"

    elif "order api" in text:
        service = "Order API"

    if any(
        keyword in text
        for keyword in (
            "http",
            "api",
            "401",
            "402",
            "403",
            "404",
            "429",
            "500",
            "502",
            "503",
        )
    ):

        category = "API / Microservices"

    if "critical severity" in text:
        severity = "Critical"

    elif "high severity" in text:
        severity = "High"

    elif "medium severity" in text:
        severity = "Medium"

    elif "low severity" in text:
        severity = "Low"

    return {
        "service": service,
        "category": category,
        "severity": severity,
    }


# =========================================================
# REPOSITORY INVESTIGATION
# =========================================================

def investigate_repository(
    incident: str,
    repository: str,
    stack_trace: str | None = None,
) -> dict[str, Any]:

    source = LocalRepositorySource(
        repository
    )

    investigator = RepositoryInvestigator(
        source
    )

    evidence = investigator.investigate(
        incident,
        stack_trace,
    )

    return evidence.to_dict()


# =========================================================
# MAIN PIPELINE
# =========================================================

def run_incident_pipeline(
    incident: str,
    *,
    repository: str | None = None,
    stack_trace: str | None = None,
) -> dict[str, Any]:

    if not incident or not incident.strip():

        raise ValueError(
            "Incident description cannot be empty."
        )

    incident = incident.strip()

    # =====================================================
    # HISTORICAL DATA
    # =====================================================

    historical_incidents = (
        load_incidents()
    )

    # =====================================================
    # 1. KEYWORD RETRIEVAL TOP 20
    # =====================================================

    keyword_top20 = (
        keyword_retrieve_incidents(
            incident,
            historical_incidents,
            top_k=20,
        )
    )

    # =====================================================
    # 2. KEYWORD RERANK TOP 5
    # =====================================================

    keyword_top5 = (
        rerank_keyword_incidents(
            keyword_top20,
            incident,
            top_k=5,
        )
    )

    # =====================================================
    # 3. SEMANTIC RETRIEVAL TOP 20
    # =====================================================

    semantic_vector_top20 = (
        retrieve_similar_incidents(
            incident,
            top_k=20,
        )
    )

    developer_kb_top5 = (
        retrieve_developer_knowledge(
            incident,
            top_k=5,
        )
    )

    semantic_top20 = merge_historical_candidates(
        semantic_vector_top20,
        developer_kb_top5,
        top_k=20,
    )

    # =====================================================
    # 4. HYBRID / METADATA RERANK TOP 5
    # =====================================================

    query_metadata = (
        _extract_query_metadata(
            incident
        )
    )

    # =====================================================
    # 4A. HISTORICAL RELEVANCE GATE
    # =====================================================

    historical_relevance = assess_historical_relevance(
        incident,
        semantic_top20,
        query_metadata,
    )

    if not historical_relevance["is_relevant"]:

        return {
            "input_incident":
                incident,

            "incident_status":
                "COMPLETELY_NEW",

            "action":
                "REQUEST_KNOWLEDGE_BASE_ENTRY",

            "message": (
                "This is a completely new incident. "
                "No sufficiently similar historical incident "
                "or validated evidence was found."
            ),

            "query_metadata":
                query_metadata,

            "historical_relevance":
                historical_relevance,

            "keyword_retrieval": {
                "top20":
                    keyword_top20,

                "top5":
                    keyword_top5,
            },

            "semantic_retrieval": {
                "top20":
                    semantic_top20,

                "top5":
                    [],

                "accepted":
                    [],
            },

            "developer_knowledge": {
                "status":
                    "NOT_FOUND",

                "required":
                    True,

                "message": (
                    "Developer must add the verified incident, "
                    "root cause, resolution and prevention."
                ),

                "storage":
                    str(DEVELOPER_KB_PATH),
            },

            "root_cause":
                {
                    "historical":
                        None,
                },

            "evidence":
                {
                    "historical":
                        None,
                },

            "historical_evidence":
                [],

            "repository_evidence":
                None,

            "code_aware_llm":
                None,

            "confidence":
                {
                    "confidence":
                        0.0,

                    "reason":
                        "No sufficiently relevant historical evidence.",
                },

            "resolution":
                {
                    "recommended_resolution":
                        None,
                },

            "prevention":
                {
                    "recommended_prevention":
                        None,
                },

            "recurrence":
                {
                    "is_recurring":
                        False,

                    "occurrence_count":
                        0,
                },

            "final_root_cause":
                None,

            "final_file_path":
                None,

            "final_line_start":
                None,

            "final_line_end":
                None,

            "final_evidence":
                [],

            "final_resolution":
                None,

            "final_prevention":
                None,

            "llm_confidence":
                None,

            "summary":
                (
                    "No sufficiently similar historical "
                    "evidence exists. Developer knowledge-base "
                    "entry is required."
                ),

            "validation": {
                "required":
                    True,

                "status":
                    "PENDING_DEVELOPER_KB_ENTRY",
            },
        }

    semantic_top5 = rerank_incidents(
        semantic_top20,
        query_metadata,
        top_k=5,
    )

    # =====================================================
    # 5. ROOT CAUSE
    # =====================================================

    root_cause_result = (
        analyze_root_cause(
            semantic_top5
        )
    )

    likely_root_cause = (
        root_cause_result.get(
            "likely_root_cause"
        )
    )

    root_cause_counts = (
        root_cause_result.get(
            "root_cause_counts",
            {},
        )
    )

    # =====================================================
    # 6. HISTORICAL EVIDENCE
    # =====================================================

    evidence_result = extract_evidence(
        semantic_top5,
        likely_root_cause,
    )

    # =====================================================
    # 7. HISTORICAL EVIDENCE FOR LLM
    # =====================================================

    historical_evidence = []

    for item in semantic_top5:

        metadata = item.get(
            "metadata",
            {}
        )

        historical_evidence.append(
            {
                "id":
                    item.get(
                        "incident_id",
                        item.get("id"),
                    ),

                "similarity":
                    item.get(
                        "similarity"
                    ),

                "root_cause":
                    metadata.get(
                        "root_cause",
                        item.get(
                            "root_cause"
                        ),
                    ),

                "resolution":
                    metadata.get(
                        "resolution",
                        item.get(
                            "resolution"
                        ),
                    ),

                "preventive_action":
                    metadata.get(
                        "preventive_action",
                        item.get(
                            "preventive_action"
                        ),
                    ),

                "service":
                    metadata.get(
                        "service",
                        item.get(
                            "affected_service"
                        ),
                    ),

                "category":
                    metadata.get(
                        "category",
                        item.get(
                            "category"
                        ),
                    ),

                "severity":
                    metadata.get(
                        "severity",
                        item.get(
                            "severity"
                        ),
                    ),

                "priority":
                    metadata.get(
                        "priority",
                        item.get(
                            "priority"
                        ),
                    ),

                "environment":
                    metadata.get(
                        "environment",
                        item.get(
                            "environment"
                        ),
                    ),

                "status":
                    metadata.get(
                        "status"
                    ),
            }
        )

    # =====================================================
    # 8. CURRENT REPOSITORY
    # =====================================================

    repository_evidence = None

    code_rca = None

    if repository:

        repository_evidence = (
            investigate_repository(
                incident,
                repository,
                stack_trace,
            )
        )

        # =================================================
        # 9. CODE-AWARE LLM
        # =================================================

        if repository_evidence.get(
            "findings"
        ):

            code_rca = (
                generate_code_aware_rca(
                    incident=incident,
                    historical_evidence=(
                        historical_evidence
                    ),
                    repository_evidence=(
                        repository_evidence
                    ),
                    stack_trace=stack_trace,
                )
            )

    # =====================================================
    # 10. CONFIDENCE
    # =====================================================

    confidence_result = (
        calculate_confidence(
            semantic_top5,
            root_cause_counts,
        )
    )

    # =====================================================
    # 11. RESOLUTION
    # =====================================================

    resolution_result = (
        recommend_resolution(
            semantic_top5
        )
    )

    # =====================================================
    # 12. PREVENTION
    # =====================================================

    prevention_result = (
        recommend_prevention(
            semantic_top5
        )
    )

    # =====================================================
    # 13. RECURRENCE
    # =====================================================

    recurrence_result = (
        detect_recurring_incident(
            semantic_top5
        )
    )

    # =====================================================
    # FINAL RESULT
    # =====================================================

    return {

        "input_incident":
            incident,

        "query_metadata":
            query_metadata,

        "keyword_retrieval": {

            "top20":
                keyword_top20,

            "top5":
                keyword_top5,
        },

        "semantic_retrieval": {

            "top20":
                semantic_top20,

            "top5":
                semantic_top5,

            "relevance_gate":
                historical_relevance,
        },

        "developer_knowledge": {
            "status":
                "AVAILABLE"
                if developer_kb_top5
                else "NONE",

            "candidates":
                developer_kb_top5,

            "source":
                str(DEVELOPER_KB_PATH),
        },

        "historical_relevance":
            historical_relevance,

        "root_cause": {

            "historical":
                root_cause_result,
        },

        "evidence": {

            "historical":
                evidence_result,
        },

        "confidence":
            confidence_result,

        "resolution":
            resolution_result,

        "prevention":
            prevention_result,

        "recurrence":
            recurrence_result,

        "repository_evidence":
            repository_evidence,

        "code_aware_llm":
            code_rca,

        "historical_evidence":
            historical_evidence,

        "final_root_cause":
            (
                code_rca.get(
                    "root_cause"
                )
                if code_rca
                else likely_root_cause
            ),

        "final_file_path":
            (
                code_rca.get(
                    "file_path"
                )
                if code_rca
                else None
            ),

        "final_line_start":
            (
                code_rca.get(
                    "line_start"
                )
                if code_rca
                else None
            ),

        "final_line_end":
            (
                code_rca.get(
                    "line_end"
                )
                if code_rca
                else None
            ),

        "final_evidence":
            (
                code_rca.get(
                    "evidence",
                    [],
                )
                if code_rca
                else []
            ),

        "final_resolution":
            (
                code_rca.get(
                    "suggested_fix"
                )
                if code_rca
                else resolution_result
            ),

        "final_prevention":
            (
                code_rca.get(
                    "prevention"
                )
                if code_rca
                else prevention_result
            ),

        "llm_confidence":
            (
                code_rca.get(
                    "confidence"
                )
                if code_rca
                else None
            ),

        "summary":
            (
                code_rca.get(
                    "summary"
                )
                if code_rca
                else ""
            ),
    }