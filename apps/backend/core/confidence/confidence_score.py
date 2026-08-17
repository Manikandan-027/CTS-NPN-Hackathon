from __future__ import annotations

from typing import Any


def _clamp(value: float) -> float:
    """Keep a score between 0 and 1."""
    return max(0.0, min(1.0, value))


def calculate_confidence(
    incidents: list[dict[str, Any]],
    root_cause_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Calculate confidence for the predicted root cause.

    Confidence is based on:
        1. Retrieval quality
        2. Number of supporting incidents
        3. Root-cause agreement

    Returns a score between 0 and 1.
    """

    if not incidents:
        return {
            "confidence_score": 0.0,
            "confidence_percentage": 0.0,
            "confidence_level": "Low",
            "supporting_incidents": 0,
            "root_cause_agreement": 0.0,
            "average_retrieval_score": 0.0,
        }

    root_cause_counts = (
        root_cause_counts
        if isinstance(root_cause_counts, dict)
        else {}
    )

    # ---------------------------------------------------------
    # 1. Retrieval quality
    # ---------------------------------------------------------

    retrieval_scores = []

    for incident in incidents:
        score = incident.get(
            "final_score",
            incident.get(
                "semantic_score",
                incident.get(
                    "similarity",
                    0.0,
                ),
            ),
        )

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0

        retrieval_scores.append(
            _clamp(score)
        )

    average_retrieval_score = (
        sum(retrieval_scores)
        / len(retrieval_scores)
    )

    # ---------------------------------------------------------
    # 2. Supporting incident strength
    # ---------------------------------------------------------

    supporting_count = len(incidents)

    # More supporting historical incidents increase confidence,
    # but the contribution is capped.
    support_score = _clamp(
        supporting_count / 5.0
    )

    # ---------------------------------------------------------
    # 3. Root-cause agreement
    # ---------------------------------------------------------

    if root_cause_counts:
        total = sum(
            root_cause_counts.values()
        )

        highest_count = max(
            root_cause_counts.values()
        )

        root_cause_agreement = (
            highest_count / total
            if total > 0
            else 0.0
        )
    else:
        root_cause_agreement = 0.0

    # ---------------------------------------------------------
    # Final confidence
    # ---------------------------------------------------------

    confidence_score = (
        average_retrieval_score * 0.50
        + support_score * 0.20
        + root_cause_agreement * 0.30
    )

    confidence_score = _clamp(
        confidence_score
    )

    confidence_percentage = (
        confidence_score * 100
    )

    if confidence_score >= 0.80:
        confidence_level = "High"
    elif confidence_score >= 0.60:
        confidence_level = "Medium"
    else:
        confidence_level = "Low"

    return {
        "confidence_score": round(
            confidence_score,
            4,
        ),
        "confidence_percentage": round(
            confidence_percentage,
            2,
        ),
        "confidence_level": confidence_level,
        "supporting_incidents": supporting_count,
        "root_cause_agreement": round(
            root_cause_agreement,
            4,
        ),
        "average_retrieval_score": round(
            average_retrieval_score,
            4,
        ),
    }