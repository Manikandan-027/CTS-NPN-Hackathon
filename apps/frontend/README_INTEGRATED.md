# Integrated Frontend

Run from this directory:

```bat
npm install
npm run dev
```

The frontend uses Axios directly in the page/component that owns each endpoint call. There is no React Query dependency and no endpoint-function layer.

The RCA chatbot calls `POST /api/chat` and displays:
- LLM summary/answer
- current RCA object
- pipeline progress
- evidence
- exact code location when available
- human validation
- a developer-only knowledge-base form for COMPLETELY_NEW incidents

Backend base URL:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```
