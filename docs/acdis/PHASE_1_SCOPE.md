# Phase 1 scope

Phase 1 adds a manual, deterministic workflow for preparing a structured research case file and turning it into a Markdown opportunity report.

## What Phase 1 implements

- A manual JSON case-file format for operator-supplied research context
- Validation that preserves explicit evidence classifications and rejects unsupported defaults
- Deterministic Markdown rendering into the required report sections
- Safe report writing that uses the existing ACDIS path-fence safeguard
- A small standard-library CLI for rendering a case file into Markdown

## What remains manual

- The operator supplies the research content, evidence statements, competitor notes, and recommendation rationale.
- ACDIS validates the structure and preserves the operator's explicit evidence categories.
- ACDIS never invents evidence, classifications, conclusions, scores, or recommendations.

## Explicitly deferred capabilities

Phase 1 does not implement:

- live web crawling or scraping
- browser automation
- competitor discovery
- network requests or API calls
- model or LLM integration
- scoring, weighted rankings, or calculated market size
- autonomous GO/HOLD/REJECT decisions
- SEO generation or deployment work

## Boundaries

All Phase 1 work remains inside the approved ACDIS sandbox under acdis/, docs/acdis/, and tests/acdis/.
