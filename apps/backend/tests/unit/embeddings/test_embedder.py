import numpy as np

from backend.core.embeddings.config import (
    DEFAULT_CONFIG,
)

from backend.core.embeddings.embedder import (
    MiniLMEmbedder,
)


def test_embedding_dimension():

    embedder = MiniLMEmbedder()

    vector = embedder.embed_text(
        "Payment API returned HTTP 500."
    )

    assert vector.shape == (
        DEFAULT_CONFIG.embedding_dimension,
    )


def test_embedding_is_normalized():

    embedder = MiniLMEmbedder()

    vector = embedder.embed_text(
        "Payment API returned HTTP 500."
    )

    norm = np.linalg.norm(
        vector
    )

    assert np.isclose(
        norm,
        1.0,
        atol=1e-4,
    )


def test_batch_embeddings():

    embedder = MiniLMEmbedder()

    vectors = embedder.embed_texts(
        [
            "Payment API failed.",
            "Database connection failed.",
        ],
        show_progress_bar=False,
    )

    assert vectors.shape == (
        2,
        DEFAULT_CONFIG.embedding_dimension,
    )