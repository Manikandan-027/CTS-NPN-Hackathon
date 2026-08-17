from backend.core.confidence.confidence_score import (
    calculate_confidence,
)


def test_calculates_high_confidence():
    incidents = [
        {
            "incident_id": "RCA-001",
            "final_score": 0.90,
        },
        {
            "incident_id": "RCA-002",
            "final_score": 0.85,
        },
        {
            "incident_id": "RCA-003",
            "final_score": 0.80,
        },
    ]

    root_cause_counts = {
        "database failure": 3,
    }

    result = calculate_confidence(
        incidents,
        root_cause_counts,
    )

    assert 0.0 <= result["confidence_score"] <= 1.0
    assert result["confidence_level"] == "High"
    assert result["supporting_incidents"] == 3
    assert result["root_cause_agreement"] == 1.0


def test_calculates_lower_confidence_when_root_causes_disagree():
    incidents = [
        {
            "incident_id": "RCA-001",
            "final_score": 0.70,
        },
        {
            "incident_id": "RCA-002",
            "final_score": 0.65,
        },
        {
            "incident_id": "RCA-003",
            "final_score": 0.60,
        },
    ]

    root_cause_counts = {
        "database failure": 1,
        "api timeout": 1,
        "network failure": 1,
    }

    result = calculate_confidence(
        incidents,
        root_cause_counts,
    )

    assert result["root_cause_agreement"] == 0.3333
    assert result["confidence_score"] < 0.80


def test_empty_incidents_returns_zero_confidence():
    result = calculate_confidence(
        [],
        {},
    )

    assert result["confidence_score"] == 0.0
    assert result["confidence_percentage"] == 0.0
    assert result["confidence_level"] == "Low"
    assert result["supporting_incidents"] == 0