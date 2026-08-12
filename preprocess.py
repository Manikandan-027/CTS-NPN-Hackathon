#!/usr/bin/env python3
"""
Complete preprocessing pipeline for the AI Incident RCA & Resolution Intelligence System.

Input:
    complete_it_rca_dataset_8000_balanced.csv

Outputs:
    data/processed/incidents_processed.csv
    data/processed/preprocessing_report.json
    data/processed/feature_schema.json

The pipeline creates three representations for every incident:
1. Embedding text       -> Sentence Transformer / semantic retrieval
2. Metadata             -> ChromaDB / hybrid retrieval
3. RCA evidence fields  -> RCA, evidence, confidence and recurrence engines

Dependencies:
    pandas
    numpy

Run:
    python preprocess.py \
        --input data/raw/complete_it_rca_dataset_8000_balanced.csv \
        --output data/processed/incidents_processed.csv
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

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

# Categories from the project's RCA feature definition.
RCA_CATEGORIES = {
    "Application / Software",
    "API / Microservices",
    "Database",
    "Data / Data Pipeline",
    "Network",
    "Infrastructure",
    "Deployment / Change Management",
    "Security",
    "External Dependencies",
    "Business Process / Configuration",
    "Human / Operational",
    "Monitoring / Observability",
    "Capacity / Performance Management",
    "Business Continuity / Disaster Recovery",
    "Testing / Quality",
}

# This category describes user/customer symptoms, not necessarily an RCA.
SYMPTOM_CATEGORY = "User / Customer Incident"

STANDARD_SEVERITIES = {"Low", "Medium", "High", "Critical"}
STANDARD_STATUSES = {"Closed", "Resolved", "Investigating"}

# Fields that are useful as metadata for ChromaDB.
METADATA_COLUMNS = [
    "incident_id",
    "category",
    "severity",
    "priority",
    "affected_service",
    "environment",
    "status",
    "source_type",
    "issue_type",
]

# Numeric fields commonly useful for RCA evidence. The pipeline also discovers
# additional numeric fields dynamically from dataset_features.
KNOWN_NUMERIC_FEATURES = [
    "observed_cpu_percent",
    "observed_memory_percent",
    "request_latency_ms",
    "error_rate_percent",
    "affected_records_or_requests",
    "incident_duration_minutes",
    "retry_count",
    "records_processed",
    "records_affected",
    "pipeline_delay_minutes",
    "validation_failure_rate_percent",
    "queue_depth",
    "packet_loss_percent",
    "network_latency_ms",
    "bandwidth_utilization_percent",
    "dns_response_ms",
    "db_connections",
    "db_cpu_percent",
    "db_memory_percent",
    "query_latency_ms",
    "lock_waits",
    "replication_lag_seconds",
    "disk_utilization_percent",
    "pod_restart_count",
    "resource_utilization_percent",
    "alert_delay_seconds",
    "missing_signal_percent",
    "tests_executed",
    "tests_failed",
    "coverage_percent",
    "minutes_after_change",
    "error_rate_before_change_percent",
    "error_rate_after_change_percent",
]

# Values which should be interpreted as numeric if present.
NUMERIC_NAME_HINTS = (
    "_percent",
    "_ms",
    "_seconds",
    "_minutes",
    "_count",
    "_depth",
    "_utilization",
    "_latency",
    "_connections",
    "_waits",
    "_growth",
    "_requests",
    "_records",
    "_processed",
    "_failed",
    "_executed",
    "_coverage",
    "_retries",
)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def clean_text(value: Any) -> str:
    """Normalize whitespace and harmless formatting without changing meaning."""
    if pd.isna(value):
        return ""

    text = str(value)
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text).strip()

    # Normalize repeated punctuation but preserve useful punctuation.
    text = re.sub(r"([!?.,])\1{2,}", r"\1", text)

    return text


def normalize_label(value: Any) -> str:
    """Normalize categorical labels conservatively."""
    text = clean_text(value)
    if not text:
        return ""

    # Normalize separators.
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s*-\s*", "-", text)

    # Case-insensitive matching against known canonical values.
    lookup = {x.casefold(): x for x in RCA_CATEGORIES | {SYMPTOM_CATEGORY}}
    lookup.update({x.casefold(): x for x in STANDARD_SEVERITIES})
    lookup.update({x.casefold(): x for x in STANDARD_STATUSES})

    return lookup.get(text.casefold(), text)


def normalize_free_text(value: Any) -> str:
    """
    Conservative normalization for root cause/resolution/preventive action.
    Does NOT paraphrase or semantically rewrite the source.
    """
    text = clean_text(value)
    text = re.sub(r"\s*([,:;])\s*", r"\1 ", text)
    return text.strip()


def safe_json_loads(value: Any) -> Dict[str, Any]:
    """Parse dataset_features safely."""
    if isinstance(value, dict):
        return value

    if pd.isna(value):
        return {}

    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def json_safe(value: Any) -> Any:
    """Convert numpy/pandas values into JSON-safe Python values."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    return value


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_schema(df: pd.DataFrame) -> None:
    """Fail fast if the dataset schema is incompatible."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if df.empty:
        raise ValueError("Input dataset is empty.")

    if df["incident_id"].isna().any():
        raise ValueError("incident_id contains missing values.")

    duplicate_ids = int(df["incident_id"].duplicated().sum())
    if duplicate_ids:
        raise ValueError(f"Found {duplicate_ids} duplicate incident_id values.")


def quality_check(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a non-destructive data quality report."""
    report: Dict[str, Any] = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "missing_values_by_column": {
            str(k): int(v) for k, v in df.isna().sum().items()
        },
        "exact_duplicate_rows": int(df.duplicated().sum()),
        "duplicate_incident_ids": int(df["incident_id"].duplicated().sum()),
        "unique_categories": int(df["category"].nunique(dropna=True)),
        "category_counts": {
            str(k): int(v)
            for k, v in df["category"].value_counts(dropna=False).items()
        },
    }
    return report


