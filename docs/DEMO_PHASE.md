# Real-Time Demo Phase

## What this adds
- FastAPI `apps/backend/main.py`
- PostgreSQL incident history + activity tables
- Sample customer-facing page at `/demo`
- Support engineer console at `/support`
- Browser catches the demo HTTP 429 and reports it to the RCA backend
- Backend logs history, RAG, repository scan, LLM, persistence and support notification stages
- Default demo history is seeded so the first run demonstrates the known-incident path
- `POST /api/demo/reset` clears the demo incident so the next occurrence runs the new-incident investigation path

## Start

1. Copy `.env.example` to `.env` and set `GROQ_API_KEY` for new-incident testing.
2. Start PostgreSQL:

```powershell
docker compose up -d postgres
```

3. Install the new dependencies:

```powershell
pip install -r requirements-demo.txt
```

4. From the project root:

```powershell
$env:PYTHONPATH="apps"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

5. Open:
- http://127.0.0.1:8000/demo
- http://127.0.0.1:8000/support

## Demo sequence

### Known incident
Open `/demo`. The page automatically requests the product endpoint, receives HTTP 429, catches it, and reports it to the RCA API. Because the demo seeds the same incident in PostgreSQL, the system reuses the previous solution and skips code scanning.

### New incident / full LLM path
Open `/support`, click **Reset Demo History**, then open `/demo` again. The next incident has no SQL history match, so the pipeline performs ChromaDB retrieval, scans the local sample repository, calls Groq, saves the diagnosis, and publishes the support response.

The sample defect is intentionally at:
`apps/sample_code_project/src/rate_limiter.py:7`
