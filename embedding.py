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

# all-MiniLM-L6-v2 supports 256 tokens.
# Keep a safety margin.
DEFAULT_CHUNK_SIZE = 200
DEFAULT_CHUNK_OVERLAP = 40
DEFAULT_BATCH_SIZE = 32

REQUIRED_COLUMNS = [
    "incident_id",
    "embedding_text",
]

EXPECTED_RECORDS = 8000
EXPECTED_EMBEDDING_DIMENSION = 384


# ============================================================
# FIELDS USED TO BUILD RICH INCIDENT REPRESENTATION
# ============================================================

CORE_FIELDS = [
    "incident_description",
    "category",
    "severity",
    "priority",
    "affected_service",
    "environment",
    "issue_type",
]


TECHNICAL_SIGNAL_FIELDS = [
    # Application / API / workload
    "feature_observed_cpu_percent",
    "feature_observed_memory_percent",
    "feature_request_latency_ms",
    "feature_error_rate_percent",
    "feature_affected_records_or_requests",
    "feature_incident_duration_minutes",
    "feature_retry_count",
    "feature_records_processed",
    "feature_records_affected",
    "feature_pipeline_delay_minutes",
    "feature_validation_failure_rate_percent",
    "feature_schema_check",
    "feature_normal_workload_multiplier",
    "feature_peak_cpu_percent",
    "feature_peak_memory_percent",
    "feature_queue_depth",

    # Disaster recovery
    "feature_rpo_minutes",
    "feature_rto_minutes",
    "feature_backup_age_hours",
    "feature_recovery_test_status",

    # Network
    "feature_packet_loss_percent",
    "feature_network_latency_ms",
    "feature_bandwidth_utilization_percent",
    "feature_dns_response_ms",

    # Database
    "feature_db_connections",
    "feature_db_cpu_percent",
    "feature_query_latency_ms",
    "feature_lock_waits",
    "feature_replication_lag_seconds",

    # Security
    "feature_suspicious_requests",
    "feature_blocked_requests",
    "feature_authentication_failures",
    "feature_security_event_count",

    # Change / deployment
    "feature_change_event",
    "feature_minutes_after_change",
    "feature_error_rate_before_change_percent",
    "feature_error_rate_after_change_percent",

    # Testing
    "feature_tests_executed",
    "feature_tests_failed",
    "feature_coverage_percent",

    # Observability
    "feature_environment_match",
    "feature_telemetry_events",
    "feature_missing_signal_percent",
    "feature_alert_delay_seconds",
    "feature_metric_collection_status",

    # Infrastructure
    "feature_disk_utilization_percent",
    "feature_pod_restart_count",
    "feature_pending_workloads",
    "feature_node_health",
    "feature_resource_utilization_percent",
]


# ============================================================
# FIELDS THAT MUST NEVER ENTER EMBEDDING TEXT
# ============================================================

FORBIDDEN_EMBEDDING_FIELDS = {
    # Ground-truth / answer fields
    "root_cause",
    "root_cause_clean",
    "root_cause_normalized",

    "resolution",
    "resolution_clean",
    "resolution_normalized",

    "preventive_action",
    "preventive_action_clean",
    "preventive_action_normalized",

    # Identifier must not be used to create artificial uniqueness
    "incident_id",

    # Existing derived embedding field must not recursively enter itself
    "embedding_text",

    # Derived RCA/evidence information may leak target information
    "rca_evidence_features",

    # ChromaDB-specific information
    "chroma_metadata",

    # Dataset metadata / validation fields
    "dataset_features",
    "is_symptom_category",
    "rca_category_valid",

    # Derived temporal metadata
    "timestamp_parsed",
    "incident_date",
    "incident_year",
    "incident_month",
    "incident_week",
    "incident_day_of_week",
    "incident_hour",

    # Existing derived change indicators
    "change_event_present",
    "post_change_incident",
    "minutes_after_change_numeric",
    "error_rate_change_after_change",
}


# ============================================================
# DATA LOADING
# ============================================================

