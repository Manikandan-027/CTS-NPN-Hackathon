from __future__ import annotations

from collections import Counter
from typing import Any


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _get_resolution(incident: dict[str, Any]) -> str:
    """
    Read resolution from either the incident itself or its metadata.
    Supports the project's dataset structure.
    """

    metadata = incident.get("metadata", {})

    if isinstance(metadata, dict):
        resolution = metadata.get("resolution")
        if resolution:
            return _normalize(resolution)

    resolution = incident.get("resolution")

    if resolution:
        return _normalize(resolution)

    return ""


def recommend_resolution(
    incidents: list[dict[str, Any]],
    top_k: int = 1,
) -> dict[str, Any]:
    """
    Recommend a resolution based on the resolutions of the
    most relevant historical incidents.

    The most frequently occurring resolution among the supplied
    historical incidents is selected.

    Parameters
    ----------
    incidents:
        Relevant historical incidents, normally the final
        re-ranked Top-5 incidents.

    top_k:
        Number of resolution recommendations to return.

    Returns
    -------
    dict
        Contains:
            recommended_resolution
            supporting_incidents
            resolution_counts
            recommendations
    """

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")

    if not incidents:
        return {
            "recommended_resolution": "",
            "supporting_incidents": [],
            "resolution_counts": {},
            "recommendations": [],
        }

    resolution_to_incidents: dict[str, list[str]] = {}

    for incident in incidents:
        resolution = _get_resolution(incident)

        if not resolution:
            continue

        incident_id = _normalize(
            incident.get("incident_id")
        )

        resolution_to_incidents.setdefault(
            resolution,
            [],
        ).append(incident_id)

    if not resolution_to_incidents:
        return {
            "recommended_resolution": "",
            "supporting_incidents": [],
            "resolution_counts": {},
            "recommendations": [],
        }

    resolution_counts = Counter(
        {
            resolution: len(ids)
            for resolution, ids
            in resolution_to_incidents.items()
        }
    )

    ranked_resolutions = sorted(
        resolution_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    recommendations = []

    for resolution, count in ranked_resolutions[:top_k]:
        recommendations.append(
            {
                "resolution": resolution,
                "supporting_incidents": (
                    resolution_to_incidents[resolution]
                ),
                "count": count,
            }
        )

    best_resolution = recommendations[0]

    return {
        "recommended_resolution": best_resolution["resolution"],
        "supporting_incidents": best_resolution[
            "supporting_incidents"
        ],
        "resolution_counts": dict(
            resolution_counts
        ),
        "recommendations": recommendations,
    }
