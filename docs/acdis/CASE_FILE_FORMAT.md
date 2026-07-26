# Case file format

Phase 1 uses UTF-8 JSON for a manual research case file. The loader reads the file, validates it, constructs the in-memory model, and renders a deterministic Markdown report.

## Top-level fields

The JSON object must include:

- case_id: required string
- case_title: required string
- opportunity_name: required string
- target_market: required string
- proposed_directory_category: required string
- customer_type: required string
- user_problem: required string
- proposed_minimum_useful_pilot: required string
- likely_monetization_paths: required list of non-empty strings
- potential_data_moat_opportunities: required list of non-empty strings
- reasons_not_to_pursue: required list of non-empty strings
- next_research_actions: required list of non-empty strings
- competitors: required list of competitor objects
- evidence: required list of evidence objects

The following fields are optional:

- operator_notes: optional string
- proposed_wedge_ideas: optional list of strings
- unresolved_questions: optional list of strings
- operator_recommendation: optional value of GO, HOLD, or REJECT
- operator_recommendation_rationale: optional string

## Competitor object

Each competitor object must contain:

- competitor_id: required non-empty string
- name: required non-empty string

Optional competitor fields:

- supplied_urls: list of strings
- artifact_references: list of strings
- observed_monetization_methods: list of strings
- operator_notes: string

## Evidence object

Each evidence object must contain:

- evidence_id: required non-empty string
- evidence_type: required classification value
- statement: required non-empty string

Optional evidence fields:

- source_references: list of strings
- excerpt: string
- related_competitor_ids: list of strings
- supporting_evidence_ids: list of strings
- operator_notes: string

## Evidence classifications

The implemented loader accepts only these values:

- FACT
- INFERENCE
- HYPOTHESIS
- UNKNOWN

The renderer preserves the operator-supplied classification and renders each type into its own section.

## Validation rules

The validator rejects:

- missing required top-level fields
- blank required text values
- duplicate competitor IDs
- duplicate evidence IDs
- missing evidence classification
- unknown EvidenceType values
- competitor references that do not exist
- evidence references that do not exist
- FACT items without a source reference
- INFERENCE items without supporting evidence
- INFERENCE items whose supporting evidence does not include at least one FACT
- operator recommendations outside GO, HOLD, or REJECT

## CLI usage

Render a case file as Markdown:

```powershell
python -m acdis render-case docs\acdis\examples\sample_case.json --output docs\acdis\examples\sample_report.md
```

The CLI accepts:

- a required input path
- a required --output path
- an optional --overwrite flag

The CLI exits nonzero for malformed input, validation failure, unsafe output paths, or existing outputs without --overwrite.

## Deterministic rendering

The renderer preserves the operator's ordering and does not promote one evidence category into another. Rendering the same valid case twice produces byte-for-byte identical Markdown.

## Safe output-path rules

Report writing uses the approved-worktree path fence. Output paths outside the approved worktree are rejected.