def load_dataset(input_path: Path) -> pd.DataFrame:
    """Load and validate the processed incident dataset."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found:\n{input_path}"
        )

    df = pd.read_csv(input_path)

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    if df.empty:
        raise ValueError(
            "Processed incident dataset is empty."
        )

    duplicate_ids = int(
        df["incident_id"].duplicated().sum()
    )

    if duplicate_ids:
        raise ValueError(
            f"Found {duplicate_ids} duplicate incident_id values."
        )

    if EXPECTED_RECORDS and len(df) != EXPECTED_RECORDS:
        raise ValueError(
            f"Expected {EXPECTED_RECORDS} incidents, "
            f"but found {len(df)}."
        )

    return df


# ============================================================
# SAFE VALUE FORMATTING
# ============================================================

def is_missing(value) -> bool:
    """Return True when a dataframe value is missing."""

    if pd.isna(value):
        return True

    text = str(value).strip()

    return text == "" or text.lower() in {
        "nan",
        "none",
        "null",
        "na",
        "n/a",
    }


def format_field(
    label: str,
    value,
) -> str | None:
    """
    Convert a dataframe field into readable text.

    Missing values are skipped instead of generating
    meaningless text such as 'CPU: nan'.
    """

    if is_missing(value):
        return None

    if isinstance(value, float):
        if np.isnan(value):
            return None

        # Keep useful numerical precision without excessive decimals.
        if value.is_integer():
            value = int(value)
        else:
            value = round(value, 3)

    return f"{label}: {value}"


# ============================================================
# RICH EMBEDDING TEXT
# ============================================================

def build_rich_embedding_text(
    row: pd.Series,
) -> str:
    """
    Build a semantic representation of the INCIDENT itself.

    IMPORTANT:
        Root cause, resolution and preventive action are excluded.

    This representation combines:
        - incident description
        - issue/category context
        - service/environment context
        - observed technical signals
        - change/deployment signals
        - operational metrics

    It does NOT add incident_id to create artificial uniqueness.
    """

    sections: List[str] = []

    # --------------------------------------------------------
    # 1. Core incident context
    # --------------------------------------------------------

    core_lines: List[str] = []

    for column in CORE_FIELDS:
        if column not in row.index:
            continue

        value = format_field(
            column.replace("_", " ").title(),
            row[column],
        )

        if value:
            core_lines.append(value)

    if core_lines:
        sections.append(
            "Incident Context:\n"
            + "\n".join(core_lines)
        )

    # --------------------------------------------------------
    # 2. Technical observations
    # --------------------------------------------------------

    signal_lines: List[str] = []

    for column in TECHNICAL_SIGNAL_FIELDS:
        if column not in row.index:
            continue

        value = format_field(
            column.replace("_", " ").title(),
            row[column],
        )

        if value:
            signal_lines.append(value)

    if signal_lines:
        sections.append(
            "Observed Technical Signals:\n"
            + "\n".join(signal_lines)
        )

    return "\n\n".join(sections).strip()


def build_embedding_texts(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construct rich embedding_text for every incident.

    The existing embedding_text is NOT blindly trusted because
    duplicate/template-heavy text is the current problem.
    """

    print("\nBuilding rich incident representations...")

    texts = []

    for _, row in tqdm(
        df.iterrows(),
        total=len(df),
        desc="Building embedding text",
    ):
        text = build_rich_embedding_text(row)

        if not text:
            raise ValueError(
                f"Incident {row['incident_id']} produced "
                "an empty embedding representation."
            )

        texts.append(text)

    result = df.copy()

    result["embedding_text"] = texts

    return result


# ============================================================
# TOKENIZER
# ============================================================

def load_tokenizer(model_name: str):
    """Load the tokenizer associated with the embedding model."""

    return AutoTokenizer.from_pretrained(
        model_name
    )


