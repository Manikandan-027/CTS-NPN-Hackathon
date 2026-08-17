from __future__ import annotations

from typing import Any

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


def analyze_incident(
    incidents: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Complete Phase 3 incident-analysis pipeline.

    Pipeline:

        Retrieved Top-5 incidents
                |
                v
        Root Cause Analysis
                |
                v
             Evidence
                |
                v
           Confidence
                |
                v
           Resolution
                |
                v
           Prevention
                |
                v
           Recurrence

    Returns one structured result suitable for
    backend/API/frontend integration.
    """

    # ---------------------------------------------------------
    # EMPTY INPUT
    # ---------------------------------------------------------

    if not incidents:
        return {
            "root_cause": {
                "likely_root_cause": None,
                "supporting_incidents": [],
                "root_cause_counts": {},
            },
            "evidence": {
                "root_cause": None,
                "evidence": [],
                "evidence_count": 0,
            },
            "confidence": {
                "confidence_score": 0.0,
                "confidence_percentage": 0.0,
                "confidence_level": "Low",
                "supporting_incidents": 0,
                "root_cause_agreement": 0.0,
                "average_retrieval_score": 0.0,
            },
            "resolution": {
                "recommended_resolution": None,
                "supporting_incidents": [],
                "resolution_counts": {},
            },
            "prevention": {
                "recommended_prevention": None,
                "supporting_incidents": [],
                "prevention_counts": {},
            },
            "recurrence": {
                "is_recurring": False,
                "occurrence_count": 0,
                "recurrence_rate": 0.0,
                "recurring_pattern": "",
                "supporting_incidents": [],
                "pattern_counts": {},
            },
        }

    # ---------------------------------------------------------
    # 1. ROOT CAUSE ANALYSIS
    # ---------------------------------------------------------

    root_cause_result = analyze_root_cause(
        incidents
    )

    likely_root_cause = root_cause_result.get(
        "likely_root_cause"
    )

    root_cause_counts = root_cause_result.get(
        "root_cause_counts",
        {},
    )

    # ---------------------------------------------------------
    # 2. EVIDENCE
    # ---------------------------------------------------------

    evidence_result = extract_evidence(
        incidents,
        likely_root_cause,
    )

    # ---------------------------------------------------------
    # 3. CONFIDENCE
    # ---------------------------------------------------------

    confidence_result = calculate_confidence(
        incidents,
        root_cause_counts,
    )

    # ---------------------------------------------------------
    # 4. RESOLUTION
    # ---------------------------------------------------------

    resolution_result = recommend_resolution(
        incidents
    )

    # ---------------------------------------------------------
    # 5. PREVENTION
    # ---------------------------------------------------------

    prevention_result = recommend_prevention(
        incidents
    )

    # ---------------------------------------------------------
    # 6. RECURRING INCIDENT
    # ---------------------------------------------------------

    recurrence_result = detect_recurring_incident(
        incidents
    )

    # ---------------------------------------------------------
    # FINAL STRUCTURED RESULT
    # ---------------------------------------------------------

    return {
        "root_cause": root_cause_result,
        "evidence": evidence_result,
        "confidence": confidence_result,
        "resolution": resolution_result,
        "prevention": prevention_result,
        "recurrence": recurrence_result,
    }