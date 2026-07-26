# Review Case Format (Phase 2)

Phase 2 adds an optional review object at the top level of the existing Phase 1 case JSON. Phase 1 files without review remain valid.

## CLI usage

- Render Phase 1 report:
  - python -m acdis render-case <input.json> --output <report.md> [--overwrite]
- Render Phase 2 review report:
  - python -m acdis review-case <input.json> --output <report.md> [--overwrite]

CLI behavior:

- input is required
- output is required
- --overwrite is explicit
- output path must remain inside the approved worktree
- existing output is rejected without --overwrite
- malformed JSON, validation failures, unsafe paths, and rendering failures return nonzero

## Deterministic output rules

- operator ordering is preserved
- identical input renders identically
- absent optional values render as Not supplied
- no current date or time is added
- no evidence category promotion
- no inferred matrix cells or wedge content

## Optional review object

Top-level key:

- review: object (optional)

Inside review:

### research_questions

- research_questions: list (optional)
- question_id: required, unique, non-empty string
- question_text: required, non-empty string
- status: required enum
  - OPEN
  - PARTIAL
  - ANSWERED
- related_evidence_ids: optional list of evidence IDs
- related_competitor_ids: optional list of competitor IDs
- operator_notes: optional string

Validation rules:

- duplicate question IDs rejected
- unknown statuses rejected
- unknown competitor references rejected
- unknown evidence references rejected
- OPEN may omit evidence
- PARTIAL must include evidence and include at least one FACT evidence item
- ANSWERED must include evidence and include at least one FACT evidence item

### comparison_dimensions

- comparison_dimensions: list (optional)
- dimension_id: required, unique, non-empty string
- label: required, non-empty string
- description: required, non-empty string
- why_it_matters: required, non-empty string
- operator_notes: optional string

Validation rules:

- duplicate dimension IDs rejected

### comparison_observations

- comparison_observations: list (optional)
- observation_id: required, unique, non-empty string
- competitor_id: required competitor reference
- dimension_id: required comparison dimension reference
- state: required enum
  - PRESENT
  - ABSENT
  - PARTIAL
  - UNKNOWN
  - NOT_APPLICABLE
- statement: required, non-empty string
- supporting_evidence_ids: optional list of evidence IDs
- operator_notes: optional string

Validation rules:

- duplicate observation IDs rejected
- unknown states rejected
- unknown competitor references rejected
- unknown dimension references rejected
- unknown evidence references rejected
- duplicate competitor/dimension pairs rejected
- PRESENT, ABSENT, PARTIAL require supporting evidence and at least one FACT evidence item
- UNKNOWN and NOT_APPLICABLE may omit evidence

### wedge_candidates

- wedge_candidates: list (optional)
- wedge_id: required, unique, non-empty string
- title: required, non-empty string
- target_user: optional string
- payer: optional string
- user_pain: optional string
- proposed_advantage: optional string
- competitor_gap: optional string
- supporting_evidence_ids: optional list of evidence IDs
- hypothesis_evidence_ids: optional list of evidence IDs
- reasons_the_wedge_might_fail: optional list of strings
- smallest_manual_test: optional string
- test_timebox: optional string
- cost_cap: optional string
- success_signal: optional string
- invalidating_signal: optional string
- test_participants: optional string
- dependencies: optional list of strings
- next_operator_action: optional string
- operator_notes: optional string

Validation rules:

- duplicate wedge IDs rejected
- unknown supporting evidence references rejected
- hypothesis_evidence_ids must reference HYPOTHESIS evidence only

Readiness rules:

- READY_FOR_MANUAL_TEST requires:
  - target_user
  - payer
  - user_pain
  - proposed_advantage
  - competitor_gap
  - at least one supporting evidence reference to FACT evidence
  - smallest_manual_test
  - test_timebox
  - success_signal
  - invalidating_signal
  - next_operator_action
- BLOCKED_INCOMPLETE lists all missing required fields
- BLOCKED_INVALID_BASIS lists invalid or inappropriate evidence references

Readiness output label:

- Structural test readiness - not an ACDIS business recommendation.

## Base evidence classification behavior

Phase 1 evidence_type remains required for all evidence items and must be one of:

- FACT
- INFERENCE
- HYPOTHESIS
- UNKNOWN

Classification is never defaulted silently.
