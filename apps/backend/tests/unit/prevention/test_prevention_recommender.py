from backend.core.prevention.prevention_recommender import (
    recommend_prevention,
)


def test_recommends_most_frequent_prevention_action():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {
                "preventive_action":
                    "Add integration testing."
            },
        },
        {
            "incident_id": "RCA-002",
            "metadata": {
                "preventive_action":
                    "Add integration testing."
            },
        },
        {
            "incident_id": "RCA-003",
            "metadata": {
                "preventive_action":
                    "Review monitoring configuration."
            },
        },
    ]

    result = recommend_prevention(
        incidents
    )

    assert (
        result["recommended_prevention"]
        == "Add integration testing."
    )

    assert result["supporting_incidents"] == [
        "RCA-001",
        "RCA-002",
    ]

    assert (
        result["prevention_counts"][
            "Add integration testing."
        ]
        == 2
    )


def test_reads_prevention_from_incident():
    incidents = [
        {
            "incident_id": "RCA-001",
            "preventive_action":
                "Improve recovery testing.",
        }
    ]

    result = recommend_prevention(
        incidents
    )

    assert (
        result["recommended_prevention"]
        == "Improve recovery testing."
    )


def test_empty_incidents():
    result = recommend_prevention([])

    assert result["recommended_prevention"] == ""
    assert result["supporting_incidents"] == []
    assert result["prevention_counts"] == {}


def test_ignores_missing_prevention_action():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {},
        },
        {
            "incident_id": "RCA-002",
            "metadata": {
                "preventive_action":
                    "Review service configuration."
            },
        },
    ]

    result = recommend_prevention(
        incidents
    )

    assert (
        result["recommended_prevention"]
        == "Review service configuration."
    )


def test_invalid_top_k():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {
                "preventive_action":
                    "Improve monitoring."
            },
        }
    ]

    try:
        recommend_prevention(
            incidents,
            0,
        )
        assert False
    except ValueError:
        assert True