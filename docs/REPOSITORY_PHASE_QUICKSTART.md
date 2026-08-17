# Repository Phase Quick Start

The existing project remains unchanged except for the new code-investigation/LLM layer.

## 1. Activate the existing Conda environment

```powershell
conda activate RCA
```

## 2. Go to the project root

```powershell
cd C:\path\to\RCA
```

## 3. Test the local repository scanner

```powershell
$env:PYTHONPATH="apps"
python apps/backend/scripts/test_repository_phase.py
```

The included sample repository is `apps/sample_code_project`.

Expected key finding:

```text
src/rate_limiter.py:7
self.max_requests = 2
```

## 4. Run the new tests

```powershell
python -m pytest -q apps/backend/tests/unit/code_investigation
```

## 5. Run the code-aware Groq phase

Set your key in `.env`:

```text
GROQ_API_KEY=your_key_here
```

Then:

```powershell
$env:PYTHONPATH="apps"
python apps/backend/scripts/run_code_aware_rca.py
```

The LLM receives the incident plus structured repository findings. It is prevented from returning a file/line location that was not actually found by the repository scanner.

## GitHub production adapter

The same investigation interface includes `GitHubRepositorySource`. It uses a shallow `git clone` of a public GitHub URL, scans the same supported files, and produces the same `RepositoryEvidence` structure. Local testing intentionally uses `LocalRepositorySource` so development does not depend on network access.

## Scope

This phase implements repository/code investigation and its structured LLM handoff. The persistent SQL incident-history layer (known-issue lookup, solution reuse, and incident logging) should be implemented as the following phase so that it can sit in front of this investigator without coupling repository scanning to storage.
