from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.core.code_investigation import LocalRepositorySource, RepositoryInvestigator


def main() -> None:
    parser = argparse.ArgumentParser(description="Test repository-aware code investigation locally.")
    parser.add_argument(
        "--repo",
        default="apps/sample_code_project",
        help="Local repository directory to scan.",
    )
    parser.add_argument(
        "--error",
        default="GET /products returns HTTP 429 Too Many Requests immediately for a new user",
        help="Incident/error text.",
    )
    parser.add_argument("--stack-trace", default=None)
    args = parser.parse_args()

    source = LocalRepositorySource(args.repo)
    investigator = RepositoryInvestigator(source)
    evidence = investigator.investigate(args.error, args.stack_trace)

    print("=" * 72)
    print("LOCAL REPOSITORY CODE INVESTIGATION")
    print("=" * 72)
    print(f"Repository : {evidence.repository}")
    print(f"Files      : {evidence.scanned_files}")
    print(f"Lines      : {evidence.total_lines}")
    print(f"Relevant   : {evidence.relevant_files}")
    print()

    for index, finding in enumerate(evidence.findings, start=1):
        print(f"[{index}] {finding.file_path}:{finding.line_start}")
        print(f"    Score  : {finding.score}")
        print(f"    Terms  : {', '.join(finding.matched_terms)}")
        for item in finding.evidence:
            print(f"    Evidence: {item}")
        print("    Context:")
        print("\n".join(f"      {line}" for line in finding.context.splitlines()))
        print()

    print("Summary:")
    print(evidence.investigation_summary)
    print("=" * 72)
    print("JSON:")
    print(json.dumps(evidence.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
