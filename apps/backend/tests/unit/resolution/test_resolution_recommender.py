from backend.core.resolution.resolution_recommender import (
    recommend_resolution,
)


def test_recommends_most_frequent_resolution():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {
                "resolution": "Restarted the payment service."
            },
        },
        {
            "incident_id": "RCA-002",
            "metadata": {
                "resolution": "Restarted the payment service."
            },
        },
        {
            "incident_id": "RCA-003",
            "metadata": {
                "resolution": "Cleared the application cache."
            },
        },
    ]

    result = recommend_resolution(incidents)

    assert (
        result["recommended_resolution"]
        == "Restarted the payment service."
    )

    assert result["supporting_incidents"] == [
        "RCA-001",
        "RCA-002",
    ]

    assert (
        result["resolution_counts"][
            "Restarted the payment service."
        ]
        == 2
    )


def test_reads_resolution_from_incident():
    incidents = [
        {
            "incident_id": "RCA-001",
            "resolution": "Rolled back the deployment.",
        }
    ]

    result = recommend_resolution(incidents)

    assert (
        result["recommended_resolution"]
        == "Rolled back the deployment."
    )


def test_empty_incidents():
    result = recommend_resolution([])

    assert result["recommended_resolution"] == ""
    assert result["supporting_incidents"] == []
    assert result["resolution_counts"] == {}


def test_ignores_missing_resolution():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {},
        },
        {
            "incident_id": "RCA-002",
            "metadata": {
                "resolution": "Restored the service."
            },
        },
    ]

    result = recommend_resolution(incidents)

    assert (
        result["recommended_resolution"]
        == "Restored the service."
    )


def test_invalid_top_k():
    incidents = [
        {
            "incident_id": "RCA-001",
            "metadata": {
                "resolution": "Restarted service."
            },
        }
    ]

    try:
        recommend_resolution(incidents, 0)
        assert False
    except ValueError:
        assert True