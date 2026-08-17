from __future__ import annotations

from typing import Any


def _normalize(value: Any) -> str:
    """Normalize metadata values for comparison."""
    if value is None:
        return ""

    return str(value).strip().lower()


def _metadata_value(
    incident: dict[str, Any],
    *keys: str,
) -> str:
    """
    Read a metadata value from either the flat incident
    structure or nested metadata structure.
    """

    metadata = incident.get("metadata", {})

    if not isinstance(metadata, dict):
        metadata = {}

    for key in keys:

        if incident.get(key) is not None:
            return _normalize(incident.get(key))

        if metadata.get(key) is not None:
            return _normalize(metadata.get(key))

    return ""


def _metadata_match(
    query: str,
    value: str,
) -> float:
    """
    Check whether a metadata value is explicitly present
    in the user's incident description.

    We do NOT guess metadata.

    Example:

        query = "Payment API is returning HTTP 500"

        service = "Payment API"

        => match = 1.0
    """

    query_normalized = _normalize(query)

    if not query_normalized or not value:
        return 0.0

    if value in query_normalized:
        return 1.0

    return 0.0


def rerank_keyword_incidents(
    candidates: list[dict[str, Any]],
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Re-rank keyword Top-20 candidates.

    Keyword score remains the primary score.

    Metadata is used only when the metadata is explicitly
    identifiable from the user's incident text.

    This prevents fabricated query metadata.
    """

    if not query or not query.strip():
        raise ValueError(
            "Query cannot be empty."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    ranked: list[dict[str, Any]] = []

    for incident in candidates:

        keyword_score = float(
            incident.get(
                "keyword_score",
                0.0,
            )
        )

        service = _metadata_value(
            incident,
            "service",
            "affected_service",
        )

        category = _metadata_value(
            incident,
            "category",
        )

        severity = _metadata_value(
            incident,
            "severity",
        )

        service_match = _metadata_match(
            query,
            service,
        )

        category_match = _metadata_match(
            query,
            category,
        )

        severity_match = _metadata_match(
            query,
            severity,
        )

        # Keyword remains dominant.
        final_score = (
            keyword_score * 0.70
            + service_match * 0.15
            + category_match * 0.10
            + severity_match * 0.05
        )

        result = dict(incident)

        result["service_match"] = service_match
        result["category_match"] = category_match
        result["severity_match"] = severity_match

        result["final_score"] = round(
            final_score,
            6,
        )

        ranked.append(result)

    ranked.sort(
        key=lambda item: (
            item["final_score"],
            item.get("keyword_score", 0.0),
        ),
        reverse=True,
    )

    return ranked[:top_k]