from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.core.data_preprocessing.schema import (
    ALLOWED_ENVIRONMENTS,
    ALLOWED_SEVERITIES,
    REQUIRED_COLUMNS,
    normalize_text,
    normalize_timestamp,
    parse_dataset_features,
)


TEXT_COLUMNS = [
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
    "status",
    "source_type",
]


class DatasetProcessor:
    """
    Validate, normalize, and save the IT incident dataset.

    Important:
    root_cause, resolution, and preventive_action are preserved as
    historical knowledge for later RCA/retrieval stages.

    They must NOT be included in the embedding text used for a new incident.
    """

    def __init__(
        self,
        input_path: str | Path,
        output_dir: str | Path,
    ) -> None:

        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)

    # ---------------------------------------------------------
    # LOAD
    # ---------------------------------------------------------

    def load(self) -> pd.DataFrame:
        """
        Load the CSV dataset and verify that the required columns exist.
        """

        if not self.input_path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {self.input_path}"
            )

        df = pd.read_csv(self.input_path)

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                "Dataset is missing required columns: "
                f"{missing_columns}"
            )

        # Keep the agreed canonical column order.
        df = df[REQUIRED_COLUMNS].copy()

        return df

    # ---------------------------------------------------------
    # VALIDATE
    # ---------------------------------------------------------

    def validate(self, df: pd.DataFrame) -> None:
        """
        Validate dataset integrity.
        """

        errors: list[str] = []

        # Empty dataset
        if df.empty:
            errors.append("Dataset is empty.")

        # -----------------------------------------------------
        # Required columns
        # -----------------------------------------------------

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            errors.append(
                f"Missing columns: {missing_columns}"
            )

        if errors:
            raise ValueError(
                "Dataset validation failed:\n- "
                + "\n- ".join(errors)
            )

        # -----------------------------------------------------
        # Incident IDs
        # -----------------------------------------------------

        if df["incident_id"].isna().any():
            errors.append(
                "incident_id contains missing values."
            )

        if not df["incident_id"].is_unique:
            errors.append(
                "incident_id values must be unique."
            )

        # -----------------------------------------------------
        # Missing values
        # -----------------------------------------------------

        for column in REQUIRED_COLUMNS:

            missing_count = int(
                df[column].isna().sum()
            )

            if missing_count > 0:
                errors.append(
                    f"{column}: "
                    f"{missing_count} missing values."
                )

        # -----------------------------------------------------
        # Text fields
        # -----------------------------------------------------

        for column in TEXT_COLUMNS:

            if column not in df.columns:
                continue

            non_string_mask = ~df[column].map(
                lambda value: isinstance(value, str)
            )

            if non_string_mask.any():
                errors.append(
                    f"{column}: contains non-string values."
                )

        # -----------------------------------------------------
        # Severity
        # -----------------------------------------------------

        if "severity" in df.columns:

            invalid_severity = sorted(
                set(df["severity"])
                - ALLOWED_SEVERITIES
            )

            if invalid_severity:
                errors.append(
                    "Invalid severity values: "
                    f"{invalid_severity}"
                )

        # -----------------------------------------------------
        # Environment
        # -----------------------------------------------------

        if "environment" in df.columns:

            invalid_environment = sorted(
                set(df["environment"])
                - ALLOWED_ENVIRONMENTS
            )

            if invalid_environment:
                errors.append(
                    "Invalid environment values: "
                    f"{invalid_environment}"
                )

        # -----------------------------------------------------
        # Timestamp
        # -----------------------------------------------------

        try:
            pd.to_datetime(
                df["timestamp"],
                errors="raise",
            )
        except Exception as exc:

            errors.append(
                f"Invalid timestamp value: {exc}"
            )

        # -----------------------------------------------------
        # dataset_features
        # -----------------------------------------------------

        for index, value in df[
            "dataset_features"
        ].items():

            try:
                parse_dataset_features(value)

            except Exception as exc:

                errors.append(
                    f"dataset_features row {index} "
                    f"could not be parsed: {exc}"
                )

                # Prevent an enormous error message.
                if len(errors) >= 20:
                    break

        # -----------------------------------------------------
        # Raise validation errors
        # -----------------------------------------------------

        if errors:

            raise ValueError(
                "Dataset validation failed:\n- "
                + "\n- ".join(errors)
            )

    # ---------------------------------------------------------
    # NORMALIZE
    # ---------------------------------------------------------

    def normalize(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        """
        Normalize text, timestamps, and dataset_features.
        """

        result = df.copy()

        # -----------------------------------------------------
        # Text normalization
        # -----------------------------------------------------

        for column in TEXT_COLUMNS:

            result[column] = result[column].map(
                normalize_text
            )

        # -----------------------------------------------------
        # Timestamp normalization
        # -----------------------------------------------------

        result["timestamp"] = result[
            "timestamp"
        ].map(normalize_timestamp)

        # -----------------------------------------------------
        # dataset_features normalization
        # -----------------------------------------------------

        result["dataset_features"] = result[
            "dataset_features"
        ].map(
            lambda value: json.dumps(
                parse_dataset_features(value),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )

        return result

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    def save(
        self,
        df: pd.DataFrame,
    ) -> tuple[Path, Path]:

        """
        Save processed data in CSV and JSONL formats.
        """

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        csv_path = (
            self.output_dir
            / "processed_incidents.csv"
        )

        jsonl_path = (
            self.output_dir
            / "processed_incidents.jsonl"
        )

        # CSV
        df.to_csv(
            csv_path,
            index=False,
        )

        # JSONL
        with jsonl_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            for record in df.to_dict(
                orient="records"
            ):

                file.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        return csv_path, jsonl_path

    # ---------------------------------------------------------
    # COMPLETE PIPELINE
    # ---------------------------------------------------------

    def run(
        self,
    ) -> tuple[pd.DataFrame, Path, Path]:

        """
        Complete preprocessing pipeline:

        Load
        ↓
        Validate
        ↓
        Normalize
        ↓
        Validate again
        ↓
        Save
        """

        # 1. Load
        df = self.load()

        # 2. Validate raw data
        self.validate(df)

        # 3. Normalize
        df = self.normalize(df)

        # 4. Validate processed data
        self.validate(df)

        # 5. Save
        csv_path, jsonl_path = self.save(df)

        return df, csv_path, jsonl_path