# ---------------------------------------------------------------------------
# dataset_features parsing
# ---------------------------------------------------------------------------

def parse_dataset_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Parse the JSON field and flatten it into individual columns.

    Original dataset_features is retained.
    Flattened fields are prefixed with 'feature_' to avoid collisions.
    """
    parsed = df["dataset_features"].apply(safe_json_loads)

    invalid_count = int((parsed.map(len) == 0).sum())

    flattened = pd.json_normalize(parsed.tolist())
    if not flattened.empty:
        flattened.columns = [
            f"feature_{str(c).strip()}" for c in flattened.columns
        ]

        # Convert obvious numeric fields to numeric values.
        for col in flattened.columns:
            raw_name = col.replace("feature_", "", 1)
            if (
                raw_name in KNOWN_NUMERIC_FEATURES
                or raw_name.endswith(NUMERIC_NAME_HINTS)
            ):
                flattened[col] = pd.to_numeric(
                    flattened[col], errors="coerce"
                )

        flattened.index = df.index
        df = pd.concat([df, flattened], axis=1)

    feature_keys = sorted(
        {
            str(key)
            for obj in parsed
            for key in obj.keys()
        }
    )

    report = {
        "records_with_empty_or_invalid_dataset_features": invalid_count,
        "unique_feature_keys": len(feature_keys),
        "feature_keys": feature_keys,
    }

    return df, report


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------

def create_text_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create cleaned fields and an embedding-focused representation."""
    text_columns = [
        "incident_description",
        "root_cause",
        "resolution",
        "preventive_action",
    ]

    for col in text_columns:
        df[f"{col}_clean"] = df[col].apply(clean_text)

    df["root_cause_normalized"] = df["root_cause"].apply(normalize_free_text)
    df["resolution_normalized"] = df["resolution"].apply(normalize_free_text)
    df["preventive_action_normalized"] = df[
        "preventive_action"
    ].apply(normalize_free_text)

    # Issue type comes from dataset_features when available.
    if "feature_issue_type" in df.columns:
        df["issue_type"] = df["feature_issue_type"].apply(clean_text)
    else:
        df["issue_type"] = ""

    # The embedding text intentionally emphasizes incident semantics and
    # operational context. Do not include the historical root cause, because
    # that would leak the answer into a retrieval query representation.
    def build_embedding_text(row: pd.Series) -> str:
        parts = []

        if row.get("issue_type"):
            parts.append(f"Issue Type: {row['issue_type']}")

        if row.get("incident_description_clean"):
            parts.append(
                f"Incident: {row['incident_description_clean']}"
            )

        if row.get("category"):
            parts.append(f"Category: {row['category']}")

        if row.get("affected_service"):
            parts.append(
                f"Affected Service: {row['affected_service']}"
            )

        if row.get("environment"):
            parts.append(f"Environment: {row['environment']}")

        return "\n".join(parts)

    df["embedding_text"] = df.apply(build_embedding_text, axis=1)

    return df


