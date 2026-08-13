from __future__ import annotations

from pathlib import Path

import chromadb

from backend.core.vector_db.config import (
    CHROMA_STORAGE_PATH,
    COLLECTION_NAME,
)


class ChromaClient:
    """
    Persistent LOCAL ChromaDB client.

    No cloud database is used.

    Database files are stored at:

        apps/backend/storage/chroma/
    """

    def __init__(
        self,
        persist_directory: str | Path = (
            CHROMA_STORAGE_PATH
        ),
    ) -> None:

        self.persist_directory = Path(
            persist_directory
        )

        self.persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ----------------------------------------------------
        # LOCAL PERSISTENT DATABASE
        # ----------------------------------------------------

        self.client = (
            chromadb.PersistentClient(
                path=str(
                    self.persist_directory
                )
            )
        )

    def get_collection(self):
        """
        Get or create the historical incident collection.
        """

        return (
            self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "description": (
                        "Historical incidents "
                        "for AI RCA retrieval"
                    ),
                    "hnsw:space": "cosine",
                },
            )
        )

    def delete_collection(self) -> None:
        """
        Delete the historical incident collection.
        """

        try:

            self.client.delete_collection(
                name=COLLECTION_NAME
            )

        except Exception:

            # Collection doesn't exist.
            pass

    def recreate_collection(self):
        """
        Delete and recreate the collection.
        """

        self.delete_collection()

        return self.get_collection()