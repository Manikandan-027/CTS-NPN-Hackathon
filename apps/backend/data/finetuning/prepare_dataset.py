"""
Prepare RAG-aware supervised fine-tuning datasets for Qwen3-8B.

IMPORTANT:
    This script NEVER modifies the original processed dataset.
    It also does NOT modify ChromaDB or the existing RCA implementation.

Pipeline:

    Original JSONL
        |
        v
    Scenario grouping
        |
        v
    Group-level stratified split
        |
        v
    Existing project retrieval
        |
        v
    Leakage filtering
        |
        v
    Qwen SFT JSONL
        |
        +--> train.jsonl
        +--> validation.jsonl
        +--> test.jsonl
        +--> dataset_statistics.json
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from backend.core.hybrid_retrieval.reranker import (
    rerank_incidents,
)
from backend.core.pipeline.incident_pipeline import (
    _extract_query_metadata,
)
from backend.core.retrieval.semantic_retrieval import (
    retrieve_similar_incidents,
)

# ============================================================================
# PATHS
# ============================================================================

# Repository root:
#   cts-npn-hackathon/
#
# This file:
#   apps/backend/data/finetuning/prepare_dataset.py

FILE_PATH = Path(__file__).resolve()
FINETUNING_DIR = FILE_PATH.parent
BACKEND_DIR = FINETUNING_DIR.parent.parent
APPS_DIR = BACKEND_DIR.parent
PROJECT_ROOT = APPS_DIR.parent

ORIGINAL_DATASET = (
    BACKEND_DIR / "data" / "processed" / "processed_incidents.jsonl"
)

OUTPUT_DIR = FINETUNING_DIR

TRAIN_FILE = OUTPUT_DIR / "train.jsonl"
VALIDATION_FILE = OUTPUT_DIR / "validation.jsonl"
TEST_FILE = OUTPUT_DIR / "test.jsonl"
STATISTICS_FILE = OUTPUT_DIR / "dataset_statistics.json"


# ============================================================================
# CONFIGURATION
# ============================================================================

SEED = 42

TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
TEST_RATIO = 0.15

# Existing RAG is Top-20.
#
# We request more candidates where the existing retrieval API allows it,
# because some candidates may later be removed because they belong to:
#   - target incident
#   - same scenario group
#   - wrong split pool
#
# We still only expose the final Top-5 to Qwen.
FINAL_EVIDENCE_COUNT = 5

MIN_FINAL_EVIDENCE = 1

# If False, examples for which no valid RAG evidence exists are skipped.
#
# For the first dataset version, this is safer than manufacturing evidence.
SKIP_WITHOUT_EVIDENCE = True

# Maximum number of examples to process.
# None = process everything.
MAX_EXAMPLES: int | None = None


# ============================================================================
# REQUIRED DATASET FIELDS
# ============================================================================

INPUT_FIELDS = [
    "incident_description",
    "category",
    "severity",
    "priority",
    "affected_service",
    "environment",
    "dataset_features",
]

TARGET_FIELDS = [
    "root_cause",
    "resolution",
    "preventive_action",
]

ALL_REQUIRED_FIELDS = [
    "incident_id",
    *INPUT_FIELDS,
    *TARGET_FIELDS,
]


# ============================================================================
# QWEN SYSTEM INSTRUCTION
# ============================================================================

SYSTEM_PROMPT = """You are the project-specific AI Incident Root Cause Analysis assistant.

Your task is to analyze the current incident using ONLY:
1. the current incident information, and
2. the supplied historical incident evidence.

Do not use external knowledge for the RCA.

Do not invent:
- root causes
- resolutions
- preventive actions
- evidence

Only make claims supported by the current incident and supplied historical evidence.

If the supplied evidence is insufficient to determine a reliable RCA, say that the evidence is insufficient rather than guessing.

Return the result as valid JSON with exactly these fields:

{
  "root_cause": "...",
  "evidence": ["INCxxxxx", "INCxxxxx"],
  "resolution": "...",
  "prevention": "..."
}

