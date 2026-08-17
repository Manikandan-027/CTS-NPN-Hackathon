from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from types import SimpleNamespace

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# PATHS
# =========================================================

ROOT = Path(
    __file__
).resolve().parents[2]

APPS_DIR = ROOT / "apps"

DATA_DIR = (
    Path(__file__).resolve().parent
    / "data"
)

CUSTOMER_QUERY_FILE = (
    DATA_DIR / "customer_queries.json"
)

DEVELOPER_KB_FILE = (
    DATA_DIR / "knowledge_base.json"
)

if str(APPS_DIR) not in sys.path:

    sys.path.insert(
        0,
        str(APPS_DIR),
    )


# =========================================================
# IMPORT YOUR EXISTING MODULES
# =========================================================

from backend.core.code_investigation import (  # noqa: E402
    LocalRepositorySource,
    RepositoryInvestigator,
)

from backend.core.incident_history.repository import (  # noqa: E402
    IncidentHistoryRepository,
)

from backend.core.incident_history.service import (  # noqa: E402
    IncidentHistoryService,
)

from backend.core.pipeline.incident_pipeline import (  # noqa: E402
    run_incident_pipeline,
)

from backend.core.llm.code_aware_rca import (  # noqa: E402
    generate_code_aware_rca,
)


# =========================================================
# FASTAPI
# =========================================================

print()
print("=" * 72)
print("RCA BACKEND STARTED")
print("Main file :", __file__)
print(
    "IncidentHistoryRepository.add_activity available:",
    callable(
        getattr(
            IncidentHistoryRepository,
            "add_activity",
            None,
        )
    ),
)
print("=" * 72)
print()

