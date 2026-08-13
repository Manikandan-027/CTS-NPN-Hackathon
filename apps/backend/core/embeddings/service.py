from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.core.embeddings.chunker import (
    IncidentChunker,
    TextChunk,
)

from backend.core.embeddings.config import (
    DEFAULT_CONFIG,
)

from backend.core.embeddings.embedder import (
    MiniLMEmbedder,
)

from backend.core.embeddings.tokenizer import (
    IncidentTokenizer,
)


@dataclass
class IncidentEmbeddingResult:
    """
    Complete embedding result for ONE incident.
    """

    incident_id: str

    original_text: str

    token_count: int

    chunk_count: int

    chunks: list[TextChunk]

    embedding: np.ndarray


class IncidentEmbeddingService:
    """
    Complete incident embedding pipeline.

    For each incident:

        Description
             ↓
        Tokenization
             ↓
        Token-aware chunking
             ↓
        MiniLM chunk embeddings
             ↓
        Mean pooling
             ↓
        L2 normalization
             ↓
        384-dimensional vector
    """

    def __init__(
        self,
        model_name: str = (
            DEFAULT_CONFIG.model_name
        ),
        max_input_tokens: int = (
            DEFAULT_CONFIG.max_input_tokens
        ),
        overlap_tokens: int = (
            DEFAULT_CONFIG.chunk_overlap_tokens
        ),
        batch_size: int = (
            DEFAULT_CONFIG.batch_size
        ),
    ) -> None:

        self.tokenizer = (
            IncidentTokenizer(
                model_name
            )
        )

        self.chunker = (
            IncidentChunker(
                tokenizer=self.tokenizer,
                max_tokens=max_input_tokens,
                overlap_tokens=overlap_tokens,
            )
        )

        self.embedder = (
            MiniLMEmbedder(
                model_name=model_name,
                batch_size=batch_size,
            )
        )

    def process_incident(
        self,
        incident_id: str,
        description: str,
    ) -> IncidentEmbeddingResult:

        if not description.strip():
            raise ValueError(
                f"Incident {incident_id} "
                "has an empty description."
            )

        # ----------------------------------------------------
        # 1. Tokenization
        # ----------------------------------------------------

        tokenized = (
            self.tokenizer.tokenize(
                description
            )
        )

        token_count = (
            tokenized.token_count
        )

        # ----------------------------------------------------
        # 2. Token-aware chunking
        # ----------------------------------------------------

        chunks = (
            self.chunker.chunk(
                description
            )
        )

        # ----------------------------------------------------
        # 3. Embed chunks
        # ----------------------------------------------------

        chunk_texts = [
            chunk.text
            for chunk in chunks
        ]

        chunk_embeddings = (
            self.embedder.embed_texts(
                chunk_texts,
                show_progress_bar=False,
            )
        )

        # ----------------------------------------------------
        # 4. Mean-pool chunks
        # ----------------------------------------------------

        incident_embedding = (
            self.embedder.mean_pool(
                chunk_embeddings
            )
        )

        # ----------------------------------------------------
        # 5. Validate dimension
        # ----------------------------------------------------

        if incident_embedding.shape != (
            DEFAULT_CONFIG.embedding_dimension,
        ):

            raise ValueError(
                f"Incident embedding for "
                f"{incident_id} has incorrect "
                f"shape: "
                f"{incident_embedding.shape}"
            )

        return IncidentEmbeddingResult(
            incident_id=incident_id,
            original_text=description,
            token_count=token_count,
            chunk_count=len(chunks),
            chunks=chunks,
            embedding=incident_embedding,
        )

    def embed_incidents(
        self,
        incident_ids: list[str],
        descriptions: list[str],
    ) -> tuple[
        np.ndarray,
        list[dict],
    ]:

        if len(incident_ids) != len(
            descriptions
        ):

            raise ValueError(
                "incident_ids and descriptions "
                "must have the same length."
            )

        all_embeddings: list[
            np.ndarray
        ] = []

        metadata: list[dict] = []

        total = len(
            incident_ids
        )

        for index, (
            incident_id,
            description,
        ) in enumerate(
            zip(
                incident_ids,
                descriptions,
            ),
            start=1,
        ):

            result = (
                self.process_incident(
                    incident_id=incident_id,
                    description=description,
                )
            )

            all_embeddings.append(
                result.embedding
            )

            metadata.append(
                {
                    "incident_id": (
                        result.incident_id
                    ),
                    "token_count": (
                        result.token_count
                    ),
                    "chunk_count": (
                        result.chunk_count
                    ),
                }
            )

            if (
                index % 100 == 0
                or index == total
            ):

                print(
                    f"Embedded "
                    f"{index}/{total}"
                )

        matrix = np.vstack(
            all_embeddings
        ).astype(
            np.float32
        )

        return matrix, metadata