The evidence field must contain incident IDs from the supplied historical evidence.
"""


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def normalize_value(value: Any) -> str:
    """
    Convert arbitrary JSON values into a stable string representation.

    dataset_features can sometimes be represented as a dictionary/list/string,
    so JSON serialization is used where appropriate.
    """
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    return str(value).strip()


def canonical_record_value(record: dict[str, Any], field: str) -> str:
    return normalize_value(record.get(field))


def scenario_key(record: dict[str, Any]) -> str:
    """
    Build the leakage-control scenario identity.

    The complete incident input is the primary scenario identity.

    Target fields are included as well so that if future data versions contain
    identical inputs with different outputs, they will not accidentally be
    treated as the same supervised scenario.
    """
    values = {
        field: canonical_record_value(record, field)
        for field in [*INPUT_FIELDS, *TARGET_FIELDS]
    }

    serialized = json.dumps(
        values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def input_scenario_key(record: dict[str, Any]) -> str:
    """
    Input-only scenario identity.

    This is additionally stored for diagnostics and retrieval filtering.
    """
    values = {
        field: canonical_record_value(record, field)
        for field in INPUT_FIELDS
    }

    serialized = json.dumps(
        values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def stable_json_dump(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
                + "\n"
            )


# ============================================================================
# DATASET LOADING
# ============================================================================


def load_original_dataset() -> list[dict[str, Any]]:
    """
    Read the original dataset without modifying it.
    """
    if not ORIGINAL_DATASET.exists():
        raise FileNotFoundError(
            f"Original dataset not found:\n{ORIGINAL_DATASET}"
        )

    records: list[dict[str, Any]] = []

    with ORIGINAL_DATASET.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at line {line_number}: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Line {line_number} is not a JSON object."
                )

            missing = [
                field
                for field in ALL_REQUIRED_FIELDS
                if field not in record
            ]

            if missing:
                raise ValueError(
                    f"Missing fields at line {line_number}: {missing}"
                )

            records.append(record)

    if not records:
        raise ValueError("Original dataset is empty.")

    return records


# ============================================================================
# SCENARIO GROUPING
# ============================================================================


def build_groups(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Group all copies of the same scenario together.
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in records:
        key = scenario_key(record)

        enriched = dict(record)
        enriched["_scenario_group"] = key
        enriched["_input_scenario_group"] = input_scenario_key(record)

        groups[key].append(enriched)

    return dict(groups)


# ============================================================================
# ROOT-CAUSE GROUP INDEX
# ============================================================================


def build_root_cause_group_index(
    groups: dict[str, list[dict[str, Any]]],
) -> dict[str, list[str]]:
    """
    Map root cause -> scenario groups.

    Every scenario group is expected to have one root cause.
    """
    result: dict[str, list[str]] = defaultdict(list)

    for group_id, rows in groups.items():
        root_causes = {
            canonical_record_value(row, "root_cause")
            for row in rows
        }

        if len(root_causes) != 1:
            raise ValueError(
                "A scenario group contains multiple root causes.\n"
                f"Group: {group_id}\n"
                f"Root causes: {sorted(root_causes)}"
            )

        root_cause = next(iter(root_causes))
        result[root_cause].append(group_id)

    return dict(result)


# ============================================================================
# GROUP-LEVEL STRATIFIED SPLIT
# ============================================================================


def allocate_groups_for_root_cause(
    group_ids: list[str],
    groups: dict[str, list[dict[str, Any]]],
    rng: random.Random,
) -> tuple[list[str], list[str], list[str]]:
    """
    Allocate groups belonging to one root cause.

    Important:
        A group is never split.

    Strategy:
        1 group:
            train

        2 groups:
            train + test

        >=3 groups:
            at least one group goes into each split.

    Remaining groups are assigned using approximate row-count targets.
    """

    shuffled = list(group_ids)
    rng.shuffle(shuffled)

    if len(shuffled) == 1:
        return shuffled, [], []

    if len(shuffled) == 2:
        return [shuffled[0]], [], [shuffled[1]]

    # Start with one group in every split.
    train = [shuffled[0]]
    validation = [shuffled[1]]
    test = [shuffled[2]]

    remaining = shuffled[3:]

    total_rows = sum(len(groups[group_id]) for group_id in shuffled)

    train_target = total_rows * TRAIN_RATIO
    validation_target = total_rows * VALIDATION_RATIO
    test_target = total_rows * TEST_RATIO

    current_rows = {
        "train": len(groups[train[0]]),
        "validation": len(groups[validation[0]]),
        "test": len(groups[test[0]]),
    }

    targets = {
        "train": train_target,
        "validation": validation_target,
        "test": test_target,
    }

    # Larger groups first because their placement matters more.
    remaining.sort(
        key=lambda group_id: len(groups[group_id]),
        reverse=True,
    )

    for group_id in remaining:
        group_size = len(groups[group_id])

        deficits = {
            split: targets[split] - current_rows[split]
            for split in ("train", "validation", "test")
        }

        selected_split = max(
            deficits,
            key=deficits.get,
        )

        if selected_split == "train":
            train.append(group_id)
        elif selected_split == "validation":
            validation.append(group_id)
        else:
            test.append(group_id)

        current_rows[selected_split] += group_size

    return train, validation, test


def create_group_split(
    groups: dict[str, list[dict[str, Any]]],
    seed: int = SEED,
) -> dict[str, str]:
    """
    Create:

        scenario_group_id -> train/validation/test

    with root-cause-aware group allocation.
    """
    rng = random.Random(seed)

    root_cause_groups = build_root_cause_group_index(groups)

    split_by_group: dict[str, str] = {}

    root_causes = list(root_cause_groups.keys())
    rng.shuffle(root_causes)

    for root_cause in root_causes:
        train_groups, validation_groups, test_groups = (
            allocate_groups_for_root_cause(
                root_cause_groups[root_cause],
                groups,
                rng,
            )
        )

        for group_id in train_groups:
            split_by_group[group_id] = "train"

        for group_id in validation_groups:
            split_by_group[group_id] = "validation"

        for group_id in test_groups:
            split_by_group[group_id] = "test"

    expected = set(groups.keys())
    actual = set(split_by_group.keys())

    if expected != actual:
        missing = expected - actual
        extra = actual - expected

        raise RuntimeError(
            "Group split is incomplete.\n"
            f"Missing groups: {len(missing)}\n"
            f"Extra groups: {len(extra)}"
        )

    return split_by_group


def assign_records_to_splits(
    records: list[dict[str, Any]],
    split_by_group: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    result = {
        "train": [],
        "validation": [],
        "test": [],
    }

    for record in records:
        group_id = scenario_key(record)

        split = split_by_group[group_id]

        enriched = dict(record)
        enriched["_scenario_group"] = group_id
        enriched["_input_scenario_group"] = input_scenario_key(record)
        enriched["_split"] = split

        result[split].append(enriched)

    return result


# ============================================================================
# EXISTING RETRIEVAL ADAPTER
# ============================================================================


def import_existing_retrieval():
    """
    Locate the existing project retrieval implementation.

    We intentionally do NOT implement a second retrieval system here.

    Candidate modules/functions cover common names used in the project.
    """

    candidate_modules = [
        "backend.core.retrieval.semantic_retrieval",
        "backend.core.retrieval.hybrid_retrieval",
        "backend.core.retrieval.retrieval",
        "backend.core.retrieval",
    ]

    candidate_functions = [
        "retrieve_similar_incidents",
        "hybrid_retrieve",
        "retrieve_incidents",
        "retrieve_similar",
    ]

    for module_name in candidate_modules:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue

        for function_name in candidate_functions:
            function = getattr(module, function_name, None)

            if callable(function):
                print(
                    f"[RETRIEVAL] Using "
                    f"{module_name}.{function_name}"
                )
                return function

    raise ImportError(
        "Could not locate the existing project retrieval function.\n\n"
        "Expected one of:\n"
        + "\n".join(
            f"  - {module}.{function}"
            for module in candidate_modules
            for function in candidate_functions
        )
        + "\n\n"
        "Do NOT create a new retrieval implementation. "
        "Update this adapter only after checking the existing project "
        "retrieval module/function name."
    )


def build_incident_query(record: dict[str, Any]) -> str:
    """
    Construct the query passed to the existing retrieval pipeline.
    """
    parts = [
        f"Incident Description: {record['incident_description']}",
        f"Category: {record['category']}",
        f"Severity: {record['severity']}",
        f"Priority: {record['priority']}",
        f"Affected Service: {record['affected_service']}",
        f"Environment: {record['environment']}",
        f"Dataset Features: {record['dataset_features']}",
    ]

    return "\n".join(parts)


def _find_parameter(
    parameters: dict[str, inspect.Parameter],
    names: list[str],
) -> str | None:
    for name in names:
        if name in parameters:
            return name

    return None


def call_existing_retrieval(
    retrieval_function,
    record: dict[str, Any],
    candidate_k: int,
):
    """
    Adapt to the existing retrieval function without changing it.

    Supported common signatures include:

        retrieve_similar_incidents(query)
        retrieve_similar_incidents(query, top_k=20)
        retrieve_similar_incidents(incident_description, top_k=20)
        retrieve_similar_incidents(incident=record, top_k=20)

    The function signature is inspected before calling.
    """

    signature = inspect.signature(retrieval_function)
    parameters = dict(signature.parameters)

    kwargs: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # top-k parameter
    # ------------------------------------------------------------------

    top_k_name = _find_parameter(
        parameters,
        [
            "top_k",
            "k",
            "n_results",
            "limit",
            "num_results",
        ],
    )

    if top_k_name:
        kwargs[top_k_name] = candidate_k

    # ------------------------------------------------------------------
    # Query/incident parameter
    # ------------------------------------------------------------------

    incident_parameter = _find_parameter(
        parameters,
        [
            "incident",
            "incident_data",
            "incident_record",
            "record",
            "payload",
        ],
    )

    if incident_parameter:
        kwargs[incident_parameter] = record

        try:
            return retrieval_function(**kwargs)
        except TypeError:
            pass

    query_parameter = _find_parameter(
        parameters,
        [
            "query",
            "query_text",
            "text",
            "incident_description",
            "description",
            "input_text",
        ],
    )

    query = build_incident_query(record)

    if query_parameter:
        kwargs[query_parameter] = query

        try:
            return retrieval_function(**kwargs)
        except TypeError:
            # Try only the raw incident description if the project expects it.
            kwargs[query_parameter] = record["incident_description"]
            return retrieval_function(**kwargs)

    # ------------------------------------------------------------------
    # Fallback for simple positional APIs.
    # ------------------------------------------------------------------

    positional_parameters = [
        p
        for p in parameters.values()
        if p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]

    if positional_parameters:
        first_parameter = positional_parameters[0]

        positional_name = first_parameter.name.lower()

        if "incident" in positional_name or "record" in positional_name:
            if top_k_name:
                return retrieval_function(record, candidate_k)
            return retrieval_function(record)

        if top_k_name:
            return retrieval_function(query, candidate_k)

        return retrieval_function(query)

    raise TypeError(
        f"Could not determine how to call retrieval function: "
        f"{retrieval_function}"
    )


# ============================================================================
# RETRIEVAL RESULT NORMALIZATION
# ============================================================================


def first_non_empty(
    mapping: dict[str, Any],
    keys: list[str],
    default: Any = None,
):
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]

    return default


def normalize_retrieval_results(raw_results: Any) -> list[dict[str, Any]]:
    """
    Convert common retrieval result structures into:

        {
            "incident_id": ...,
            "description": ...,
            "service": ...,
            "category": ...,
            "severity": ...,
            "root_cause": ...,
            "resolution": ...,
            "preventive_action": ...,
            "score": ...
        }

    No assumptions are made about the exact existing return type beyond
    common Python structures.
    """

    if raw_results is None:
        return []

    # Some retrieval functions return:
    #
    # {
    #     "results": [...]
    # }
    #
    if isinstance(raw_results, dict):
        for key in (
            "results",
            "incidents",
            "documents",
            "matches",
            "retrieved",
            "data",
        ):
            value = raw_results.get(key)

            if isinstance(value, list):
                raw_results = value
                break

    # Chroma-style nested output:
    #
    # {
    #   "ids": [[...]],
    #   "documents": [[...]],
    #   "metadatas": [[...]],
    #   "distances": [[...]]
    # }
    if isinstance(raw_results, dict) and "ids" in raw_results:
        ids = raw_results.get("ids", [[]])
        documents = raw_results.get("documents", [[]])
        metadatas = raw_results.get("metadatas", [[]])
        distances = raw_results.get("distances", [[]])

        ids = ids[0] if ids and isinstance(ids[0], list) else ids
        documents = (
            documents[0]
            if documents and isinstance(documents[0], list)
            else documents
        )
        metadatas = (
            metadatas[0]
            if metadatas and isinstance(metadatas[0], list)
            else metadatas
        )
        distances = (
            distances[0]
            if distances and isinstance(distances[0], list)
            else distances
        )

        normalized = []

        for index, incident_id in enumerate(ids):
            metadata = (
                metadatas[index]
                if index < len(metadatas)
                and isinstance(metadatas[index], dict)
                else {}
            )

            document = (
                documents[index]
                if index < len(documents)
                else ""
            )

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            item = {
                "incident_id": first_non_empty(
                    metadata,
                    ["incident_id", "id"],
                    incident_id,
                ),
                "description": first_non_empty(
                    metadata,
                    [
                        "incident_description",
                        "description",
                    ],
                    document,
                ),
                "service": first_non_empty(
                    metadata,
                    [
                        "affected_service",
                        "service",
                    ],
                    "",
                ),
                "category": first_non_empty(
                    metadata,
                    ["category"],
                    "",
                ),
                "severity": first_non_empty(
                    metadata,
                    ["severity"],
                    "",
                ),
                "root_cause": first_non_empty(
                    metadata,
                    ["root_cause"],
                    "",
                ),
                "resolution": first_non_empty(
                    metadata,
                    ["resolution"],
                    "",
                ),
                "preventive_action": first_non_empty(
                    metadata,
                    [
                        "preventive_action",
                        "prevention",
                    ],
                    "",
                ),
                "score": distance,
                "_metadata": metadata,
            }

            normalized.append(item)

        return normalized

    if not isinstance(raw_results, list):
        return []

    normalized = []

    for item in raw_results:
        if isinstance(item, dict):
            incident_id = first_non_empty(
                item,
                [
                    "incident_id",
                    "id",
                    "document_id",
                ],
            )

            metadata = item.get("metadata", {})

            if not isinstance(metadata, dict):
                metadata = {}

            incident_id = (
                incident_id
                or first_non_empty(
                    metadata,
                    ["incident_id", "id"],
                )
            )

            normalized.append(
                {
                    "incident_id": incident_id,
                    "description": first_non_empty(
                        item,
                        [
                            "incident_description",
                            "description",
                            "document",
                            "text",
                        ],
                        first_non_empty(
                            metadata,
                            [
                                "incident_description",
                                "description",
                            ],
                            "",
                        ),
                    ),
                    "service": first_non_empty(
                        item,
                        [
                            "affected_service",
                            "service",
                        ],
                        first_non_empty(
                            metadata,
                            [
                                "affected_service",
                                "service",
                            ],
                            "",
                        ),
                    ),
                    "category": first_non_empty(
                        item,
                        ["category"],
                        first_non_empty(
                            metadata,
                            ["category"],
                            "",
                        ),
                    ),
                    "severity": first_non_empty(
                        item,
                        ["severity"],
                        first_non_empty(
                            metadata,
                            ["severity"],
                            "",
                        ),
                    ),
                    "root_cause": first_non_empty(
                        item,
                        ["root_cause"],
                        first_non_empty(
                            metadata,
                            ["root_cause"],
                            "",
                        ),
                    ),
                    "resolution": first_non_empty(
                        item,
                        ["resolution"],
                        first_non_empty(
                            metadata,
                            ["resolution"],
                            "",
                        ),
                    ),
                    "preventive_action": first_non_empty(
                        item,
                        [
                            "preventive_action",
                            "prevention",
                        ],
                        first_non_empty(
                            metadata,
                            [
                                "preventive_action",
                                "prevention",
                            ],
                            "",
                        ),
                    ),
                    "score": first_non_empty(
                        item,
                        [
                            "score",
                            "similarity",
                            "distance",
                            "rerank_score",
                        ],
                    ),
                    "_metadata": metadata,
                }
            )

        elif isinstance(item, (tuple, list)):
            if not item:
                continue

            incident_id = item[0]

            normalized.append(
                {
                    "incident_id": incident_id,
                    "description": (
                        item[1]
                        if len(item) > 1
                        else ""
                    ),
                    "service": "",
                    "category": "",
                    "severity": "",
                    "root_cause": "",
                    "resolution": "",
                    "preventive_action": "",
                    "score": (
                        item[2]
                        if len(item) > 2
                        else None
                    ),
                    "_metadata": {},
                }
            )

    return normalized


# ============================================================================
# RETRIEVAL POOL
# ============================================================================


def build_allowed_incident_ids(
    split_records: dict[str, list[dict[str, Any]]],
    target_split: str,
) -> set[str]:
    """
    Determine which historical incidents are allowed as evidence.

    Train:
        train only

    Validation:
        train only

    Test:
        train + validation

    This gives strict evaluation isolation.
    """

    if target_split == "train":
        allowed_splits = {"train"}

    elif target_split == "validation":
        allowed_splits = {"train"}

    elif target_split == "test":
        allowed_splits = {"train", "validation"}

    else:
        raise ValueError(
            f"Unknown split: {target_split}"
        )

    ids: set[str] = set()

    for split in allowed_splits:
        for record in split_records[split]:
            ids.add(
                canonical_record_value(
                    record,
                    "incident_id",
                )
            )

    return ids


def build_incident_lookup(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        canonical_record_value(
            record,
            "incident_id",
        ): record
        for record in records
    }
def hydrate_retrieval_results(
    candidates: list[dict[str, Any]],
    incident_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Fill retrieved incidents with the authoritative fields from the
    original processed dataset.

    Retrieval determines WHICH incidents are relevant.
    The original dataset determines the COMPLETE historical record.

    This does not modify ChromaDB or the retrieval pipeline.
    """

    hydrated: list[dict[str, Any]] = []

    for candidate in candidates:
        incident_id = normalize_value(
            candidate.get("incident_id")
        )

        if not incident_id:
            continue

        original = incident_lookup.get(incident_id)

        if original is None:
            # Keep the retrieval result if the ID cannot be found,
            # but do not invent missing historical information.
            hydrated.append(candidate)
            continue

        result = dict(candidate)

        # Preserve retrieval/reranking scores.
        retrieval_score = candidate.get("score")

        # Use the authoritative original dataset fields.
        result["incident_id"] = incident_id
        result["description"] = original.get(
            "incident_description",
            "",
        )
        result["service"] = original.get(
            "affected_service",
            "",
        )
        result["category"] = original.get(
            "category",
            "",
        )
        result["severity"] = original.get(
            "severity",
            "",
        )
        result["root_cause"] = original.get(
            "root_cause",
            "",
        )
        result["resolution"] = original.get(
            "resolution",
            "",
        )
        result["preventive_action"] = original.get(
            "preventive_action",
            "",
        )

        if retrieval_score is not None:
            result["score"] = retrieval_score

        hydrated.append(result)

    return hydrated

