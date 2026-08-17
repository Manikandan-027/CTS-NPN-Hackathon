from __future__ import annotations

from collections import Counter
from typing import Any


def _normalize(value: Any) -> str:
    """Normalize a value for comparison."""
    if value is None:
        return ""

    return str(value).strip().lower()


def _get_metadata(incident: dict[str, Any]) -> dict[str, Any]:
    """Return incident metadata safely."""
    metadata = incident.get("metadata", {})

    if isinstance(metadata, dict):
        return metadata

    return {}


def _get_value(
    incident: dict[str, Any],
    key: str,
) -> str:
    """
    Read a value from metadata or directly from the incident.

    Supports the dataset's affected_service field.
    """
    metadata = _get_metadata(incident)

    if metadata.get(key) is not None:
        return _normalize(metadata[key])

    if incident.get(key) is not None:
        return _normalize(incident[key])

    aliases = {
        "service": "affected_service",
    }

    alias = aliases.get(key)

    if alias:
        if metadata.get(alias) is not None:
            return _normalize(metadata[alias])

        if incident.get(alias) is not None:
            return _normalize(incident[alias])

    return ""


def _build_pattern(incident: dict[str, Any]) -> str:
    """
    Build the recurring-incident pattern.

    Pattern:
        service + category + root cause
    """

    service = _get_value(incident, "service")
    category = _get_value(incident, "category")

    metadata = _get_metadata(incident)

    root_cause = _normalize(
        metadata.get(
            "root_cause",
            incident.get("root_cause", ""),
        )
    )

    parts = [
        service,
        category,
        root_cause,
    ]

    return " | ".join(
        part for part in parts if part
    )


def detect_recurring_incident(
    incidents: list[dict[str, Any]],
    min_occurrences: int = 2,
) -> dict[str, Any]:
    """
    Detect whether a recurring incident pattern exists.

    A recurring pattern is identified when the same
    service + category + root cause occurs at least
    `min_occurrences` times.

    Parameters
    ----------
    incidents:
        Retrieved historical incidents.

    min_occurrences:
        Minimum number of occurrences required to
        classify a pattern as recurring.

    Returns
    -------
    dict
        Recurrence analysis result.
    """

    if min_occurrences <= 0:
        raise ValueError(
            "min_occurrences must be greater than 0."
        )

    if not incidents:
        return {
            "is_recurring": False,
            "occurrence_count": 0,
            "recurrence_rate": 0.0,
            "recurring_pattern": "",
            "supporting_incidents": [],
            "pattern_counts": {},
        }

    pattern_to_incidents: dict[
        str,
        list[str],
    ] = {}

    for incident in incidents:
        pattern = _build_pattern(incident)

        if not pattern:
            continue

        incident_id = str(
            incident.get(
                "incident_id",
                "",
            )
        )

        pattern_to_incidents.setdefault(
            pattern,
            [],
        ).append(incident_id)

    if not pattern_to_incidents:
        return {
            "is_recurring": False,
            "occurrence_count": 0,
            "recurrence_rate": 0.0,
            "recurring_pattern": "",
            "supporting_incidents": [],
            "pattern_counts": {},
        }

    pattern_counts = {
        pattern: len(ids)
        for pattern, ids in pattern_to_incidents.items()
    }

    best_pattern, supporting_incidents = max(
        pattern_to_incidents.items(),
        key=lambda item: len(item[1]),
    )

    occurrence_count = len(
        supporting_incidents
    )

    is_recurring = (
        occurrence_count >= min_occurrences
    )

    recurrence_rate = (
        occurrence_count / len(incidents)
        if incidents
        else 0.0
    )

    return {
        "is_recurring": is_recurring,
        "occurrence_count": occurrence_count,
        "recurrence_rate": round(
            recurrence_rate,
            4,
        ),
        "recurring_pattern": (
            best_pattern
            if is_recurring
            else ""
        ),
        "supporting_incidents": (
            supporting_incidents
            if is_recurring
            else []
        ),
        "pattern_counts": pattern_counts,
    }