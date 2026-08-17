from __future__ import annotations

from typing import Any

from backend.core.embeddings.embedder import MiniLMEmbedder
from backend.core.vector_db.client import ChromaClient


class SemanticRetriever:
    """
    Semantic retrieval using the existing embedding module
    and the existing LOCAL persistent ChromaDB client.
    """

    def __init__(
        self,
        embedder: MiniLMEmbedder | None = None,
        chroma_client: ChromaClient | None = None,
    ) -> None:
        self.embedder = embedder or MiniLMEmbedder()
        self.chroma_client = (
            chroma_client or ChromaClient()
        )

    def retrieve_similar_incidents(
        self,
        query: str,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most semantically similar historical incidents.

        Args:
            query:
                New incident description.

            top_k:
                Number of historical incidents to retrieve.

        Returns:
            [
                {
                    "incident_id": "INC1021",
                    "similarity": 0.95
                }
            ]
        """

        if not query or not query.strip():
            raise ValueError(
                "Query incident description cannot be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        # --------------------------------------------------
        # 1. Generate incident embedding
        # --------------------------------------------------

        embedding = self.embedder.embed_text(
            query.strip()
        )

        # --------------------------------------------------
        # 2. Get LOCAL persistent ChromaDB collection
        # --------------------------------------------------

        collection = (
            self.chroma_client.get_collection()
        )

        # --------------------------------------------------
        # 3. Query ChromaDB
        # --------------------------------------------------

        results = collection.query(
            query_embeddings=[
                embedding.tolist()
            ],
            n_results=top_k,
            include=[
                "metadatas",
                "distances",
            ],
        )

        # --------------------------------------------------
        # 4. Convert ChromaDB response
        # --------------------------------------------------

        return self._format_results(results)

    @staticmethod
    def _format_results(
        results: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Convert ChromaDB query results into the standard
        retrieval output format.
        """

        if not results:
            return []

        ids = results.get("ids") or [[]]
        distances = (
            results.get("distances") or [[]]
        )
        metadatas = (
            results.get("metadatas") or [[]]
        )

        if not ids or not ids[0]:
            return []

        ids = ids[0]

        distances = (
            distances[0]
            if distances and distances[0]
            else []
        )

        metadatas = (
            metadatas[0]
            if metadatas and metadatas[0]
            else []
        )

        output: list[dict[str, Any]] = []

        for index, document_id in enumerate(ids):

            distance = (
                float(distances[index])
                if index < len(distances)
                else 0.0
            )

            # ChromaDB is configured with:
            #
            # hnsw:space = cosine
            #
            # Therefore cosine distance is:
            #
            # distance = 1 - cosine_similarity
            #
            # Convert it back to similarity.

            similarity = 1.0 - distance

            # Protect against floating-point overflow.
            similarity = max(
                0.0,
                min(
                    1.0,
                    similarity,
                ),
            )

            metadata = (
                metadatas[index]
                if index < len(metadatas)
                else {}
            )

            # Prefer incident_id from metadata when available.
            incident_id = (
                metadata.get("incident_id")
                if metadata
                else None
            )

            if not incident_id:
                incident_id = document_id

            result = {
                "incident_id": str(
                    incident_id
                ),
                "similarity": round(
                    similarity,
                    6,
                ),
            }

            # Preserve metadata for Phase 2
            # hybrid re-ranking.
            if metadata:
                result["metadata"] = metadata

            output.append(result)

        return output


def retrieve_similar_incidents(
    query: str,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """
    Convenience function for semantic retrieval.
    """

    retriever = SemanticRetriever()

    return retriever.retrieve_similar_incidents(
        query=query,
        top_k=top_k,
    )