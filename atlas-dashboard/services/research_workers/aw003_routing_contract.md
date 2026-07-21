# ATLAS-WORKERS-003 — Publication Routing & Escalation Airlock

**Status:** delivered. **Scope:** the `HOTEL_POLICY_RESEARCH` worker only.
**Module:** `services/research_workers/routing.py` (+ `repository.py` queue,
`cli.py route` command). `routing_version` `1.0.0`.

This is the deterministic boundary that converts a **validated** worker result
into exactly one operational destination. It is Atlas's decision, never the
model's — `vocabulary` states it directly: *"The worker NEVER emits
READY/REVIEW/REJECT — those are Atlas's decision."* Routing reads only the
validated `WorkerResult` (and, when present, the sanitized provider-error detail
on the `ModelProposal`); it never reads a model's free-form explanation, never
consults benchmark expected answers, never calls a model, and never reads the
wall clock.

## Route states

| Route | Meaning |
| --- | --- |
| `READY` | Eligible to proceed toward publication. Fail-closed (see airlock). |
| `REVIEW` | Safely withheld for human review, more research, or Tier-2. |
| `RETRY` | A bounded transient provider/transport failure; may be retried. |
| `REJECTED` | Structurally unsafe or permanently invalid; cannot enter review. |

## READY airlock (fail-closed)

A result reaches `READY` **only** when the model responded successfully, its
output was structurally valid, the validator produced `COMPLETED`, an official
source was selected, every supported fact is verbatim-evidenced against the
assignment's own source, at least one fact is published, and no contradiction,
blocking validator warning, prompt-injection-in-evidence, or un-named-species
inference is present. A missing, unknown, or unrecognized condition can never
default to `READY` — the decision falls through to `REJECTED`.

Routing adds two safety backstops **beyond** the validator (they only ever
withhold more): a `COMPLETED` fact whose evidence quote is itself injected
instruction text → `PROMPT_INJECTION_RISK`; a supported `dogs_accepted` /
`cats_accepted` fact whose quote does not name the species → `FORBIDDEN_INFERENCE`.

## Canonical reason codes

- **READY** — `PUBLICATION_ELIGIBLE`.
- **REVIEW** — `CONTRADICTORY_OFFICIAL_SOURCES`, `NO_OFFICIAL_SOURCE`,
  `EXACT_EVIDENCE_MISMATCH`, `INCOMPLETE_EXTRACTION`, `UNSUPPORTED_INFERENCE`,
  `FORBIDDEN_INFERENCE`, `VALIDATOR_WARNING`, `MODEL_QUALITY_FAILURE`,
  `PROMPT_INJECTION_RISK`, `SOURCE_AUTHORITY_AMBIGUITY`, `HUMAN_REVIEW_REQUIRED`.
- **RETRY** — `PROVIDER_TIMEOUT`, `PROVIDER_RATE_LIMITED`, `PROVIDER_SERVER_ERROR`,
  `TRANSPORT_FAILURE`.
- **REJECTED** — `INVALID_WORKER_CONTRACT`, `INVALID_ROUTING_ENVELOPE`,
  `PROVIDER_CONFIG_ERROR`, `PROVIDER_AUTH_ERROR`, `NON_TRANSIENT_PROVIDER_ERROR`,
  `CORRUPT_EVIDENCE_BUNDLE`, `UNSAFE_RESULT`.

Reasons are derived deterministically from result fields. Structural note: an
unparseable **model** response is `REVIEW` (`MODEL_QUALITY_FAILURE`) — safely
withheld and eligible for re-extraction; only an invalid **request/contract or
corrupt evidence bundle** is `REJECTED`.

## Routing envelope

An immutable, typed `RoutingEnvelope` records the route, reason codes, contract
versions (`worker_contract`, `prompt`, `validator`, `routing`), provider/model
snapshot, research status, publication eligibility, source identities, supported
facts with verbatim quotes, contradiction records, and the sanitized
provider-error detail when applicable. It never contains API keys, Authorization
headers, raw model responses, or machine secrets.

**Identity & idempotency.** `route_id` is a content hash of the authoritative
inputs (assignment id, `result_hash`, worker/prompt/validator/routing versions,
provider, model, route, reasons). `observed_at` / `run_id` are explicit inputs
excluded from identity, so identical inputs produce byte-identical envelopes.
Re-routing the same validated result writes the same queue file with the same
content (idempotent); a same-`route_id` file with different content is a
collision and is never silently overwritten.

## Queue persistence

`WorkerRepository.write_routing_envelope` writes atomically under the gitignored
worker runtime root (`data/worker_runs/pettripfinder/routing/`). It never writes
to PetTripFinder production inventory, launch data, site bundles, or deployment
directories.

## Tier-2 escalation contract (defined, disabled)

`Tier2EscalationRequest` + `build_tier2_escalation` package a withheld result
(envelope id, reasons, allowed sources, disputed fields, prior provider/model and
claims, contradictions, warnings, operator-supplied max spend + provider/model,
and a post-Tier-2 human-review flag) **without executing anything**.
`TIER2_ENABLED` is `False`; `escalate_tier2` always raises. No live model call is
authorized in this sprint, no provider/model is ever inferred from availability,
and a contradictory-source or no-source case never becomes publishable merely
because a Tier-2 model would answer.

## CLI

`python -m services.research_workers route` evaluates the committed benchmark
with the offline `FakeProvider` oracle, validates, and routes each result.
Dry-run by default (prints route + reason counts); `--write` persists envelopes
to the gitignored queue; `--assignment-id` routes exactly one case. No network
call, no production write, no publishing command.
