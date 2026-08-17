from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.core.vector_db.client import ChromaClient


class IncidentVectorRepository:
    """
    Repository layer for historical incident vectors stored in
    local persistent ChromaDB.

    This class provides a small, stable interface for:
        - resetting the collection
        - inserting incident records
        - counting stored incidents
        - querying similar incidents
    """

    def __init__(
        self,
        persist_directory: str | Path | None = None,
    ) -> None:

        if persist_directory is None:
            self.client = ChromaClient()
        else:
            self.client = ChromaClient(
                persist_directory=persist_directory
            )

        self.collection = (
            self.client.get_collection()
        )

    def reset(self) -> None:
        """
        Delete and recreate the historical incident collection.
        """

        self.collection = (
            self.client.recreate_collection()
        )

    def add_records(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """
        Add incident records to ChromaDB.
        """

        if not (
            len(ids)
            == len(documents)
            == len(embeddings)
            == len(metadatas)
        ):
            raise ValueError(
                "ids, documents, embeddings, and "
                "metadatas must have the same length."
            )

        if not ids:
            return

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def count(self) -> int:
        """
        Return the number of incidents stored
        in the current collection.
        """

        return self.collection.count()

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 20,
    ) -> dict[str, Any]:
        """
        Query the most similar historical incidents.
        """

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        if not query_embedding:
            raise ValueError(
                "query_embedding must not be empty."
            )

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )