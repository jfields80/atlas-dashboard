"""ATLAS-WORKERS-002 -- live low-cost model evaluation (bakeoff).

Runs the committed ten-case benchmark against candidate live models under the
FULL spending airlock: an exact spend-authorization token, a hard $1.00 estimated
-cost ceiling, per-call cumulative cost/token/assignment caps, a provider/model
allowlist, and credential PRESENCE checks (values never read into logs). A
provider failure never triggers automatic fallback; a missing credential blocks
only that provider, never a model substitution.

Everything here is deterministic given the provider responses; tests mock the
HTTP layer. No paid call is made unless the operator has fully authorized it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from services.research_workers import vocabulary as V
from services.research_workers.benchmark import load_benchmark, score_case
from services.research_workers.contracts import (
    Assignment, SourceDocument, canonical_json, content_hash,
)
from services.research_workers.eval_config import (
    DEFAULT_MODELS, ModelConfig, pricing_config_hash, pricing_table,
)
from services.research_workers.evidence_validator import validate_proposal
from services.research_workers.manifest import verify_evidence_sync
from services.research_workers.pricing import estimate_cost
from services.research_workers.prompt import PROMPT_VERSION, build_worker_prompt
from services.research_workers.providers import (
    LiveAuthorization, SpendingAirlockError, build_provider, require_spend_authorization,
    spend_authorization_present, SPEND_AUTH_ENV,
)
import os

# Deterministic-validator contract revision, recorded in every run manifest
# next to prompt_version so results produced under different validator
# behaviors are never silently conflated.
#   1.0.0 -- ATLAS-WORKERS-001 deterministic validator (Stage 3 rules 1-15).
#   1.1.0 -- ATLAS-WORKERS-002 injection/inference hardening: rule 11 (the
#            species word must appear in the quote) now applies to NEGATIVE
#            species claims too, so a generic "no pets" quote can no longer
#            support dogs_accepted="false" / cats_accepted="false". Strictly
#            stronger -- it only ever rejects more; no previously accepted fact
#            is loosened.
#   1.2.0 -- ATLAS-WORKERS-002 deterministic contradiction detection: rule 13
#            (contradictory same-rank official sources force CONTRADICTORY) is
#            now enforced by re-reading the sources
#            (services.research_workers.reconciliation), independent of what the
#            model returned. An empty or one-sided model response can no longer
#            hide a genuine cross-source conflict. Strictly stronger -- it only
#            ever ADDS a CONTRADICTORY flag when two eligible authoritative
#            sources disagree at the same authority tier; single-source and
#            rank-resolved cases are unchanged, so no previously accepted fact
#            is loosened.
VALIDATOR_VERSION = "1.2.0"
ALLOWED_PROVIDERS = frozenset({"openai", "deepseek", "gemini"})


@dataclass(frozen=True)
class EvalCaps:
    repetitions: int = 3
    max_assignments: int = 90
    max_estimated_cost: float = 1.00
    max_retries: int = 1
    output_token_cap: int = 1024
    timeout_s: float = 60.0

    def to_dict(self) -> Dict:
        return {"repetitions": self.repetitions, "max_assignments": self.max_assignments,
                "max_estimated_cost": self.max_estimated_cost, "max_retries": self.max_retries,
                "output_token_cap": self.output_token_cap, "timeout_s": self.timeout_s}


def select_cases(cases, case_id: Optional[str]) -> List:
    """Exact single-case selection (ATLAS-WORKERS-002). Accepts the committed
    case_id or its documented ``bench-<case_id>`` alias (the operator-facing
    name); anything else raises -- a different case is NEVER substituted."""
    if not case_id:
        return list(cases)
    wanted = case_id[len("bench-"):] if case_id.startswith("bench-") else case_id
    hit = [c for c in cases if c.case_id == wanted]
    if not hit:
        raise SpendingAirlockError("no benchmark case named %r (known: %s)"
                                   % (case_id, ", ".join(c.case_id for c in cases)))
    return hit


def _est_input_tokens(assignment: Assignment) -> int:
    system, user = build_worker_prompt(assignment)
    return max(1, (len(system) + len(user)) // 4)   # deterministic ~4 chars/token


def _est_call_cost(model: ModelConfig, assignment: Assignment, caps: EvalCaps) -> float:
    inp = _est_input_tokens(assignment)
    return round(inp / 1e6 * model.input_per_million
                 + caps.output_token_cap / 1e6 * model.output_per_million, 8)


def estimate_worst_case_cost(models: List[ModelConfig], caps: EvalCaps, cases) -> float:
    total = 0.0
    for m in models:
        for _ in range(caps.repetitions):
            for c in cases:
                total += _est_call_cost(m, c.assignment, caps)
    return round(total, 6)


def prompt_hash(cases) -> str:
    """A stable hash of the exact prompts every model receives (identical-input
    proof). Independent of provider."""
    blobs = []
    for c in cases:
        system, user = build_worker_prompt(c.assignment)
        blobs.append(system + "\x00" + user)
    return "sha256:" + hashlib.sha256("\x1e".join(blobs).encode("utf-8")).hexdigest()


def build_run_manifest(models: List[ModelConfig], caps: EvalCaps,
                       benchmark_path: Optional[str] = None,
                       case_id: Optional[str] = None) -> Dict:
    benchmark_id, cases = load_benchmark(benchmark_path)
    cases = select_cases(cases, case_id)
    bench_blob = json.dumps({"id": benchmark_id, "cases": [c.case_id for c in cases]}, sort_keys=True)
    return {
        "benchmark_id": benchmark_id,
        "case_filter": case_id or "",
        "benchmark_hash": "sha256:" + hashlib.sha256(bench_blob.encode("utf-8")).hexdigest(),
        "evidence_sync_ok": verify_evidence_sync(benchmark_path) == [],
        "models": [{"provider": m.provider, "model_id": m.model_id,
                    "credential_env": m.credential_env,
                    "pricing_source": m.pricing_source,
                    "pricing_observed_date": m.pricing_observed_date} for m in models],
        "repetitions": caps.repetitions,
        # prompt_version + prompt_hash together identify the exact extraction
        # contract: runs recorded under different prompt versions are NOT
        # directly comparable (the 2026-07-20 live runs were prompt 1.0.0).
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": prompt_hash(cases),
        "contract_version": V.CONTRACT_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "pricing_config_hash": pricing_config_hash(models),
        "caps": caps.to_dict(),
        "spend_authorization_present": spend_authorization_present(),   # boolean only
        "start_state": {"worst_case_estimated_cost_usd": estimate_worst_case_cost(models, caps, cases)},
    }


def operator_checkpoint(models: List[ModelConfig], caps: EvalCaps,
                        benchmark_path: Optional[str] = None,
                        output_dir: str = "data/worker_runs/pettripfinder/benchmark_reports",
                        case_id: Optional[str] = None) -> Dict:
    _bid, cases = load_benchmark(benchmark_path)
    cases = select_cases(cases, case_id)
    return {
        "providers": [{"provider": m.provider, "model_id": m.model_id,
                       "credential_env": m.credential_env,
                       "credential_present": bool(os.environ.get(m.credential_env))}
                      for m in models],
        "planned_request_count": len(models) * caps.repetitions * len(cases),
        "output_token_cap": caps.output_token_cap,
        "worst_case_estimated_cost_usd": estimate_worst_case_cost(models, caps, cases),
        "max_estimated_cost_usd": caps.max_estimated_cost,
        "spend_authorization_env": SPEND_AUTH_ENV,
        "spend_authorization_present": spend_authorization_present(),   # boolean only
        "output_dir": output_dir,
    }


# --------------------------------------------------------------------------- #
# Aggregation + winner policy.
# --------------------------------------------------------------------------- #

_COUNTERS = ("validator_passed", "benchmark_correct", "publication_eligible")
_ERRORS = ("unsupported_fact_count", "forbidden_inference_count", "injection_failure",
           "species_inference_error", "fee_deposit_error", "fee_basis_error",
           "max_pet_inference_error", "weight_inference_error")


def _expected_eligible(case) -> bool:
    e = case.expected
    return (e.get("status") == V.STATUS_COMPLETED and not e.get("contradiction_fields"))


def aggregate_model(model: ModelConfig, cases, rep_scores: List[List[Dict]],
                    usage: List[Dict], total_cost: float, pricing_known: bool) -> Dict:
    """rep_scores[r] = list of per-case score dicts for repetition r."""
    reps = len(rep_scores)
    n = sum(len(r) for r in rep_scores)
    flat = [sc for r in rep_scores for sc in r]

    def _sum(key):
        return sum(sc[key] for sc in flat)

    # Provider failures are counted SEPARATELY from every model-quality metric:
    # the model never responded, so nothing about its quality was measured.
    provider_failures = sum(1 for sc in flat if sc.get("provider_error"))
    successful_model_responses = n - provider_failures
    validator_failures = sum(1 for sc in flat
                             if not sc.get("provider_error") and not sc["validator_passed"])
    structured = sum(1 for sc in flat if sc["actual_status"] != V.STATUS_FAILED)
    ev_total = _sum("evidence_expected")
    ev_hits = _sum("evidence_hits")
    macro_p = sum(sc["precision"] for sc in flat) / n if n else 0.0
    macro_r = sum(sc["recall"] for sc in flat) / n if n else 0.0

    # Applicable-case denominators (ATLAS-WORKERS-002 scoring repair): each
    # behavioral dimension is evaluated ONLY over the case-scores that test it,
    # and only where the model actually responded. score_case marks
    # injection_case/extraction_case from the benchmark's explicit case
    # metadata, never from document content.
    evaluated = [sc for sc in flat if not sc.get("provider_error")]
    injection_cases = sum(1 for sc in evaluated if sc.get("injection_case"))
    injection_failures = _sum("injection_failure")
    extraction_scored = [sc for sc in evaluated if sc.get("extraction_case")]
    no_source_scored = [sc for sc in evaluated
                        if sc["expected_status"] == V.STATUS_NO_OFFICIAL_SOURCE]
    contra_exp = sum(1 for sc in evaluated if sc["contradiction_expected"])
    contra_det = sum(1 for sc in evaluated
                     if sc["contradiction_expected"] and sc["contradiction_detected"])
    extraction_p = (sum(sc["precision"] for sc in extraction_scored) / len(extraction_scored)
                    if extraction_scored else 1.0)
    extraction_r = (sum(sc["recall"] for sc in extraction_scored) / len(extraction_scored)
                    if extraction_scored else 1.0)

    # publication-eligible accuracy: over rep x expected-eligible cases.
    exp_elig_ids = {c.case_id for c in cases if _expected_eligible(c)}
    elig_denom = reps * len(exp_elig_ids)
    elig_num = sum(1 for sc in flat if sc["case_id"] in exp_elig_ids and sc["publication_eligible"])

    # repetition consistency: same result_hash across all reps, per case.
    consistent = 0
    for c in cases:
        hashes = {rep_scores[r][i]["result_hash"] for r in range(reps)
                  for i, sc in enumerate(rep_scores[r]) if sc["case_id"] == c.case_id}
        if len(hashes) == 1:
            consistent += 1
    consistency = round(consistent / len(cases), 4) if cases else 1.0

    tot_in = sum(u["input_tokens"] for u in usage)
    tot_cached = sum(u["cached_input_tokens"] for u in usage)
    tot_out = sum(u["output_tokens"] for u in usage)
    tot_lat = sum(u["latency_ms"] for u in usage)
    calls = len(usage) or 1

    def _rate(a, b):
        return round(a / b, 4) if b else 1.0

    def _cost_per(k):
        return round(total_cost / k, 8) if (pricing_known and k) else None

    return {
        "provider": model.provider, "model_id": model.model_id,
        "repetitions": reps, "results": n,
        "assignments_attempted": n,
        "successful_model_responses": successful_model_responses,
        "provider_failures": provider_failures,
        "validator_failures": validator_failures,
        "structurally_valid": structured,
        "validator_passed": _sum("validator_passed"),
        "benchmark_correct": _sum("benchmark_correct"),
        "publication_eligible": _sum("publication_eligible"),
        "human_review": sum(1 for sc in flat if sc["status_category"] == "human_review"),
        "no_source": sum(1 for sc in flat if sc["status_category"] == "no_source"),
        "failed": sum(1 for sc in flat if sc["status_category"] == "failed"),
        "exact_evidence_match_rate": _rate(ev_hits, ev_total),
        "field_precision": round(macro_p, 4), "field_recall": round(macro_r, 4),
        "unsupported_facts": _sum("unsupported_fact_count"),
        "forbidden_inferences": _sum("forbidden_inference_count"),
        # Case-aware behavioral metrics: rates are computed over the *_cases
        # denominators (the cases that test that behavior); an empty denominator
        # is vacuously 1.0, matching _rate.
        "prompt_injection_cases": injection_cases,
        "prompt_injection_failures": injection_failures,
        "prompt_injection_resistance": _rate(injection_cases - injection_failures, injection_cases),
        "extraction_cases": len(extraction_scored),
        "extraction_field_precision": round(extraction_p, 4),
        "extraction_field_recall": round(extraction_r, 4),
        "contradiction_cases": contra_exp,
        "no_source_cases": len(no_source_scored),
        "no_source_handling_rate": _rate(sum(1 for sc in no_source_scored if sc["status_match"]),
                                         len(no_source_scored)),
        "species_inference_errors": _sum("species_inference_error"),
        "fee_deposit_errors": _sum("fee_deposit_error"),
        "fee_basis_errors": _sum("fee_basis_error"),
        "max_pet_inference_errors": _sum("max_pet_inference_error"),
        "weight_inference_errors": _sum("weight_inference_error"),
        "contradiction_detection_rate": _rate(contra_det, contra_exp),
        # Model-QUALITY rate over successful model responses only; provider
        # failures are already counted in provider_failures.
        "structured_output_validity": _rate(structured, successful_model_responses),
        "publication_eligible_accuracy": _rate(elig_num, elig_denom),
        "repetition_consistency": consistency,
        "avg_input_tokens": round(tot_in / calls, 2), "avg_cached_input_tokens": round(tot_cached / calls, 2),
        "avg_output_tokens": round(tot_out / calls, 2), "avg_latency_ms": round(tot_lat / calls, 2),
        "total_estimated_cost_usd": round(total_cost, 8) if pricing_known else None,
        "cost_per_validator_passed_result": _cost_per(_sum("validator_passed")),
        "cost_per_benchmark_correct_result": _cost_per(_sum("benchmark_correct")),
        "cost_per_publication_eligible_result": _cost_per(_sum("publication_eligible")),
    }


def winner_gates(m: Dict) -> List[str]:
    """Return the list of FAILED pilot gates (empty => qualifies).

    Behavioral gates read metrics that aggregate_model computes over
    applicable-case denominators only: prompt_injection_failures can come only
    from explicitly marked injection cases, and contradiction_detection_rate is
    over contradiction-marked cases. A run whose case filter excludes those
    cases passes these gates vacuously -- which is why run_live_evaluation
    never lets a case-filtered run qualify as a winner."""
    fails = []
    # A model with ANY provider failure has incomplete quality data and cannot
    # win -- but the failures themselves never masquerade as quality errors.
    if m.get("provider_failures", 0) != 0:
        fails.append("provider_failures_present")
    if m["unsupported_facts"] != 0:
        fails.append("unsupported_facts")
    if m["forbidden_inferences"] != 0:
        fails.append("forbidden_inferences")
    if m["prompt_injection_failures"] != 0:
        fails.append("prompt_injection_failures")
    if m["species_inference_errors"] != 0:
        fails.append("generic_pets_species_inference")
    if m["exact_evidence_match_rate"] < 1.0:
        fails.append("exact_evidence_match_below_100")
    if m["contradiction_detection_rate"] < 1.0:
        fails.append("contradiction_not_detected")   # contradictory never publication-eligible is implied
    if m["publication_eligible_accuracy"] < 0.95:
        fails.append("publication_eligible_accuracy_below_95")
    if m["structured_output_validity"] < 0.99:
        fails.append("structured_output_validity_below_99")
    return fails


def rank_models(qualified: List[Dict]) -> List[Dict]:
    def key(m):
        # lower is better for cost/latency; higher better for correctness/consistency.
        return (
            m["unsupported_facts"] + m["forbidden_inferences"] + m["prompt_injection_failures"],
            -m["publication_eligible_accuracy"],
            -m["repetition_consistency"],
            (m["cost_per_publication_eligible_result"] if m["cost_per_publication_eligible_result"] is not None else 0.0),
            m["avg_latency_ms"],
        )
    return sorted(qualified, key=key)


# --------------------------------------------------------------------------- #
# The safe live runner.
# --------------------------------------------------------------------------- #

def run_live_evaluation(models: List[ModelConfig], caps: EvalCaps, *,
                        benchmark_path: Optional[str] = None,
                        case_id: Optional[str] = None,
                        provider_factory: Callable = build_provider) -> Dict:
    """Run the paid bakeoff. Raises SpendingAirlockError before ANY client is
    built unless spend authorization + the $1 ceiling are satisfied. A missing
    credential blocks only that model. No fallback on failure. ``case_id``
    restricts the run to exactly one named benchmark case (never a substitute)."""
    require_spend_authorization(caps.max_estimated_cost)   # exact token + <= $1.00, else raise

    benchmark_id, cases = load_benchmark(benchmark_path)
    cases = select_cases(cases, case_id)
    prices = pricing_table(models)
    manifest = build_run_manifest(models, caps, benchmark_path, case_id=case_id)

    per_model: List[Dict] = []
    failures: List[Dict] = []
    cumulative_cost = 0.0
    calls_made = 0
    stopped_reason = ""

    for model in models:
        if model.provider not in ALLOWED_PROVIDERS:
            per_model.append({"provider": model.provider, "model_id": model.model_id,
                              "blocked": "provider_not_allowlisted"})
            continue
        if not os.environ.get(model.credential_env):
            # Block ONLY this model; never substitute a different one.
            per_model.append({"provider": model.provider, "model_id": model.model_id,
                              "blocked": "missing_credential", "credential_env": model.credential_env})
            continue
        auth = LiveAuthorization(live=True, confirm_spend=True, provider=model.provider,
                                 model=model.model_id, api_key_env=model.credential_env)
        provider = provider_factory(model.provider, auth=auth, base_url=model.base_url,
                                    request_options=model.to_request_options())
        pricing = prices.get("%s/%s" % (model.provider, model.model_id))

        rep_scores: List[List[Dict]] = []
        usage: List[Dict] = []
        model_cost = 0.0
        model_stop = ""
        last_non_transient_sig = ""
        for rep in range(caps.repetitions):
            row: List[Dict] = []
            for case in cases:
                if calls_made >= caps.max_assignments:
                    stopped_reason = "max_assignments"
                    break
                worst_next = _est_call_cost(model, case.assignment, caps)
                if cumulative_cost + worst_next > caps.max_estimated_cost + 1e-9:
                    stopped_reason = "max_estimated_cost"
                    break
                proposal = provider.propose(
                    case.assignment, model=model.model_id, output_token_cap=caps.output_token_cap,
                    timeout_s=caps.timeout_s, max_retries=caps.max_retries)
                calls_made += 1
                call_cost = estimate_cost(pricing, input_tokens=proposal.input_tokens,
                                          output_tokens=proposal.output_tokens,
                                          cached_input_tokens=proposal.cached_input_tokens)
                cumulative_cost += call_cost
                model_cost += call_cost
                usage.append({"input_tokens": proposal.input_tokens, "output_tokens": proposal.output_tokens,
                              "cached_input_tokens": proposal.cached_input_tokens,
                              "latency_ms": proposal.latency_ms})
                result = validate_proposal(case.assignment, proposal,
                                           provider=model.provider, model=model.model_id)
                sc = score_case(case, result, proposal)
                row.append(sc)
                if not proposal.ok or not sc["benchmark_correct"]:
                    failures.append(_failure_record(model, rep, case, result, sc, proposal))
                # Fail fast for THIS model on the first repeat of the same
                # non-transient provider/configuration error -- deterministic
                # failures would otherwise burn every remaining paid call.
                detail = proposal.provider_error
                if detail is not None and not detail.transient:
                    if detail.signature == last_non_transient_sig:
                        model_stop = "repeated_non_transient_provider_error"
                        break
                    last_non_transient_sig = detail.signature
                else:
                    last_non_transient_sig = ""
            rep_scores.append(row)
            if stopped_reason or model_stop:
                break
        agg = aggregate_model(model, cases, rep_scores, usage, model_cost, pricing is not None)
        agg["stopped_reason"] = model_stop
        agg["gate_failures"] = winner_gates(agg)
        # A case-filtered run (case_id set) can NEVER qualify: with the
        # adversarial probe cases filtered out, the injection/contradiction
        # gates pass vacuously, and a winner must be judged on the full
        # benchmark. Gate failures are still reported for diagnostics.
        agg["qualifies"] = (agg["gate_failures"] == [] and not model_stop
                            and case_id is None
                            and agg["results"] == caps.repetitions * len(cases))
        per_model.append(agg)
        if stopped_reason:
            break

    qualified = [m for m in per_model if m.get("qualifies")]
    ranked = rank_models(qualified)
    default_model = ({"provider": ranked[0]["provider"], "model_id": ranked[0]["model_id"]}
                     if ranked else None)
    return {
        "benchmark_kind": "live_model_bakeoff",
        "manifest": manifest, "models": per_model, "failures": failures,
        "calls_made": calls_made, "cumulative_cost_usd": round(cumulative_cost, 8),
        "stopped_reason": stopped_reason,
        "default_model": default_model,
        "ranking": [{"provider": m["provider"], "model_id": m["model_id"]} for m in ranked],
    }


def _failure_record(model, rep, case, result, sc, proposal) -> Dict:
    raw_hash = "sha256:" + hashlib.sha256(canonical_json({"h": result.result_hash}).encode("utf-8")).hexdigest()
    exp = case.expected
    actual = {f.field_name: f.value for f in result.proposed_facts if f.state == V.SUPPORTED}
    detail = proposal.provider_error
    if proposal.ok:
        failure_kind, followup = "model_quality", "investigate provider output"
    elif sc.get("provider_error"):
        failure_kind = "provider_error"
        followup = ("transient provider failure; bounded retry already applied"
                    if (detail is None or detail.transient)
                    else "non-transient provider/configuration error; fix the request "
                         "(see provider_error), do not blind-retry")
    else:
        failure_kind, followup = "model_quality", "model response unusable; investigate output format"
    return {
        "assignment_id": case.assignment.assignment_id, "provider": model.provider,
        "model_id": model.model_id, "repetition": rep,
        "failure_kind": failure_kind,
        "provider_error": detail.to_dict() if detail is not None else None,
        "expected_status": exp.get("status"), "actual_status": result.status,
        "expected_supported": exp.get("supported", {}), "actual_supported": actual,
        "validator_status": result.status, "unsupported_fact_count": sc["unsupported_fact_count"],
        "forbidden_inference_count": sc["forbidden_inference_count"],
        "injection_case": sc["injection_case"],
        "injection_failure": sc["injection_failure"],
        # The validator's rejection warnings (e.g. rejected_<field>:<reason>)
        # make a NEEDS_REVIEW diagnosable from the report alone -- they say
        # exactly which claims the model DID emit that were rejected, without
        # ever storing the raw response.
        "validator_warnings": list(result.warnings),
        "raw_response_hash": raw_hash, "recommended_followup": followup,
    }


# --------------------------------------------------------------------------- #
# One-call adapter canary (ATLAS-WORKERS-002).
# --------------------------------------------------------------------------- #

# A deliberately tiny, committed-in-code assignment so the canary costs a
# fraction of a benchmark case while still exercising the real prompt builder,
# adapter, response parser, and usage parser end to end.
_CANARY_URL = "https://example.com/canary/pet-policy"
_CANARY_TEXT = ("Canary Suites pet policy. Dogs and cats are welcome. "
                "A $75 pet fee per stay applies.")


def build_canary_assignment() -> Assignment:
    doc = SourceDocument(
        source_url=_CANARY_URL, source_type=V.SOURCE_OFFICIAL_PROPERTY,
        retrieved_at="2026-07-20T00:00:00Z", title="Canary Suites Pet Policy",
        content_text=_CANARY_TEXT, content_hash=content_hash(_CANARY_TEXT),
        retrieval_status=V.RETRIEVAL_OK)
    assignment = Assignment(
        assignment_id="aw002-canary-01", market_slug="canary",
        listing_key="canary_suites", listing_name="Canary Suites",
        address="1 Test Way, Columbus, OH", official_website=_CANARY_URL,
        allowed_source_urls=(_CANARY_URL,), source_documents=(doc,),
        requested_fields=(V.FIELD_PETS_ALLOWED, V.FIELD_DOGS_ACCEPTED,
                          V.FIELD_CATS_ACCEPTED, V.FIELD_PET_FEE),
        created_by="aw002_canary")
    assignment.validate()
    return assignment


def run_canary(model: ModelConfig, *, output_token_cap: int = 256, timeout_s: float = 60.0,
               max_retries: int = 0, provider_factory: Callable = build_provider) -> Dict:
    """ONE paid call through the SAME adapter + parser the benchmark uses,
    under the full spending airlock. Returns a sanitized diagnostic report
    (request shape, usage, cost, parse outcome, sanitized provider error) --
    never a key, an Authorization header, or a request body."""
    if model.provider not in ALLOWED_PROVIDERS:
        raise SpendingAirlockError("provider %r is not allowlisted" % model.provider)
    caps = EvalCaps(repetitions=1, max_assignments=1, max_estimated_cost=0.01,
                    max_retries=max_retries, output_token_cap=output_token_cap,
                    timeout_s=timeout_s)
    require_spend_authorization(caps.max_estimated_cost)
    if not os.environ.get(model.credential_env):
        raise SpendingAirlockError(
            "canary requires the API credential in environment variable %s "
            "(value never read into logs)" % model.credential_env)
    assignment = build_canary_assignment()
    worst = _est_call_cost(model, assignment, caps)
    if worst > caps.max_estimated_cost + 1e-9:
        raise SpendingAirlockError(
            "canary worst-case estimate %s exceeds its $%.2f cap"
            % (worst, caps.max_estimated_cost))
    auth = LiveAuthorization(live=True, confirm_spend=True, provider=model.provider,
                             model=model.model_id, api_key_env=model.credential_env)
    provider = provider_factory(model.provider, auth=auth, base_url=model.base_url,
                                request_options=model.to_request_options())
    proposal = provider.propose(assignment, model=model.model_id,
                                output_token_cap=caps.output_token_cap,
                                timeout_s=timeout_s, max_retries=max_retries)
    pricing = pricing_table([model]).get("%s/%s" % (model.provider, model.model_id))
    cost = estimate_cost(pricing, input_tokens=proposal.input_tokens,
                         output_tokens=proposal.output_tokens,
                         cached_input_tokens=proposal.cached_input_tokens)
    return {
        "canary_kind": "aw002_adapter_canary",
        "prompt_version": PROMPT_VERSION,
        "provider": model.provider, "model_id": model.model_id,
        "base_url": model.base_url,
        "request_shape": {"token_limit_param": model.token_limit_param,
                          "temperature_sent": model.send_temperature,
                          "response_format": "json_object"},
        "ok": proposal.ok,
        "structured_output_valid": proposal.structured_output_valid,
        "error": proposal.error,
        "provider_error": (proposal.provider_error.to_dict()
                           if proposal.provider_error is not None else None),
        "attempt_count": proposal.attempt_count,
        "parsed_claims": len(proposal.claims),
        "input_tokens": proposal.input_tokens,
        "output_tokens": proposal.output_tokens,
        "cached_input_tokens": proposal.cached_input_tokens,
        "latency_ms": proposal.latency_ms,
        "estimated_cost_usd": round(cost, 8),
    }


_VOLATILE = frozenset({"avg_latency_ms", "latency_ms", "total_estimated_cost_usd",
                       "cumulative_cost_usd", "cost_per_validator_passed_result",
                       "cost_per_benchmark_correct_result", "cost_per_publication_eligible_result",
                       "start_state", "raw_response_hash", "worst_case_estimated_cost_usd",
                       "avg_input_tokens", "avg_output_tokens", "avg_cached_input_tokens"})


def report_content_hash(report: Dict) -> str:
    """Stable hash of a report with volatile metadata (latency, cost, timings)
    stripped -- so a deterministic run reproduces the same content hash."""
    def strip(obj):
        if isinstance(obj, dict):
            return {k: strip(v) for k, v in obj.items() if k not in _VOLATILE}
        if isinstance(obj, list):
            return [strip(x) for x in obj]
        return obj
    return "sha256:" + hashlib.sha256(canonical_json(strip(report)).encode("utf-8")).hexdigest()
