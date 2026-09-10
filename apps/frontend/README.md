# RCA Console — AI Incident Root Cause Analysis Frontend

Developer/support console for the AI Incident RCA platform. This is the
**support-side** React app — it is separate from the customer-facing demo
payment application (Flask, http://127.0.0.1:5001).

## Stack
React 18 · Vite · React Router · TanStack Query · Axios · Tailwind CSS · Lucide icons

## Setup

```bash
npm install
npm run dev
```

The app runs at http://localhost:5173.

## Backend configuration

Set the FastAPI backend base URL in `.env`:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The backend must expose CORS to `http://localhost:5173`. No CORS workaround
is implemented in the frontend — configure it on the FastAPI side.

## What's inside

- **Dashboard** — live metrics, latest incident, pipeline visualization.
- **Incidents** — searchable/filterable table, click-through to detail.
- **Incident Detail** — all 14 RCA sections: summary, historical match,
  similarity gate, Top 20 / Hybrid Top 5 (collapsible), root cause, evidence,
  repository investigation, code location, confidence, resolution,
  prevention, human validation, knowledge base status. Renders a strong
  **COMPLETELY NEW INCIDENT** warning state when no root cause exists —
  it never fabricates one.
- **Validation** — pending incidents with Approve / Reject / Needs Review.
- **Customer Queries** — table of customer-submitted queries.
- **Activity** — chronological, human-readable pipeline timeline with
  expandable technical metadata.
- **Knowledge Base** — approved developer knowledge, entry detail, and an
  "Add verified knowledge" form used both from the KB page and from any
  COMPLETELY_NEW incident.
- **Settings** — the only place with the destructive demo reset control.

## Data policy

Nothing in this app is hard-coded. Every incident, confidence score, root
cause, and code location comes from the backend API listed in
`src/api/endpoints.js`. If a field isn't present in the API response, the
corresponding UI section is omitted or shows an explicit "unavailable" state
— it is never invented.

## Polling

- Latest incident: every 2s
- Activity log: every 2s
- Incident list: every 5s

All polling is handled by TanStack Query and never reloads the page.
