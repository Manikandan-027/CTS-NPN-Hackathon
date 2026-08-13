from __future__ import annotations

from typing import Any

from backend.core.vector_db.client import (
    ChromaClient,
)

from backend.core.vector_db.config import (
    DEFAULT_TOP_K,
    EMBEDDING_DIMENSION,
)


class IncidentVectorRepository:
    """
    Repository for historical incident vectors.

    Responsibilities:

    - Add incident embeddings
    - Count stored incidents
    - Search similar incidents
    - Retrieve metadata
    """

    def __init__(
        self,
        persist_directory=None,
    ) -> None:

        if persist_directory is None:

            self.chroma = (
                ChromaClient()
            )

        else:

            self.chroma = (
                ChromaClient(
                    persist_directory
                )
            )

        self.collection = (
            self.chroma.get_collection()
        )

    # ========================================================
    # RESET
    # ========================================================

    def reset(self) -> None:
        """
        Completely recreate the collection.

        Used during initial dataset ingestion.
        """

        self.collection = (
            self.chroma.recreate_collection()
        )

    # ========================================================
    # COUNT
    # ========================================================

    def count(self) -> int:
        """
        Return the number of stored incidents.
        """

        return self.collection.count()

    # ========================================================
    # ADD INCIDENTS
    # ========================================================

    def add_records(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """
        Insert or update incident vectors.
        """

        if not ids:
            return

        lengths = {
            len(ids),
            len(documents),
            len(embeddings),
            len(metadatas),
        }

        if len(lengths) != 1:

            raise ValueError(
                "ids, documents, embeddings and "
                "metadatas must contain the same "
                "number of records."
            )

        # ----------------------------------------------------
        # Validate embeddings
        # ----------------------------------------------------

        for index, embedding in enumerate(
            embeddings
        ):

            if len(embedding) != (
                EMBEDDING_DIMENSION
            ):

                raise ValueError(
                    f"Embedding at index {index} "
                    f"has dimension "
                    f"{len(embedding)}. "
                    f"Expected "
                    f"{EMBEDDING_DIMENSION}."
                )

        # ----------------------------------------------------
        # ChromaDB upsert
        # ----------------------------------------------------

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    # ========================================================
    # QUERY
    # ========================================================

    def query(
        self,
        query_embedding: list[float],
        top_k: int = DEFAULT_TOP_K,
    ) -> dict[str, Any]:
        """
        Search historical incidents using cosine similarity.
        """

        if len(query_embedding) != (
            EMBEDDING_DIMENSION
        ):

            raise ValueError(
                "Query embedding must have "
                f"{EMBEDDING_DIMENSION} dimensions. "
                f"Received "
                f"{len(query_embedding)}."
            )

        collection_count = (
            self.collection.count()
        )

        if collection_count == 0:

            raise RuntimeError(
                "ChromaDB collection is empty. "
                "Run populate_vector_db.py first."
            )

        if top_k <= 0:

            raise ValueError(
                "top_k must be greater than zero."
            )

        top_k = min(
            top_k,
            collection_count,
        )

        return self.collection.query(
            query_embeddings=[
                query_embedding
            ],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

    # ========================================================
    # GET BY ID
    # ========================================================

    def get_by_id(
        self,
        incident_id: str,
    ) -> dict[str, Any]:

        result = self.collection.get(
            ids=[incident_id],
            include=[
                "documents",
                "metadatas",
                "embeddings",
            ],
        )

        return result