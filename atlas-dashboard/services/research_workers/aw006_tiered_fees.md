# ATLAS-WORKERS-006 — Tiered-Fee Safety Airlock

**Delivered scope:** a fail-closed safety airlock that prevents evidence
containing multiple distinct pet-fee amounts from reaching `READY` through a
flattened scalar `pet_fee`, plus the typed, immutable, additive
`PetFeeTerm` / `PetFeePolicy` contract that a future multi-term downstream can
consume. **Baseline:** `4f5a04d`. Version bumps: `FEE_POLICY_VERSION` `1.0.0`
(new), `CONTRACT_VERSION` unchanged `1.0.0`, `VALIDATOR_VERSION`
1.3.0 → **1.5.0**, `PROMPT_VERSION` 1.4.0 → **1.6.0**, `ROUTING_VERSION`
1.0.0 → **1.2.0**.

## Qualification status (explicit)

- **SAFETY AIRLOCK — QUALIFIED.** Evidence with ≥2 distinct pet-fee amounts can
  no longer route `READY` through a lossy scalar `pet_fee`. The scalar fee
  fields are withheld and the result routes `REVIEW`.
- **LIVE STRUCTURED FEE EXTRACTION — NOT QUALIFIED.** Across all six Stage-D
  live calls (three original + three remediation), Nano emitted **no**
  `fee_terms` and **no live `PetFeePolicy` was ever created**. The preferred
  structured outcome remains unproven with the live Tier-1 model. Tiered-fee
  extraction is **not** complete and must not be described as such.

The single scalar fields (`pet_fee` / `fee_currency` / `fee_basis`) cannot
faithfully represent a recurring fee with a cap, first-N/after-N tiers,
short/long-stay tiers, or a fee distinct from a refundable deposit. This sprint
does not weaken evidence, routing, or publication gates — it only adds a
representation and makes the fail-open path fail closed.

## 1. Five-hotel Stage-A evidence analysis (all OFFICIAL_PROPERTY, all *conditional*, none contradictory)

| Hotel | Structure |
| --- | --- |
| Aloft University District | recurring `$50` per_night **+ CAP** `$150` per_stay |
| Extended Stay Dublin | `$25` per_pet_per_day **first 6 nights**, then `$15` per_pet_per_day |
| Hyatt House OSU | `$75` per_stay (1–6 nights) **+ additional** `$100` cleaning (7–30 nights) |
| Sonesta Simply Dublin | `$75` per_pet (≤7 nights), `$150` (>7 nights) |
| Staybridge Dublin | `$75` per_stay (1–7 nights), `$150` per_stay (≥8 nights) |

Every one is legitimately CONDITIONAL, not contradictory. The prior single-value
schema flattened them, producing either a misleading single amount or a false
`CONTRADICTORY`.

## 2. Contract — additive `PetFeeTerm` / `PetFeePolicy` (typed, immutable)

`PetFeeTerm` keeps **role**, **basis**, and **scope** as DISTINCT dimensions:
- `role` ∈ {`RECURRING_CHARGE`, `ONE_TIME_CHARGE`, `CAP`, `DEPOSIT`} (a cap is never an ordinary charge; a refundable deposit is never a fee).
- `basis` ∈ {`per_day`, `per_night`, `per_stay`, `one_time`} (rate unit only).
- `scope` ∈ {`per_room`, `per_pet`, `policy_total`, `unstated`} (never inferred).
- `amount` — canonical decimal string ("50.00", via `Decimal`, never binary float, never "$50"); the raw wording lives in `evidence_quote`.
- `condition_type` ∈ {`unconditional`, `stay_length_range`} with **typed integer** `condition_min`/`condition_max` (or null) and `boundary_unit` ∈ {`nights`, `days`}.

