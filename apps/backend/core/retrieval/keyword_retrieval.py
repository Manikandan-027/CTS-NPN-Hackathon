from __future__ import annotations

import re
from typing import Any


def _tokenize(text: str) -> set[str]:
    """Convert text into normalized keyword tokens."""
    if not text or not text.strip():
        return set()

    return set(
        re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )
    )


def _keyword_score(
    query: str,
    incident_text: str,
) -> float:
    """
    Calculate keyword-overlap similarity.

    Score =
        matching query keywords / total query keywords
    """

    query_words = _tokenize(query)
    incident_words = _tokenize(incident_text)

    if not query_words:
        return 0.0

    matching_words = query_words.intersection(
        incident_words
    )

    return len(matching_words) / len(query_words)


def keyword_retrieve_incidents(
    query: str,
    incidents: list[dict[str, Any]],
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """
    Retrieve historical incidents using exact keyword overlap.

    The function searches the complete incident text, not only
    the 'description' field.

    This is important because the dataset uses:
        incident_description
        affected_service
        category
        severity
        root_cause
        resolution
        preventive_action
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    results: list[dict[str, Any]] = []

    for incident in incidents:

        searchable_fields = [
            incident.get(
                "incident_description",
                "",
            ),
            incident.get(
                "description",
                "",
            ),
            incident.get(
                "affected_service",
                "",
            ),
            incident.get(
                "service",
                "",
            ),
            incident.get(
                "category",
                "",
            ),
            incident.get(
                "severity",
                "",
            ),
            incident.get(
                "root_cause",
                "",
            ),
            incident.get(
                "resolution",
                "",
            ),
            incident.get(
                "preventive_action",
                "",
            ),
        ]

        incident_text = " ".join(
            str(value)
            for value in searchable_fields
            if value
        )

        score = _keyword_score(
            query,
            incident_text,
        )

        result = dict(incident)

        result["keyword_score"] = round(
            score,
            6,
        )

        results.append(result)

    results.sort(
        key=lambda item: item["keyword_score"],
        reverse=True,
    )

    return results[:top_k]