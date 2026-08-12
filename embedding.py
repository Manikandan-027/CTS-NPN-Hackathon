"""
Chunking + Tokenization + Embedding pipeline
for the AI Incident RCA & Resolution Intelligence System.

INPUT
-----
data/processed/incidents_processed.csv

The preprocessing stage has already created:
    embedding_text
    incident_id
    category
    severity
    priority
    affected_service
    environment
    ...other processed fields

This script performs:

    Processed CSV
        ↓
    Tokenization
        ↓
    Token-length analysis
        ↓
    Token-aware chunking for long incidents
        ↓
    Sentence Transformer embeddings
        ↓
    Chunk embedding aggregation
        ↓
    L2 normalization
        ↓
    Save embeddings + chunk data + metadata

IMPORTANT
---------
For this project, most incident descriptions are short.
Therefore, chunking is NOT forced on every record.

If an incident fits inside the model's token limit:
    one incident -> one chunk -> one embedding

If it is longer:
    one incident -> multiple overlapping chunks
    -> embed each chunk
    -> weighted mean pooling
    -> one final vector per incident

This preserves ONE VECTOR PER INCIDENT, which is ideal for ChromaDB.

Recommended model:
    sentence-transformers/all-MiniLM-L6-v2

Install:
    pip install pandas numpy torch transformers sentence-transformers tqdm

Run:
    python embedding_pipeline.py

Or:
    python embedding_pipeline.py ^
        --input data/processed/incidents_processed.csv ^
        --output-dir data/embeddings

Outputs:
    data/embeddings/
        incident_embeddings.npy
        incident_ids.csv
        incident_chunks.csv
        token_statistics.csv
        embedding_metadata.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# all-MiniLM-L6-v2 is designed around a 256-token input length.
# We keep a safety margin for special tokens.
DEFAULT_CHUNK_SIZE = 200
DEFAULT_CHUNK_OVERLAP = 40

DEFAULT_BATCH_SIZE = 32

REQUIRED_COLUMNS = [
    "incident_id",
    "embedding_text",
]


# ============================================================
# DATA LOADING / VALIDATION
# ============================================================

def load_dataset(input_path: Path) -> pd.DataFrame:
    """Load and validate the processed RCA dataset."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"Processed dataset was not found:\n{input_path}\n\n"
            "Make sure your preprocessing script created "
            "data/processed/incidents_processed.csv."
        )

    df = pd.read_csv(input_path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing:
        raise ValueError(
            "The processed CSV is missing required columns:\n"
            f"{missing}\n\n"
            "Your preprocessing output must contain at least:\n"
            "incident_id\n"
            "embedding_text"
        )

    if df.empty:
        raise ValueError("The processed dataset is empty.")

    # Incident IDs must be unique because we create one final embedding
    # per historical incident.
    duplicate_ids = int(df["incident_id"].duplicated().sum())

    if duplicate_ids:
        raise ValueError(
            f"Found {duplicate_ids} duplicate incident_id values. "
            "Resolve duplicates before creating embeddings."
        )

    # Do not silently embed missing text.
    missing_text = int(
        df["embedding_text"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    if missing_text:
        raise ValueError(
            f"{missing_text} incidents have empty embedding_text. "
            "Fix the preprocessing stage before embedding."
        )

    df["embedding_text"] = (
        df["embedding_text"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return df


# ============================================================
# TOKENIZER
# ============================================================

def load_tokenizer(model_name: str):
    """
    Load the tokenizer belonging to the embedding model.

    We intentionally use the SAME tokenizer family as the embedding
    model. Do not use a different tokenizer for chunking.
    """

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    return tokenizer


def get_model_token_limit(
    tokenizer,
    model: SentenceTransformer,
) -> int:
    """
    Determine a safe token limit.

    all-MiniLM-L6-v2 normally uses 256 tokens. We use the lower of
    the tokenizer limit and SentenceTransformers model limit when
    both are finite.
    """

    tokenizer_limit = getattr(tokenizer, "model_max_length", 256)

    try:
        st_limit = int(model.max_seq_length)
    except Exception:
        st_limit = 256

    # Hugging Face sometimes represents "unlimited" as a huge integer.
    if tokenizer_limit is None or tokenizer_limit > 10000:
        tokenizer_limit = 256

    if st_limit is None or st_limit > 10000:
        st_limit = 256

    return min(int(tokenizer_limit), int(st_limit))


# ============================================================
# TOKENIZATION
# ============================================================

def count_tokens(
    text: str,
    tokenizer,
) -> int:
    """
    Count tokens WITHOUT adding [CLS]/[SEP] special tokens.

    The count is used for statistics and chunking.
    """

    token_ids = tokenizer.encode(
        text,
        add_special_tokens=False,
        truncation=False,
    )

    return len(token_ids)


def tokenize_text(
    text: str,
    tokenizer,
) -> List[int]:
    """Convert text into token IDs without special tokens."""

    return tokenizer.encode(
        text,
        add_special_tokens=False,
        truncation=False,
    )


# ============================================================
# TOKEN-AWARE CHUNKING
# ============================================================

def chunk_token_ids(
    token_ids: List[int],
    tokenizer,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """
    Split token IDs into overlapping token-aware chunks.

    Example:
        token count = 420
        chunk size = 200
        overlap = 40

        chunk 1: 0:200
        chunk 2: 160:360
        chunk 3: 320:420

    The chunks are decoded back to text before embedding.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0.")

    if overlap < 0:
        raise ValueError("overlap must be >= 0.")

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size."
        )

    if not token_ids:
        return [""]

    if len(token_ids) <= chunk_size:
        return [
            tokenizer.decode(
                token_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            ).strip()
        ]

    chunks: List[str] = []

    start = 0
    step = chunk_size - overlap

    while start < len(token_ids):
        end = min(start + chunk_size, len(token_ids))

        chunk_ids = token_ids[start:end]

        chunk_text = tokenizer.decode(
            chunk_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        ).strip()

        if chunk_text:
            chunks.append(chunk_text)

        if end >= len(token_ids):
            break

        start += step

    return chunks


def create_chunks(
    df: pd.DataFrame,
    tokenizer,
    chunk_size: int,
    overlap: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create token statistics and chunk records.

    Returns:
        token_stats_df
        chunks_df
    """

    token_stats: List[Dict] = []
    chunk_records: List[Dict] = []

    for _, row in tqdm(
        df.iterrows(),
        total=len(df),
        desc="Tokenizing + chunking",
    ):
        incident_id = str(row["incident_id"])
        text = str(row["embedding_text"])

        token_ids = tokenize_text(text, tokenizer)

        token_count = len(token_ids)

        chunks = chunk_token_ids(
            token_ids=token_ids,
            tokenizer=tokenizer,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        token_stats.append(
            {
                "incident_id": incident_id,
                "token_count": token_count,
                "chunk_count": len(chunks),
                "was_chunked": len(chunks) > 1,
            }
        )

        for chunk_index, chunk_text in enumerate(chunks):
            chunk_token_count = count_tokens(
                chunk_text,
                tokenizer,
            )

            chunk_records.append(
                {
                    "incident_id": incident_id,
                    "chunk_index": chunk_index,
                    "chunk_id": (
                        f"{incident_id}_chunk_{chunk_index}"
                    ),
                    "chunk_text": chunk_text,
                    "chunk_token_count": chunk_token_count,
                }
            )

    token_stats_df = pd.DataFrame(token_stats)
    chunks_df = pd.DataFrame(chunk_records)

    return token_stats_df, chunks_df


# ============================================================
# EMBEDDING
# ============================================================

def load_embedding_model(model_name: str) -> SentenceTransformer:
    """Load the Sentence Transformer model."""

    print("\nLoading embedding model...")
    print(f"Model: {model_name}")

    model = SentenceTransformer(model_name)

    print(
        f"Model max sequence length: "
        f"{model.max_seq_length}"
    )

    print(
        f"Embedding dimension: "
        f"{model.get_sentence_embedding_dimension()}"
    )

    return model


def encode_chunks(
    chunks_df: pd.DataFrame,
    model: SentenceTransformer,
    batch_size: int,
) -> np.ndarray:
    """Generate one embedding for every chunk."""

    texts = chunks_df["chunk_text"].tolist()

    print("\nGenerating chunk embeddings...")
    print(f"Total chunks: {len(texts)}")
    print(f"Batch size: {batch_size}")

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    if embeddings.ndim != 2:
        raise ValueError(
            f"Unexpected embedding shape: {embeddings.shape}"
        )

    return embeddings


# ============================================================
# CHUNK EMBEDDING AGGREGATION
# ============================================================

def l2_normalize(vector: np.ndarray) -> np.ndarray:
    """Normalize a vector to unit length."""

    norm = np.linalg.norm(vector)

    if norm == 0:
        return vector.astype(np.float32)

    return (vector / norm).astype(np.float32)


def aggregate_chunk_embeddings(
    df: pd.DataFrame,
    chunks_df: pd.DataFrame,
    chunk_embeddings: np.ndarray,
) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    Convert multiple chunk vectors back into ONE vector per incident.

    Weighted mean pooling:
        chunk embedding × chunk token count

    Then L2 normalize.

    This means:
        8000 incidents -> 8000 final embeddings
    """

    if len(chunks_df) != len(chunk_embeddings):
        raise ValueError(
            "Chunk count and embedding count do not match."
        )

    embedding_dim = chunk_embeddings.shape[1]

    final_embeddings: List[np.ndarray] = []
    incident_rows: List[Dict] = []

    grouped = chunks_df.groupby(
        "incident_id",
        sort=False,
    )

    for incident_id, group in grouped:
        indices = group.index.to_numpy()

        # The chunk dataframe index is reset/kept aligned before this call.
        vectors = chunk_embeddings[indices]

        weights = group[
            "chunk_token_count"
        ].to_numpy(dtype=np.float32)

        # Prevent zero total weight.
        if weights.sum() <= 0:
            weights = np.ones(len(weights), dtype=np.float32)

        weighted_vector = (
            vectors * weights[:, None]
        ).sum(axis=0) / weights.sum()

        final_vector = l2_normalize(weighted_vector)

        final_embeddings.append(final_vector)

        incident_rows.append(
            {
                "incident_id": str(incident_id),
                "chunk_count": int(len(group)),
            }
        )

    final_embeddings_array = np.vstack(
        final_embeddings
    ).astype(np.float32)

    incident_embedding_info = pd.DataFrame(
        incident_rows
    )

    # Verify that every original incident has exactly one vector.
    expected_ids = (
        df["incident_id"]
        .astype(str)
        .tolist()
    )

    actual_ids = (
        incident_embedding_info["incident_id"]
        .astype(str)
        .tolist()
    )

    if set(expected_ids) != set(actual_ids):
        missing = sorted(
            set(expected_ids) - set(actual_ids)
        )
        extra = sorted(
            set(actual_ids) - set(expected_ids)
        )

        raise ValueError(
            "Final embedding incident IDs do not match "
            f"the source dataset.\nMissing: {missing[:10]}"
            f"\nExtra: {extra[:10]}"
        )

    return final_embeddings_array, incident_embedding_info


# ============================================================
# SAVE METADATA
# ============================================================

def build_embedding_metadata(
    df: pd.DataFrame,
    token_stats_df: pd.DataFrame,
    final_embeddings: np.ndarray,
    model_name: str,
    tokenizer,
    chunk_size: int,
    overlap: int,
) -> Dict:

    token_counts = token_stats_df["token_count"]

    metadata = {
        "project": (
            "Evidence-Based AI Incident RCA "
            "& Resolution Intelligence System"
        ),
        "model": model_name,
        "tokenizer": model_name,
        "embedding_dimension": int(
            final_embeddings.shape[1]
        ),
        "incident_count": int(len(df)),
        "final_embedding_count": int(
            len(final_embeddings)
        ),
        "chunk_count": int(
            token_stats_df["chunk_count"].sum()
        ),
        "chunked_incident_count": int(
            token_stats_df["was_chunked"].sum()
        ),
        "unchunked_incident_count": int(
            (~token_stats_df["was_chunked"]).sum()
        ),
        "min_token_count": int(token_counts.min()),
        "max_token_count": int(token_counts.max()),
        "mean_token_count": float(token_counts.mean()),
        "median_token_count": float(
            token_counts.median()
        ),
        "chunk_size": int(chunk_size),
        "chunk_overlap": int(overlap),
        "normalization": "L2",
        "aggregation": (
            "token-count-weighted mean of chunk embeddings"
        ),
        "one_vector_per_incident": True,
        "tokenizer_model_max_length": int(
            getattr(
                tokenizer,
                "model_max_length",
                256,
            )
        ),
    }

    return metadata


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline(
    input_path: Path,
    output_dir: Path,
    model_name: str,
    chunk_size: int,
    overlap: int,
    batch_size: int,
) -> None:

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 72)
    print("RCA TOKENIZATION + CHUNKING + EMBEDDING PIPELINE")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. Load processed dataset
    # --------------------------------------------------------

    print("\n[1/7] Loading processed dataset...")
    df = load_dataset(input_path)

    print(f"Incidents loaded: {len(df):,}")

    # --------------------------------------------------------
    # 2. Load model + tokenizer
    # --------------------------------------------------------

    print("\n[2/7] Loading tokenizer and embedding model...")

    tokenizer = load_tokenizer(model_name)
    model = load_embedding_model(model_name)

    model_limit = get_model_token_limit(
        tokenizer,
        model,
    )

    print(f"Safe model token limit: {model_limit}")

    if chunk_size >= model_limit:
        raise ValueError(
            f"chunk_size={chunk_size} is too large for "
            f"model limit={model_limit}. "
            "Use a smaller value such as 200."
        )

    # --------------------------------------------------------
    # 3. Tokenization + chunking
    # --------------------------------------------------------

    print("\n[3/7] Tokenizing and chunking...")

    token_stats_df, chunks_df = create_chunks(
        df=df,
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    # IMPORTANT:
    # Reset index so chunk dataframe row positions correspond exactly
    # to chunk_embeddings row positions.
    chunks_df = chunks_df.reset_index(drop=True)

    print(
        f"Total chunks generated: "
        f"{len(chunks_df):,}"
    )

    print(
        f"Incidents requiring chunking: "
        f"{int(token_stats_df['was_chunked'].sum()):,}"
    )

    print(
        f"Maximum tokens in an incident: "
        f"{int(token_stats_df['token_count'].max())}"
    )

    # --------------------------------------------------------
    # 4. Save chunk information
    # --------------------------------------------------------

    print("\n[4/7] Saving chunk information...")

    chunks_path = (
        output_dir / "incident_chunks.csv"
    )

    token_stats_path = (
        output_dir / "token_statistics.csv"
    )

    chunks_df.to_csv(
        chunks_path,
        index=False,
    )

    token_stats_df.to_csv(
        token_stats_path,
        index=False,
    )

    # --------------------------------------------------------
    # 5. Generate chunk embeddings
    # --------------------------------------------------------

    print("\n[5/7] Generating embeddings...")

    chunk_embeddings = encode_chunks(
        chunks_df=chunks_df,
        model=model,
        batch_size=batch_size,
    )

    print(
        f"Chunk embedding shape: "
        f"{chunk_embeddings.shape}"
    )

    # --------------------------------------------------------
    # 6. Aggregate chunks -> one vector per incident
    # --------------------------------------------------------

    print(
        "\n[6/7] Aggregating chunk embeddings "
        "into one vector per incident..."
    )

    final_embeddings, embedding_info = (
        aggregate_chunk_embeddings(
            df=df,
            chunks_df=chunks_df,
            chunk_embeddings=chunk_embeddings,
        )
    )

    print(
        f"Final embedding shape: "
        f"{final_embeddings.shape}"
    )

    # --------------------------------------------------------
    # 7. Save final vectors + metadata
    # --------------------------------------------------------

    print("\n[7/7] Saving final embeddings...")

    embeddings_path = (
        output_dir / "incident_embeddings.npy"
    )

    ids_path = (
        output_dir / "incident_ids.csv"
    )

    metadata_path = (
        output_dir / "embedding_metadata.json"
    )

    np.save(
        embeddings_path,
        final_embeddings,
    )

    # Keep IDs in the exact same order as final_embeddings.
    embedding_info.to_csv(
        ids_path,
        index=False,
    )

    metadata = build_embedding_metadata(
        df=df,
        token_stats_df=token_stats_df,
        final_embeddings=final_embeddings,
        model_name=model_name,
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metadata,
            f,
            indent=2,
        )

    # --------------------------------------------------------
    # Final sanity checks
    # --------------------------------------------------------

    loaded_embeddings = np.load(
        embeddings_path
    )

    if loaded_embeddings.shape[0] != len(df):
        raise RuntimeError(
            "Number of final embeddings does not "
            "equal number of incidents."
        )

    if embedding_info["incident_id"].duplicated().any():
        raise RuntimeError(
            "Duplicate incident IDs found in embedding mapping."
        )

    # Check normalization.
    norms = np.linalg.norm(
        loaded_embeddings,
        axis=1,
    )

    if not np.allclose(
        norms,
        1.0,
        atol=1e-4,
    ):
        raise RuntimeError(
            "Some final embeddings are not L2 normalized."
        )

    print("\n" + "=" * 72)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 72)

    print(f"Incidents              : {len(df):,}")
    print(f"Total chunks           : {len(chunks_df):,}")
    print(
        "Chunked incidents      : "
        f"{int(token_stats_df['was_chunked'].sum()):,}"
    )
    print(
        "Max incident tokens    : "
        f"{int(token_stats_df['token_count'].max()):,}"
    )
    print(
        "Embedding dimension    : "
        f"{final_embeddings.shape[1]}"
    )
    print(
        "Final vectors          : "
        f"{final_embeddings.shape[0]:,}"
    )

    print("\nOutput files:")

    print(f"  {embeddings_path}")
    print(f"  {ids_path}")
    print(f"  {chunks_path}")
    print(f"  {token_stats_path}")
    print(f"  {metadata_path}")

    print("\nReady for ChromaDB ingestion.")
    print("=" * 72)


# ============================================================
# COMMAND LINE
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Tokenize, chunk and embed the processed "
            "IT RCA incident dataset."
        )
    )

    parser.add_argument(
        "--input",
        default=(
            "data/processed/"
            "incidents_processed.csv"
        ),
        help="Processed CSV path.",
    )

    parser.add_argument(
        "--output-dir",
        default="data/embeddings",
        help="Directory for embedding outputs.",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Sentence Transformer model.",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Maximum content tokens per chunk.",
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help="Token overlap between consecutive chunks.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Embedding batch size.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    run_pipeline(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        model_name=args.model,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
