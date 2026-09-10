# Incident History + Decision Phase

This phase adds persistent incident memory without changing the existing ChromaDB or repository investigation modules.

## Flow

1. Receive the current incident and repository identifier.
2. Compute an exact incident fingerprint.
3. Search SQLite incident history.
4. If an existing solution is found, return it and skip repository scanning/LLM RCA.
5. If no solution is found, scan the current repository and run code-aware RCA.
6. Save the new root cause, exact code location, evidence, suggested fix, prevention and confidence.
7. Record audit activities for history misses, matches and new investigations.

## Storage

Default database: `apps/storage/incident_history.db`

SQLite is used deliberately for this phase so local testing requires no database server or new dependency. The persistence logic is isolated behind a repository and can later be migrated to PostgreSQL without changing the decision engine contract.

## Test

From the project root:

```powershell
$env:PYTHONPATH="apps"
python apps/backend/scripts/test_incident_history_phase.py
```

The test proves both branches:

- first occurrence -> `INVESTIGATE_AND_SAVE`
- repeated occurrence -> `REUSE_PREVIOUS_SOLUTION`

The second branch deliberately fails if the LLM is called, proving that a historical solution prevents unnecessary code investigation.

## Real workflow with Groq

Set your Groq key in the existing `.env` configuration, then run a local repository:

```powershell
$env:PYTHONPATH="apps"
python apps/backend/scripts/run_incident_workflow.py `
  --error "GET /products returns HTTP 429 Too Many Requests immediately for a new user" `
  --repo "apps/sample_code_project" `
  --service "sample-api" `
  --route "/products"
```

For a public GitHub repository:

```powershell
$env:PYTHONPATH="apps"
python apps/backend/scripts/run_incident_workflow.py `
  --error "GET /products returns HTTP 429 Too Many Requests" `
  --repo "https://github.com/OWNER/REPOSITORY" `
  --service "sample-api" `
  --route "/products"
```

The first occurrence scans the repository and calls the code-aware LLM. A repeated matching incident reads the SQLite history and returns the stored solution without calling the LLM or scanning the repository again.