# ============================================================================
# LEAKAGE FILTERING
# ============================================================================


def filter_retrieval_results(
    candidates: list[dict[str, Any]],
    target: dict[str, Any],
    allowed_ids: set[str],
) -> list[dict[str, Any]]:
    """
    Remove:

        1. target incident
        2. same scenario group
        3. records outside the allowed split pool
        4. duplicate incident IDs
    """

    target_id = canonical_record_value(
        target,
        "incident_id",
    )

    target_group = target["_scenario_group"]
    target_input_group = target["_input_scenario_group"]

    valid = []
    seen_ids: set[str] = set()

    for candidate in candidates:
        incident_id = normalize_value(
            candidate.get("incident_id")
        )

        if not incident_id:
            continue

        if incident_id == target_id:
            continue

        if incident_id not in allowed_ids:
            continue

        if incident_id in seen_ids:
            continue

        metadata = candidate.get("_metadata", {})

        candidate_group = normalize_value(
            metadata.get("_scenario_group")
        )

        candidate_input_group = normalize_value(
            metadata.get("_input_scenario_group")
        )

        # If the existing Chroma metadata already contains the group,
        # use it directly.
        if candidate_group and candidate_group == target_group:
            continue

        if (
            candidate_input_group
            and candidate_input_group == target_input_group
        ):
            continue

        seen_ids.add(incident_id)
        valid.append(candidate)

    return valid


