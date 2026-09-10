from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.core.retrieval.semantic_retrieval import (
    SemanticRetriever,
)


def create_retriever_mock():
    embedder = MagicMock()

    # 384-dimensional embedding, matching all-MiniLM-L6-v2
    embedder.embed_text.return_value = np.zeros(
        384,
        dtype=np.float32,
    )

    chroma_client = MagicMock()
    collection = MagicMock()

    chroma_client.get_collection.return_value = collection

    collection.query.return_value = {
        "ids": [
            [
                "INC1021",
                "INC2045",
                "INC3102",
            ]
        ],
        "distances": [
            [
                0.05,
                0.09,
                0.12,
            ]
        ],
        "metadatas": [
            [
                {
                    "incident_id": "INC1021",
                    "service": "payment",
                    "category": "database",
                    "severity": "high",
                },
                {
                    "incident_id": "INC2045",
                    "service": "payment",
                    "category": "database",
                    "severity": "high",
                },
                {
                    "incident_id": "INC3102",
                    "service": "payment",
                    "category": "api",
                    "severity": "medium",
                },
            ]
        ],
    }

    retriever = SemanticRetriever(
        embedder=embedder,
        chroma_client=chroma_client,
    )

    return (
        retriever,
        embedder,
        chroma_client,
        collection,
    )


def test_retrieve_similar_incidents():
    (
        retriever,
        embedder,
        chroma_client,
        collection,
    ) = create_retriever_mock()

    results = retriever.retrieve_similar_incidents(
        "Payment API is returning HTTP 500",
        top_k=3,
    )

    assert len(results) == 3

    assert results[0]["incident_id"] == "INC1021"
    assert results[1]["incident_id"] == "INC2045"
    assert results[2]["incident_id"] == "INC3102"

    assert results[0]["similarity"] == 0.95
    assert results[1]["similarity"] == 0.91
    assert results[2]["similarity"] == 0.88

    embedder.embed_text.assert_called_once_with(
        "Payment API is returning HTTP 500"
    )

    chroma_client.get_collection.assert_called_once()

    collection.query.assert_called_once()

    query_kwargs = collection.query.call_args.kwargs

    assert query_kwargs["n_results"] == 3
    assert query_kwargs["include"] == [
        "metadatas",
        "distances",
    ]


def test_empty_description_raises_error():
    (
        retriever,
        _,
        _,
        _,
    ) = create_retriever_mock()

    with pytest.raises(ValueError):
        retriever.retrieve_similar_incidents(
            "",
            top_k=20,
        )


def test_invalid_top_k_raises_error():
    (
        retriever,
        _,
        _,
        _,
    ) = create_retriever_mock()

    with pytest.raises(ValueError):
        retriever.retrieve_similar_incidents(
            "Payment API failure",
            top_k=0,
        )