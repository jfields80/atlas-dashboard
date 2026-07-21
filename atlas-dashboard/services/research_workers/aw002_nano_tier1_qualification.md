# ATLAS-WORKERS-002 — GPT-5.4 Nano Tier-1 Qualification Decision

**Status:** APPROVED — validator-protected Tier-1 extraction worker.
**Decision type:** human operator qualification decision (recorded, binding).
**Subsystem:** `services/research_workers` (HOTEL_POLICY_RESEARCH worker).
**Product:** PetTripFinder hotel-policy extraction.

This record documents the operator's qualification decision for the candidate
low-cost extraction model evaluated under the ATLAS-WORKERS-002 live bakeoff. It
governs how the model may be used; it does **not** relax any Atlas validation
gate.

---

## Model snapshot

| Attribute | Value |
| --- | --- |
| Provider | `openai` |
| Model id (exact, dated snapshot) | `gpt-5.4-nano-2026-03-17` |
| Credential env var (name only; value never read into logs) | `OPENAI_API_KEY` |
| API base URL | `https://api.openai.com/v1` |
| Request shape | `max_completion_tokens` (not `max_tokens`); temperature omitted; `response_format: {"type": "json_object"}` |
| Pricing (operator-verified) | input $0.20 / M, cached input $0.02 / M, output $1.25 / M |
| Pricing source | Official OpenAI GPT-5.4 Nano model documentation |
| Pricing observed date | 2026-07-20 |

The selection is by **exact `(provider, model_id)`** only. There is no fallback
to a different model, snapshot, or undated alias (`eval_config.select_model`).

## Contract versions in force at qualification

| Contract | Version | Authority |
| --- | --- | --- |
| Prompt / extraction schema | `1.3.0` | `prompt.PROMPT_VERSION` |
| Deterministic validator | `1.2.0` | `model_eval.VALIDATOR_VERSION` |
| Worker data contract | `1.0.0` | `vocabulary.CONTRACT_VERSION` |
| Benchmark | `hotel_policy_columbus_v2` | `benchmarks/hotel_policy_columbus.json` |

Results produced under different prompt/validator versions are **not** directly
comparable; every run manifest records these versions next to the prompt hash.

---

## Approved role — Tier-1 first-pass extraction

GPT-5.4 Nano is approved to perform **first-pass hotel-policy extraction**: it
reads supplied official source content and proposes structured facts. It never
approves, publishes, changes a URL, or takes any action — it only proposes.

## Disallowed role — unrestricted autonomous publication

Nano is **not** approved for unrestricted, unattended publishing. It is a
proposer behind Atlas validation, never the publication authority. Formal
autonomous-winner qualification is **false** (see benchmark result): a model may
be crowned an autonomous winner only at a 100% exact-evidence match, and Nano
reached 29/30.

## Publication authority and review routing (binding)

1. Nano may perform first-pass extraction.
2. The Atlas deterministic validator (`evidence_validator`) and cross-source
   reconciliation (`reconciliation`) remain the **publication authority**. The
   model's output is untrusted input; a fact survives only if the validator can
   re-derive it from the assignment's own source documents.
3. A result may proceed automatically **only when all applicable publication
   gates pass** (`score_case.publication_eligible`: a clean `COMPLETED` result
   with an official source, no contradiction, and no forbidden inference).
4. Any result involving any of the following **must be withheld** and routed to
   human review (or a future stronger-model tier) — never auto-published:
   - evidence mismatch (exact-evidence miss on a published fact);
   - unsupported inference (any forbidden or non-verbatim fact);
   - contradictory authoritative sources (`CONTRADICTORY`);
   - missing official source (`NO_OFFICIAL_SOURCE`);
   - provider failure (transport/HTTP; the model never responded);
   - structural failure (unparseable model output → `FAILED`/`NEEDS_REVIEW`);
   - any validator warning requiring review (`NEEDS_REVIEW`).
5. The **100% exact-evidence qualification gate is not weakened.** The
   exact-evidence metric is scoped to *publication candidates* (facts a result
   actually publishes); a no-source / contradictory / human-review outcome that
   intentionally withholds a fact is never scored as a publishable evidence
   failure, but every fact that **is** published must still carry an exact
   verbatim evidence quote.

---

## Benchmark result (authoritative, preserved)

Live run: `gpt-5.4-nano-2026-03-17`, benchmark `hotel_policy_columbus_v2`,
10 cases × 3 repetitions = 30 assignments.

| Metric | Result |
| --- | --- |
| Benchmark correct | 30 / 30 |
| Structurally valid | 30 / 30 |
| Publication-eligible accuracy | 1.0 |
| Contradiction detection rate | 1.0 |
| Forbidden inferences | 0 |
| Prompt-injection failures | 0 |
| Exact-evidence match | 29 / 30 (0.9667) |
| Total estimated cost | $0.012507 |
| Publication-eligible / human-review / no-source | 21 / 3 / 6 |
| **Formal autonomous-winner qualification** | **false** (exact evidence 29/30, gate requires 100%) |

The single exact-evidence miss occurred in a **publication-eligible** result
(one valid-but-non-canonical evidence quote in one repetition), not in any
no-source or contradictory outcome. It is caught by the gate and routed to
review — exactly the Tier-1 boundary this decision establishes.

---

## How the guarantee is enforced (not by trust in the model)

- **Deterministic validator** re-derives every fact from source text after the
  model responds; unsupported AI output is rejected even when the model claims
  confidence.
- **Deterministic reconciliation** re-reads the sources itself, so an empty or
  one-sided model response can no longer hide a genuine cross-source
  contradiction.
- **Spending airlock**: an exact spend-authorization token, a hard $1.00 ceiling,
  per-call cumulative caps, a provider allowlist, and credential-presence checks
  (values never read into logs). A provider failure never triggers automatic
  fallback or model substitution.
- The offline FakeProvider oracle plus all mocked provider tests reproduce the
  contracts, validator, reconciliation, and scorer without any network call.

## Notes

- This is a controlled Tier-1 approval, not a redesign of any completed
  subsystem. OpenClaw is **not** installed or configured; the future invocation
  contract is documented separately in `openclaw_task_envelope.md`.
- Runtime benchmark reports are written under `data/` and are gitignored; they
  are diagnostic artifacts, not committed evidence.
