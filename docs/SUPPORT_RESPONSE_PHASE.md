# Unified Support Response Phase

This phase converts the existing history + ChromaDB RAG + repository investigation + code-aware LLM pipeline into one support-engineer-facing response.

## Decision

1. Check SQLite incident history first.
2. If a known incident is found, reuse its stored solution and skip repository investigation.
3. If it is new, retrieve historical evidence from ChromaDB.
4. Investigate the current repository.
5. Ask the code-aware LLM for a structured RCA grounded in the supplied evidence.
6. Save the investigation and solution to SQLite.
7. Return one stable `SupportResponse` object.

## Demo command

```powershell
$env:PYTHONPATH="apps"
python apps/backend/scripts/test_support_response.py
```

## Real workflow

```powershell
$env:PYTHONPATH="apps"
python apps/backend/scripts/run_support_response.py `
  --error "GET /products returns HTTP 429 Too Many Requests immediately for a new user" `
  --repo "apps/sample_code_project" `
  --service "sample-api" `
  --route "/products"
```

The output is designed to be the payload that a future API/notification layer can send to a support engineer.

PostgreSQL is intentionally not part of this phase; SQLite remains the local demo history store.
