from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceFile:
    path: str
    language: str
    size_bytes: int
    line_count: int
    content: str


@dataclass(frozen=True)
class CodeFinding:
    file_path: str
    line_start: int
    line_end: int
    score: float
    matched_terms: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepositoryEvidence:
    source_type: str
    repository: str
    scanned_files: int
    skipped_files: int
    total_lines: int
    relevant_files: list[str]
    findings: list[CodeFinding]
    investigation_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": True,
            "source_type": self.source_type,
            "repository": self.repository,
            "scanned_files": self.scanned_files,
            "skipped_files": self.skipped_files,
            "total_lines": self.total_lines,
            "relevant_files": self.relevant_files,
            "findings": [finding.to_dict() for finding in self.findings],
            "investigation_summary": self.investigation_summary,
        }
