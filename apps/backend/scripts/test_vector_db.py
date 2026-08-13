from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from backend.core.embeddings.service import (
    IncidentEmbeddingService,
)

from backend.core.vector_db.repository import (
    IncidentVectorRepository,
)


def main() -> None:

    print("=" * 70)
    print(
        "LOCAL CHROMADB SEMANTIC SEARCH TEST"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # New incident
    # --------------------------------------------------------

    incident = (
        "Customers are unable to complete payment. "
        "Payment API is returning HTTP 500."
    )

    print(
        "\nNew Incident:"
    )

    print(
        incident
    )

    # --------------------------------------------------------
    # Create embedding
    # --------------------------------------------------------

    print(
        "\nGenerating query embedding..."
    )

    embedding_service = (
        IncidentEmbeddingService()
    )

    result = (
        embedding_service.process_incident(
            incident_id="NEW_INCIDENT",
            description=incident,
        )
    )

    query_embedding = (
        result.embedding.tolist()
    )

    print(
        f"Embedding dimension: "
        f"{len(query_embedding)}"
    )

    # --------------------------------------------------------
    # Repository
    # --------------------------------------------------------

    repository = (
        IncidentVectorRepository()
    )

    print(
        f"Stored incidents: "
        f"{repository.count()}"
    )

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    print(
        "\nSearching Top 20 similar incidents..."
    )

    results = repository.query(
        query_embedding=query_embedding,
        top_k=20,
    )

    ids = results["ids"][0]

    documents = results[
        "documents"
    ][0]

    metadatas = results[
        "metadatas"
    ][0]

    distances = results[
        "distances"
    ][0]

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print(
        "TOP 20 SEMANTICALLY SIMILAR INCIDENTS"
    )
    print("=" * 70)

    for index in range(
        len(ids)
    ):

        incident_id = ids[index]

        description = (
            documents[index]
        )

        metadata = (
            metadatas[index]
        )

        distance = float(
            distances[index]
        )

        similarity = (
            1.0 - distance
        )

        similarity = max(
            0.0,
            min(
                1.0,
                similarity,
            ),
        )

        print(
            f"\n{index + 1}. "
            f"{incident_id}"
        )

        print(
            f"   Similarity : "
            f"{similarity * 100:.2f}%"
        )

        print(
            f"   Service    : "
            f"{metadata.get('service', '')}"
        )

        print(
            f"   Category   : "
            f"{metadata.get('category', '')}"
        )

        print(
            f"   Severity   : "
            f"{metadata.get('severity', '')}"
        )

        print(
            f"   Root Cause : "
            f"{metadata.get('root_cause', '')}"
        )

        print(
            f"   Description: "
            f"{description}"
        )

    print("\n" + "=" * 70)
    print(
        f"Retrieved {len(ids)} incidents."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()