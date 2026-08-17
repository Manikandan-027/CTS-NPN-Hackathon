# Repository-Aware RCA Phase

This phase adds a repository investigation layer without changing the team's existing retrieval/RCA modules.

## What it does

1. Accepts a local repository directory for deterministic testing.
2. Supports public GitHub URLs through a separate `GitHubRepositorySource` adapter.
3. Scans the whole repository while excluding generated/vendor directories.
4. Builds a lightweight in-memory code index from supported source/configuration files.
5. Extracts incident signals such as status codes and technical terms.
6. Ranks relevant files and returns exact line-level findings with surrounding context.
7. Produces structured repository evidence that can be passed to the existing Groq RCA layer.

## Local test

From the project root:

```powershell
python apps/backend/scripts/test_repository_phase.py
```

Expected behavior for the included sample project:

```text
HTTP 429 Too Many Requests
        ↓
src/rate_limiter.py
        ↓
self.max_requests = 2
```

The scanner does not claim that the value `2` is universally wrong. It reports it as suspicious evidence for the support engineer/LLM to evaluate against the incident context.

## Why local testing is used

The production adapter can later consume a public GitHub URL. Local testing keeps the feature deterministic, avoids network/authentication problems during development, and uses the exact same investigation interface.
