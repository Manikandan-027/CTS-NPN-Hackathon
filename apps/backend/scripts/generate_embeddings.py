from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


# ============================================================
# IMPORTS
# ============================================================

from backend.core.embeddings.config import (
    DEFAULT_CONFIG,
)

from backend.core.embeddings.service import (
    IncidentEmbeddingService,
)


# ============================================================
# PATHS
# ============================================================

INPUT_PATH = (
    ROOT
    / "backend"
    / "data"
    / "processed"
    / "processed_incidents.csv"
)

OUTPUT_DIR = (
    ROOT
    / "backend"
    / "data"
    / "processed"
)

EMBEDDINGS_PATH = (
    OUTPUT_DIR
    / "embeddings.npy"
)

METADATA_PATH = (
    OUTPUT_DIR
    / "embedding_records.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

def load_processed_dataset() -> pd.DataFrame:

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            f"Processed dataset not found:\n"
            f"{INPUT_PATH}\n\n"
            "Run Member 1 preprocessing first."
        )

    df = pd.read_csv(
        INPUT_PATH
    )

    required_columns = [
        "incident_id",
        "incident_description",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            "Processed dataset is missing: "
            f"{missing}"
        )

    return df


# ============================================================
# VALIDATE INPUT
# ============================================================

def validate_input(
    df: pd.DataFrame,
) -> None:

    if df.empty:

        raise ValueError(
            "Processed dataset is empty."
        )

    if df["incident_id"].isna().any():

        raise ValueError(
            "incident_id contains missing values."
        )

    if not df["incident_id"].is_unique:

        raise ValueError(
            "incident_id values must be unique."
        )

    if df[
        "incident_description"
    ].isna().any():

        raise ValueError(
            "incident_description contains "
            "missing values."
        )

    empty_descriptions = (
        df[
            "incident_description"
        ]
        .astype(str)
        .str.strip()
        .eq("")
    )

    if empty_descriptions.any():

        raise ValueError(
            "One or more incident descriptions "
            "are empty."
        )


# ============================================================
# SAVE
# ============================================================

def save_outputs(
    embeddings: np.ndarray,
    metadata: list[dict],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Embeddings
    # --------------------------------------------------------

    np.save(
        EMBEDDINGS_PATH,
        embeddings,
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata_df = pd.DataFrame(
        metadata
    )

    metadata_df.to_csv(
        METADATA_PATH,
        index=False,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 70)
    print(
        "AI INCIDENT RCA - "
        "TOKENIZATION + CHUNKING + EMBEDDING"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    print("\nLoading processed dataset...")

    df = load_processed_dataset()

    validate_input(df)

    print(
        f"Incident count: {len(df)}"
    )

    # --------------------------------------------------------
    # Configuration
    # --------------------------------------------------------

    print("\nEmbedding configuration:")

    print(
        "Model:",
        DEFAULT_CONFIG.model_name,
    )

    print(
        "Embedding dimension:",
        DEFAULT_CONFIG.embedding_dimension,
    )

    print(
        "Maximum input tokens:",
        DEFAULT_CONFIG.max_input_tokens,
    )

    print(
        "Chunk overlap:",
        DEFAULT_CONFIG.chunk_overlap_tokens,
    )

    print(
        "Batch size:",
        DEFAULT_CONFIG.batch_size,
    )

    # --------------------------------------------------------
    # Service
    # --------------------------------------------------------

    print(
        "\nLoading tokenizer and model..."
    )

    service = IncidentEmbeddingService()

    # --------------------------------------------------------
    # Process
    # --------------------------------------------------------

    print(
        "\nStarting tokenization → "
        "chunking → embedding..."
    )

    embeddings, metadata = (
        service.embed_incidents(
            incident_ids=[
                str(x)
                for x in df[
                    "incident_id"
                ]
            ],
            descriptions=[
                str(x)
                for x in df[
                    "incident_description"
                ]
            ],
        )
    )

    # --------------------------------------------------------
    # Validate output
    # --------------------------------------------------------

    print(
        "\nValidating embedding matrix..."
    )

    expected_shape = (
        len(df),
        DEFAULT_CONFIG.embedding_dimension,
    )

    if embeddings.shape != expected_shape:

        raise RuntimeError(
            "Embedding matrix has incorrect "
            f"shape.\n"
            f"Expected: {expected_shape}\n"
            f"Received: {embeddings.shape}"
        )

    if not np.isfinite(
        embeddings
    ).all():

        raise RuntimeError(
            "Embedding matrix contains "
            "NaN or Inf values."
        )

    # Verify vectors are normalized.
    norms = np.linalg.norm(
        embeddings,
        axis=1,
    )

    if not np.allclose(
        norms,
        1.0,
        atol=1e-4,
    ):

        raise RuntimeError(
            "Embeddings are not properly "
            "L2 normalized."
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_outputs(
        embeddings,
        metadata,
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    metadata_df = pd.DataFrame(
        metadata
    )

    chunked_count = int(
        (
            metadata_df[
                "chunk_count"
            ]
            > 1
        )
        .sum()
    )

    max_tokens = int(
        metadata_df[
            "token_count"
        ].max()
    )

    average_tokens = float(
        metadata_df[
            "token_count"
        ].mean()
    )

    average_chunks = float(
        metadata_df[
            "chunk_count"
        ].mean()
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print(
        "EMBEDDING PIPELINE COMPLETE"
    )
    print("=" * 70)

    print(
        f"Incidents processed:  {len(df)}"
    )

    print(
        f"Embedding shape:      {embeddings.shape}"
    )

    print(
        f"Embedding dimension:  "
        f"{embeddings.shape[1]}"
    )

    print(
        f"Average tokens:       "
        f"{average_tokens:.2f}"
    )

    print(
        f"Maximum tokens:       "
        f"{max_tokens}"
    )

    print(
        f"Average chunks:       "
        f"{average_chunks:.2f}"
    )

    print(
        f"Multi-chunk incidents: "
        f"{chunked_count}"
    )

    print()

    print(
        f"Embeddings saved to:\n"
        f"{EMBEDDINGS_PATH}"
    )

    print()

    print(
        f"Metadata saved to:\n"
        f"{METADATA_PATH}"
    )

    print()

    print(
        "STATUS: SUCCESS"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()