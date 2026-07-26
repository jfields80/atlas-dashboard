# ACDIS Python Package

This package provides a small, isolated Python boundary for the Atlas Competitor Directory Intelligence Sandbox (ACDIS).

## Phase 1 boundaries

Phase 1 adds a manual, deterministic workflow for preparing research case files and rendering them into Markdown reports. The package remains side-effect free and does not perform network calls, database access, model-provider activity, crawling, deployment work, or production-system behavior.

## Package layout

- acdis/casefiles/ contains the manual case-file models, loader, and validation logic.
- acdis/reports/ contains the deterministic Markdown renderer and safe writer.
- acdis/safeguards/ contains the approved-worktree path-fence helper.

## Phase 1 workflow

Render a case file to Markdown with:

```powershell
python -m acdis render-case docs\\acdis\\examples\\sample_case.json --output docs\\acdis\\examples\\sample_report.md
```

## Phase 2 workflow

Render a deterministic competitor-comparison review pack with:

```powershell
python -m acdis review-case docs\\acdis\\examples\\sample_review_case.json --output docs\\acdis\\examples\\sample_review_report.md
```

## Documentation

- [docs/acdis/PHASE_1_SCOPE.md](../docs/acdis/PHASE_1_SCOPE.md)
- [docs/acdis/CASE_FILE_FORMAT.md](../docs/acdis/CASE_FILE_FORMAT.md)
- [docs/acdis/examples/sample_case.json](../docs/acdis/examples/sample_case.json)
- [docs/acdis/examples/sample_report.md](../docs/acdis/examples/sample_report.md)
- [docs/acdis/PHASE_2_SCOPE.md](../docs/acdis/PHASE_2_SCOPE.md)
- [docs/acdis/REVIEW_CASE_FORMAT.md](../docs/acdis/REVIEW_CASE_FORMAT.md)
- [docs/acdis/examples/sample_review_case.json](../docs/acdis/examples/sample_review_case.json)
- [docs/acdis/examples/sample_review_report.md](../docs/acdis/examples/sample_review_report.md)

## Targeted verification

Run the ACDIS tests with:

```powershell
python -m pytest tests\\acdis -v
```
