from __future__ import annotations

from typing import Any

from backend.core.pipeline.incident_pipeline import run_incident_pipeline


def run_multiple_incident_pipeline(
    incidents: list[str],
) -> list[dict[str, Any]]:
    """
    Process multiple new incidents independently.

    Each incident gets its own:
        Keyword Retrieval
        Semantic Retrieval
        Metadata Reranking
        RCA
        Evidence
        Confidence
        Resolution
        Prevention
        Recurrence

    Parameters
    ----------
    incidents:
        List of new incident descriptions.

    Returns
    -------
    list[dict[str, Any]]
        Complete analysis result for every incident.
    """

    if not isinstance(incidents, list):
        raise TypeError("incidents must be a list of strings")

    results: list[dict[str, Any]] = []

    for index, incident in enumerate(incidents, start=1):

        if not isinstance(incident, str):
            raise TypeError(
                f"Incident {index} must be a string."
            )

        incident = incident.strip()

        if not incident:
            continue

        try:
            result = run_incident_pipeline(incident)

            result["incident_number"] = index

            results.append(result)

        except Exception as exc:
            results.append(
                {
                    "incident_number": index,
                    "input_incident": incident,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return results