from __future__ import annotations

from collections import Counter
from typing import Any


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _get_preventive_action(
    incident: dict[str, Any],
) -> str:
    """
    Read preventive action from either the incident itself
    or its metadata.

    Supports the project's dataset structure.
    """

    metadata = incident.get("metadata", {})

    if isinstance(metadata, dict):
        preventive_action = metadata.get(
            "preventive_action"
        )

        if preventive_action:
            return _normalize(
                preventive_action
            )

    preventive_action = incident.get(
        "preventive_action"
    )

    if preventive_action:
        return _normalize(
            preventive_action
        )

    return ""


def recommend_prevention(
    incidents: list[dict[str, Any]],
    top_k: int = 1,
) -> dict[str, Any]:
    """
    Recommend preventive actions based on relevant
    historical incidents.

    The most frequently occurring preventive action
    is treated as the strongest recommendation.

    Parameters
    ----------
    incidents:
        Relevant historical incidents, normally the
        final re-ranked Top-5 incidents.

    top_k:
        Number of preventive-action recommendations.

    Returns
    -------
    dict
        Recommended preventive action, supporting incidents,
        action counts, and ranked recommendations.
    """

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    if not incidents:
        return {
            "recommended_prevention": "",
            "supporting_incidents": [],
            "prevention_counts": {},
            "recommendations": [],
        }

    action_to_incidents: dict[
        str, list[str]
    ] = {}

    for incident in incidents:

        action = _get_preventive_action(
            incident
        )

        if not action:
            continue

        incident_id = _normalize(
            incident.get("incident_id")
        )

        action_to_incidents.setdefault(
            action,
            [],
        ).append(incident_id)

    if not action_to_incidents:
        return {
            "recommended_prevention": "",
            "supporting_incidents": [],
            "prevention_counts": {},
            "recommendations": [],
        }

    prevention_counts = Counter(
        {
            action: len(ids)
            for action, ids
            in action_to_incidents.items()
        }
    )

    ranked_actions = sorted(
        prevention_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    recommendations = []

    for action, count in ranked_actions[:top_k]:

        recommendations.append(
            {
                "preventive_action": action,
                "supporting_incidents":
                    action_to_incidents[action],
                "count": count,
            }
        )

    best_action = recommendations[0]

    return {
        "recommended_prevention":
            best_action["preventive_action"],
        "supporting_incidents":
            best_action["supporting_incidents"],
        "prevention_counts":
            dict(prevention_counts),
        "recommendations":
            recommendations,
    }