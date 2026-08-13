from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from backend.core.embeddings.config import (
    DEFAULT_CONFIG,
)


@lru_cache(maxsize=1)
def get_embedding_model(
    model_name: str = DEFAULT_CONFIG.model_name,
) -> SentenceTransformer:

    model = SentenceTransformer(
        model_name
    )

    # Explicitly enforce the expected input length.
    model.max_seq_length = (
        DEFAULT_CONFIG.max_input_tokens
    )

    return model


class MiniLMEmbedder:
    """
    all-MiniLM-L6-v2 embedding engine.

    Output:
        384-dimensional normalized vectors.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_CONFIG.model_name,
        expected_dimension: int = (
            DEFAULT_CONFIG.embedding_dimension
        ),
        batch_size: int = (
            DEFAULT_CONFIG.batch_size
        ),
    ) -> None:

        self.model_name = model_name
        self.expected_dimension = (
            expected_dimension
        )
        self.batch_size = batch_size

        self.model = get_embedding_model(
            model_name
        )

    def embed_texts(
        self,
        texts: list[str],
        show_progress_bar: bool = True,
    ) -> np.ndarray:

        if not texts:
            return np.empty(
                (0, self.expected_dimension),
                dtype=np.float32,
            )

        cleaned = []

        for text in texts:

            if not text or not text.strip():
                raise ValueError(
                    "Cannot embed empty text."
                )

            cleaned.append(
                text.strip()
            )

        embeddings = self.model.encode(
            cleaned,
            batch_size=self.batch_size,
            show_progress_bar=(
                show_progress_bar
            ),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        embeddings = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        if embeddings.ndim != 2:

            raise ValueError(
                "Embedding output must be "
                "a 2D matrix."
            )

        if embeddings.shape[1] != (
            self.expected_dimension
        ):

            raise ValueError(
                "Unexpected embedding dimension. "
                f"Expected {self.expected_dimension}, "
                f"got {embeddings.shape[1]}."
            )

        if not np.isfinite(
            embeddings
        ).all():

            raise ValueError(
                "Embeddings contain NaN or Inf."
            )

        return embeddings

    def embed_text(
        self,
        text: str,
    ) -> np.ndarray:

        result = self.embed_texts(
            [text],
            show_progress_bar=False,
        )

        return result[0]

    @staticmethod
    def mean_pool(
        embeddings: np.ndarray,
    ) -> np.ndarray:

        if embeddings.ndim != 2:
            raise ValueError(
                "Expected a 2D embedding matrix."
            )

        if embeddings.shape[0] == 0:
            raise ValueError(
                "Cannot pool zero embeddings."
            )

        pooled = np.mean(
            embeddings,
            axis=0,
        )

        # L2 normalization.
        norm = np.linalg.norm(
            pooled
        )

        if norm == 0:
            raise ValueError(
                "Cannot normalize a zero vector."
            )

        pooled = pooled / norm

        return pooled.astype(
            np.float32
        )