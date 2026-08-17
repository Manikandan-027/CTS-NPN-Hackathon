from __future__ import annotations

import json

from backend.core.retrieval.keyword_retrieval import (
    keyword_retrieve_incidents,
)

from backend.core.retrieval.keyword_reranker import (
    rerank_keyword_incidents,
)

from backend.core.retrieval.semantic_retrieval import (
    retrieve_similar_incidents,
)

from backend.core.hybrid_retrieval.reranker import (
    rerank_incidents,
)

from backend.core.retrieval.query_metadata import (
    extract_query_metadata,
)


DATASET_PATH = (
    "apps/backend/data/processed/"
    "processed_incidents.jsonl"
)


def load_incidents():

    incidents = []

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

            line = line.strip()

            if line:
                incidents.append(
                    json.loads(line)
                )

    return incidents


def get_metadata(
    incident,
):

    metadata = incident.get(
        "metadata",
        {},
    )

    if isinstance(metadata, dict):
        return metadata

    return incident


def description(
    incident,
):

    return incident.get(
        "incident_description",
        incident.get(
            "description",
            "",
        ),
    )


def print_top_results(
    title,
    results,
    score_field,
):

    print()
    print(
        f"---------------- {title} ----------------"
    )

    for i, item in enumerate(
        results,
        1,
    ):

        metadata = get_metadata(
            item
        )

        score = item.get(
            score_field,
            0.0,
        )

        print(
            f"{i} . "
            f"{item['incident_id']} "
            f"| {score_field} = "
            f"{score:.4f}"
        )

        print(
            "    Service=",
            metadata.get(
                "service",
                metadata.get(
                    "affected_service",
                    "N/A",
                ),
            ),
            "| Category=",
            metadata.get(
                "category",
                "N/A",
            ),
            "| Severity=",
            metadata.get(
                "severity",
                "N/A",
            ),
        )

        print(
            "    ",
            description(item)[:180],
        )


def main():

    query = input(
        "Enter incident: "
    ).strip()

    if not query:

        print(
            "ERROR: Incident cannot be empty."
        )

        return

    incidents = load_incidents()

    # ======================================================
    # QUERY METADATA
    # ======================================================

    query_metadata = extract_query_metadata(
        query,
        incidents,
    )

    # ======================================================
    # KEYWORD RETRIEVAL
    # ======================================================

    keyword_top20 = (
        keyword_retrieve_incidents(
            query,
            incidents,
            top_k=20,
        )
    )

    keyword_top5 = (
        rerank_keyword_incidents(
            keyword_top20,
            query,
            top_k=5,
        )
    )

    # ======================================================
    # SEMANTIC RETRIEVAL
    # ======================================================

    semantic_top20 = (
        retrieve_similar_incidents(
            query,
            top_k=20,
        )
    )

    # ======================================================
    # SEMANTIC + METADATA RERANKING
    # ======================================================

    semantic_top5 = rerank_incidents(
        semantic_top20,
        query_metadata=query_metadata,
        top_k=5,
    )

    # ======================================================
    # OUTPUT
    # ======================================================

    print()
    print(
        "=========================================================="
    )

    print(
        "          KEYWORD vs SEMANTIC RETRIEVAL"
    )

    print(
        "=========================================================="
    )

    print()
    print(
        "INPUT INCIDENT:"
    )

    print(query)

    print()
    print(
        "EXTRACTED QUERY METADATA:"
    )

    print(
        query_metadata
    )

    # ------------------------------------------------------
    # KEYWORD TOP 20
    # ------------------------------------------------------

    print_top_results(
        "KEYWORD TOP 20",
        keyword_top20,
        "keyword_score",
    )

    # ------------------------------------------------------
    # KEYWORD TOP 5
    # ------------------------------------------------------

    print_top_results(
        "KEYWORD RERANKED TOP 5",
        keyword_top5,
        "final_score",
    )

    # ------------------------------------------------------
    # SEMANTIC TOP 20
    # ------------------------------------------------------

    print_top_results(
        "SEMANTIC TOP 20",
        semantic_top20,
        "similarity",
    )

    # ------------------------------------------------------
    # SEMANTIC + METADATA TOP 5
    # ------------------------------------------------------

    print_top_results(
        "SEMANTIC + METADATA TOP 5",
        semantic_top5,
        "final_score",
    )

    # ======================================================
    # COMPARISON
    # ======================================================

    keyword_ids = {
        x["incident_id"]
        for x in keyword_top5
    }

    semantic_ids = {
        x["incident_id"]
        for x in semantic_top5
    }

    print()
    print(
        "---------------- FINAL COMPARISON ----------------"
    )

    print(
        "Keyword Top 5:",
        keyword_ids,
    )

    print(
        "Semantic + Metadata Top 5:",
        semantic_ids,
    )

    print(
        "Keyword-only:",
        keyword_ids - semantic_ids,
    )

    print(
        "Semantic-only:",
        semantic_ids - keyword_ids,
    )

    print(
        "Common:",
        keyword_ids & semantic_ids,
    )

    # ======================================================
    # RELEVANCE SUMMARY
    # ======================================================

    print()
    print(
        "================ RELEVANCE SUMMARY ================"
    )

    print(
        "Query service:",
        query_metadata.get(
            "service",
            "Not detected",
        ),
    )

    print(
        "Query category:",
        query_metadata.get(
            "category",
            "Not detected",
        ),
    )

    print(
        "Query severity:",
        query_metadata.get(
            "severity",
            "Not detected",
        ),
    )

    print()
    print(
        "Keyword retrieval:"
    )

    print(
        "  Exact lexical matching."
    )

    print(
        "Semantic retrieval:"
    )

    print(
        "  Meaning-based vector retrieval."
    )

    print(
        "Semantic + metadata:"
    )

    print(
        "  Vector similarity refined using "
        "metadata explicitly detected from "
        "the new incident."
    )

    print()
    print(
        "=========================================================="
    )

    print(
        "PHASE 2 RETRIEVAL TEST COMPLETE"
    )

    print(
        "=========================================================="
    )


if __name__ == "__main__":
    main()