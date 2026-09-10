from __future__ import annotations

import ast
import json
from datetime import datetime
from typing import Any


REQUIRED_COLUMNS = [
    "incident_id",
    "incident_description",
    "category",
    "severity",
    "priority",
    "affected_service",
    "environment",
    "root_cause",
    "resolution",
    "preventive_action",
    "timestamp",
    "status",
    "source_type",
    "dataset_features",
]


ALLOWED_SEVERITIES = {
    "Low",
    "Medium",
    "High",
    "Critical",
}


ALLOWED_ENVIRONMENTS = {
    "Production",
    "Staging",
    "UAT",
    "Development",
}


def parse_dataset_features(value: Any) -> dict[str, Any]:
    """
    Convert dataset_features into a Python dictionary.

    Supports:
    - JSON strings
    - Python dictionary strings
    - Existing dictionaries
    """

    if isinstance(value, dict):
        return value

    if value is None:
        return {}

    text = str(value).strip()

    if not text or text.lower() in {
        "nan",
        "none",
        "null",
    }:
        return {}

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError) as exc:
            raise ValueError(
                "dataset_features is not valid JSON or dictionary syntax."
            ) from exc

    if not isinstance(parsed, dict):
        raise ValueError(
            "dataset_features must contain a dictionary/object."
        )

    return parsed


def normalize_text(value: Any) -> str:
    """
    Normalize text by:
    - converting to string
    - removing leading/trailing whitespace
    - collapsing repeated whitespace
    """

    if value is None:
        return ""

    return " ".join(str(value).strip().split())


def normalize_timestamp(value: Any) -> str:
    """
    Convert timestamp to ISO-8601 format.

    Example:
        2026-01-01 10:20:30
    becomes:
        2026-01-01T10:20:30
    """

    if value is None:
        raise ValueError("Timestamp cannot be empty.")

    parsed = datetime.fromisoformat(str(value).strip())

    return parsed.isoformat(timespec="seconds")