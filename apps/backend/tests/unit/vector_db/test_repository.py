from backend.core.vector_db.repository import (
    IncidentVectorRepository,
)


def test_insert_and_count(
    tmp_path,
):

    repository = (
        IncidentVectorRepository(
            persist_directory=(
                tmp_path / "chroma"
            )
        )
    )

    repository.reset()

    repository.add_records(
        ids=[
            "TEST001",
            "TEST002",
        ],

        documents=[
            "payment API failure",
            "database connection failure",
        ],

        embeddings=[
            [1.0] + [0.0] * 383,
            [0.0, 1.0] + [0.0] * 382,
        ],

        metadatas=[
            {
                "service": "Payment API",
                "category": "API",
                "severity": "High",
            },
            {
                "service": "Database",
                "category": "Database",
                "severity": "Medium",
            },
        ],
    )

    assert (
        repository.count()
        == 2
    )


def test_query_returns_most_similar(
    tmp_path,
):

    repository = (
        IncidentVectorRepository(
            persist_directory=(
                tmp_path / "chroma"
            )
        )
    )

    repository.reset()

    repository.add_records(
        ids=[
            "TEST001",
            "TEST002",
        ],

        documents=[
            "payment API failure",
            "database failure",
        ],

        embeddings=[
            [1.0] + [0.0] * 383,
            [0.0, 1.0] + [0.0] * 382,
        ],

        metadatas=[
            {
                "service": "Payment API",
                "category": "API",
                "severity": "High",
            },
            {
                "service": "Database",
                "category": "Database",
                "severity": "Medium",
            },
        ],
    )

    result = repository.query(
        query_embedding=(
            [1.0] + [0.0] * 383
        ),
        top_k=1,
    )

    assert (
        result["ids"][0][0]
        == "TEST001"
    )