def get_model_token_limit(
    tokenizer,
    model: SentenceTransformer,
) -> int:
    """Determine the safe token limit."""

    tokenizer_limit = getattr(
        tokenizer,
        "model_max_length",
        256,
    )

    try:
        model_limit = int(
            model.max_seq_length
        )
    except Exception:
        model_limit = 256

    if tokenizer_limit is None or tokenizer_limit > 10000:
        tokenizer_limit = 256

    if model_limit is None or model_limit > 10000:
        model_limit = 256

    return min(
        int(tokenizer_limit),
        int(model_limit),
    )


# ============================================================
# TOKENIZATION
# ============================================================

def tokenize_text(
    text: str,
    tokenizer,
) -> List[int]:

    return tokenizer.encode(
        text,
        add_special_tokens=False,
        truncation=False,
    )


def count_tokens(
    text: str,
    tokenizer,
) -> int:

    return len(
        tokenize_text(
            text,
            tokenizer,
        )
    )


# ============================================================
# TOKEN-AWARE CHUNKING
# ============================================================

def chunk_token_ids(
    token_ids: List[int],
    tokenizer,
    chunk_size: int,
    overlap: int,
) -> List[str]:
    """
    Split only long incident representations.

    Short incidents remain one incident -> one chunk.
    """

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than zero."
        )

    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative."
        )

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size."
        )

    if not token_ids:
        return []

    if len(token_ids) <= chunk_size:
        text = tokenizer.decode(
            token_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        ).strip()

        return [text] if text else []

    chunks: List[str] = []

    step = chunk_size - overlap
    start = 0

    while start < len(token_ids):

        end = min(
            start + chunk_size,
            len(token_ids),
        )

        chunk_ids = token_ids[
            start:end
        ]

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

    token_statistics = []
    chunk_records = []

    for _, row in tqdm(
        df.iterrows(),
        total=len(df),
        desc="Tokenizing + chunking",
    ):

        incident_id = str(
            row["incident_id"]
        )

        text = str(
            row["embedding_text"]
        )

        token_ids = tokenize_text(
            text,
            tokenizer,
        )

        chunks = chunk_token_ids(
            token_ids=token_ids,
            tokenizer=tokenizer,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        if not chunks:
            raise ValueError(
                f"No chunks generated for {incident_id}."
            )

        token_statistics.append(
            {
                "incident_id": incident_id,
                "token_count": len(token_ids),
                "chunk_count": len(chunks),
                "was_chunked": len(chunks) > 1,
            }
        )

        for chunk_index, chunk_text in enumerate(
            chunks
        ):

            chunk_records.append(
                {
                    "incident_id": incident_id,
                    "chunk_index": chunk_index,
                    "chunk_id": (
                        f"{incident_id}_"
                        f"chunk_{chunk_index}"
                    ),
                    "chunk_text": chunk_text,
                    "chunk_token_count": count_tokens(
                        chunk_text,
                        tokenizer,
                    ),
                }
            )

    token_stats_df = pd.DataFrame(
        token_statistics
    )

    chunks_df = pd.DataFrame(
        chunk_records
    )

    return (
        token_stats_df,
        chunks_df.reset_index(drop=True),
    )


# ============================================================
# EMBEDDING MODEL
# ============================================================

def load_embedding_model(
    model_name: str,
) -> SentenceTransformer:

    print("\nLoading embedding model:")
    print(model_name)

    model = SentenceTransformer(
        model_name
    )

    dimension = (
        model.get_sentence_embedding_dimension()
    )

    print(
        f"Embedding dimension: {dimension}"
    )

    if dimension != EXPECTED_EMBEDDING_DIMENSION:
        raise ValueError(
            f"Expected embedding dimension "
            f"{EXPECTED_EMBEDDING_DIMENSION}, "
            f"but model produced {dimension}."
        )

    return model


# ============================================================
# CHUNK EMBEDDINGS
# ============================================================

def encode_chunks(
    chunks_df: pd.DataFrame,
    model: SentenceTransformer,
    batch_size: int,
) -> np.ndarray:

    texts = (
        chunks_df["chunk_text"]
        .tolist()
    )

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    if embeddings.ndim != 2:
        raise ValueError(
            f"Invalid embedding shape: "
            f"{embeddings.shape}"
        )

    if not np.isfinite(
        embeddings
    ).all():

        raise ValueError(
            "Chunk embeddings contain "
            "NaN or infinite values."
        )

    return embeddings


# ============================================================
# L2 NORMALIZATION
# ============================================================

def l2_normalize(
    vector: np.ndarray,
) -> np.ndarray:

    norm = np.linalg.norm(
        vector
    )

    if norm == 0:
        raise ValueError(
            "Cannot normalize a zero vector."
        )

    return (
        vector / norm
    ).astype(np.float32)


# ============================================================
# AGGREGATION
# ============================================================

def aggregate_chunk_embeddings(
    df: pd.DataFrame,
    chunks_df: pd.DataFrame,
    chunk_embeddings: np.ndarray,
) -> Tuple[np.ndarray, pd.DataFrame]:

    if len(chunks_df) != len(
        chunk_embeddings
    ):
        raise ValueError(
            "Chunk count and embedding count "
            "do not match."
        )

    embedding_by_incident = {}

    for incident_id, group in chunks_df.groupby(
        "incident_id",
        sort=False,
    ):

        indices = group.index.to_numpy()

        vectors = chunk_embeddings[
            indices
        ]

        weights = group[
            "chunk_token_count"
        ].to_numpy(
            dtype=np.float32
        )

        if weights.sum() <= 0:
            weights = np.ones(
                len(weights),
                dtype=np.float32,
            )

        weighted_mean = (
            vectors * weights[:, None]
        ).sum(axis=0) / weights.sum()

        final_vector = l2_normalize(
            weighted_mean
        )

        embedding_by_incident[
            str(incident_id)
        ] = final_vector

    # --------------------------------------------------------
    # IMPORTANT:
    # Preserve EXACT original CSV incident order.
    # --------------------------------------------------------

    final_embeddings = []

    embedding_rows = []

    for incident_id in (
        df["incident_id"]
        .astype(str)
        .tolist()
    ):

        if incident_id not in (
            embedding_by_incident
        ):
            raise ValueError(
                f"Missing final embedding "
                f"for {incident_id}."
            )

        final_embeddings.append(
            embedding_by_incident[
                incident_id
            ]
        )

        chunk_count = int(
            chunks_df[
                chunks_df["incident_id"]
                .astype(str)
                == incident_id
            ].shape[0]
        )

        embedding_rows.append(
            {
                "incident_id": incident_id,
                "chunk_count": chunk_count,
            }
        )

    final_embeddings = np.vstack(
        final_embeddings
    ).astype(np.float32)

    embedding_info = pd.DataFrame(
        embedding_rows
    )

    return (
        final_embeddings,
        embedding_info,
    )


# ============================================================
# DIVERSITY ANALYSIS
# ============================================================

def calculate_diversity(
    embedding_texts: List[str],
    embeddings: np.ndarray,
) -> Dict:

    unique_texts = len(
        set(embedding_texts)
    )

    duplicate_texts = (
        len(embedding_texts)
        - unique_texts
    )

    unique_vectors = np.unique(
        embeddings,
        axis=0,
    ).shape[0]

    duplicate_vectors = (
        len(embeddings)
        - unique_vectors
    )

    return {
        "total_incidents": int(
            len(embedding_texts)
        ),
        "unique_embedding_texts": int(
            unique_texts
        ),
        "duplicate_embedding_texts": int(
            duplicate_texts
        ),
        "text_uniqueness_percent": round(
            100 * unique_texts / len(
                embedding_texts
            ),
            2,
        ),
        "unique_embeddings": int(
            unique_vectors
        ),
        "duplicate_embeddings": int(
            duplicate_vectors
        ),
        "embedding_uniqueness_percent": round(
            100 * unique_vectors / len(
                embeddings
            ),
            2,
        ),
    }


# ============================================================
# METADATA
# ============================================================

def build_metadata(
    df: pd.DataFrame,
    token_stats_df: pd.DataFrame,
    embeddings: np.ndarray,
    diversity: Dict,
    model_name: str,
    chunk_size: int,
    overlap: int,
) -> Dict:

    token_counts = (
        token_stats_df["token_count"]
    )

    return {
        "project": (
            "Evidence-Based AI Incident RCA "
            "& Resolution Intelligence System"
        ),
        "model": model_name,
        "embedding_dimension": int(
            embeddings.shape[1]
        ),
        "incident_count": int(
            len(df)
        ),
        "final_embedding_count": int(
            len(embeddings)
        ),
        "chunk_count": int(
            token_stats_df[
                "chunk_count"
            ].sum()
        ),
        "chunked_incident_count": int(
            token_stats_df[
                "was_chunked"
            ].sum()
        ),
        "chunk_size": int(
            chunk_size
        ),
        "chunk_overlap": int(
            overlap
        ),
        "normalization": "L2",
        "aggregation": (
            "token-count-weighted "
            "mean pooling"
        ),
        "one_vector_per_incident": True,
        "embedding_input_policy": (
            "Incident description, categorical "
            "context and observed technical signals"
        ),
        "label_leakage_protection": [
            "root_cause",
            "resolution",
            "preventive_action",
        ],
        "diversity": diversity,
        "min_token_count": int(
            token_counts.min()
        ),
        "max_token_count": int(
            token_counts.max()
        ),
        "mean_token_count": float(
            token_counts.mean()
        ),
        "median_token_count": float(
            token_counts.median()
        ),
    }


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
    print(
        "AI INCIDENT RCA - "
        "SEMANTIC EMBEDDING PIPELINE"
    )
    print("=" * 72)

    # --------------------------------------------------------
    # 1. Load dataset
    # --------------------------------------------------------

    print("\n[1/7] Loading dataset...")

    df = load_dataset(
        input_path
    )

    print(
        f"Incidents loaded: {len(df):,}"
    )

    # --------------------------------------------------------
    # 2. Build rich embedding representation
    # --------------------------------------------------------

    print(
        "\n[2/7] Building rich "
        "incident representations..."
    )

    original_texts = (
        df["embedding_text"]
        .fillna("")
        .astype(str)
        .str.strip()
        .tolist()
    )

    original_unique = len(
        set(original_texts)
    )

    print(
        f"Original unique embedding_text: "
        f"{original_unique:,}"
    )

    df = build_embedding_texts(
        df
    )

    new_texts = (
        df["embedding_text"]
        .astype(str)
        .str.strip()
        .tolist()
    )

    new_unique = len(
        set(new_texts)
    )

    print(
        f"New unique embedding_text: "
        f"{new_unique:,}"
    )

    print(
        f"New duplicate embedding_text: "
        f"{len(new_texts) - new_unique:,}"
    )

    # --------------------------------------------------------
    # 3. Load tokenizer + model
    # --------------------------------------------------------

    print(
        "\n[3/7] Loading tokenizer "
        "and embedding model..."
    )

    tokenizer = load_tokenizer(
        model_name
    )

    model = load_embedding_model(
        model_name
    )

    model_limit = get_model_token_limit(
        tokenizer,
        model,
    )

    print(
        f"Safe token limit: "
        f"{model_limit}"
    )

    if chunk_size >= model_limit:
        raise ValueError(
            f"chunk_size={chunk_size} must be "
            f"less than model limit={model_limit}."
        )

    # --------------------------------------------------------
    # 4. Tokenization + optional chunking
    # --------------------------------------------------------

    print(
        "\n[4/7] Tokenizing and "
        "chunking long incidents..."
    )

    token_stats_df, chunks_df = (
        create_chunks(
            df=df,
            tokenizer=tokenizer,
            chunk_size=chunk_size,
            overlap=overlap,
        )
    )

    print(
        f"Total chunks: "
        f"{len(chunks_df):,}"
    )

    print(
        f"Incidents chunked: "
        f"{int(token_stats_df['was_chunked'].sum()):,}"
    )

    # --------------------------------------------------------
    # 5. Generate chunk embeddings
    # --------------------------------------------------------

    print(
        "\n[5/7] Generating "
        "Sentence Transformer embeddings..."
    )

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
    # 6. Aggregate to one vector per incident
    # --------------------------------------------------------

    print(
        "\n[6/7] Creating one final "
        "vector per incident..."
    )

    final_embeddings, embedding_info = (
        aggregate_chunk_embeddings(
            df=df,
            chunks_df=chunks_df,
            chunk_embeddings=chunk_embeddings,
        )
    )

    if final_embeddings.shape != (
        len(df),
        EXPECTED_EMBEDDING_DIMENSION,
    ):
        raise RuntimeError(
            f"Unexpected final embedding shape: "
            f"{final_embeddings.shape}"
        )

    # --------------------------------------------------------
    # 7. Diversity + save
    # --------------------------------------------------------

    print(
        "\n[7/7] Validating and "
        "saving embeddings..."
    )

    diversity = calculate_diversity(
        embedding_texts=new_texts,
        embeddings=final_embeddings,
    )

    embeddings_path = (
        output_dir
        / "incident_embeddings.npy"
    )

    ids_path = (
        output_dir
        / "incident_ids.csv"
    )

    chunks_path = (
        output_dir
        / "incident_chunks.csv"
    )

    token_stats_path = (
        output_dir
        / "token_statistics.csv"
    )

    metadata_path = (
        output_dir
        / "embedding_metadata.json"
    )

    # Save vectors
    np.save(
        embeddings_path,
        final_embeddings,
    )

    # Save IDs in EXACT vector order
    embedding_info.to_csv(
        ids_path,
        index=False,
    )

    # Save chunk information
    chunks_df.to_csv(
        chunks_path,
        index=False,
    )

    token_stats_df.to_csv(
        token_stats_path,
        index=False,
    )

    metadata = build_metadata(
        df=df,
        token_stats_df=token_stats_df,
        embeddings=final_embeddings,
        diversity=diversity,
        model_name=model_name,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
        )

    # --------------------------------------------------------
    # Final numerical validation
    # --------------------------------------------------------

    if not np.isfinite(
        final_embeddings
    ).all():

        raise RuntimeError(
            "Final embeddings contain "
            "NaN or infinite values."
        )

    norms = np.linalg.norm(
        final_embeddings,
        axis=1,
    )

    if not np.allclose(
        norms,
        1.0,
        atol=1e-4,
    ):

        raise RuntimeError(
            "Final embeddings are not "
            "properly L2 normalized."
        )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print("\n" + "=" * 72)
    print("EMBEDDING PIPELINE COMPLETE")
    print("=" * 72)

    print(
        f"Total incidents           : "
        f"{len(df):,}"
    )

    print(
        f"Original unique texts     : "
        f"{original_unique:,}"
    )

    print(
        f"New unique texts          : "
        f"{diversity['unique_embedding_texts']:,}"
    )

    print(
        f"New duplicate texts       : "
        f"{diversity['duplicate_embedding_texts']:,}"
    )

    print(
        f"Unique final embeddings   : "
        f"{diversity['unique_embeddings']:,}"
    )

    print(
        f"Duplicate final embeddings: "
        f"{diversity['duplicate_embeddings']:,}"
    )

    print(
        f"Final vector shape        : "
        f"{final_embeddings.shape}"
    )

    print(
        "\nOutputs:"
    )

    print(
        f"  {embeddings_path}"
    )

    print(
        f"  {ids_path}"
    )

    print(
        f"  {chunks_path}"
    )

    print(
        f"  {token_stats_path}"
    )

    print(
        f"  {metadata_path}"
    )

    print("=" * 72)


# ============================================================
# CLI
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Generate semantic embeddings "
            "for the AI Incident RCA system."
        )
    )

    parser.add_argument(
        "--input",
        default=(
            "data/processed/"
            "incidents_processed.csv"
        ),
    )

    parser.add_argument(
        "--output-dir",
        default="data/embeddings",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
    )

    return parser.parse_args()


def main():

    args = parse_args()

    run_pipeline(
        input_path=Path(
            args.input
        ),
        output_dir=Path(
            args.output_dir
        ),
        model_name=args.model,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()