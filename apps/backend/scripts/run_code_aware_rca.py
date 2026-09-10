from __future__ import annotations

import argparse
import json

from backend.core.code_investigation import LocalRepositorySource, RepositoryInvestigator
from backend.core.llm.code_aware_rca import generate_code_aware_rca


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the code-aware LLM RCA phase against a local repository.")
    parser.add_argument("--repo", default="apps/sample_code_project")
    parser.add_argument(
        "--error",
        default="GET /products returns HTTP 429 Too Many Requests immediately for a new user",
    )
    parser.add_argument("--stack-trace", default=None)
    args = parser.parse_args()

    evidence = RepositoryInvestigator(LocalRepositorySource(args.repo)).investigate(
        args.error,
        args.stack_trace,
    )

    result = generate_code_aware_rca(
        incident=args.error,
        historical_evidence=[],
        repository_evidence=evidence.to_dict(),
        stack_trace=args.stack_trace,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
