from __future__ import annotations

from typing import Any


SEMANTIC_WEIGHT = 0.70
SERVICE_WEIGHT = 0.15
CATEGORY_WEIGHT = 0.10
SEVERITY_WEIGHT = 0.05
class HybridReranker:
    """
    Configuration wrapper for the hybrid incident reranker.

    The actual ranking logic remains in rerank_incidents().
    This class exposes the configured weights for callers/tests
    that need access to the reranker configuration.
    """

    semantic_weight = SEMANTIC_WEIGHT
    service_weight = SERVICE_WEIGHT
    category_weight = CATEGORY_WEIGHT
    severity_weight = SEVERITY_WEIGHT

def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def _get_metadata(
    incident: dict[str, Any],
) -> dict[str, Any]:
    metadata = incident.get(
        "metadata",
        {},
    )

    if isinstance(metadata, dict):
        return metadata

    return {}


def _get_value(
    incident: dict[str, Any],
    key: str,
) -> str:
    metadata = _get_metadata(incident)

    if metadata.get(key) is not None:
        return _normalize(
            metadata.get(key)
        )

    if incident.get(key) is not None:
        return _normalize(
            incident.get(key)
        )

    # Dataset-compatible aliases
    aliases = {
        "service": "affected_service",
    }

    alias = aliases.get(key)

    if alias:
        if metadata.get(alias) is not None:
            return _normalize(
                metadata.get(alias)
            )

        if incident.get(alias) is not None:
            return _normalize(
                incident.get(alias)
            )

    return ""


def _match(
    query_value: Any,
    incident_value: Any,
) -> float:
    """
    Exact normalized metadata comparison.
    """

    query = _normalize(query_value)
    incident = _normalize(incident_value)

    if not query or not incident:
        return 0.0

    return 1.0 if query == incident else 0.0


def rerank_incidents(
    candidates: list[dict[str, Any]],
    query_metadata: dict[str, Any] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Re-rank semantic Top-20 candidates using metadata.

    IMPORTANT:
    query_metadata must come from the actual NEW INCIDENT.

    It must NEVER be copied from candidates[0].

    If metadata is unavailable, semantic similarity remains
    the primary ranking signal.
    """

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    if not candidates:
        return []

    query_metadata = (
        query_metadata
        if isinstance(query_metadata, dict)
        else {}
    )

    ranked: list[dict[str, Any]] = []

    for incident in candidates:

        semantic_score = float(
            incident.get(
                "semantic_score",
                incident.get(
                    "similarity",
                    0.0,
                ),
            )
        )

        service_match = _match(
            query_metadata.get("service"),
            _get_value(
                incident,
                "service",
            ),
        )

        category_match = _match(
            query_metadata.get("category"),
            _get_value(
                incident,
                "category",
            ),
        )

        severity_match = _match(
            query_metadata.get("severity"),
            _get_value(
                incident,
                "severity",
            ),
        )

        final_score = (
            semantic_score * SEMANTIC_WEIGHT
            + service_match * SERVICE_WEIGHT
            + category_match * CATEGORY_WEIGHT
            + severity_match * SEVERITY_WEIGHT
        )

        result = dict(incident)

        result["semantic_score"] = round(
            semantic_score,
            6,
        )

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
            item["semantic_score"],
        ),
        reverse=True,
    )

    return ranked[:top_k]