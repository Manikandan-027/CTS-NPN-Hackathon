# Phase: ChromaDB RAG Integration

This phase connects the existing local ChromaDB historical-incident store to the incident decision engine.

Flow:

1. Check SQLite incident history first.
2. If a previously investigated incident exists, reuse its stored solution.
3. For a new incident, query the existing ChromaDB collection for historical incidents.
4. Pass those historical RCA records to the code-aware LLM together with current repository evidence.
5. Save the new code investigation in SQLite.
6. Return both historical RAG evidence and current-code diagnosis.

Run:

```powershell
$env:PYTHONPATH="apps"
python apps/backend/scripts/test_rag_phase.py
python -m pytest apps/backend/tests/unit/test_rag_decision_engine.py -q
```

For a real Groq-backed workflow:

```powershell
$env:PYTHONPATH="apps"
python apps/backend/scripts/run_rag_decision_workflow.py --error "GET /products returns HTTP 429 Too Many Requests immediately for a new user" --repo "apps/sample_code_project" --service "sample-api" --route "/products"
```

The existing ChromaDB and SQLite storage remain local. PostgreSQL is intentionally not introduced in this phase.
