# ATLAS-WORKERS-005 — Columbus Extraction Quality Remediation

**Status:** delivered (offline). **Scope:** the deterministic extraction
contract for `HOTEL_POLICY_RESEARCH`. **Trigger:** the ATLAS-WORKERS-004 Columbus
live pilot's honest 12% READY baseline. Contract bumps: **validator 1.2.0 → 1.3.0**,
**prompt 1.3.0 → 1.4.0**, `fee_basis` vocabulary extended.

Every change is **additive and non-weakening**: it recognizes evidence that was
already explicit but previously unrepresentable, and it raises READY only by
improving genuine extraction. Exact verbatim quotes and every strict publication
gate are preserved. Inference from bare plurals, non-verbatim quotes, and
contradictory sources is still rejected exactly as before.

## Pilot root causes → remediation

| Pilot finding | Remediation | Non-weakening argument |
| --- | --- | --- |
| `number_not_in_quote` — source states a count as a **word** ("limit two pets"), model emits digit `2` | Validator accepts a numeric value when its number appears in the quote as a digit **or** an explicit cardinal word (0–20). | A written number ("two") is an explicit statement of the count, not an inference from plural wording. A bare plural ("pets", "several pets") or the wrong word still fails. |
| `fee_basis_phrase_absent` — real phrasing "$50 **per room per night**" not in the closed vocab | Add `per_room_per_night` to `FEE_BASIS_VALUES`, with validator phrases + forbidden-phrase guards so `per_night`/`per_room` cannot claim it and `per_room_per_day` stays distinct. | Purely additive; the importer free-passes `fee_basis`; no benchmark case uses the new value; broader values are strictly guarded. |
| Silent under-extraction on generic "pet-friendly" evidence (0 facts) | Prompt rule 10: a generic pet-friendliness sentence supports `pets_allowed = "true"` (quoted verbatim, no species). | Behavioral guidance only; the validator still requires a verbatim quote and still forbids species inference (rule 4). |
| Model self-contradiction / **legitimate tiered fees** ("$25 … then … $15") | **Left as REVIEW by design.** Prompt rule 5 warns against collapsing tiered/conditional fees into one value; the validator still flags same-source conflicting values CONTRADICTORY → REVIEW. | Forcing a single fee would publish a misleading value — that would *loosen* faithfulness, so it is deliberately NOT done. |

## What changed

- `vocabulary.py` — `FEE_BASIS_PER_ROOM_PER_NIGHT` added to `FEE_BASIS_VALUES`.
- `evidence_validator.py` — `_numeric_supported` recognizes explicit cardinal
  words; `_FEE_BASIS_PHRASES` gains `per_room_per_night` with forbidden-phrase
  guards on `per_night`/`per_room`; rule 9 docstring updated.
- `model_eval.py` — `VALIDATOR_VERSION = "1.3.0"` (+ rationale).
- `prompt.py` — rule 5 (tiered-fee caution + per-room-per-night distinctness),
  rule 9 (per_room_per_night mapping, "emit fee_basis only with an explicit
  basis phrase", number-word instruction), rule 10 (generic pet-friendliness →
  pets_allowed); `PROMPT_VERSION = "1.4.0"`.
- `providers.py` — the deterministic FakeProvider oracle recognizes
  `per room per night` (ordered before `per night`).
- Tests: `test_extraction_remediation.py` (word-number accepted / bare-plural
  rejected / per_room_per_night guarded / Drury-style → READY / tiered fee →
  REVIEW / generic pet-friendly → pets_allowed / benchmark oracle unchanged /
  contract versions); existing version + prompt-hash pins updated to 1.4.0/1.3.0.

## Expected effect (confirmed live — see LIVE V2 PILOT RESULTS below)

Deterministically, the three Drury properties (word-number + per_room_per_night,
single fee) move from REVIEW to READY, and the generic "pet-friendly" hotels can
now publish `pets_allowed`. The tiered-fee hotels correctly remain REVIEW. The
actual live READY lift is measured by re-running the ATLAS-WORKERS-004 pilot with
the resume/skip-completed runner — no gate is relaxed to reach it. This
prediction was confirmed by the controlled live v2 rerun recorded below.

## LIVE V2 PILOT RESULTS