# ---------------------------------------------------------------------------
# Symptom / RCA separation
# ---------------------------------------------------------------------------

def create_symptom_rca_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preserve the distinction used by the project:
    User / Customer Incident describes symptoms and is not automatically an RCA.
    """
    df["is_symptom_category"] = (
        df["category"].astype(str).str.casefold()
        == SYMPTOM_CATEGORY.casefold()
    )

    df["rca_category_valid"] = df["category"].isin(RCA_CATEGORIES)

    return df


# ---------------------------------------------------------------------------
# Metadata processing
# ---------------------------------------------------------------------------

def standardize_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize categorical metadata without inventing values."""
    for col in [
        "category",
        "severity",
        "priority",
        "affected_service",
        "environment",
        "status",
        "source_type",
    ]:
        df[col] = df[col].apply(normalize_label)

    # Priority is intentionally not restricted to a fixed P1/P2/P3/P4 set
    # because the dataset may contain additional legitimate priority labels.
    return df


# ---------------------------------------------------------------------------
# Timestamp processing
# ---------------------------------------------------------------------------

def process_timestamps(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Parse timestamps and derive recurrence-friendly time features."""
    parsed = pd.to_datetime(df["timestamp"], errors="coerce")

    invalid_count = int(parsed.isna().sum())

    df["timestamp_parsed"] = parsed

    df["incident_date"] = parsed.dt.date.astype("string")
    df["incident_year"] = parsed.dt.year.astype("Int64")
    df["incident_month"] = parsed.dt.month.astype("Int64")
    df["incident_week"] = parsed.dt.isocalendar().week.astype("Int64")
    df["incident_day_of_week"] = parsed.dt.dayofweek.astype("Int64")
    df["incident_hour"] = parsed.dt.hour.astype("Int64")

    report = {
        "invalid_timestamps": invalid_count,
        "min_timestamp": (
            parsed.min().isoformat() if parsed.notna().any() else None
        ),
        "max_timestamp": (
            parsed.max().isoformat() if parsed.notna().any() else None
        ),
    }

    return df, report


# ---------------------------------------------------------------------------
# Numerical and temporal RCA features
# ---------------------------------------------------------------------------

def numeric_feature_columns(df: pd.DataFrame) -> List[str]:
    """Find flattened feature columns that are numeric."""
    result = []

    for col in df.columns:
        if not col.startswith("feature_"):
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            result.append(col)

    return sorted(result)


def validate_numeric_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Convert known numeric RCA fields to numeric and report suspicious ranges.
    Values are not silently clipped.
    """
    report: Dict[str, Any] = {
        "numeric_feature_count": 0,
        "range_checks": {},
    }

    for col in df.columns:
        if not col.startswith("feature_"):
            continue

        raw_name = col.replace("feature_", "", 1)

        if (
            raw_name in KNOWN_NUMERIC_FEATURES
            or raw_name.endswith(NUMERIC_NAME_HINTS)
        ):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    numeric_cols = numeric_feature_columns(df)
    report["numeric_feature_count"] = len(numeric_cols)

    # Conservative range checks for percentage-style fields.
    for col in numeric_cols:
        raw_name = col.replace("feature_", "", 1)

        if raw_name.endswith("_percent"):
            values = df[col].dropna()
            invalid = int(((values < 0) | (values > 100)).sum())

            report["range_checks"][raw_name] = {
                "expected_range": [0, 100],
                "invalid_count": invalid,
            }

    return df, report


def create_temporal_rca_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive deployment/change-related RCA evidence where the source dataset
    contains the required fields.

    No new causal labels are invented.
    """
    required = [
        "feature_change_event",
        "feature_minutes_after_change",
    ]

    if all(c in df.columns for c in required):
        change_event = (
            df["feature_change_event"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        minutes = pd.to_numeric(
            df["feature_minutes_after_change"],
            errors="coerce",
        )

        df["change_event_present"] = change_event.ne("")
        df["post_change_incident"] = (
            df["change_event_present"]
            & minutes.notna()
            & (minutes >= 0)
        )

        df["minutes_after_change_numeric"] = minutes

    if {
        "feature_error_rate_before_change_percent",
        "feature_error_rate_after_change_percent",
    }.issubset(df.columns):
        before = pd.to_numeric(
            df["feature_error_rate_before_change_percent"],
            errors="coerce",
        )
        after = pd.to_numeric(
            df["feature_error_rate_after_change_percent"],
            errors="coerce",
        )

        df["error_rate_change_after_change"] = after - before

    return df


# ---------------------------------------------------------------------------
# RCA evidence representation
# ---------------------------------------------------------------------------

def create_rca_evidence_text(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a compact human-readable evidence representation from selected
    structured fields. This is NOT used as the primary embedding text.
    """
    evidence_columns = [
        "feature_observed_cpu_percent",
        "feature_observed_memory_percent",
        "feature_request_latency_ms",
        "feature_error_rate_percent",
        "feature_db_connections",
        "feature_db_cpu_percent",
        "feature_query_latency_ms",
        "feature_lock_waits",
        "feature_replication_lag_seconds",
        "feature_packet_loss_percent",
        "feature_network_latency_ms",
        "feature_queue_depth",
        "feature_disk_utilization_percent",
        "feature_pod_restart_count",
        "feature_alert_delay_seconds",
        "feature_missing_signal_percent",
        "feature_minutes_after_change",
        "feature_error_rate_before_change_percent",
        "feature_error_rate_after_change_percent",
    ]

    available = [c for c in evidence_columns if c in df.columns]

    def build_evidence(row: pd.Series) -> str:
        parts = []

        for col in available:
            value = row.get(col)

            if pd.isna(value):
                continue

            name = col.replace("feature_", "", 1).replace("_", " ")
            parts.append(f"{name}: {value}")

        if row.get("change_event_present", False):
            event = row.get("feature_change_event", "")
            if event:
                parts.append(f"change event: {event}")

        return "; ".join(parts)

    df["rca_evidence_features"] = df.apply(build_evidence, axis=1)

    return df


# ---------------------------------------------------------------------------
# Metadata JSON for ChromaDB
# ---------------------------------------------------------------------------

def create_metadata_json(df: pd.DataFrame) -> pd.DataFrame:
    """Create one JSON object per incident for ChromaDB ingestion."""
    def build_metadata(row: pd.Series) -> str:
        data = {}

        for col in METADATA_COLUMNS:
            if col not in row.index:
                continue

            value = row[col]

            if pd.isna(value):
                continue

            data[col] = str(value)

        data["is_symptom_category"] = bool(
            row.get("is_symptom_category", False)
        )

        return json.dumps(data, ensure_ascii=False)

    df["chroma_metadata"] = df.apply(build_metadata, axis=1)
    return df


# ---------------------------------------------------------------------------
# Final validation
# ---------------------------------------------------------------------------

def final_validation(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate outputs after all transformations."""
    required_output = [
        "incident_id",
        "embedding_text",
        "category",
        "severity",
        "priority",
        "affected_service",
        "environment",
        "root_cause_normalized",
        "resolution_normalized",
        "preventive_action_normalized",
        "timestamp_parsed",
        "chroma_metadata",
        "rca_evidence_features",
    ]

    missing = [c for c in required_output if c not in df.columns]

    empty_embedding = int(
        df["embedding_text"].fillna("").astype(str).str.strip().eq("").sum()
    )

    report = {
        "output_rows": int(len(df)),
        "missing_required_output_columns": missing,
        "empty_embedding_text": empty_embedding,
        "unique_incident_ids": int(df["incident_id"].nunique()),
        "unique_categories": int(df["category"].nunique()),
        "category_counts": {
            str(k): int(v)
            for k, v in df["category"].value_counts().items()
        },
        "valid": not missing and empty_embedding == 0,
    }

    if not report["valid"]:
        raise ValueError(f"Final validation failed: {report}")

    return report


# ---------------------------------------------------------------------------
# Main preprocessing pipeline
# ---------------------------------------------------------------------------

def preprocess_dataset(
    input_path: str | Path,
    output_path: str | Path,
    report_path: str | Path | None = None,
    schema_path: str | Path | None = None,
) -> pd.DataFrame:
    """Run the complete preprocessing pipeline."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Dataset not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if report_path is None:
        report_path = output_path.parent / "preprocessing_report.json"

    if schema_path is None:
        schema_path = output_path.parent / "feature_schema.json"

    # 1. Load
    df = pd.read_csv(input_path)

    # 2. Schema validation
    validate_schema(df)

    # 3. Initial quality report
    initial_quality = quality_check(df)

    # 4. Parse structured JSON features
    df, feature_report = parse_dataset_features(df)

    # 5. Standardize metadata
    df = standardize_metadata(df)

    # 6. Clean text and create embedding representation
    df = create_text_features(df)

    # 7. Separate symptoms from RCA categories
    df = create_symptom_rca_flags(df)

    # 8. Process timestamps
    df, timestamp_report = process_timestamps(df)

    # 9. Validate numeric RCA signals
    df, numeric_report = validate_numeric_features(df)

    # 10. Create temporal RCA features
    df = create_temporal_rca_features(df)

    # 11. Create structured RCA evidence representation
    df = create_rca_evidence_text(df)

    # 12. Create ChromaDB metadata JSON
    df = create_metadata_json(df)

    # 13. Final validation
    final_report = final_validation(df)

    # 14. Build feature schema report
    feature_columns = [
        c for c in df.columns
        if c.startswith("feature_")
    ]

    feature_schema = {
        "flattened_dataset_features": [
            c.replace("feature_", "", 1)
            for c in feature_columns
        ],
        "embedding_field": "embedding_text",
        "chroma_metadata_field": "chroma_metadata",
        "rca_evidence_field": "rca_evidence_features",
        "metadata_columns": METADATA_COLUMNS,
        "symptom_category": SYMPTOM_CATEGORY,
        "rca_categories": sorted(RCA_CATEGORIES),
        "numeric_feature_columns": [
            c.replace("feature_", "", 1)
            for c in numeric_feature_columns(df)
        ],
    }

    # 15. Save CSV
    # Keep the original dataset_features JSON string for traceability.
    df.to_csv(output_path, index=False)

    # 16. Save reports
    full_report = {
        "input_file": str(input_path),
        "output_file": str(output_path),
        "initial_quality": initial_quality,
        "dataset_features": feature_report,
        "timestamps": timestamp_report,
        "numeric_features": numeric_report,
        "final_validation": final_report,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(json_safe(full_report), f, indent=2, ensure_ascii=False)

    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(json_safe(feature_schema), f, indent=2, ensure_ascii=False)

    print("=" * 70)
    print("RCA DATA PREPROCESSING COMPLETED")
    print("=" * 70)
    print(f"Input : {input_path}")
    print(f"Output: {output_path}")
    print(f"Rows  : {len(df)}")
    print(f"Cols  : {len(df.columns)}")
    print(f"Report: {report_path}")
    print(f"Schema: {schema_path}")
    print("=" * 70)

    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess the IT RCA dataset for semantic retrieval, "
                    "ChromaDB metadata, and RCA evidence analysis."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to raw CSV dataset.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path for processed CSV.",
    )

    parser.add_argument(
        "--report",
        default=None,
        help="Optional preprocessing report JSON path.",
    )

    parser.add_argument(
        "--schema",
        default=None,
        help="Optional feature schema JSON path.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    preprocess_dataset(
        input_path=args.input,
        output_path=args.output,
        report_path=args.report,
        schema_path=args.schema,
    )


if __name__ == "__main__":
    main()
