from __future__ import annotations

from typing import Any


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value).strip().lower().split()
    )


def _get_value(
    incident: dict[str, Any],
    key: str,
) -> Any:
    """
    Read a value from either the incident itself
    or its metadata dictionary.
    """

    metadata = incident.get("metadata", {})

    if isinstance(metadata, dict):
        if key in metadata:
            return metadata[key]

    return incident.get(key)


def extract_evidence(
    incidents: list[dict[str, Any]],
    root_cause: str | None = None,
) -> dict[str, Any]:
    """
    Extract supporting evidence from retrieved historical incidents.

    Parameters
    ----------
    incidents:
        Final retrieved/reranked historical incidents.

    root_cause:
        Root cause identified by the RCA analyzer.

    Returns
    -------
    dict
        Evidence supporting the root-cause prediction.
    """

    if not incidents:
        return {
            "root_cause": root_cause,
            "evidence": [],
            "evidence_count": 0,
        }

    normalized_root_cause = _normalize(root_cause)

    evidence = []

    for incident in incidents:
        incident_root_cause = _get_value(
            incident,
            "root_cause",
        )

        normalized_incident_root_cause = _normalize(
            incident_root_cause
        )

        # If a root cause was supplied, only incidents
        # supporting that root cause are evidence.
        if (
            normalized_root_cause
            and normalized_incident_root_cause
            != normalized_root_cause
        ):
            continue

        evidence_item = {
            "incident_id": incident.get(
                "incident_id",
                "UNKNOWN",
            ),
            "similarity": incident.get(
                "similarity",
                incident.get(
                    "semantic_score",
                    0.0,
                ),
            ),
            "final_score": incident.get(
                "final_score",
                0.0,
            ),
            "service": _get_value(
                incident,
                "service",
            )
            or _get_value(
                incident,
                "affected_service",
            ),
            "category": _get_value(
                incident,
                "category",
            ),
            "severity": _get_value(
                incident,
                "severity",
            ),
            "root_cause": incident_root_cause,
            "resolution": _get_value(
                incident,
                "resolution",
            ),
            "preventive_action": _get_value(
                incident,
                "preventive_action",
            ),
        }

        evidence.append(evidence_item)

    return {
        "root_cause": root_cause,
        "evidence": evidence,
        "evidence_count": len(evidence),
    }