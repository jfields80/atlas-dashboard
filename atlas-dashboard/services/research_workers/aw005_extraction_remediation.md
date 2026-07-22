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

## Expected effect (to be confirmed on a controlled live rerun)

Deterministically, the three Drury properties (word-number + per_room_per_night,
single fee) move from REVIEW to READY, and the generic "pet-friendly" hotels can
now publish `pets_allowed`. The tiered-fee hotels correctly remain REVIEW. The
actual live READY lift is measured by re-running the ATLAS-WORKERS-004 pilot with
the resume/skip-completed runner — no gate is relaxed to reach it.
