# ACDIS Phase 2 Scope

Phase 2 extends the Phase 1 manual case-file workflow with deterministic competitor comparison, evidence coverage auditing, wedge structural-readiness gating, and manual experiment cards.

## What Phase 2 implements

- Optional review section inside the existing case JSON format.
- Deterministic validation of review IDs, states, statuses, and references.
- Deterministic competitor comparison matrix using only operator-supplied dimensions and observations.
- Deterministic evidence coverage audit with evidence-type inventory counts.
- Structural wedge readiness gate:
  - READY_FOR_MANUAL_TEST
  - BLOCKED_INCOMPLETE
  - BLOCKED_INVALID_BASIS
- Deterministic manual experiment cards rendered from wedge candidates.
- New CLI command:
  - python -m acdis review-case <input.json> --output <report.md> [--overwrite]

## Operator-supplied versus ACDIS behavior

Operator-supplied:

- comparison dimensions
- comparison observations and states
- research-question status values
- wedge candidate content
- recommendation GO/HOLD/REJECT

ACDIS behavior:

- validates structure and references
- checks evidence-basis rules
- organizes supplied content into deterministic sections
- labels readiness based on structural completeness and evidence basis

## Matrix limitations

- No inferred observations.
- No inferred competitor strengths or weaknesses.
- Missing observation remains missing and is rendered as Not supplied.
- No weighted score or ranking is generated.

## Evidence coverage versus market gaps

Coverage output distinguishes:

- covered
- missing
- unknown
- not applicable
- fact-supported
- insufficient basis

Coverage labels do not claim market attractiveness. Missing research is not automatically a competitor weakness.

## Structural wedge readiness

Readiness is a structural gate only. It does not forecast outcomes, estimate demand, estimate revenue, or produce a recommendation.

## Manual experiment-card behavior

Experiment cards render only operator-supplied inputs and validated evidence references. If a field is absent, output shows Not supplied.

## Deferred automation

Phase 2 intentionally excludes crawling, scraping, browser automation, APIs, model calls, databases, scoring, ranking, and deployment behavior.
