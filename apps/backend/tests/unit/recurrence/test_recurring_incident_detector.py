from backend.core.recurrence.recurring_incident_detector import (
    detect_recurring_incident,
)


def test_detects_recurring_incident():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {
                "service": "Payment API",
                "category": "API / Microservices",
                "root_cause": "database connection failure",
            },
        },
        {
            "incident_id": "RCA-002",
            "metadata": {
                "service": "Payment API",
                "category": "API / Microservices",
                "root_cause": "database connection failure",
            },
        },
        {
            "incident_id": "RCA-003",
            "metadata": {
                "service": "Payment API",
                "category": "API / Microservices",
                "root_cause": "API timeout",
            },
        },
    ]

    result = detect_recurring_incident(incidents)

    assert result["is_recurring"] is True
    assert result["occurrence_count"] == 2
    assert "RCA-001" in result["supporting_incidents"]
    assert "RCA-002" in result["supporting_incidents"]


def test_non_recurring_incident():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {
                "service": "Payment API",
                "category": "API / Microservices",
                "root_cause": "database failure",
            },
        },
        {
            "incident_id": "RCA-002",
            "metadata": {
                "service": "Customer API",
                "category": "API / Microservices",
                "root_cause": "API timeout",
            },
        },
    ]

    result = detect_recurring_incident(incidents)

    assert result["is_recurring"] is False
    assert result["occurrence_count"] == 1
    assert result["supporting_incidents"] == []


def test_empty_incidents():
    result = detect_recurring_incident([])

    assert result["is_recurring"] is False
    assert result["occurrence_count"] == 0
    assert result["supporting_incidents"] == []


def test_invalid_min_occurrences():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {
                "root_cause": "database failure",
            },
        }
    ]

    try:
        detect_recurring_incident(
            incidents,
            min_occurrences=0,
        )
        assert False
    except ValueError:
        assert True