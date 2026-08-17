"""Unit tests for hybrid incident reranking."""

from backend.core.hybrid_retrieval.reranker import (
    HybridReranker,
    rerank_incidents,
)


def test_rerank_incidents():

    candidates = [
        {
            "incident_id": "INC1021",
            "similarity": 0.95,
            "metadata": {
                "service": "payment-api",
                "category": "database",
                "severity": "high",
                "root_cause": "DB connection exhaustion",
            },
        },
        {
            "incident_id": "INC2045",
            "similarity": 0.97,
            "metadata": {
                "service": "order-api",
                "category": "database",
                "severity": "medium",
                "root_cause": "DB timeout",
            },
        },
    ]

    query_metadata = {
        "service": "payment-api",
        "category": "database",
        "severity": "high",
    }

    results = rerank_incidents(
        candidates=candidates,
        query_metadata=query_metadata,
        top_k=2,
    )

    assert len(results) == 2

    # INC1021 has a slightly lower semantic score,
    # but matches all metadata fields.
    assert results[0]["incident_id"] == "INC1021"

    assert results[0]["service_match"] == 1.0
    assert results[0]["category_match"] == 1.0
    assert results[0]["severity_match"] == 1.0


def test_weights_sum_to_one():

    reranker = HybridReranker()

    total = (
        reranker.semantic_weight
        + reranker.service_weight
        + reranker.category_weight
        + reranker.severity_weight
    )

    assert total == 1.0


def test_empty_candidates():

    results = rerank_incidents(
        candidates=[],
        query_metadata={
            "service": "payment-api",
            "category": "database",
            "severity": "high",
        },
    )

    assert results == []


def test_top_k_limit():

    candidates = [
        {
            "incident_id": f"INC{i}",
            "similarity": 0.90 - (i * 0.01),
            "metadata": {
                "service": "payment-api",
                "category": "database",
                "severity": "high",
            },
        }
        for i in range(10)
    ]

    results = rerank_incidents(
        candidates=candidates,
        query_metadata={
            "service": "payment-api",
            "category": "database",
            "severity": "high",
        },
        top_k=5,
    )

    assert len(results) == 5
    