A controlled live re-run of the ATLAS-WORKERS-004 Columbus/Dublin pilot against
the remediated contract, into a separate gitignored v2 directory that preserves
the original v1 baseline for direct comparison.

### Run identity

| | |
| --- | --- |
| Baseline commit (before remediation) | `1563f8b` |
| AW-005 remediation commit | `21fe53c` |
| Model (exact, no substitution/fallback) | `gpt-5.4-nano-2026-03-17` |
| Prompt version | 1.4.0 |
| Validator version | 1.3.0 |
| Authoritative hotels | 25 |
| Reused canary (no duplicate network call) | 1 (Drury Inn & Suites Columbus Polaris) |
| New live calls | 24 |
| Successful new responses | 24 |
| Provider failures | 0 |

### Routing: v1 baseline vs v2 remediated

| Route | v1 (baseline) | v2 (remediated) |
| --- | --- | --- |
| READY | 3 / 25 — 12% | **17 / 25 — 68%** |
| REVIEW | 22 / 25 — 88% | 8 / 25 — 32% |
| RETRY | 0 | 0 |
| REJECTED | 0 | 0 |

**Improvement:** +14 READY hotels · +56 percentage points · **0 READY
regressions** · **0 unsafe READY results**.

### Remediation effects (14 hotels moved REVIEW → READY)

- **Explicit number-word normalization** helped **10** records (all 3 Drury plus
  Home2 Suites Dublin, Hyatt Place OSU, Hyatt Regency, Red Roof Downtown
  Convention Center, Red Roof Dublin, The Westin Great Southern, TownePlace
  Dublin) — previously `rejected_maximum_pets:number_not_in_quote` on "two"/
  "three pets".
- **`per_room_per_night` representation** helped the **three Drury** records
  (Dublin, Polaris, Plaza Downtown) — previously
  `rejected_fee_basis:fee_basis_phrase_absent` on "$50 per room per night".
- **Generic pet-friendly completeness** helped **four** records (Days Inn,
  Hampton Inn, Homewood Suites, The Plaza) — previously 0 facts; now publish
  `pets_allowed = "true"` from the verbatim pet-friendliness sentence.
- Some records benefited from **more than one** repair (the three Drury
  properties needed both the word-number and `per_room_per_night` fixes).

### Remaining REVIEW (8) — correctly withheld

| Hotel | Reason |
| --- | --- |
| Aloft University District | tiered/conditional pet fees |
| Extended Stay America Dublin | tiered fees and species quote warning |
| Hyatt House OSU Short North | conflicting fee and weight conditions |
| Sonesta Simply Suites Dublin | tiered fee and weight warning |
| Staybridge Suites Dublin | tiered/conditional fees |
| La Quinta Columbus Dublin | refundable-deposit evidence mismatch |
| Red Roof PLUS+ Worthington | refundable-deposit evidence mismatch |
| Red Roof Inn West Hilliard | fee-basis and source-authority ambiguity |

These eight were **correctly withheld**. Tiered/conditional pricing cannot be
represented faithfully by the current single-value `pet_fee` schema, so forcing a
single value would loosen faithfulness; the deposit and source-authority cases
are genuine validator withholds. **No validator or routing gate was weakened**,
every READY fact retained **exact verbatim evidence**, and no code was altered in
response to these normal hotel-specific REVIEW outcomes.

### Cost, tokens, and latency

| Metric | Value |
| --- | --- |
| Total input tokens | 37,912 |
| Total cached-input tokens | 0 |
| Total output tokens | 8,604 |
| New 24-call spend | $0.017434 |
| Cumulative v2 cost (incl. reused canary) | $0.018338 |
| Average cost per hotel | $0.000734 |
| Average cost per READY hotel | $0.001079 |
| Total model latency | 76,738 ms |
| Average latency per new successful call | 3,197.4 ms |

### Safety confirmations

- The original ATLAS-WORKERS-004 **v1 baseline remains preserved** (still
  READY 3 / REVIEW 22) for direct comparison.
- Both the **v1 and v2 runtime artifacts remain gitignored and uncommitted**
  (`data/worker_runs/pettripfinder/columbus_hotel_pilot{,_v2}/`).
- **No production inventory, website generation, deployment, OpenClaw, Tier-2,
  or model substitution occurred**; every READY fact is verbatim-evidenced.
