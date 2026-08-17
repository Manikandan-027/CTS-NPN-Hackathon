from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.core.code_investigation import GitHubRepositorySource, LocalRepositorySource, RepositoryInvestigator
from backend.core.incident_history import IncidentHistoryRepository, IncidentHistoryService
from backend.core.investigation import IncidentDecisionEngine
from backend.core.llm.code_aware_rca import generate_code_aware_rca


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the incident-history decision flow: reuse history or investigate current code."
    )
    parser.add_argument("--error", required=True, help="Current production incident/error message.")
    parser.add_argument("--repo", required=True, help="Local repository path or public GitHub URL.")
    parser.add_argument("--service", default=None)
    parser.add_argument("--route", default=None)
    parser.add_argument("--stack-trace", default=None)
    parser.add_argument("--db", default="apps/storage/incident_history.db")
    args = parser.parse_args()

    history = IncidentHistoryService(IncidentHistoryRepository(args.db))
    engine = IncidentDecisionEngine(history)
    active_sources: list[GitHubRepositorySource] = []

    def investigator_factory(repository: str, source_type: str) -> RepositoryInvestigator:
        if source_type == "github":
            source = GitHubRepositorySource(repository)
            active_sources.append(source)
            return RepositoryInvestigator(source)
        return RepositoryInvestigator(LocalRepositorySource(repository))

    source_type = "github" if args.repo.lower().startswith(("https://github.com/", "http://github.com/")) else "local"
    try:
        decision = engine.handle(
            args.error,
            args.repo,
            service=args.service,
            route=args.route,
            stack_trace=args.stack_trace,
            source_type=source_type,
            investigator_factory=investigator_factory,
            llm_rca=generate_code_aware_rca,
        )
        print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
    finally:
        for source in active_sources:
            source.cleanup()


if __name__ == "__main__":
    main()
