from backend.core.evidence.evidence_extractor import (
    extract_evidence,
)


def test_extracts_matching_root_cause_evidence():
    incidents = [
        {
            "incident_id": "RCA-001",
            "similarity": 0.91,
            "final_score": 0.94,
            "metadata": {
                "service": "Payment API",
                "category": "API / Microservices",
                "severity": "High",
                "root_cause": "Payment gateway unavailable",
                "resolution": "Restarted payment gateway",
                "preventive_action": "Add gateway health checks",
            },
        },
        {
            "incident_id": "RCA-002",
            "similarity": 0.88,
            "final_score": 0.90,
            "metadata": {
                "service": "Payment API",
                "category": "API / Microservices",
                "severity": "Medium",
                "root_cause": "Payment gateway unavailable",
                "resolution": "Restored gateway connection",
                "preventive_action": "Improve gateway monitoring",
            },
        },
        {
            "incident_id": "RCA-003",
            "similarity": 0.85,
            "final_score": 0.86,
            "metadata": {
                "service": "Payment API",
                "category": "API / Microservices",
                "severity": "Low",
                "root_cause": "Database timeout",
                "resolution": "Restarted database connection",
                "preventive_action": "Tune database timeout",
            },
        },
    ]

    result = extract_evidence(
        incidents,
        "Payment gateway unavailable",
    )

    assert result["root_cause"] == (
        "Payment gateway unavailable"
    )

    assert result["evidence_count"] == 2

    assert [
        item["incident_id"]
        for item in result["evidence"]
    ] == [
        "RCA-001",
        "RCA-002",
    ]


def test_empty_incidents():
    result = extract_evidence(
        [],
        "Database timeout",
    )

    assert result["evidence"] == []
    assert result["evidence_count"] == 0


def test_no_matching_root_cause():
    incidents = [
        {
            "incident_id": "RCA-001",
            "root_cause": "API timeout",
        }
    ]

    result = extract_evidence(
        incidents,
        "Database failure",
    )

    assert result["evidence"] == []
    assert result["evidence_count"] == 0