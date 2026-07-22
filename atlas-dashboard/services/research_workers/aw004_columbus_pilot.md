# ATLAS-WORKERS-004 — Columbus/Dublin Hotel Live Intake Pilot

**Status:** delivered; controlled live pilot COMPLETED 2026-07-21 (see
*Completed live pilot* below). **Scope:** the existing tracked Columbus/Dublin
pet-friendly hotel inventory only. **Module:**
`services/research_workers/columbus_pilot.py` (+ `cli.py columbus-hotel-pilot`).
`pilot_version` `1.0.0`.

This is the first controlled live operational intake. It builds deterministic
`HOTEL_POLICY_RESEARCH` assignments from committed authority, runs the approved
Nano Tier-1 extractor behind the existing spend airlock, validates every result,
routes it through the ATLAS-WORKERS-003 airlock, and persists safe
operator-review artifacts. **Nothing is published.**

## Completed live pilot (2026-07-21)

The first controlled live intake ran against the approved Nano snapshot
(`openai / gpt-5.4-nano-2026-03-17`) in two operator-approved stages: a
one-hotel canary (Sonesta Columbus Downtown), then the remaining hotels with
deterministic resume of the canary.

| Metric | Result |
| --- | --- |
| Authoritative hotels | 25 |
| Reused canary (no duplicate call) | 1 (Sonesta) |
| New live calls | 24 |
| Successful structured responses | 25 |
| Provider failures | 0 |
| **Routes** | **READY 3 / REVIEW 22 / RETRY 0 / REJECTED 0** |
| READY percentage | 12% (80% target NOT met) |
| Unsafe READY results | 0 |
| Total input tokens | 32,362 |
| Total output tokens | 8,466 |
| Total cumulative cost | $0.017058 |
| Production/site/deploy writes | 0 |

**Primary review causes (honest diagnosis — no gate was weakened to raise
READY):** word-number evidence normalization (the messier cohort states counts
as words like "two pets" while the validator requires the verbatim digit),
incomplete fee-basis vocabulary (non-canonical phrasing such as "per room per
night"), model self-contradiction (two conflicting values for one field from a
single source, deterministically caught), and silent under-extraction on generic
"pet-friendly" evidence. Every imperfect extraction was safely withheld to
REVIEW; the three READY hotels are clean, fully verbatim-evidenced, and
non-contradictory. The pilot infrastructure is accepted as successful; the 12%
READY rate is an honest baseline, not production-ready throughput, and is the
subject of the follow-up remediation sprint (ATLAS-WORKERS-005).

**Runtime artifacts are gitignored and are NOT committed.** All pilot output
(assignments, model/validated results, routing envelopes, operator summary,
candidate export) lives under `data/worker_runs/pettripfinder/columbus_hotel_pilot/`,
covered by `.gitignore` (`data/`). Only the pilot CODE and this document are
committed.

## Authoritative inventory

`launch_packages/pettripfinder/seed_businesses.csv`, category
`pet-friendly-hotels` → **25 hotels** (20 observed 2026-07-15 + 5 observed
2026-07-18, the latter also in `hotel_policy_facts.json`). Each row carries name,
address, phone, official `source_url`, `source_type`, `observed_at`, and evidence
text (`pet_policy`). No discovery, no Google Places, no browsing — the pilot reads
only tracked authority. Missing/unusable evidence is reported, never replaced.

## Assignment construction (deterministic)

One assignment per candidate: `listing_key = normalize_listing_key(name)` (lower
+ `&`→`and` + strip — matches the importer key convention, so the five verified
hotels key-match `hotel_policy_facts.json`); the single source document carries
the tracked evidence body verbatim (`content_hash` bound); `assignment_id =
col-pilot-<slug>-<hash12>` over the authoritative inputs. Identical inputs →
byte-identical assignment; a changed source/evidence/observed-at/contract/identity
→ distinguishable id. **Readiness** is decided before any call:
`READY_FOR_RESEARCH`, `BLOCKED_MISSING_EVIDENCE`, `BLOCKED_INVALID_CONTRACT`,
`BLOCKED_IDENTITY_CONFLICT`. Blocked assignments never reach the model.

## Live spend airlock

Live calls target **only** `openai / gpt-5.4-nano-2026-03-17` — no substitution,
no fallback, no availability inference. Requires `--live --confirm-spend`, the
`ATLAS_BENCHMARK_SPEND_AUTHORIZATION=YES_MAX_1_USD` token, and `OPENAI_API_KEY`
(presence only; value never read). Hard caps: ≤ $1.00 estimated, 1024 output
tokens/call, ≤ 1 transient retry, fail-closed on non-transient error (fail-fast on
a repeated non-transient signature). Credentials/headers/raw responses are never
printed or persisted.

## Execution & persistence

Per READY hotel: propose → validate → deterministic reconciliation → publication
eligibility → WORKERS-003 route → atomic persist. Provider failures are scored as
provider failures (RETRY/REJECTED), never hotel-policy failures; the model never
picks its own route; READY requires every airlock condition. Artifacts under the
gitignored `data/worker_runs/pettripfinder/columbus_hotel_pilot/`:
`assignments/`, `model_results/` (usage + parse outcome + sanitized error — never
raw text), `validated_results/`, `routing_envelopes/`, `failure_diagnostics/`,
plus top-level `operator_summary.json` and `candidate_export.json`. No production
inventory, launch CSV, site output, or deployment is ever written.

## Non-production candidate export

`candidate_export.json` is marked `NON_PRODUCTION` +
`HUMAN_REVIEW_REQUIRED_BEFORE_IMPORT`, `auto_import: false`. Results are bucketed
by route (READY / REVIEW / RETRY / REJECTED) with hotel identity, candidate id,
route + reasons, validated facts, verbatim quotes, sources, contradictions,
warnings, provider/model, prompt/validator versions, token usage, cost, assignment
hash, result hash, and routing-envelope id. READY candidates may appear but are
never auto-imported.

## Success criteria (reported, never engineered)

≥ 80% of executable hotels → READY; zero unsafe READY; 100% verbatim evidence for
READY facts; zero unresolved contradictions / forbidden inferences in READY; every
non-READY result has a deterministic reason; spend < $1.00. Missing the 80% target
is an honest diagnosis, not a reason to weaken any validator or routing rule.
`publication_eligible_accuracy` is reported as not measurable without ground truth
(a live intake has no expected answers).

## CLI

`python -m services.research_workers columbus-hotel-pilot`
— **dry-run** (default): discover, classify, print the operator checkpoint +
blockers; no network, no writes. **live** (`--live --confirm-spend`): run the
approved model, write gitignored artifacts; `--max-assignments`, `--assignment-filter`
for controlled testing. **report** (`--report`): print the persisted summary; no
calls. There is deliberately no publish/import command.
