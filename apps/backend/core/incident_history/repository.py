from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class IncidentRecord:
    def __init__(self, data: dict[str, Any]):
        self.__dict__.update(data)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class IncidentHistoryRepository:
    """
    Local JSON incident storage.

    PostgreSQL is NOT required.

    Files:
        apps/backend/data/incidents.json
        apps/backend/data/activities.json
    """

    def __init__(self) -> None:

        # repository.py
        #   incident_history/
        #       repository.py
        #
        # parents[2] = backend

        self.backend_dir = Path(__file__).resolve().parents[2]

        self.data_dir = self.backend_dir / "data"

        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.incidents_file = (
            self.data_dir / "incidents.json"
        )

        self.activities_file = (
            self.data_dir / "activities.json"
        )

        self.customer_queries_file = (
            self.data_dir / "customer_queries.json"
        )

        self.lock = Lock()

        self._ensure_files()

    # =========================================================
    # FILE INITIALIZATION
    # =========================================================

    def _ensure_files(self) -> None:

        for path in (
            self.incidents_file,
            self.activities_file,
            self.customer_queries_file,
        ):
            if not path.exists():
                path.write_text(
                    "[]",
                    encoding="utf-8",
                )

    # =========================================================
    # JSON HELPERS
    # =========================================================

    def _read(
        self,
        path: Path,
    ) -> list[dict[str, Any]]:

        try:

            text = path.read_text(
                encoding="utf-8"
            )

            if not text.strip():
                return []

            data = json.loads(text)

            if isinstance(data, list):
                return data

            return []

        except (
            json.JSONDecodeError,
            FileNotFoundError,
        ):

            return []

    def _write(
        self,
        path: Path,
        data: list[dict[str, Any]],
    ) -> None:

        path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

    # =========================================================
    # ID GENERATION
    # =========================================================

    def _next_id(
        self,
        records: list[dict[str, Any]],
    ) -> int:

        if not records:
            return 1

        ids = []

        for item in records:

            try:
                ids.append(
                    int(item.get("id", 0))
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        return max(ids, default=0) + 1

    # =========================================================
    # RECORD CONVERSION
    # =========================================================

    def _record_to_dict(
        self,
        record: Any,
    ) -> dict[str, Any]:

        if isinstance(record, dict):
            return dict(record)

        if hasattr(record, "model_dump"):
            return dict(record.model_dump())

        if hasattr(record, "dict"):
            return dict(record.dict())

        if hasattr(record, "__dict__"):
            return dict(record.__dict__)

        raise TypeError(
            f"Unsupported record type: {type(record)}"
        )

    # =========================================================
    # FIND BY FINGERPRINT
    # =========================================================

    def find_by_fingerprint(
        self,
        fingerprint: str,
    ) -> IncidentRecord | None:

        with self.lock:

            incidents = self._read(
                self.incidents_file
            )

        for incident in incidents:

            if (
                incident.get("fingerprint")
                == fingerprint
            ):

                return IncidentRecord(
                    incident
                )

        return None

    # =========================================================
    # FIND BY ERROR SIGNATURE
    # =========================================================

    def find_by_signature(
        self,
        signature: str,
        repository: str | None = None,
    ) -> IncidentRecord | None:

        """
        Used by IncidentHistoryService.

        Match the normalized error signature.

        If repository is supplied, prefer the same
        repository.
        """

        with self.lock:

            incidents = self._read(
                self.incidents_file
            )

        # First prefer same repository.
        if repository:

            for incident in incidents:

                if (
                    incident.get(
                        "error_signature"
                    )
                    == signature
                    and incident.get(
                        "repository"
                    )
                    == repository
                ):

                    return IncidentRecord(
                        incident
                    )

        # Fallback to signature-only match.
        for incident in incidents:

            if (
                incident.get(
                    "error_signature"
                )
                == signature
            ):

                return IncidentRecord(
                    incident
                )

        return None

    # =========================================================
    # GET INCIDENT
    # =========================================================

    def get_incident(
        self,
        incident_id: int,
    ) -> IncidentRecord | None:

        with self.lock:

            incidents = self._read(
                self.incidents_file
            )

        for incident in incidents:

            try:
                current_id = int(
                    incident.get("id")
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if current_id == incident_id:

                return IncidentRecord(
                    incident
                )

        return None

    # =========================================================
    # LIST INCIDENTS
    # =========================================================

    def list_incidents(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:

        with self.lock:

            incidents = self._read(
                self.incidents_file
            )

        incidents.reverse()

        return incidents[:limit]

    # =========================================================
    # SAVE INVESTIGATION
    # =========================================================

    def save_investigation(
        self,
        record: Any,
    ) -> IncidentRecord:

        data = self._record_to_dict(
            record
        )

        with self.lock:

            incidents = self._read(
                self.incidents_file
            )

            data["id"] = self._next_id(
                incidents
            )

            data.setdefault(
                "created_at",
                datetime.now(
                    timezone.utc
                ).isoformat(),
            )

            incidents.append(
                data
            )

            self._write(
                self.incidents_file,
                incidents,
            )

        return IncidentRecord(
            data
        )

    # =========================================================
    # ADD INCIDENT
    # =========================================================

    def add_incident(
        self,
        incident: dict[str, Any],
    ) -> IncidentRecord:

        return self.save_investigation(
            incident
        )

    # =========================================================
    # CUSTOMER QUERY
    # =========================================================

    def save_customer_query(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:

        with self.lock:

            queries = self._read(
                self.customer_queries_file
            )

            data = dict(data)

            data["id"] = self._next_id(
                queries
            )

            data.setdefault(
                "created_at",
                datetime.now(
                    timezone.utc
                ).isoformat(),
            )

            queries.append(data)

            self._write(
                self.customer_queries_file,
                queries,
            )

        return data

    def list_customer_queries(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        with self.lock:

            queries = self._read(
                self.customer_queries_file
            )

        queries.reverse()

        return queries[:limit]
    
    
    # =========================================================
# FIND BY EXTERNAL INCIDENT ID
# =========================================================

def find_by_incident_id(
    self,
    incident_id: str,
) -> IncidentRecord | None:

    """
    Find an incident using the externally visible
    incident ID, for example:

        DEMO-20260816-6A953B5B

    This is different from the internal numeric JSON id.
    """

    incident_id = str(incident_id).strip()

    if not incident_id:
        return None

    with self.lock:

        incidents = self._read(
            self.incidents_file
        )

    for incident in incidents:

        # External incident ID
        if str(
            incident.get("incident_id", "")
        ).strip() == incident_id:

            return IncidentRecord(
                incident
            )

        # Also support systems where the external ID
        # was stored as "id".
        if str(
            incident.get("id", "")
        ).strip() == incident_id:

            return IncidentRecord(
                incident
            )

    return None

    # =========================================================
    # UPDATE INCIDENT
    # =========================================================

    def update_incident(
        self,
        incident_id: int,
        updates: dict[str, Any],
    ) -> IncidentRecord | None:

        with self.lock:

            incidents = self._read(
                self.incidents_file
            )

            for item in incidents:

                try:
                    current_id = int(
                        item.get("id")
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if current_id == incident_id:

                    item.update(
                        updates
                    )

                    item["updated_at"] = (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    )

                    self._write(
                        self.incidents_file,
                        incidents,
                    )

                    return IncidentRecord(
                        item
                    )

        return None

    # =========================================================
    # ACTIVITY LOG
    # =========================================================

    def add_activity(
        self,
        activity_type: str,
        message: str,
        incident_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        activity = {

            "activity_type":
                activity_type,

            "message":
                message,

            "incident_id":
                incident_id,

            "metadata":
                metadata or {},

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }

        with self.lock:

            activities = self._read(
                self.activities_file
            )

            activities.append(
                activity
            )

            self._write(
                self.activities_file,
                activities,
            )

        return activity

    def list_activities(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        with self.lock:

            activities = self._read(
                self.activities_file
            )

        activities.reverse()

        return activities[:limit]

    # =========================================================
    # DELETE INCIDENT
    # =========================================================

    def delete_demo_incident(
        self,
        fingerprint: str,
    ) -> None:

        with self.lock:

            incidents = self._read(
                self.incidents_file
            )

            incidents = [
                item
                for item in incidents
                if item.get(
                    "fingerprint"
                ) != fingerprint
            ]

            self._write(
                self.incidents_file,
                incidents,
            )