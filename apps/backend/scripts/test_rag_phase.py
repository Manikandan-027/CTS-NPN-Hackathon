from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.rag import HistoricalRAGService


def main() -> None:
    incident = "Customers are unable to complete payment. Payment API is returning HTTP 500."
    rag = HistoricalRAGService()
    results = rag.retrieve(incident, top_k=5)

    print("=" * 72)
    print("CHROMADB RAG INTEGRATION TEST")
    print("=" * 72)
    print(f"Incident: {incident}")
    print(f"Retrieved: {len(results)}")
    assert results, "ChromaDB returned no historical incidents."
    for index, item in enumerate(results, 1):
        print(f"\n{index}. {item['id']}")
        print(f"   Similarity : {item['similarity']:.2%}")
        print(f"   Service    : {item['affected_service']}")
        print(f"   Category   : {item['category']}")
        print(f"   Severity   : {item['severity']}")
        print(f"   Root Cause : {item['root_cause']}")
        print(f"   Resolution : {item['resolution']}")
    print("\nRAG integration test passed.")


if __name__ == "__main__":
    main()
