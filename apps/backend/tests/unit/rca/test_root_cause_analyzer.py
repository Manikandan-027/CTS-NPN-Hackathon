import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[4]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from backend.core.rca.root_cause_analyzer import (
    analyze_root_cause,
)


def test_identifies_most_frequent_root_cause():
    incidents = [
        {
            "incident_id": "RCA-001",
            "root_cause": "Database connection exhaustion",
        },
        {
            "incident_id": "RCA-002",
            "root_cause": "Database connection exhaustion",
        },
        {
            "incident_id": "RCA-003",
            "root_cause": "API timeout",
        },
        {
            "incident_id": "RCA-004",
            "root_cause": "Database connection exhaustion",
        },
        {
            "incident_id": "RCA-005",
            "root_cause": "Database connection exhaustion",
        },
    ]

    result = analyze_root_cause(incidents)

    assert (
        result["likely_root_cause"]
        == "database connection exhaustion"
    )

    assert result["supporting_incidents"] == [
        "RCA-001",
        "RCA-002",
        "RCA-004",
        "RCA-005",
    ]

    assert result["root_cause_counts"] == {
        "database connection exhaustion": 4,
        "api timeout": 1,
    }


def test_reads_root_cause_from_metadata():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {
                "root_cause": "Payment gateway unavailable",
            },
        },
        {
            "incident_id": "RCA-002",
            "metadata": {
                "root_cause": "Payment gateway unavailable",
            },
        },
    ]

    result = analyze_root_cause(incidents)

    assert (
        result["likely_root_cause"]
        == "payment gateway unavailable"
    )


def test_empty_incidents():
    result = analyze_root_cause([])

    assert result["likely_root_cause"] is None
    assert result["supporting_incidents"] == []
    assert result["root_cause_counts"] == {}
    assert result["total_incidents"] == 0


def test_ignores_missing_root_cause():
    incidents = [
        {
            "incident_id": "RCA-001",
        },
        {
            "incident_id": "RCA-002",
            "root_cause": "API timeout",
        },
    ]

    result = analyze_root_cause(incidents)

    assert result["likely_root_cause"] == "api timeout"
    assert result["supporting_incidents"] == ["RCA-002"]