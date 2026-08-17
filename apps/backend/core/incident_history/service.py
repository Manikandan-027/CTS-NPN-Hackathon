from __future__ import annotations
import hashlib
import re
from typing import Any
from .models import HistoryLookupResult, IncidentHistoryRecord
from .repository import IncidentHistoryRepository

TOKEN_RE = re.compile(r"\b(?:4\d\d|5\d\d)\b|[a-zA-Z][a-zA-Z0-9_-]{2,}")
STOP_WORDS = {"the","and","for","with","from","this","that","was","are","has","have","user","users","request","requests","error","failed","failure","production","returns","return","immediately","new"}

class IncidentHistoryService:
    def __init__(self, repository: IncidentHistoryRepository) -> None:
        self.repository = repository

    @staticmethod
    def normalize(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"https?://", "", text)
        text = re.sub(r"[^a-z0-9\s/_-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def build_error_signature(cls, incident: str) -> str:
        tokens = []
        for token in TOKEN_RE.findall(cls.normalize(incident)):
            if token in STOP_WORDS or len(token) < 3:
                continue
            if token not in tokens:
                tokens.append(token)
        return "|".join(sorted(tokens))

    @classmethod
    def build_fingerprint(cls, incident: str, repository: str, service: str | None = None, route: str | None = None) -> str:
        canonical = "|".join([cls.normalize(incident), cls.normalize(repository), cls.normalize(service or ""), cls.normalize(route or "")])
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def lookup(self, incident: str, repository: str, service: str | None = None, route: str | None = None) -> HistoryLookupResult:
        fingerprint = self.build_fingerprint(incident, repository, service, route)
        exact = self.repository.find_by_fingerprint(fingerprint)
        if exact:
            self.repository.add_activity("HISTORY_MATCH", "Existing incident matched by exact fingerprint; repository investigation was skipped.", exact.id, {"match_type": "fingerprint"})
            return HistoryLookupResult(True, "fingerprint", exact)
        signature = self.build_error_signature(incident)
        by_signature = self.repository.find_by_signature(signature, repository)
        if by_signature:
            self.repository.add_activity("HISTORY_MATCH", "Existing incident matched by normalized error signature; repository investigation was skipped.", by_signature.id, {"match_type": "error_signature"})
            return HistoryLookupResult(True, "error_signature", by_signature)
        self.repository.add_activity("HISTORY_MISS", "No previous solved incident matched; code investigation is required.", None, {"fingerprint": fingerprint, "error_signature": signature})
        return HistoryLookupResult(False, None, None)

    def save_new_investigation(self, incident: str, repository: str, investigation: dict[str, Any], service: str | None = None, route: str | None = None, source_type: str = "local") -> IncidentHistoryRecord:
        record = {
            "fingerprint": self.build_fingerprint(incident, repository, service, route),
            "error_signature": self.build_error_signature(incident), "incident": incident,
            "repository": repository, "source_type": source_type, "service": service, "route": route,
            "root_cause": investigation["root_cause"], "file_path": investigation["file_path"],
            "line_start": investigation["line_start"], "line_end": investigation["line_end"],
            "evidence": investigation.get("evidence", []), "suggested_fix": investigation["suggested_fix"],
            "prevention": investigation.get("prevention", ""), "confidence": investigation.get("confidence", 0.0),
            "status": "OPEN",
        }
        saved = self.repository.save_investigation(record)
        self.repository.add_activity("NEW_INVESTIGATION_SAVED", "New code investigation and suggested solution were stored for future incidents.", saved.id, {"file_path": saved.file_path, "line_start": saved.line_start})
        return saved
