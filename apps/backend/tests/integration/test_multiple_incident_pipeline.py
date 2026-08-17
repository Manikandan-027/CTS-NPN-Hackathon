import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
APPS_DIR = ROOT / "apps"

for entry in (str(ROOT), str(APPS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from apps.backend.core.pipeline.multiple_incident_pipeline import (
    run_multiple_incident_pipeline,
)


def main():
    incidents = [
        "Customers are unable to complete payment. Payment API is returning HTTP 500 errors.",

        "Users are unable to login because authentication requests are timing out.",

        "Order creation is failing because the database connection pool is exhausted.",
    ]

    results = run_multiple_incident_pipeline(incidents)

    print()
    print("=" * 70)
    print("MULTIPLE INCIDENT ANALYSIS")
    print("=" * 70)

    for index, result in enumerate(results, start=1):

        print()
        print(f"INCIDENT {index}")
        print("-" * 70)

        print("Input:", result.get("input_incident", "N/A"))

        if result.get("status") == "failed":
            print("STATUS: FAILED")
            print("ERROR:", result.get("error"))
            continue

        rca = result.get("rca", {})

        root_cause = rca.get("root_cause", {})
        evidence = rca.get("evidence", {})
        confidence = rca.get("confidence", {})
        resolution = rca.get("resolution", {})
        prevention = rca.get("prevention", {})
        recurrence = rca.get("recurrence", {})

        print(
            "Root Cause:",
            root_cause.get("likely_root_cause", "N/A"),
        )

        print(
            "Evidence Count:",
            evidence.get("evidence_count", "N/A"),
        )

        print(
            "Confidence:",
            confidence.get("confidence_score", "N/A"),
        )

        print(
            "Confidence Level:",
            confidence.get("confidence_level", "N/A"),
        )

        print(
            "Resolution:",
            resolution.get("recommended_resolution", "N/A"),
        )

        print(
            "Prevention:",
            prevention.get("recommended_prevention", "N/A"),
        )

        print(
            "Recurring:",
            recurrence.get("is_recurring", "N/A"),
        )

        print(
            "Occurrence Count:",
            recurrence.get("occurrence_count", "N/A"),
        )

    print()
    print("=" * 70)
    print("MULTIPLE INCIDENT ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()