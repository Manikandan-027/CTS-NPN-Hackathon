import pytest

from backend.core.retrieval.keyword_retrieval import (
    keyword_retrieve_incidents,
)


@pytest.fixture
def incidents():
    return [
        {
            "incident_id": "INC001",
            "description": (
                "Payment API is returning HTTP 500 "
                "and customers cannot complete payments."
            ),
        },
        {
            "incident_id": "INC002",
            "description": (
                "Database connection failure caused "
                "the customer transaction service to stop."
            ),
        },
        {
            "incident_id": "INC003",
            "description": (
                "Users are unable to process transactions "
                "because the payment service is unavailable."
            ),
        },
    ]


def test_keyword_retrieval_returns_results(incidents):
    results = keyword_retrieve_incidents(
        "Payment API HTTP 500",
        incidents,
        top_k=2,
    )

    assert len(results) == 2
    assert "keyword_score" in results[0]


def test_keyword_retrieval_orders_by_score(incidents):
    results = keyword_retrieve_incidents(
        "Payment API HTTP 500",
        incidents,
        top_k=3,
    )

    assert (
        results[0]["keyword_score"]
        >= results[1]["keyword_score"]
    )


def test_empty_query_raises_error(incidents):
    with pytest.raises(ValueError):
        keyword_retrieve_incidents(
            "",
            incidents,
            top_k=5,
        )


def test_invalid_top_k_raises_error(incidents):
    with pytest.raises(ValueError):
        keyword_retrieve_incidents(
            "Payment API failure",
            incidents,
            top_k=0,
        )