`PetFeePolicy` is an ordered, deterministically-serialized set of terms with a
content hash. `WorkerResult.fee_policy: Optional[PetFeePolicy] = None` is
additive: omitted from the content/hash when `None`, so **every prior serialized
result and the committed benchmark keep their exact `result_hash`**; old
artifacts read back as `None`. `CONTRACT_VERSION` stays `1.0.0`. Deterministic
per-term validation verifies each term against a verbatim quote from a usable
official source (amount, currency, basis word, scope word when claimed, CAP
language for a cap, `deposit` for a deposit, each condition boundary), rejecting
invalid role/basis/scope, amounts/boundaries not in the quote, invented
boundaries, fee/deposit confusion, and recurring/flat basis mismatch. Same-source
reconciliation rules A–F dedup identical terms, keep mutually-exclusive tiers
separate (adjacent tiers that only touch are sequential, via strict `<` overlap),
preserve a recurring charge plus a cap as distinct roles, treat overlapping or
unconditional differing amounts as a genuine contradiction, and never merge a fee
with a refundable deposit. No hotel names, benchmark ids, or URLs drive any
decision.

## 3. Production downstream limitation (fail-closed)

The production importer and renderer (`hotel_profile.py`, `policy_compose.py`,
`site_*`) are **single-value only**, and this sprint does not change them.
Therefore a validated multi-term `PetFeePolicy` **can never route `READY`** — it
routes `REVIEW` with the deterministic reason
**`DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED`** (research-complete, not
publication-eligible). AW-006 is **READY-neutral**: its value is faithful
representation and honest routing, not a `READY` lift. The structured policy is
carried additively on the `WorkerResult`, the routing envelope, and the candidate
export so a future multi-term downstream can consume it without re-research.

## 4. First three-canary failure (Stage D, prompt 1.5.0)

The three approved canaries exposed a **systemic fail-open condition**. Under
prompt 1.5.0 Nano emitted **zero** `fee_terms`; `fee_policy` was `None` for all
three, and it flattened:

- **Aloft** → single scalar `$50` per night, **dropping the `$150` cap** →
  `COMPLETED` → **incorrectly READY** (misleading single value).
- **Staybridge** → single scalar `$75`, **dropping the `$150` long-stay tier** →
  **incorrectly READY** (misleading single value).
- **Extended Stay** → two conflicting scalars (`$15` vs `$25`) → `CONTRADICTORY`
  → REVIEW (already withheld).

Two records reached `READY` carrying a misleading single fee — a faithfulness
regression the airlock had to close.

## 5. Proven root cause

- The live format is `response_format: {"type":"json_object"}` — **not** a strict
  required JSON schema (deliberately, per AW-002 GPT-5 compatibility). So
  `fee_terms` was **permitted but not required**.
- The parser path was **correctly wired** (`fee_policy=None` with zero
  `rejected_fee_term` warnings ⇒ the model emitted no terms at all; the parser
  had nothing to reject).
- **Conflicting prompt instructions:** rule 5 told the model to "emit only a
  single unambiguous amount" for a fee, directly contradicting rule 12's
  instruction to use `fee_terms`. Nano favored the scalar output.

## 6. Offline safety remediation (non-weakening)

- **Prompt 1.5.0 → 1.6.0.** Rule 5's flatten-to-one instruction is removed;
  multi-amount evidence now makes `fee_terms` **mandatory** and forbids the
  scalar fee fields.
- **Deterministic multi-amount detector + scalar withholding (validator
  1.4.0 → 1.5.0).** `fee_terms.detect_multiple_fee_amounts` flags evidence
  stating ≥2 distinct pet-fee amounts (dedup identical; **exclude room rates and
  refundable deposits**; a single fee is not multi-term). When that signal exists
  and no validated `PetFeePolicy` is present, the validator **withholds** the
  scalar `pet_fee`/`fee_currency`/`fee_basis` and records
  `rejected_pet_fee:multi_term_fee_unrepresented` plus a `multi_term_fee_amounts:`
  diagnostic, so a flattened single value **can never reach READY**. The model is
  never the only safety control.
- **Routing 1.1.0 → 1.2.0.** New review reason **`STRUCTURED_FEE_REQUIRED`**; a
  validated policy still routes `REVIEW` / `DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED`.

**Detector validation (empirical, offline):** fires on 10 genuinely multi-term
seed hotels (the 5 above + La Quinta Dublin + all 4 Red Roof, each stating two
charge/cap amounts); **never** on the 10 committed benchmark cases (stays 10/10);
never on the 15 single/no-fee hotels; a fee plus a refundable deposit is not
multi-term (distinct scalar fields).

## 7. Remediation-canary results (Stage D, prompt 1.6.0)

