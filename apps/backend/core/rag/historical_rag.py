from __future__ import annotations

from typing import Any

from backend.core.embeddings.service import IncidentEmbeddingService
from backend.core.vector_db.repository import IncidentVectorRepository


class HistoricalRAGService:
    """Retrieve historical incidents from the existing local ChromaDB."""

    def __init__(
        self,
        embedding_service: IncidentEmbeddingService | None = None,
        repository: IncidentVectorRepository | None = None,
    ) -> None:
        self.embedding_service = embedding_service or IncidentEmbeddingService()
        self.repository = repository or IncidentVectorRepository()

    def retrieve(self, incident: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not incident or not incident.strip():
            raise ValueError("Incident cannot be empty.")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        processed = self.embedding_service.process_incident(
            incident_id="LIVE_INCIDENT",
            description=incident.strip(),
        )
        raw = self.repository.query(
            query_embedding=processed.embedding.tolist(),
            top_k=top_k,
        )
        return self._format(raw)

    @staticmethod
    def _format(raw: dict[str, Any]) -> list[dict[str, Any]]:
        ids = (raw.get("ids") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        results: list[dict[str, Any]] = []
        for i, incident_id in enumerate(ids):
            metadata = metas[i] if i < len(metas) and metas[i] else {}
            document = docs[i] if i < len(docs) else ""
            distance = float(distances[i]) if i < len(distances) else 1.0
            similarity = max(0.0, min(1.0, 1.0 - distance))

            results.append({
                "id": str(incident_id),
                "similarity": round(similarity, 6),
                "incident_description": str(document),
                "category": metadata.get("category", ""),
                "severity": metadata.get("severity", ""),
                "priority": metadata.get("priority", ""),
                "affected_service": metadata.get("service", metadata.get("affected_service", "")),
                "environment": metadata.get("environment", ""),
                "root_cause": metadata.get("root_cause", ""),
                "resolution": metadata.get("resolution", ""),
                "preventive_action": metadata.get("preventive_action", ""),
                "source_type": metadata.get("source_type", ""),
            })
        return results