# ============================================================================
# EVIDENCE FORMAT
# ============================================================================


def format_historical_evidence(
    candidates: list[dict[str, Any]],
) -> str:
    """
    Format the final Top-5 historical incidents for Qwen.

    We deliberately expose the historical target fields because the model
    needs to learn project-specific RCA from retrieved examples.
    """

    blocks = []

    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):
        lines = [
            f"Historical Incident {rank}",
            f"Incident ID: {candidate.get('incident_id', '')}",
            f"Description: {candidate.get('description', '')}",
            f"Service: {candidate.get('service', '')}",
            f"Category: {candidate.get('category', '')}",
            f"Severity: {candidate.get('severity', '')}",
            f"Root Cause: {candidate.get('root_cause', '')}",
            f"Resolution: {candidate.get('resolution', '')}",
            (
                "Preventive Action: "
                f"{candidate.get('preventive_action', '')}"
            ),
        ]

        score = candidate.get("score")

        if score is not None:
            lines.append(
                f"Retrieval Score: {score}"
            )

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def build_user_prompt(
    target: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> str:
    historical_context = format_historical_evidence(evidence)

    return f"""Analyze the following new incident using only the supplied historical evidence.

CURRENT INCIDENT
================
Incident ID: {target["incident_id"]}
Incident Description: {target["incident_description"]}
Affected Service: {target["affected_service"]}
Category: {target["category"]}
Severity: {target["severity"]}
Priority: {target["priority"]}
Environment: {target["environment"]}
Dataset Features: {target["dataset_features"]}

RETRIEVED HISTORICAL EVIDENCE
=============================
{historical_context}

TASK
====
Determine the most supported:
1. root cause
2. evidence incident IDs
3. resolution
4. preventive action

Do not introduce unsupported information.

Return only valid JSON in this format:

{{
  "root_cause": "...",
  "evidence": ["INCxxxxx"],
  "resolution": "...",
  "prevention": "..."
}}
"""


def build_assistant_answer(
    target: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Ground truth comes ONLY from the target record.

    Existing rule-based RCA output is NOT used.
    """

    evidence_ids = [
        normalize_value(
            item.get("incident_id")
        )
        for item in evidence
        if normalize_value(item.get("incident_id"))
    ]

    return {
        "root_cause": target["root_cause"],
        "evidence": evidence_ids,
        "resolution": target["resolution"],
        "prevention": target["preventive_action"],
    }


# ============================================================================
# TRAINING EXAMPLE GENERATION
# ============================================================================

def generate_example(
    target: dict[str, Any],
    split: str,
    allowed_ids: set[str],
    incident_lookup: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """
    Generate one Qwen SFT example.

    Returns:
        example
        diagnostics
    """

    query = target["incident_description"]

# --------------------------------------------------------------
# 1. EXISTING PRODUCTION SEMANTIC RETRIEVAL
# --------------------------------------------------------------

    semantic_top20 = retrieve_similar_incidents(
    query,
    top_k=20,
    )

# --------------------------------------------------------------
# 2. EXISTING PRODUCTION QUERY METADATA
# --------------------------------------------------------------

    query_metadata = _extract_query_metadata(
    query
    )

# --------------------------------------------------------------
# 3. EXISTING PRODUCTION HYBRID/METADATA RERANKING
# --------------------------------------------------------------

    semantic_top5 = rerank_incidents(
    semantic_top20,
    query_metadata,
    top_k=5,
    )

    candidates = normalize_retrieval_results(
    semantic_top5
    )

    candidates = hydrate_retrieval_results(
    candidates,
    incident_lookup,
    )

    filtered = filter_retrieval_results(
    candidates,
    target,
    allowed_ids,
    )

    evidence = filtered[:FINAL_EVIDENCE_COUNT]

    diagnostics = {
    "semantic_top20": len(semantic_top20),
    "reranked_top5": len(semantic_top5),
    "valid_evidence": len(evidence),
    "target_id": target["incident_id"],
    "split": split,
    }

    if len(evidence) < MIN_FINAL_EVIDENCE:
        diagnostics["skipped"] = True
        diagnostics["skip_reason"] = (
            "insufficient_valid_rag_evidence"
        )

        if SKIP_WITHOUT_EVIDENCE:
            return None, diagnostics

    assistant_answer = build_assistant_answer(
        target,
        evidence,
    )

    assistant_content = json.dumps(
        assistant_answer,
        ensure_ascii=False,
    )

    example = {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_user_prompt(
                    target,
                    evidence,
                ),
            },
            {
                "role": "assistant",
                "content": assistant_content,
            },
        ],
        "metadata": {
            "incident_id": target["incident_id"],
            "scenario_group": target["_scenario_group"],
            "input_scenario_group": (
                target["_input_scenario_group"]
            ),
            "split": split,
            "root_cause": target["root_cause"],
            "evidence_incident_ids": [
                item["incident_id"]
                for item in evidence
            ],
        },
    }

    return example, diagnostics


# ============================================================================
# DATASET STATISTICS
# ============================================================================


def root_cause_distribution(
    records: list[dict[str, Any]],
) -> dict[str, int]:
    counter = Counter(
        canonical_record_value(
            record,
            "root_cause",
        )
        for record in records
    )

    return dict(
        sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )


def scenario_distribution(
    records: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Calculate scenario statistics without requiring the original records
    to contain internal '_scenario_group' metadata.

    This is important because the original dataset must remain untouched.
    """

    counter = Counter()

    for record in records:
        group_id = record.get("_scenario_group")

        if not group_id:
            group_id = scenario_key(record)

        counter[group_id] += 1

    return {
        "unique_scenarios": len(counter),
        "repeated_scenarios": sum(
            1
            for count in counter.values()
            if count > 1
        ),
        "rows_in_repeated_scenarios": sum(
            count
            for count in counter.values()
            if count > 1
        ),
        "maximum_repetition": max(
            counter.values()
        )
        if counter
        else 0,
    }


def build_statistics(
    original_records: list[dict[str, Any]],
    groups: dict[str, list[dict[str, Any]]],
    split_records: dict[str, list[dict[str, Any]]],
    generated_counts: dict[str, int],
    skipped_counts: dict[str, int],
    retrieval_counts: dict[str, list[int]],
) -> dict[str, Any]:

    split_root_causes = {}

    for split, records in split_records.items():
        split_root_causes[split] = root_cause_distribution(
            records
        )

    root_cause_group_counts = {
        root_cause: len(group_ids)
        for root_cause, group_ids
        in build_root_cause_group_index(groups).items()
    }

    rare_root_causes = {
        root_cause: count
        for root_cause, count
        in root_cause_group_counts.items()
        if count <= 2
    }

    statistics = {
        "configuration": {
            "seed": SEED,
            "train_ratio": TRAIN_RATIO,
            "validation_ratio": VALIDATION_RATIO,
            "test_ratio": TEST_RATIO,
            "final_evidence_count": FINAL_EVIDENCE_COUNT,
            "minimum_final_evidence": MIN_FINAL_EVIDENCE,
        },
        "original_dataset": {
            "records": len(original_records),
            "unique_scenario_groups": len(groups),
            "unique_root_causes": len(
                root_cause_group_counts
            ),
            "root_cause_distribution": root_cause_distribution(
                original_records
            ),
            "scenario_distribution": scenario_distribution(
                original_records
            ),
        },
        "split_records": {
            split: len(records)
            for split, records in split_records.items()
        },
        "split_scenario_groups": {
            split: len(
                {
                    record["_scenario_group"]
                    for record in records
                }
            )
            for split, records in split_records.items()
        },
        "split_root_cause_distribution": split_root_causes,
        "root_cause_group_counts": dict(
            sorted(
                root_cause_group_counts.items(),
                key=lambda item: (
                    item[1],
                    item[0],
                ),
            )
        ),
        "rare_root_causes": rare_root_causes,
        "generated_examples": generated_counts,
        "skipped_examples": skipped_counts,
        "retrieval_statistics": {
            split: {
                "examples_with_retrieval": len(values),
                "average_evidence": (
                    sum(values) / len(values)
                    if values
                    else 0
                ),
                "minimum_evidence": (
                    min(values)
                    if values
                    else 0
                ),
                "maximum_evidence": (
                    max(values)
                    if values
                    else 0
                ),
            }
            for split, values in retrieval_counts.items()
        },
    }

    return statistics


# ============================================================================
# VALIDATION
# ============================================================================


def validate_group_disjointness(
    split_records: dict[str, list[dict[str, Any]]],
) -> None:
    split_groups = {
        split: {
            record["_scenario_group"]
            for record in records
        }
        for split, records in split_records.items()
    }

    train_validation_overlap = (
        split_groups["train"]
        & split_groups["validation"]
    )

    train_test_overlap = (
        split_groups["train"]
        & split_groups["test"]
    )

    validation_test_overlap = (
        split_groups["validation"]
        & split_groups["test"]
    )

    if train_validation_overlap:
        raise AssertionError(
            "Scenario leakage detected between train and validation: "
            f"{len(train_validation_overlap)} groups"
        )

    if train_test_overlap:
        raise AssertionError(
            "Scenario leakage detected between train and test: "
            f"{len(train_test_overlap)} groups"
        )

    if validation_test_overlap:
        raise AssertionError(
            "Scenario leakage detected between validation and test: "
            f"{len(validation_test_overlap)} groups"
        )


def validate_no_duplicate_incident_ids(
    split_records: dict[str, list[dict[str, Any]]],
) -> None:
    seen: dict[str, str] = {}

    for split, records in split_records.items():
        for record in records:
            incident_id = record["incident_id"]

            if incident_id in seen:
                raise AssertionError(
                    "Incident appears in multiple splits: "
                    f"{incident_id} "
                    f"({seen[incident_id]} and {split})"
                )

            seen[incident_id] = split


def validate_generated_examples(
    examples: dict[str, list[dict[str, Any]]],
) -> None:

    for split, rows in examples.items():
        for row in rows:
            metadata = row.get("metadata", {})
            target_id = metadata.get("incident_id")

            evidence_ids = metadata.get(
                "evidence_incident_ids",
                [],
            )

            if target_id in evidence_ids:
                raise AssertionError(
                    f"Target incident leaked into evidence: "
                    f"{target_id}"
                )

            if not evidence_ids:
                raise AssertionError(
                    f"Generated example has no evidence: "
                    f"{target_id}"
                )

            assistant_message = row["messages"][-1]

            if assistant_message["role"] != "assistant":
                raise AssertionError(
                    f"Last message is not assistant for "
                    f"{target_id}"
                )

            try:
                parsed = json.loads(
                    assistant_message["content"]
                )
            except json.JSONDecodeError as exc:
                raise AssertionError(
                    f"Assistant output is not valid JSON for "
                    f"{target_id}"
                ) from exc

            expected_fields = {
                "root_cause",
                "evidence",
                "resolution",
                "prevention",
            }

            if set(parsed.keys()) != expected_fields:
                raise AssertionError(
                    f"Unexpected assistant fields for "
                    f"{target_id}: {parsed.keys()}"
                )


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    print("=" * 80)
    print("QWEN3-8B RAG-AWARE DATASET PREPARATION")
    print("=" * 80)

    print()
    print(f"Project root       : {PROJECT_ROOT}")
    print(f"Original dataset   : {ORIGINAL_DATASET}")
    print(f"Output directory   : {OUTPUT_DIR}")
    print()

    # ----------------------------------------------------------------------
    # Make backend importable.
    # ----------------------------------------------------------------------

    if str(APPS_DIR) not in sys.path:
        sys.path.insert(
            0,
            str(APPS_DIR),
        )

    # ----------------------------------------------------------------------
    # Load original dataset.
    # ----------------------------------------------------------------------

    print("[1/8] Loading original dataset...")

    records = load_original_dataset()
    incident_lookup = build_incident_lookup(records)
    print(
        f"      Loaded {len(records):,} records."
    )

    if len(records) != 8000:
        print(
            "      WARNING: Expected 8,000 records but found "
            f"{len(records):,}."
        )

    # ----------------------------------------------------------------------
    # Build groups.
    # ----------------------------------------------------------------------

    print("[2/8] Building scenario groups...")

    groups = build_groups(records)

    print(
        f"      Unique scenario groups: {len(groups):,}"
    )

    # ----------------------------------------------------------------------
    # Split.
    # ----------------------------------------------------------------------

    print("[3/8] Creating group-level stratified split...")

    split_by_group = create_group_split(
        groups,
        seed=SEED,
    )

    split_records = assign_records_to_splits(
        records,
        split_by_group,
    )

    validate_group_disjointness(
        split_records
    )

    validate_no_duplicate_incident_ids(
        split_records
    )

    for split in (
        "train",
        "validation",
        "test",
    ):
        print(
            f"      {split:12s}: "
            f"{len(split_records[split]):,} rows / "
            f"{len({r['_scenario_group'] for r in split_records[split]}):,} groups"
        )

    # ----------------------------------------------------------------------
    # Import existing retrieval.
    # ----------------------------------------------------------------------

    print("[4/8] Loading existing project retrieval + reranker...")

    print(
    "      Semantic retrieval: "
    "backend.core.retrieval.semantic_retrieval"
    )

    print(
    "      Hybrid reranker: "
    "backend.core.hybrid_retrieval.reranker"
    )

    print(
    "      Query metadata: "
    "backend.core.pipeline.incident_pipeline"
    )
    print("      Semantic retrieval size: 20")
    print("      Hybrid reranking size: 5")

    print(
        f"      Final evidence size: "
        f"{FINAL_EVIDENCE_COUNT}"
    )

    # ----------------------------------------------------------------------
    # Generate datasets.
    # ----------------------------------------------------------------------

    print("[5/8] Generating RAG-aware SFT examples...")

    generated_examples = {
        "train": [],
        "validation": [],
        "test": [],
    }

    generated_counts = {
        "train": 0,
        "validation": 0,
        "test": 0,
    }

    skipped_counts = {
        "train": 0,
        "validation": 0,
        "test": 0,
    }

    retrieval_counts = {
        "train": [],
        "validation": [],
        "test": [],
    }

    for split in (
        "train",
        "validation",
        "test",
    ):
        print()
        print(
            f"      Processing {split}..."
        )

        allowed_ids = build_allowed_incident_ids(
            split_records,
            split,
        )

        print(
            f"      Allowed historical IDs: "
            f"{len(allowed_ids):,}"
        )

        records_to_process = split_records[split]

        if MAX_EXAMPLES is not None:
            records_to_process = records_to_process[
                :MAX_EXAMPLES
            ]

        for index, target in enumerate(
            records_to_process,
            start=1,
        ):
            try:
                example, diagnostics = generate_example(
                target=target,
                split=split,
                allowed_ids=allowed_ids,
                incident_lookup=incident_lookup,
                )

            except Exception as exc:
                raise RuntimeError(
                    f"Retrieval failed for "
                    f"{split} target "
                    f"{target['incident_id']}.\n"
                    f"Original error: {exc}"
                ) from exc

            if example is None:
                skipped_counts[split] += 1

            else:
                generated_examples[split].append(
                    example
                )

                generated_counts[split] += 1

                retrieval_counts[split].append(
                    diagnostics["valid_evidence"]
                )

            if index % 100 == 0:
                print(
                    f"        {index:,}/"
                    f"{len(records_to_process):,}"
                )

    # ----------------------------------------------------------------------
    # Validate generated examples.
    # ----------------------------------------------------------------------

    print("[6/8] Validating generated examples...")

    validate_generated_examples(
        generated_examples
    )

    print("      Generated examples passed validation.")

    # ----------------------------------------------------------------------
    # Write JSONL.
    # ----------------------------------------------------------------------

    print("[7/8] Writing JSONL files...")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_jsonl(
        TRAIN_FILE,
        generated_examples["train"],
    )

    write_jsonl(
        VALIDATION_FILE,
        generated_examples["validation"],
    )

    write_jsonl(
        TEST_FILE,
        generated_examples["test"],
    )

    # ----------------------------------------------------------------------
    # Statistics.
    # ----------------------------------------------------------------------

    statistics = build_statistics(
        original_records=records,
        groups=groups,
        split_records=split_records,
        generated_counts=generated_counts,
        skipped_counts=skipped_counts,
        retrieval_counts=retrieval_counts,
    )

    stable_json_dump(
        STATISTICS_FILE,
        statistics,
    )

    print("[8/8] Dataset statistics written.")

    # ----------------------------------------------------------------------
    # Final report.
    # ----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("DATASET PREPARATION COMPLETE")
    print("=" * 80)

    print()
    print("OUTPUT FILES")
    print("-" * 80)
    print(f"TRAIN      : {TRAIN_FILE}")
    print(f"VALIDATION : {VALIDATION_FILE}")
    print(f"TEST       : {TEST_FILE}")
    print(f"STATISTICS : {STATISTICS_FILE}")

    print()
    print("GENERATED EXAMPLES")
    print("-" * 80)

    for split in (
        "train",
        "validation",
        "test",
    ):
        print(
            f"{split:12s}: "
            f"{generated_counts[split]:,} generated, "
            f"{skipped_counts[split]:,} skipped"
        )

    print()
    print("RAG EVIDENCE")
    print("-" * 80)

    for split in (
        "train",
        "validation",
        "test",
    ):
        values = retrieval_counts[split]

        if values:
            average = sum(values) / len(values)

            print(
                f"{split:12s}: "
                f"avg={average:.2f}, "
                f"min={min(values)}, "
                f"max={max(values)}"
            )
        else:
            print(
                f"{split:12s}: no generated examples"
            )

    print()
    print("LEAKAGE CHECK")
    print("-" * 80)
    print("Scenario groups are disjoint across splits.")
    print("Incident IDs are disjoint across splits.")
    print("Target incidents are excluded from their own evidence.")
    print("Same-scenario evidence is excluded.")
    print()
    print("Original dataset was read only and was not modified.")
    print("ChromaDB was not modified.")
    print("Existing RCA implementation was not modified.")
    print("No QLoRA training was started.")
    print()
    print("Next step: inspect and validate the generated JSONL files.")
    print("=" * 80)


if __name__ == "__main__":
    main()