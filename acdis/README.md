# ACDIS Python Package

This package provides a small, isolated Python boundary for the Atlas Competitor Directory Intelligence Sandbox (ACDIS).

## Phase 0 boundaries

The package must remain side-effect free during import. It must not perform network calls, database access, model-provider activity, crawling, deployment work, or production-system behavior during Phase 0.

## Package layout

- contracts/ contains placeholder evidence and input contracts.
- safeguards/ contains narrow path-fencing helpers that validate the approved worktree.

## Targeted verification

Run the Phase 0 tests with:

```powershell
python -m pytest tests\\acdis -v
```
