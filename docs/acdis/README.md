# ACDIS Documentation Index

ACDIS is an isolated sandbox for documenting competitor-directory evidence without touching Atlas production systems. It is intentionally narrow and limited to manual-research preparation, evidence discipline, and safe boundaries during Phase 1.

## What ACDIS is and is not

ACDIS is a manual case-file and Markdown reporting workflow for evidence work. It is not a crawler, scraper, database-backed intelligence engine, deployment system, or production workflow.

## Phase 1 documents

- [PHASE_1_SCOPE.md](PHASE_1_SCOPE.md) describes the scope and handling rules for the manual-research workflow.
- [CASE_FILE_FORMAT.md](CASE_FILE_FORMAT.md) documents the JSON schema, validation rules, and CLI usage.
- [examples/sample_case.json](examples/sample_case.json) is a synthetic example case file that conforms to the implemented schema.
- [examples/sample_report.md](examples/sample_report.md) is the deterministic Markdown report produced by the CLI from the sample case.

## Scope boundaries

C:\Atlas, main, PetTripFinder, and the existing production systems are outside the Phase 1 scope. This sandbox exists only inside the approved ACDIS worktree.
