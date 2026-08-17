from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.code_investigation import GitHubRepositorySource, LocalRepositorySource, RepositoryInvestigator
from backend.core.incident_history import IncidentHistoryRepository, IncidentHistoryService
from backend.core.investigation import IncidentDecisionEngine
from backend.core.llm.code_aware_rca import generate_code_aware_rca
from backend.core.rag import HistoricalRAGService
from backend.core.support import SupportResponseService


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified support-engineer incident response workflow.")
    parser.add_argument("--error", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--service", default=None)
    parser.add_argument("--route", default=None)
    parser.add_argument("--stack-trace", default=None)
    parser.add_argument("--db", default="apps/storage/incident_history.db")
    parser.add_argument("--rag-top-k", type=int, default=5)
    args = parser.parse_args()

    history = IncidentHistoryService(IncidentHistoryRepository(args.db))
    rag = HistoricalRAGService()
    engine = IncidentDecisionEngine(history)
    service = SupportResponseService(engine)
    active_sources = []

    def investigator_factory(repository: str, source_type: str) -> RepositoryInvestigator:
        if source_type == "github":
            source = GitHubRepositorySource(repository)
            active_sources.append(source)
            return RepositoryInvestigator(source)
        return RepositoryInvestigator(LocalRepositorySource(repository))

    source_type = "github" if args.repo.lower().startswith(("https://github.com/", "http://github.com/")) else "local"
    try:
        response = service.handle(
            args.error,
            args.repo,
            service=args.service,
            route=args.route,
            stack_trace=args.stack_trace,
            source_type=source_type,
            investigator_factory=investigator_factory,
            llm_rca=generate_code_aware_rca,
            rag_retriever=rag.retrieve,
            rag_top_k=args.rag_top_k,
        )
        print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))
    finally:
        for source in active_sources:
            source.cleanup()


if __name__ == "__main__":
    main()