Three canaries (Aloft, Extended Stay Dublin, Staybridge Dublin) into the
gitignored `data/worker_runs/pettripfinder/columbus_hotel_pilot_aw006_fixed/`:

| Hotel | Route + reasons | fee_terms emitted? | live PetFeePolicy? | scalar withheld? | detector fired? |
| --- | --- | --- | --- | --- | --- |
| Aloft | REVIEW · `CONTRADICTORY_OFFICIAL_SOURCES` | No | No | Yes | Yes (`150.00,50.00`) |
| Extended Stay | REVIEW · `STRUCTURED_FEE_REQUIRED` | No | No | Yes | Yes (`15.00,25.00`) |
| Staybridge | REVIEW · `CONTRADICTORY_OFFICIAL_SOURCES` | No | No | Yes | Yes (`150.00,75.00`) |

- **All three routed `REVIEW`; zero flattened `READY` results.**
- **All three had the scalar `pet_fee` fields withheld** (no misleading single
  value survived).
- **The detector triggered for all three** (`multi_term_fee_amounts:` diagnostic
  present in every case).
- **Nano still emitted no `fee_terms`, and no live `PetFeePolicy` was produced**
  (`fee_policy=None` for all three). Protection came from the deterministic
  backstop (Extended Stay → `STRUCTURED_FEE_REQUIRED`) and the pre-existing
  scalar-contradiction path (Aloft, Staybridge → `CONTRADICTORY`), never from the
  model producing structured terms. This validates the "model is never the only
  protection" design; it does **not** qualify live structured extraction.

## 8. Total live AW-006 canary spend

- Original three calls (prompt 1.5.0): **$0.002764**.
- Remediation three calls (prompt 1.6.0): **$0.002726**.
- **Combined: $0.005490** — well under the $1.00 airlock ceiling. Exact model
  `gpt-5.4-nano-2026-03-17` only; no Tier-2 invocation; no model substitution.

## 9. Baselines & runtime artifacts

- The AW-004 v1 (`READY 3 / REVIEW 22`) and AW-005 v2 (`READY 17 / REVIEW 8`)
  runtime baselines remain **untouched**.
- The original failed Stage-D canary artifacts
  (`columbus_hotel_pilot_aw006/`) and the remediation canary artifacts
  (`columbus_hotel_pilot_aw006_fixed/`) are preserved for comparison and remain
  **gitignored** (all of `data/worker_runs/` is a runtime artifact; nothing under
  `data/` is committed).

## 10. Offline replay (§11) — zero network

`fee_replay.replay_tiered_fee_records` reinterprets the persisted V2 candidate
export (read-only, 0 network calls, never overwriting V1/V2). Result for the five
tiered-fee hotels: **all 5 → `REQUIRES_NEW_MODEL_RESPONSE`.** The V2 run used
prompt 1.4.0, which had no `fee_terms` contract, so the raw structured terms were
never emitted or stored; a fresh Nano response would be required to produce a
structured policy — which, per §7, Nano still does not produce. No raw claim is
invented.

## AW-005 v2 launch-safe count under the stricter AW-006 policy

The AW-005 v2 result remains **historically 17 READY / 8 REVIEW** and its
persisted artifacts are unchanged. However, under the stricter AW-006 policy,
**two previously-READY Red Roof records** (Red Roof PLUS+ Columbus/Dublin and Red
Roof Downtown Convention Center) state a real recurring-fee-plus-cap
("$15/night capped at $105") that v2 flattened to a single `$15`; the AW-006
detector would correctly **withhold** them on a new run. Therefore the
**provisional launch-safe count is 15**, not 17, until those affected records are
reprocessed. This is a genuine safety catch, not a false positive; the stored
v1/v2 artifacts are not re-run and remain unchanged.

## The other REVIEW hotels (documented, unchanged)

La Quinta Columbus Dublin and Red Roof PLUS+ Worthington remain REVIEW on a
`refundable_deposit:number_not_in_quote` model-quality miss; Red Roof Inn West
Hilliard on a brand-source + fee-basis ambiguity. None is a tiered-fee case;
AW-006 does not alter deposit validation or source-authority policy. **Hyatt
House additionally has an independent `weight_limit` ambiguity ("50 pounds each
vs 75 pounds combined") that is out of scope; it remains REVIEW regardless of
fee-term reconciliation.**
