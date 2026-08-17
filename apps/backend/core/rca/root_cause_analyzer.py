from __future__ import annotations

from collections import Counter
from typing import Any


def _normalize_root_cause(value: Any) -> str:
    """Normalize a root-cause value for grouping."""
    if value is None:
        return ""

    return " ".join(str(value).strip().lower().split())


def analyze_root_cause(
    incidents: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Identify the most likely root cause from the retrieved
    historical incidents.

    The input should normally be the FINAL TOP 5 incidents
    produced by Phase 2.

    Root causes are grouped by normalized text and ranked
    by frequency.
    """

    if not incidents:
        return {
            "likely_root_cause": None,
            "supporting_incidents": [],
            "root_cause_counts": {},
            "total_incidents": 0,
        }

    root_cause_to_incidents: dict[
        str,
        list[str],
    ] = {}

    for incident in incidents:
        root_cause = _normalize_root_cause(
            incident.get("root_cause")
            or incident.get("metadata", {}).get(
                "root_cause",
                "",
            )
        )

        if not root_cause:
            continue

        incident_id = str(
            incident.get(
                "incident_id",
                "UNKNOWN",
            )
        )

        root_cause_to_incidents.setdefault(
            root_cause,
            [],
        ).append(incident_id)

    if not root_cause_to_incidents:
        return {
            "likely_root_cause": None,
            "supporting_incidents": [],
            "root_cause_counts": {},
            "total_incidents": len(incidents),
        }

    counts = Counter(
        {
            root_cause: len(incident_ids)
            for root_cause, incident_ids
            in root_cause_to_incidents.items()
        }
    )

    # Highest frequency first.
    # If tied, preserve deterministic alphabetical order.
    ranked = sorted(
        counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    likely_root_cause = ranked[0][0]

    return {
        "likely_root_cause": likely_root_cause,
        "supporting_incidents": (
            root_cause_to_incidents[
                likely_root_cause
            ]
        ),
        "root_cause_counts": dict(ranked),
        "total_incidents": len(incidents),
    }