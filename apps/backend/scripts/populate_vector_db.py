from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


# ============================================================
# PROJECT ROOT
# ============================================================

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


# ============================================================
# IMPORTS
# ============================================================

from backend.core.vector_db.repository import (
    IncidentVectorRepository,
)

from backend.core.vector_db.config import (
    CHROMA_STORAGE_PATH,
    EMBEDDING_DIMENSION,
    DEFAULT_BATCH_SIZE,
)


# ============================================================
# DATA PATHS
# ============================================================

DATA_DIR = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "processed"
)


DATASET_PATH = (
    DATA_DIR
    / "processed_incidents.csv"
)


EMBEDDINGS_PATH = (
    DATA_DIR
    / "embeddings.npy"
)


# ============================================================
# LOAD DATASET
# ============================================================

def load_dataset() -> pd.DataFrame:

    if not DATASET_PATH.exists():

        raise FileNotFoundError(
            f"Processed dataset not found:\n"
            f"{DATASET_PATH}"
        )

    df = pd.read_csv(
        DATASET_PATH
    )

    required_columns = [
        "incident_id",
        "incident_description",
        "category",
        "severity",
        "priority",
        "affected_service",
        "environment",
        "root_cause",
        "resolution",
        "preventive_action",
        "timestamp",
        "status",
        "source_type",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "Missing required columns:\n"
            f"{missing_columns}"
        )

    return df


# ============================================================
# LOAD EMBEDDINGS
# ============================================================

def load_embeddings() -> np.ndarray:

    if not EMBEDDINGS_PATH.exists():

        raise FileNotFoundError(
            f"Embedding file not found:\n"
            f"{EMBEDDINGS_PATH}\n\n"
            "Run generate_embeddings.py first."
        )

    embeddings = np.load(
        EMBEDDINGS_PATH
    )

    if embeddings.ndim != 2:

        raise ValueError(
            "Embedding array must be 2-dimensional."
        )

    if embeddings.shape[1] != (
        EMBEDDING_DIMENSION
    ):

        raise ValueError(
            "Invalid embedding dimension.\n"
            f"Expected: {EMBEDDING_DIMENSION}\n"
            f"Received: {embeddings.shape[1]}"
        )

    if not np.isfinite(
        embeddings
    ).all():

        raise ValueError(
            "Embedding matrix contains "
            "NaN or Inf values."
        )

    return embeddings.astype(
        np.float32
    )


# ============================================================
# METADATA
# ============================================================

def build_metadata(
    row: pd.Series,
) -> dict:

    return {
        "service": str(
            row["affected_service"]
        ),

        "category": str(
            row["category"]
        ),

        "severity": str(
            row["severity"]
        ),

        "priority": str(
            row["priority"]
        ),

        "environment": str(
            row["environment"]
        ),

        "root_cause": str(
            row["root_cause"]
        ),

        "resolution": str(
            row["resolution"]
        ),

        "preventive_action": str(
            row["preventive_action"]
        ),

        "timestamp": str(
            row["timestamp"]
        ),

        "status": str(
            row["status"]
        ),

        "source_type": str(
            row["source_type"]
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 70)
    print(
        "LOCAL CHROMADB - INCIDENT VECTOR INGESTION"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    print(
        "\n[1/5] Loading processed dataset..."
    )

    df = load_dataset()

    print(
        f"Records: {len(df)}"
    )

    # --------------------------------------------------------
    # Load embeddings
    # --------------------------------------------------------

    print(
        "\n[2/5] Loading embeddings..."
    )

    embeddings = load_embeddings()

    print(
        f"Embedding shape: {embeddings.shape}"
    )

    # --------------------------------------------------------
    # Verify counts
    # --------------------------------------------------------

    print(
        "\n[3/5] Validating dataset..."
    )

    if len(df) != len(embeddings):

        raise ValueError(
            "Dataset and embedding counts "
            "do not match.\n"
            f"Dataset: {len(df)}\n"
            f"Embeddings: {len(embeddings)}"
        )

    if not df[
        "incident_id"
    ].is_unique:

        raise ValueError(
            "Duplicate incident_id values detected."
        )

    print(
        "Dataset and embeddings match."
    )

    # --------------------------------------------------------
    # Create repository
    # --------------------------------------------------------

    repository = (
        IncidentVectorRepository()
    )

    print(
        "\n[4/5] Recreating local ChromaDB..."
    )

    repository.reset()

    # --------------------------------------------------------
    # Insert batches
    # --------------------------------------------------------

    total = len(df)

    print(
        f"Database path:\n"
        f"{CHROMA_STORAGE_PATH}"
    )

    print(
        f"\nInserting {total} incidents..."
    )

    for start in range(
        0,
        total,
        DEFAULT_BATCH_SIZE,
    ):

        end = min(
            start + DEFAULT_BATCH_SIZE,
            total,
        )

        batch = df.iloc[
            start:end
        ]

        batch_embeddings = embeddings[
            start:end
        ]

        ids = [
            str(value)
            for value in batch[
                "incident_id"
            ]
        ]

        documents = [
            str(value)
            for value in batch[
                "incident_description"
            ]
        ]

        metadatas = [
            build_metadata(row)
            for _, row in batch.iterrows()
        ]

        repository.add_records(
            ids=ids,
            documents=documents,
            embeddings=[
                vector.tolist()
                for vector
                in batch_embeddings
            ],
            metadatas=metadatas,
        )

        print(
            f"Inserted {end}/{total}"
        )

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    print(
        "\n[5/5] Verifying database..."
    )

    stored_count = (
        repository.count()
    )

    print(
        f"Expected: {total}"
    )

    print(
        f"Stored:   {stored_count}"
    )

    if stored_count != total:

        raise RuntimeError(
            "ChromaDB verification failed."
        )

    print("\n" + "=" * 70)
    print(
        "LOCAL CHROMADB INGESTION COMPLETE"
    )
    print("=" * 70)

    print(
        f"Records stored: {stored_count}"
    )

    print(
        f"Vector dimension: "
        f"{EMBEDDING_DIMENSION}"
    )

    print(
        f"Storage location:\n"
        f"{CHROMA_STORAGE_PATH}"
    )

    print(
        "\nSTATUS: SUCCESS"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()