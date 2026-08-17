import pandas as pd
import pytest

from backend.core.data_preprocessing.processor import (
    DatasetProcessor,
)


def sample_dataframe():

    return pd.DataFrame(
        [
            {
                "incident_id": "RCA-00001",

                "incident_description":
                    "  Payment   API failed. ",

                "category":
                    "API / Microservices",

                "severity":
                    "High",

                "priority":
                    "P2",

                "affected_service":
                    "Payment API",

                "environment":
                    "Production",

                "root_cause":
                    "database connection exhaustion",

                "resolution":
                    "Restart service.",

                "preventive_action":
                    "Add monitoring.",

                "timestamp":
                    "2026-01-01 10:20:30",

                "status":
                    "Closed",

                "source_type":
                    "Log",

                "dataset_features":
                    '{"error_rate_percent": 10.2, "issue_type": "payment failure"}',
            }
        ]
    )


def test_text_and_timestamp_normalization():

    processor = DatasetProcessor(
        "unused.csv",
        "unused",
    )

    result = processor.normalize(
        sample_dataframe()
    )

    assert (
        result.loc[
            0,
            "incident_description",
        ]
        == "Payment API failed."
    )

    assert (
        result.loc[
            0,
            "timestamp",
        ]
        == "2026-01-01T10:20:30"
    )


def test_dataset_features_is_normalized_to_json():

    processor = DatasetProcessor(
        "unused.csv",
        "unused",
    )

    result = processor.normalize(
        sample_dataframe()
    )

    features = result.loc[
        0,
        "dataset_features",
    ]

    assert (
        '"error_rate_percent":10.2'
        in features
    )


def test_duplicate_incident_ids_are_rejected():

    processor = DatasetProcessor(
        "unused.csv",
        "unused",
    )

    df = pd.concat(
        [
            sample_dataframe(),
            sample_dataframe(),
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match="incident_id",
    ):
        processor.validate(df)


def test_invalid_severity_is_rejected():

    processor = DatasetProcessor(
        "unused.csv",
        "unused",
    )

    df = sample_dataframe()

    df.loc[
        0,
        "severity",
    ] = "Urgent"

    with pytest.raises(
        ValueError,
        match="severity",
    ):
        processor.validate(df)