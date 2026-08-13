from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IncidentRecord:
    """
    One historical incident stored in ChromaDB.
    """

    incident_id: str

    description: str

    embedding: list[float]

    metadata: dict[str, Any]


@dataclass
class RetrievedIncident:
    """
    One incident returned from semantic retrieval.
    """

    incident_id: str

    description: str

    similarity: float

    distance: float

    metadata: dict[str, Any]