app = FastAPI(
    title="AI Incident RCA Backend",
    version="3.0.0",
    description=(
        "Dynamic customer incident ingestion, "
        "RAG retrieval, hybrid ranking, root-cause "
        "analysis, repository investigation and "
        "code-aware LLM RCA."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CONFIGURATION
# =========================================================

PAYMENT_REPOSITORY = os.getenv(
    "PAYMENT_REPOSITORY",
    "apps/demo-payment-service/demo-se",
)

PAYMENT_SERVICE = os.getenv(
    "PAYMENT_SERVICE",
    "demo-payment-service",
)

PAYMENT_ROUTE = os.getenv(
    "PAYMENT_ROUTE",
    "/api/demo/payment",
)


# =========================================================
# REQUEST MODELS
# =========================================================

class IncidentReport(BaseModel):

    incident: str = Field(
        min_length=3
    )

    repository: str | None = None

    service: str | None = None

    route: str | None = None

    source_type: str = "local"

    incident_id: str | None = None

    error_code: str | None = None

    error_message: str | None = None

    stack_trace: str | None = None

    customer_query: str | None = None

    customer_email: str | None = None


class CustomerQuery(BaseModel):

    query: str = Field(
        min_length=1
    )

    customer_email: str | None = None

    service: str | None = None

    incident_id: str | None = None


class ChatRequest(BaseModel):

    message: str = Field(min_length=1)
    conversation_id: str | None = None


class ValidationRequest(BaseModel):

    decision: str = Field(
        min_length=1
    )

    comments: str | None = None

    validated_by: str = "developer"


class KnowledgeBaseIncident(BaseModel):

    incident: str = Field(min_length=3)

    root_cause: str = Field(min_length=3)

    resolution: str = Field(min_length=3)

    prevention: str = ""

    file_path: str | None = None

    line_start: int | None = None

    line_end: int | None = None

    evidence: list[str] = Field(
        default_factory=list
    )

    service: str = PAYMENT_SERVICE

    route: str = PAYMENT_ROUTE

    repository: str | None = None

    validated_by: str = Field(min_length=1)

    source_incident_id: str | None = None

    confidence: float = 1.0


class KnowledgeBaseEntryResponse(BaseModel):
    incident_id: str
    incident: str
    root_cause: str
    resolution: str
    prevention: str = ""
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    evidence: list[str] = Field(default_factory=list)
    service: str
    route: str
    repository: str | None = None
    repository_investigation_available: bool = False
    validated_by: str
    source_incident_id: str | None = None
    confidence: float
    status: str
    knowledge_base: bool
    source_type: str
    created_at: str
    validated_at: str
    history_id: int | None = None


class KnowledgeBaseAddResponse(BaseModel):
    status: str
    message: str
    knowledge_base: KnowledgeBaseEntryResponse
    future_retrieval: dict[str, Any]


class KnowledgeBaseListResponse(BaseModel):
    count: int
    incidents: list[KnowledgeBaseEntryResponse]


# =========================================================
# STATE
# =========================================================

class AppState:

    def __init__(self):

        self.lock = asyncio.Lock()

        self.last_response = None

        self.last_incident = None


state = AppState()


# =========================================================
# JSON CUSTOMER QUERY STORAGE
# =========================================================

def ensure_customer_query_file():

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not CUSTOMER_QUERY_FILE.exists():

        CUSTOMER_QUERY_FILE.write_text(
            "[]",
            encoding="utf-8",
        )


def save_customer_query(
    query: dict[str, Any],
) -> dict[str, Any]:

    ensure_customer_query_file()

    try:

        import json

        data = json.loads(
            CUSTOMER_QUERY_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            data,
            list,
        ):
            data = []

    except Exception:

        data = []

    next_id = 1

    if data:

        try:

            next_id = (
                max(
                    int(
                        item.get(
                            "id",
                            0,
                        )
                    )
                    for item in data
                )
                + 1
            )

        except Exception:

            next_id = len(data) + 1

    query["id"] = next_id

    query.setdefault(
        "created_at",
        datetime.now(
            timezone.utc
        ).isoformat(),
    )

    data.append(query)

    CUSTOMER_QUERY_FILE.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return query


def list_customer_queries(
    limit: int = 100,
) -> list[dict[str, Any]]:

    ensure_customer_query_file()

    import json

    try:

        data = json.loads(
            CUSTOMER_QUERY_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        data = []

    if not isinstance(
        data,
        list,
    ):

        return []

    data.reverse()

    return data[:limit]


# =========================================================
# DEVELOPER KNOWLEDGE BASE
# =========================================================

def ensure_developer_kb_file() -> None:

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not DEVELOPER_KB_FILE.exists():

        DEVELOPER_KB_FILE.write_text(
            "[]",
            encoding="utf-8",
        )


def read_developer_kb() -> list[dict[str, Any]]:

    ensure_developer_kb_file()

    try:

        data = json.loads(
            DEVELOPER_KB_FILE.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ):

        return []

    entries = (
        data
        if isinstance(data, list)
        else []
    )

    cleaned = deduplicate_developer_kb(entries)

    if len(cleaned) != len(entries):
        write_developer_kb(cleaned)

    return cleaned


def write_developer_kb(
    data: list[dict[str, Any]],
) -> None:

    ensure_developer_kb_file()

    DEVELOPER_KB_FILE.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )


def kb_duplicate_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    """
    Canonical key used to prevent the same developer-approved knowledge
    from being inserted repeatedly.

    source_incident_id is preferred when available because a developer
    may submit the same verified incident more than once from Swagger.
    Otherwise incident + service + route are used.
    """
    source_id = str(entry.get("source_incident_id") or "").strip().lower()

    incident = re.sub(
        r"\s+",
        " ",
        str(entry.get("incident") or "").strip().lower(),
    )

    service = str(entry.get("service") or "").strip().lower()
    route = str(entry.get("route") or "").strip().lower()

    if source_id:
        return ("source", source_id, service, route)

    return ("content", incident, service, route)


def deduplicate_developer_kb(
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Keep the newest record for an identical developer KB key.
    This also cleans duplicates already present in knowledge_base.json.
    """
    unique: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for entry in entries:
        unique[kb_duplicate_key(entry)] = entry

    # Keep original chronological order after removing duplicates.
    result = list(unique.values())
    result.sort(
        key=lambda item: str(item.get("created_at") or "")
    )
    return result


def make_kb_incident_id(
    incident: str,
    existing: list[dict[str, Any]],
) -> str:

    digest = hashlib.sha1(
        incident.encode(
            "utf-8"
        )
    ).hexdigest()[:8].upper()

    return (
        f"KB-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-"
        f"{digest}-"
        f"{len(existing) + 1:04d}"
    )


def save_developer_kb_entry(
    payload: KnowledgeBaseIncident,
) -> dict[str, Any]:
    """Save developer-verified knowledge safely.

    knowledge_base.json is the primary store. Synchronization to the normal
    incident-history database is best-effort and cannot make this endpoint fail.
    """
    entries = read_developer_kb()

    incoming_key = kb_duplicate_key({
        "source_incident_id": payload.source_incident_id,
        "incident": payload.incident,
        "service": payload.service,
        "route": payload.route,
    })

    for existing in entries:
        if kb_duplicate_key(existing) == incoming_key:
            return {**existing, "status": "ALREADY_EXISTS"}

    repository_path = None
    if payload.repository:
        repository_path = resolve_repository(payload.repository)

    now = datetime.now(timezone.utc).isoformat()
    incident_id = make_kb_incident_id(payload.incident, entries)

    entry = {
        "incident_id": incident_id,
        "incident": payload.incident.strip(),
        "root_cause": payload.root_cause.strip(),
        "resolution": payload.resolution.strip(),
        "prevention": payload.prevention.strip(),
        "file_path": payload.file_path,
        "line_start": payload.line_start,
        "line_end": payload.line_end,
        "evidence": list(payload.evidence),
        "service": payload.service,
        "route": payload.route,
        "repository": repository_path,
        "repository_investigation_available": repository_path is not None,
        "validated_by": payload.validated_by.strip(),
        "source_incident_id": payload.source_incident_id,
        "confidence": max(0.0, min(float(payload.confidence), 1.0)),
        "status": "APPROVED",
        "knowledge_base": True,
        "source_type": "DeveloperKnowledgeBase",
        "created_at": now,
        "validated_at": now,
        "history_id": None,
        "history_sync_status": "PENDING",
    }

    entries.append(entry)
    write_developer_kb(entries)

    # Optional sync to normal incident history. Never fail the KB save because of this.
    try:
        repository, _ = build_history()
        repository_label = repository_path or ""
        history_record = {
            "incident_id": incident_id,
            "error_signature": payload.incident.strip().lower(),
            "fingerprint": hashlib.sha256(
                (payload.incident + "|" + repository_label + "|" + payload.service + "|" + payload.route).encode("utf-8")
            ).hexdigest(),
            "incident": payload.incident.strip(),
            "repository": repository_path,
            "service": payload.service,
            "route": payload.route,
            "source_type": "DeveloperKnowledgeBase",
            "root_cause": payload.root_cause.strip(),
            "file_path": payload.file_path,
            "line_start": payload.line_start,
            "line_end": payload.line_end,
            "evidence": list(payload.evidence),
            "suggested_fix": payload.resolution.strip(),
            "prevention": payload.prevention.strip(),
            "confidence": entry["confidence"],
            "status": "APPROVED",
            "knowledge_base": True,
            "validated_by": payload.validated_by.strip(),
            "source_incident_id": payload.source_incident_id,
            "created_at": now,
            "validated_at": now,
        }
        saved = repository.save_investigation(history_record)
        entry["history_id"] = getattr(saved, "id", None)
        entry["history_sync_status"] = "SYNCED"
        safe_add_activity(
            repository,
            "DEVELOPER_KB_ENTRY_ADDED",
            "Developer-approved incident added to the historical knowledge base.",
            getattr(saved, "id", None),
            {
                "knowledge_base_id": incident_id,
                "source_incident_id": payload.source_incident_id,
                "validated_by": payload.validated_by,
                "repository": repository_path,
            },
        )
    except Exception as exc:
        entry["history_sync_status"] = "PENDING_REPAIR"
        entry["history_sync_error"] = f"{type(exc).__name__}: {exc}"

    for idx, current in enumerate(entries):
        if current.get("incident_id") == incident_id:
            entries[idx] = entry
            break
    write_developer_kb(entries)
    return entry


# =========================================================
# ACTIVITY LOG COMPATIBILITY LAYER
# =========================================================

def safe_add_activity(
    repository: Any,
    activity_type: str,
    message: str,
    incident_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Log an activity without requiring IncidentHistoryRepository.add_activity().

    Older repository implementations do not expose add_activity(), so we
    gracefully fall back to activities.json when that method is missing.
    """
    metadata = metadata or {}

    method = getattr(repository, "add_activity", None)
    if callable(method):
        try:
            return method(
                activity_type,
                message,
                incident_id,
                metadata,
            )
        except TypeError:
            try:
                return method(
                    activity_type=activity_type,
                    message=message,
                    incident_id=incident_id,
                    metadata=metadata,
                )
            except Exception:
                pass
        except Exception:
            pass

    activity = {
        "activity_type": activity_type,
        "message": message,
        "incident_id": incident_id,
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    activities_file = getattr(repository, "activities_file", None)
    if activities_file is None:
        # Best effort fallback under the backend data directory.
        activities_file = DATA_DIR / "activities.json"
    else:
        activities_file = Path(activities_file)

    try:
        activities_file.parent.mkdir(parents=True, exist_ok=True)
        if activities_file.exists():
            try:
                data = json.loads(activities_file.read_text(encoding="utf-8"))
            except Exception:
                data = []
        else:
            data = []

        if not isinstance(data, list):
            data = []

        data.append(activity)
        activities_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except Exception:
        # Activity logging must never break the RCA request.
        pass

    return activity


# =========================================================
# SERVICE / REPOSITORY
# =========================================================

class _ActivitySafeRepositoryProxy:
    """Adapter used only for IncidentHistoryService.lookup()."""

    def __init__(self, repository: Any) -> None:
        self._repository = repository

    def add_activity(
        self,
        activity_type: str,
        message: str,
        incident_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return safe_add_activity(
            self._repository,
            activity_type,
            message,
            incident_id,
            metadata,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(
            self._repository,
            name,
        )


def safe_history_lookup(
    repository: Any,
    incident: str,
    repository_value: str,
    service: str,
    route: str,
) -> Any:
    """Run history lookup with a guaranteed activity logger."""
    proxy = _ActivitySafeRepositoryProxy(repository)
    safe_history = IncidentHistoryService(proxy)

    return safe_history.lookup(
        incident,
        repository_value,
        service,
        route,
    )


# IMPORTANT:
# Some installed versions of IncidentHistoryRepository do not implement
# add_activity(), while IncidentHistoryService.lookup() calls it directly.
# Install one compatibility method at the class level so EVERY repository
# instance used by this process is safe. This is the single compatibility
# point for both Swagger and the demo payment application.
if not callable(
    getattr(
        IncidentHistoryRepository,
        "add_activity",
        None,
    )
):

    def _repository_add_activity_compat(
        self,
        activity_type: str,
        message: str,
        incident_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return safe_add_activity(
            self,
            activity_type,
            message,
            incident_id,
            metadata,
        )

    setattr(
        IncidentHistoryRepository,
        "add_activity",
        _repository_add_activity_compat,
    )


def build_history():

    repository = (
        IncidentHistoryRepository()
    )

    # Compatibility: IncidentHistoryService.lookup() in some versions
    # directly calls repository.add_activity(). Our installed repository
    # may not expose that method, so attach the existing safe logger before
    # the service can ever perform a history lookup.
    if not callable(getattr(repository, "add_activity", None)):

        def _add_activity(
            activity_type: str,
            message: str,
            incident_id: int | None = None,
            metadata: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            return safe_add_activity(
                repository,
                activity_type,
                message,
                incident_id,
                metadata,
            )

        setattr(
            repository,
            "add_activity",
            _add_activity,
        )

    history = (
        IncidentHistoryService(
            repository
        )
    )

    return repository, history


# =========================================================
# RESOLVE REPOSITORY
# =========================================================

def resolve_repository(
    repository: str | None,
) -> str:

    repository = (
        repository
        or PAYMENT_REPOSITORY
    )

    path = Path(
        repository
    )

    if not path.is_absolute():

        path = (
            ROOT / path
        )

    path = path.resolve()

    if not path.exists():

        raise HTTPException(
            status_code=400,
            detail=(
                "Developer repository "
                f"not found: {path}"
            ),
        )

    if not path.is_dir():

        raise HTTPException(
            status_code=400,
            detail=(
                "Repository is not a "
                f"directory: {path}"
            ),
        )

    return str(path)


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    payment_repo = resolve_repository(
        PAYMENT_REPOSITORY
    )

    return {

        "status":
            "ok",

        "storage":
            "JSON",

        "postgresql":
            False,

        "payment_repository":
            payment_repo,

        "payment_service":
            PAYMENT_SERVICE,

        "payment_route":
            PAYMENT_ROUTE,
    }


# =========================================================
# ROOT API
# Frontend is a separate React application.
# =========================================================

@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "AI Incident RCA Backend",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


# =========================================================
# CUSTOMER QUERY API
# =========================================================

@app.post(
    "/api/customer/query"
)
def create_customer_query(
    payload: CustomerQuery,
):

    query = save_customer_query(
        {
            "query":
                payload.query,

            "customer_email":
                payload.customer_email,

            "service":
                payload.service,

            "incident_id":
                payload.incident_id,

            "status":
                "RECEIVED",
        }
    )

    return {
        "status":
            "saved",

        "query":
            query,
    }


@app.get(
    "/api/support/customer-queries"
)
def get_customer_queries(
    limit: int = 100,
):

    return {
        "queries":
            list_customer_queries(
                max(
                    1,
                    min(
                        limit,
                        500,
                    ),
                )
            )
    }


# =========================================================
# PAYMENT TEST ENDPOINT
# =========================================================

@app.post(
    "/api/demo/payment"
)
def payment_demo():

    """
    This is only a backend test endpoint.

    The real demo-payment-service can call
    /api/incidents/report directly.
    """

    return {

        "success":
            False,

        "status":
            401,

        "error":
            "Payment Failed",

        "message":
            "Payment authentication failed.",

        "service":
            PAYMENT_SERVICE,

        "route":
            PAYMENT_ROUTE,
    }


# =========================================================
# MAIN INCIDENT ENDPOINT
# =========================================================

@app.post(
    "/api/incidents/report"
)
async def report_incident(
    payload: IncidentReport,
):

    incident = (
        payload.incident.strip()
    )

    # Do NOT require or access the developer repository before the
    # historical relevance gate. A completely new/out-of-domain incident
    # must be handled even when no repository is available.
    requested_repository = payload.repository

    service = (
        payload.service
        or PAYMENT_SERVICE
    )

    route = (
        payload.route
        or PAYMENT_ROUTE
    )

    repository, history = (
        build_history()
    )

    # =====================================================
    # ACTIVITY: RECEIVED
    # =====================================================

    safe_add_activity(repository, 
        "INCIDENT_RECEIVED",
        "Incident received from demo application.",
        None,
        {
            "incident":
                incident,

            "incident_id":
                payload.incident_id,

            "service":
                service,

            "route":
                route,

            "repository":
                requested_repository,

            "error_code":
                payload.error_code,
        },
    )

    # =====================================================
    # SAVE CUSTOMER QUERY
    # =====================================================

    customer_query = (
        save_customer_query(
            {
                "query":
                    payload.customer_query
                    or incident,

                "customer_email":
                    payload.customer_email,

                "service":
                    service,

                "route":
                    route,

                "incident_id":
                    payload.incident_id,

                "error_code":
                    payload.error_code,

                "error_message":
                    payload.error_message,

                "repository":
                    requested_repository,

                "status":
                    "RECEIVED",
            }
        )
    )

    safe_add_activity(repository, 
        "CUSTOMER_QUERY_SAVED",
        "Customer query stored in local JSON database.",
        None,
        {
            "customer_query_id":
                customer_query["id"],
        },
    )

    # =====================================================
    # HISTORY CHECK
    # =====================================================

    safe_add_activity(repository, 
        "HISTORY_CHECK_STARTED",
        "Checking whether this incident was previously solved.",
    )

    # IncidentHistoryService.normalize() expects a string repository.
    # For a completely new/out-of-domain incident, repository is optional,
    # so use an empty repository value for the exact-history fingerprint
    # check. We do NOT resolve or access a repository here.
    if requested_repository:
        # Exact-history matching requires a repository string in the
        # existing IncidentHistoryService. Use the caller's path first,
        # then retry with the resolved absolute path when it exists.
        history_match = safe_history_lookup(
            repository,
            incident,
            requested_repository,
            service,
            route,
        )

        if not history_match.found:
            try:
                candidate_repo = Path(requested_repository)
                if candidate_repo.is_absolute():
                    resolved_history_repo = str(candidate_repo.resolve())
                else:
                    resolved_history_repo = str((ROOT / candidate_repo).resolve())

                if Path(resolved_history_repo).is_dir():
                    history_match = safe_history_lookup(
                        repository,
                        incident,
                        resolved_history_repo,
                        service,
                        route,
                    )
            except Exception:
                pass
    else:
        # No repository is not an error here. This is exactly the case
        # we need to support for a completely new/out-of-domain incident.
        history_match = SimpleNamespace(
            found=False,
            record=None,
            match_type="repository_not_supplied",
        )

    if history_match.found:

        record = (
            history_match.record
        )

        record_status = str(
            getattr(
                record,
                "status",
                ""
            )
            or ""
        ).upper()

        pending_record = (
            record_status
            == "PENDING_HUMAN_VALIDATION"
        )

        if not pending_record:

            result = {

            "incident_status":
                "KNOWN",

            "action":
                "REUSE_PREVIOUS_SOLUTION",

            "incident":
                incident,

            "history_id":
                record.id,

            "root_cause":
                record.root_cause,

            "file_path":
                record.file_path,

            "line_start":
                record.line_start,

            "line_end":
                record.line_end,

            "evidence":
                record.evidence,

            "suggested_fix":
                record.suggested_fix,

            "prevention":
                record.prevention,

            "confidence":
                record.confidence,

            "customer_query_id":
                customer_query["id"],

            "message":
                "Previous solution found.",
        }

        safe_add_activity(repository, 
            "HISTORY_MATCH",
            "Existing incident matched. Previous RCA reused.",
            record.id,
            {
                "match_type":
                    history_match.match_type,
            },
        )

        state.last_response = result
        state.last_incident = incident

        return result


    # =====================================================
    # NEW INCIDENT
    # =====================================================

    safe_add_activity(repository, 
        "NEW_INCIDENT",
        "No previous solution found. Starting complete RCA pipeline.",
    )

    # =====================================================
    # EMBEDDING / RETRIEVAL
    # =====================================================

    safe_add_activity(repository, 
        "EMBEDDING_STARTED",
        "Creating embedding for the new incident.",
    )

    safe_add_activity(repository, 
        "RAG_TOP20_STARTED",
        "Retrieving the top 20 historical incidents.",
    )

    # =====================================================
    # RUN YOUR EXISTING RCA PIPELINE
    # =====================================================

    try:

        async with state.lock:

            pipeline_result = (
                run_incident_pipeline(
                    incident,
                    repository=requested_repository,
                    stack_trace=payload.stack_trace,
                )
            )

    except Exception as exc:

        safe_add_activity(repository, 
            "PIPELINE_FAILED",
            "RCA pipeline failed.",
            None,
            {
                "error":
                    str(exc),

                "incident":
                    incident,
            },
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    # =====================================================
    # LOG RAG RESULTS
    # =====================================================

    semantic = (
        pipeline_result.get(
            "semantic_retrieval",
            {}
        )
    )

    top20 = semantic.get(
        "top20",
        []
    )

    top5 = semantic.get(
        "top5",
        []
    )

    safe_add_activity(repository, 
        "RAG_TOP20_COMPLETED",
        f"Retrieved {len(top20)} historical incidents.",
        None,
        {
            "count":
                len(top20),
        },
    )

    safe_add_activity(repository, 
        "HYBRID_RERANK_COMPLETED",
        f"Hybrid reranking selected {len(top5)} incidents.",
        None,
        {
            "count":
                len(top5),
        },
    )

    # =====================================================
    # COMPLETELY NEW INCIDENT GATE
    # =====================================================

    if (
        pipeline_result.get(
            "incident_status"
        )
        == "COMPLETELY_NEW"
    ):

        novelty_result = dict(
            pipeline_result
        )

        novelty_result.update(
            {
                "incident":
                    incident,

                "incident_id":
                    payload.incident_id,

                "customer_query_id":
                    customer_query["id"],

                "service":
                    service,

                "route":
                    route,

                "repository":
                    requested_repository,

                "status":
                    "PENDING_DEVELOPER_KB_ENTRY",

                "knowledge_base": {
                    "required":
                        True,

                    "status":
                        "PENDING_DEVELOPER_ENTRY",

                    "message": (
                        "Developer must verify this completely "
                        "new incident and add the solved incident "
                        "to the knowledge base."
                    ),

                    "endpoint":
                        "/api/knowledge-base/incidents",

                    "storage":
                        str(DEVELOPER_KB_FILE),
                },

                "validation": {
                    "required":
                        True,

                    "status":
                        "PENDING_DEVELOPER_KB_ENTRY",
                },
            }
        )

        relevance = (
            pipeline_result.get(
                "historical_relevance",
                {}
            )
            or {}
        )

        try:
            safe_add_activity(repository, 
                "COMPLETELY_NEW_INCIDENT",
                (
                    "No sufficiently similar historical incident "
                    "or validated evidence was found."
                ),
                None,
                {
                    "incident_id":
                        payload.incident_id,

                    "best_vector_similarity":
                        relevance.get(
                            "best_vector_similarity",
                            0.0,
                        ),

                    "best_developer_kb_similarity":
                        relevance.get(
                            "best_developer_kb_similarity",
                            0.0,
                        ),

                    "vector_threshold":
                        relevance.get(
                            "vector_threshold",
                            0.0,
                        ),
                },
            )

            safe_add_activity(repository, 
                "DEVELOPER_KB_ENTRY_REQUIRED",
                (
                    "Developer must add the verified incident, "
                    "root cause, resolution and prevention "
                    "before this incident becomes reusable knowledge."
                ),
            )
        except Exception:
            pass

        state.last_response = novelty_result
        state.last_incident = incident

        print()
        print("=" * 72)
        print("  COMPLETELY NEW INCIDENT")
        print("=" * 72)
        print(
            "  No sufficiently similar historical incident "
            "was found."
        )
        print(
            "  Best vector similarity   : "
            f"{relevance.get('best_vector_similarity', 0.0):.3f}"
        )
        print(
            "  Required vector threshold: "
            f"{relevance.get('vector_threshold', 0.0):.3f}"
        )
        print(
            "  Developer KB similarity  : "
            f"{relevance.get('best_developer_kb_similarity', 0.0):.3f}"
        )
        print(
            "  Historical evidence      : NONE"
        )
        print()
        print(
            "  ACTION REQUIRED:"
        )
        print(
            "  Developer must add the verified "
            "incident to the knowledge base."
        )
        print(
            "  POST /api/knowledge-base/incidents"
        )
        print("=" * 72)
        print()

        return novelty_result


    # =====================================================
    # REPOSITORY: OPTIONAL FOR HISTORICAL-ONLY RCA
    # =====================================================

    repository_path = None

    if requested_repository:
        try:
            repository_path = resolve_repository(
                requested_repository
            )

            safe_add_activity(
                repository,
                "REPOSITORY_RESOLVED",
                "Historical evidence passed the relevance gate; repository access is now available for code investigation.",
                None,
                {
                    "repository": repository_path,
                },
            )
        except HTTPException as exc:
            # A related incident can still use validated historical evidence
            # when the repository is unavailable. We explicitly report that
            # code-level investigation could not run instead of crashing RCA.
            safe_add_activity(
                repository,
                "REPOSITORY_UNAVAILABLE",
                "Historical evidence is relevant, but repository investigation could not be performed.",
                None,
                {
                    "requested_repository": requested_repository,
                    "error": exc.detail,
                },
            )
            repository_path = None

    # =====================================================
    # ROOT CAUSE
    # =====================================================

    safe_add_activity(repository, 
        "ROOT_CAUSE_ANALYSIS_COMPLETED",
        "Historical incidents analyzed for likely root cause.",
        None,
        {
            "root_cause":
                pipeline_result.get(
                    "final_root_cause"
                ),
        },
    )

    # =====================================================
    # REPOSITORY
    # =====================================================

    repository_evidence = (
        pipeline_result.get(
            "repository_evidence"
        )
        or {}
    )

    findings = (
        repository_evidence.get(
            "findings",
            []
        )
    )

    safe_add_activity(repository, 
        "CODE_SCAN_COMPLETED",
        (
            f"Developer repository scanned. "
            f"Found {len(findings)} relevant findings."
        ),
        None,
        {
            "repository":
                repository_path,

            "findings":
                len(findings),
        },
    )

    # =====================================================
    # CODE-AWARE LLM
    # =====================================================

    code_rca = (
        pipeline_result.get(
            "code_aware_llm"
        )
        or {}
    )

    if code_rca:

        safe_add_activity(repository, 
            "LLM_RCA_COMPLETED",
            "Code-aware LLM generated the final RCA.",
            None,
            {
                "file_path":
                    code_rca.get(
                        "file_path"
                    ),

                "line_start":
                    code_rca.get(
                        "line_start"
                    ),

                "line_end":
                    code_rca.get(
                        "line_end"
                    ),

                "confidence":
                    code_rca.get(
                        "confidence"
                    ),
            },
        )

    # =====================================================
    # SAVE RCA
    # =====================================================

    final_root_cause = (
        pipeline_result.get(
            "final_root_cause"
        )
        or "Root cause could not be determined."
    )

    final_file = (
        pipeline_result.get(
            "final_file_path"
        )
    )

    final_line_start = (
        pipeline_result.get(
            "final_line_start"
        )
    )

    final_line_end = (
        pipeline_result.get(
            "final_line_end"
        )
    )

    final_evidence = (
        pipeline_result.get(
            "final_evidence",
            []
        )
    )

    final_fix = (
        pipeline_result.get(
            "final_resolution"
        )
    )

    final_prevention = (
        pipeline_result.get(
            "final_prevention"
        )
    )

    llm_confidence = (
        pipeline_result.get(
            "llm_confidence"
        )
    )

    # Use calculated confidence if LLM confidence is absent.
    confidence_result = (
        pipeline_result.get(
            "confidence"
        )
    )

    if isinstance(
        confidence_result,
        dict,
    ):

        calculated_confidence = (
            confidence_result.get(
                "confidence"
            )
        )

    else:

        calculated_confidence = (
            confidence_result
        )

    final_confidence = (
        llm_confidence
        if llm_confidence is not None
        else calculated_confidence
    )

    # =====================================================
    # SAVE HISTORY
    # =====================================================

    investigation = {

        "root_cause":
            final_root_cause,

        "file_path":
            final_file,

        "line_start":
            final_line_start,

        "line_end":
            final_line_end,

        "evidence":
            final_evidence,

        "suggested_fix":
            final_fix
            or "Review the recommended resolution.",

        "prevention":
            final_prevention
            or "",

        "confidence":
            final_confidence
            or 0.0,
    }

    history_record = {

        "incident_id":
            payload.incident_id,

        "incident":
            incident,

        "repository":
            repository_path,

        "service":
            service,

        "route":
            route,

        "source_type":
            payload.source_type,

        "root_cause":
            final_root_cause,

        "file_path":
            final_file,

        "line_start":
            final_line_start,

        "line_end":
            final_line_end,

        "evidence":
            final_evidence,

        "suggested_fix":
            final_fix or "",

        "prevention":
            final_prevention or "",

        "confidence":
            float(final_confidence or 0.0),

        "status":
            "PENDING_HUMAN_VALIDATION",
    }

    saved = repository.save_investigation(
        history_record
    )

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    result = {

        "incident_status":
            "NEW",

        "action":
            "INVESTIGATE_AND_SAVE",

        "incident":
            incident,

        "incident_id":
            payload.incident_id,

        "customer_query_id":
            customer_query["id"],

        "history_id":
            saved.id,

        "service":
            service,

        "route":
            route,

        "repository":
            repository_path,

        # ------------------------------
        # RETRIEVAL
        # ------------------------------

        "retrieval":

            {
                "top20":
                    top20,

                "top5":
                    top5,
            },

        # ------------------------------
        # RCA
        # ------------------------------

        "root_cause":
            final_root_cause,

        "evidence":
            final_evidence,

        "confidence":
            final_confidence,

        # ------------------------------
        # CODE LOCATION
        # ------------------------------

        "file_path":
            final_file,

        "line_start":
            final_line_start,

        "line_end":
            final_line_end,

        "repository_evidence":
            repository_evidence,

        # ------------------------------
        # RESOLUTION
        # ------------------------------

        "suggested_fix":
            final_fix,

        "prevention":
            final_prevention,

        # ------------------------------
        # LLM
        # ------------------------------

        "llm":

            code_rca,

        "summary":
            pipeline_result.get(
                "summary",
                "",
            ),

        # ------------------------------
        # EXTRA RCA RESULTS
        # ------------------------------

        "historical_root_cause":
            pipeline_result.get(
                "root_cause"
            ),

        "historical_evidence":
            pipeline_result.get(
                "evidence"
            ),

        "resolution_analysis":
            pipeline_result.get(
                "resolution"
            ),

        "prevention_analysis":
            pipeline_result.get(
                "prevention"
            ),

        "recurrence":
            pipeline_result.get(
                "recurrence"
            ),

        "status":
            "PENDING_HUMAN_VALIDATION",

        "repository_investigation_available": repository_path is not None,

        "repository_status": (
            "AVAILABLE" if repository_path else "NOT_AVAILABLE"
        ),
    }

    safe_add_activity(repository, 
        "NEW_INVESTIGATION_SAVED",
        "Complete RCA result saved for human validation.",
        saved.id,
        {
            "file_path":
                final_file,

            "line_start":
                final_line_start,

            "confidence":
                final_confidence,
        },
    )

    safe_add_activity(repository, 
        "HUMAN_VALIDATION_REQUIRED",
        "Developer must validate the generated RCA before applying the fix.",
        saved.id,
    )

    state.last_response = result
    state.last_incident = incident

    return result


# =========================================================
# DEVELOPER KNOWLEDGE BASE API
# =========================================================

@app.post("/api/knowledge-base/incidents")
def add_knowledge_base_incident(
    payload: KnowledgeBaseIncident,
):

    if not payload.validated_by.strip():

        raise HTTPException(
            status_code=400,
            detail="validated_by is required.",
        )

    if not payload.incident.strip():

        raise HTTPException(
            status_code=400,
            detail="incident is required.",
        )

    if not payload.root_cause.strip():

        raise HTTPException(
            status_code=400,
            detail="root_cause is required.",
        )

    if not payload.resolution.strip():

        raise HTTPException(
            status_code=400,
            detail="resolution is required.",
        )

    try:

        entry = save_developer_kb_entry(
            payload
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Knowledge-base entry could not be saved: "
                f"{exc}"
            ),
        ) from exc

    if entry.get("status") == "ALREADY_EXISTS":
        return {
            "status": "ALREADY_EXISTS",
            "message": (
                "This developer-approved incident is already "
                "present in the knowledge base. No duplicate was added."
            ),
            "knowledge_base": entry,
            "future_retrieval": {
                "enabled": True,
                "source": "developer_knowledge_base",
            },
        }

    return {
        "status":
            "ADDED",

        "message": (
            "Developer-approved incident added to the "
            "historical knowledge base. Future similar "
            "incidents can retrieve it."
        ),

        "knowledge_base":
            entry,

        "future_retrieval": {
            "enabled":
                True,

            "source":
                "developer_knowledge_base",
        },
    }


@app.get(
    "/api/knowledge-base/incidents",
    response_model=KnowledgeBaseListResponse,
)
def list_knowledge_base_incidents(
    limit: int = 100,
):

    entries = read_developer_kb()

    entries.reverse()

    return {
        "count":
            len(entries),

        "incidents":
            entries[
                :max(
                    1,
                    min(
                        limit,
                        500,
                    ),
                )
            ],
    }


@app.get(
    "/api/knowledge-base/status"
)
def knowledge_base_status() -> dict[str, Any]:
    """
    Verify that the developer KB JSON database exists and report its
    current record count plus storage path.
    """
    entries = read_developer_kb()

    return {
        "status": "ok",
        "database": "developer_knowledge_base",
        "storage": "JSON",
        "file": str(DEVELOPER_KB_FILE),
        "exists": DEVELOPER_KB_FILE.exists(),
        "count": len(entries),
        "latest_incident_id": (
            entries[-1].get("incident_id")
            if entries
            else None
        ),
    }


@app.get(
    "/api/knowledge-base/incidents/{knowledge_base_id}",
    response_model=KnowledgeBaseEntryResponse,
)
def get_knowledge_base_incident(
    knowledge_base_id: str,
):
    """
    Return one developer-approved knowledge-base record.

    Use this endpoint after POSTing a new incident to verify that the
    exact record was persisted to backend/data/knowledge_base.json.
    """
    entries = read_developer_kb()

    for entry in entries:
        if str(entry.get("incident_id", "")) == knowledge_base_id:
            return entry

    raise HTTPException(
        status_code=404,
        detail=f"Knowledge-base incident not found: {knowledge_base_id}",
    )


# =========================================================
# HUMAN VALIDATION
# =========================================================

@app.post(
    "/api/support/validate/{incident_id}"
)
def validate_incident(
    incident_id: str,
    payload: ValidationRequest,
):

    repository, _ = (
        build_history()
    )

    decision = (
        payload.decision
        .strip()
        .upper()
    )

    if decision not in {
        "APPROVE",
        "REJECT",
        "NEEDS_REVIEW",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "decision must be "
                "APPROVE, REJECT or "
                "NEEDS_REVIEW"
            ),
        )

    updated = (
        repository.update_incident(
            incident_id,
            {
                "human_validation":
                    decision,

                "validation_comments":
                    payload.comments,

                "validated_by":
                    payload.validated_by,

                "validation_status":
                    decision,
            },
        )
    )

    if not updated:

        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    safe_add_activity(repository, 
        "HUMAN_VALIDATION_COMPLETED",
        f"Developer validation completed: {decision}",
        incident_id,
        {
            "decision":
                decision,

            "validated_by":
                payload.validated_by,

            "comments":
                payload.comments,
        },
    )

    return {

        "status":
            "validated",

        "incident_id":
            incident_id,

        "decision":
            decision,

        "comments":
            payload.comments,

        "validated_by":
            payload.validated_by,
    }



# =========================================================
# RAG CHATBOT
# =========================================================

def _find_incident_record(incident_id: str) -> dict[str, Any] | None:
    repository, _ = build_history()
    records = repository.list_incidents(500)
    for item in records:
        if str(item.get("incident_id", item.get("id", ""))) == str(incident_id):
            return item
    return None


def _extract_verified_kb_fields(message: str) -> tuple[str | None, str | None, str | None]:
    """Allow a developer to add KB knowledge through chat using explicit labels."""
    text = message.strip()

    def capture(label: str, next_labels: list[str]) -> str | None:
        import re
        pattern = rf"{label}\s*:\s*(.*?)(?=\\n\\s*(?:{'|'.join(next_labels)})\\s*:|$)"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None

    root = capture("root cause", ["resolution", "prevention"])
    resolution = capture("resolution", ["prevention", "root cause"])
    prevention = capture("prevention", ["root cause", "resolution"])
    return root, resolution, prevention


def _chat_answer_from_incident(message: str, incident: dict[str, Any]) -> str:
    """Small deterministic fallback used when the LLM is unavailable."""
    q = message.lower()
    if "file" in q or "code" in q or "line" in q:
        if incident.get("file_path"):
            return f"The repository investigation localized the issue to {incident['file_path']} lines {incident.get('line_start', '?')}-{incident.get('line_end', incident.get('line_start', '?'))}."
        return "No verified repository code location is available for this incident."
    if "why" in q or "root cause" in q:
        return incident.get("root_cause") or "A root cause was not generated for this incident."
    if "fix" in q or "resolution" in q:
        return incident.get("suggested_fix") or "A verified resolution is not available yet."
    if "prevent" in q:
        return incident.get("prevention") or "No prevention recommendation is available yet."
    status = incident.get("incident_status") or incident.get("status") or "UNKNOWN"
    return f"Incident {incident.get('incident_id', '')} is currently {status}. Root cause: {incident.get('root_cause') or 'not generated'}"


def _generate_chat_summary(message: str, incident: dict[str, Any]) -> str:
    """Use the same Groq/Qwen infrastructure to summarize verified RCA context."""
    try:
        from backend.core.llm.groq_client import create_groq_client
        model = os.getenv("RCA_CHAT_MODEL", "qwen/qwen3.6-27b")
        client = create_groq_client()
        compact = {
            "user_question": message,
            "incident_id": incident.get("incident_id"),
            "incident": incident.get("incident"),
            "status": incident.get("incident_status") or incident.get("status"),
            "root_cause": incident.get("root_cause"),
            "file_path": incident.get("file_path"),
            "line_start": incident.get("line_start"),
            "line_end": incident.get("line_end"),
            "evidence": incident.get("evidence", [])[:8] if isinstance(incident.get("evidence"), list) else [],
            "suggested_fix": incident.get("suggested_fix"),
            "prevention": incident.get("prevention"),
            "confidence_percent": incident.get("confidence_percent"),
            "historical_relevance": incident.get("historical_relevance"),
            "knowledge_base": incident.get("knowledge_base"),
            "repository": incident.get("repository"),
        }
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the support-side RCA chatbot. Answer ONLY from the supplied verified RCA context. "
                        "Do not invent code, incidents, files, metrics or causes. Be concise and engineer-friendly. "
                        "When the incident is COMPLETELY_NEW, explain that no RCA was generated and that developer knowledge is required."
                    ),
                },
                {"role": "user", "content": json.dumps(compact, ensure_ascii=False)},
            ],
        )
        return response.choices[0].message.content or _chat_answer_from_incident(message, incident)
    except Exception:
        return _chat_answer_from_incident(message, incident)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Chat message cannot be empty.")

    # Developer knowledge can be added directly from the chatbot after a
    # completely-new incident has been reviewed and the developer provides
    # explicit verified fields in the message.
    if request.conversation_id and "knowledge base" in message.lower() and "add" in message.lower():
        incident = _find_incident_record(request.conversation_id)
        if not incident:
            return {
                "conversation_id": request.conversation_id,
                "message_type": "text",
                "reply": "I could not find that incident. Open the incident again and retry.",
                "incident": None,
            }
        root, resolution, prevention = _extract_verified_kb_fields(message)
        if not root or not resolution:
            return {
                "conversation_id": request.conversation_id,
                "message_type": "text",
                "reply": (
                    "To add this completely new incident to the knowledge base, send a verified developer message containing:\n\n"
                    "Root cause: ...\nResolution: ...\nPrevention: ..."
                ),
                "incident": incident,
                "knowledge_base_action_required": True,
            }
        payload = KnowledgeBaseIncident(
            incident=incident.get("incident") or incident.get("error_message") or "",
            root_cause=root,
            resolution=resolution,
            prevention=prevention or "",
            file_path=incident.get("file_path"),
            line_start=incident.get("line_start"),
            line_end=incident.get("line_end"),
            evidence=incident.get("evidence") if isinstance(incident.get("evidence"), list) else [],
            service=incident.get("service") or PAYMENT_SERVICE,
            route=incident.get("route") or PAYMENT_ROUTE,
            repository=incident.get("repository"),
            validated_by="developer",
            source_incident_id=incident.get("incident_id"),
            confidence=1.0,
        )
        entry = save_developer_kb_entry(payload)
        return {
            "conversation_id": request.conversation_id,
            "message_type": "knowledge_base_saved",
            "reply": (
                "The verified incident was added to the developer knowledge base. "
                f"Knowledge ID: {entry.get('incident_id')}"
            ),
            "incident": incident,
            "knowledge_base": entry,
        }

    if request.conversation_id:
        incident = _find_incident_record(request.conversation_id)
        if not incident:
            return {
                "conversation_id": request.conversation_id,
                "message_type": "text",
                "reply": "I could not find the incident associated with this conversation.",
                "incident": None,
            }
        return {
            "conversation_id": request.conversation_id,
            "message_type": "rca_result",
            "reply": _generate_chat_summary(message, incident),
            "incident": incident,
        }

    # First chat message is treated as a real incident and runs the same
    # backend pipeline as the payment application. Use the configured payment
    # repository for the support chatbot unless the caller later opens a real
    # incident from the incident list.
    incident_id = f"CHAT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S%f')[:-3]}"
    report = IncidentReport(
        incident=message,
        repository=PAYMENT_REPOSITORY,
        service=PAYMENT_SERVICE,
        route=PAYMENT_ROUTE,
        source_type="chat",
        incident_id=incident_id,
        error_message=message,
        customer_query=message,
    )
    result = await report_incident(report)
    return {
        "conversation_id": result.get("incident_id") or incident_id,
        "message_type": "rca_result",
        "reply": _generate_chat_summary(message, result),
        "incident": result,
    }


# =========================================================
# SUPPORT LATEST
# =========================================================

@app.get(
    "/api/support/latest"
)
def support_latest():

    return {

        "response":
            state.last_response,

        "last_incident":
            state.last_incident,
    }


# =========================================================
# SUPPORT INCIDENTS
# =========================================================

@app.get(
    "/api/support/incidents"
)
def support_incidents(
    limit: int = 50,
):

    repository, _ = (
        build_history()
    )

    return {

        "incidents":
            repository.list_incidents(
                max(
                    1,
                    min(
                        limit,
                        200,
                    ),
                )
            )
    }


# =========================================================
# SUPPORT LOGS
# =========================================================

@app.get(
    "/api/support/logs"
)
def support_logs(
    limit: int = 100,
):

    repository, _ = (
        build_history()
    )

    return {

        "activities":
            repository.list_activities(
                max(
                    1,
                    min(
                        limit,
                        500,
                    ),
                )
            )
    }


# =========================================================
# RESET
# =========================================================

@app.post(
    "/api/demo/reset"
)
def reset_demo():

    repository, _ = (
        build_history()
    )

    # Clear only runtime incident history.
    # Historical RAG dataset and ChromaDB are NOT touched.

    repository.incidents_file.write_text(
        "[]",
        encoding="utf-8",
    )

    repository.activities_file.write_text(
        "[]",
        encoding="utf-8",
    )

    state.last_response = None
    state.last_incident = None

    return {

        "status":
            "reset",

        "message":
            "Runtime incident history cleared.",
    }
