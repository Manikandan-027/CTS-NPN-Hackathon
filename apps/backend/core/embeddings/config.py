from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingConfig:
    """
    Configuration for the incident embedding pipeline.
    """

    model_name: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    embedding_dimension: int = 384

    # all-MiniLM-L6-v2 supports 256 input tokens.
    max_input_tokens: int = 256

    # Number of tokens reused between adjacent chunks.
    chunk_overlap_tokens: int = 32

    # Batch size for model inference.
    batch_size: int = 64

    # Number of worker threads used by SentenceTransformer.
    show_progress_bar: bool = True


DEFAULT_CONFIG = EmbeddingConfig()