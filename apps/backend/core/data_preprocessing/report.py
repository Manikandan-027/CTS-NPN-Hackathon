from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def build_report(
    df: pd.DataFrame,
) -> dict:

    """
    Generate a complete dataset summary.
    """

    report = {
        "rows": int(len(df)),

        "columns": int(
            len(df.columns)
        ),

        "column_names": (
            df.columns.tolist()
        ),

        "unique_incident_ids": int(
            df["incident_id"].nunique()
        ),

        "missing_values_total": int(
            df.isna().sum().sum()
        ),

        "unique_descriptions": int(
            df["incident_description"].nunique()
        ),

        "category_counts": (
            df["category"]
            .value_counts()
            .sort_index()
            .to_dict()
        ),

        "severity_counts": (
            df["severity"]
            .value_counts()
            .sort_index()
            .to_dict()
        ),

        "environment_counts": (
            df["environment"]
            .value_counts()
            .sort_index()
            .to_dict()
        ),

        "service_count": int(
            df["affected_service"].nunique()
        ),

        "root_cause_count": int(
            df["root_cause"].nunique()
        ),

        "resolution_count": int(
            df["resolution"].nunique()
        ),

        "preventive_action_count": int(
            df["preventive_action"].nunique()
        ),

        "status_counts": (
            df["status"]
            .value_counts()
            .sort_index()
            .to_dict()
        ),

        "source_type_counts": (
            df["source_type"]
            .value_counts()
            .sort_index()
            .to_dict()
        ),

        "timestamp_min": str(
            df["timestamp"].min()
        ),

        "timestamp_max": str(
            df["timestamp"].max()
        ),
    }

    return report


def save_report(
    report: dict,
    path: str | Path,
) -> Path:

    """
    Save dataset report as JSON.
    """

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return path