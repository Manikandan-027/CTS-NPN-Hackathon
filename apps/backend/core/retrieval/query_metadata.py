from __future__ import annotations

import re
from typing import Any


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def extract_query_metadata(
    query: str,
    incidents: list[dict[str, Any]],
) -> dict[str, str]:
    """
    Extract metadata explicitly mentioned in the
    user's incident description.

    IMPORTANT:
    We never copy metadata from a retrieved incident.

    Metadata is detected from the user's actual query.
    """

    query_normalized = _normalize(query)

    result = {
        "service": "",
        "category": "",
        "severity": "",
    }

    if not query_normalized:
        return result

    services: set[str] = set()
    categories: set[str] = set()
    severities: set[str] = set()

    for incident in incidents:

        service = incident.get(
            "affected_service",
            incident.get("service", ""),
        )

        category = incident.get(
            "category",
            "",
        )

        severity = incident.get(
            "severity",
            "",
        )

        if service:
            services.add(
                str(service).strip()
            )

        if category:
            categories.add(
                str(category).strip()
            )

        if severity:
            severities.add(
                str(severity).strip()
            )

    # --------------------------------------------------
    # Find service explicitly mentioned in query
    # --------------------------------------------------

    service_matches = []

    for service in services:

        normalized_service = _normalize(
            service
        )

        if (
            normalized_service
            and normalized_service
            in query_normalized
        ):
            service_matches.append(service)

    if service_matches:

        result["service"] = max(
            service_matches,
            key=len,
        )

    # --------------------------------------------------
    # Find category explicitly mentioned
    # --------------------------------------------------

    category_matches = []

    for category in categories:

        normalized_category = _normalize(
            category
        )

        if (
            normalized_category
            and normalized_category
            in query_normalized
        ):
            category_matches.append(category)

    if category_matches:

        result["category"] = max(
            category_matches,
            key=len,
        )

    # --------------------------------------------------
    # Find severity explicitly mentioned
    # --------------------------------------------------

    severity_matches = []

    for severity in severities:

        normalized_severity = _normalize(
            severity
        )

        if (
            normalized_severity
            and re.search(
                rf"\b{re.escape(normalized_severity)}\b",
                query_normalized,
            )
        ):
            severity_matches.append(severity)

    if severity_matches:

        result["severity"] = max(
            severity_matches,
            key=len,
        )

    return result