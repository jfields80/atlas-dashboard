"""ATLAS-WORKERS-001 -- benchmark loader, runner, and scorer (Stages 6/7).

Loads the committed ten-hotel benchmark, runs every case through the SAME
provider + validator pipeline, and scores the results against each case's
expected answer. The primary economic metric is total model/search expense
divided by the number of records that pass BOTH deterministic validation and
the expected-answer checks (accepted records). A model winner is never declared
here -- only per-run metrics for whatever provider/model was supplied.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from services.research_workers import vocabulary as V
from services.research_workers.contracts import Assignment, WorkerResult
from services.research_workers.evidence_validator import validate_proposal
from services.research_workers.pricing import ModelPricing, estimate_cost, pricing_for
from services.research_workers.providers import ResearchProvider

DEFAULT_BENCHMARK = Path(__file__).resolve().parent / "benchmarks" / "hotel_policy_columbus.json"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    description: str
    assignment: Assignment
    expected: Dict
    case_kind: str = ""
    provenance: Dict = None


@dataclass(frozen=True)
class Budget:
    """Hard spend/volume caps. ``exceeded`` returns a reason slug once a running
    total crosses a cap, so a live run stops BEFORE issuing the next call."""
    max_assignments: Optional[int] = None
    max_total_input_tokens: Optional[int] = None
    max_total_output_tokens: Optional[int] = None
    max_estimated_cost: Optional[float] = None

    def exceeded(self, *, ran: int, input_tokens: int, output_tokens: int, cost: float) -> Optional[str]:
        if self.max_assignments is not None and ran >= self.max_assignments:
            return "max_assignments"
        if self.max_total_input_tokens is not None and input_tokens > self.max_total_input_tokens:
            return "max_total_input_tokens"
        if self.max_total_output_tokens is not None and output_tokens > self.max_total_output_tokens:
            return "max_total_output_tokens"
        if self.max_estimated_cost is not None and cost > self.max_estimated_cost:
            return "max_estimated_cost"
        return None


def load_benchmark(path: Optional[str] = None) -> Tuple[str, List[BenchmarkCase]]:
    data = json.loads(Path(path or DEFAULT_BENCHMARK).read_text(encoding="utf-8"))
    cases = [BenchmarkCase(c["case_id"], c.get("description", ""),
                           Assignment.from_dict(c["assignment"]), c["expected"],
                           case_kind=c.get("case_kind", ""), provenance=c.get("provenance", {}))
             for c in data["cases"]]
    return (data["benchmark_id"], cases)


def _supported_map(result: WorkerResult) -> Dict[str, str]:
    return {f.field_name: f.value for f in result.proposed_facts if f.state == V.SUPPORTED}


def _quote_map(result: WorkerResult) -> Dict[str, str]:
    return {f.field_name: f.evidence_quote for f in result.proposed_facts if f.state == V.SUPPORTED}


def _doc_text(assignment: Assignment, url: str) -> str:
    for d in assignment.source_documents:
        if d.source_url == url:
            return d.content_text
    return ""


def score_case(case: BenchmarkCase, result: WorkerResult) -> Dict:
    exp = case.expected
    exp_supported: Dict[str, str] = dict(exp.get("supported", {}))
    forbidden = set(exp.get("forbidden_supported", []))
    contradiction_fields = set(exp.get("contradiction_fields", []))
    evidence_contains: Dict[str, str] = dict(exp.get("evidence_contains", {}))

    actual = _supported_map(result)
    quotes = _quote_map(result)
    actual_contradictions = {c.split(":")[0].strip() for c in result.contradictions}

    # Precision/recall over fields we have an opinion about (expected or
    # forbidden); genuinely-evidenced neutral extras (e.g. a service-animal
    # note) are not counted against precision.
    correct = sum(1 for f, v in exp_supported.items() if actual.get(f) == v)
    scored_positives = [f for f in actual if f in exp_supported or f in forbidden]
    precision = correct / len(scored_positives) if scored_positives else 1.0
    recall = correct / len(exp_supported) if exp_supported else 1.0

    forbidden_inference_count = sum(1 for f in forbidden if f in actual)

    # Every SUPPORTED fact must be verbatim in its cited source (safety net).
    unsupported = 0
    for f in result.proposed_facts:
        if f.state == V.SUPPORTED:
            txt = _doc_text(case.assignment, f.source_url)
            if not f.evidence_quote or f.evidence_quote not in txt:
                unsupported += 1

    ev_total = len(evidence_contains)
    ev_hits = sum(1 for f, sub in evidence_contains.items() if sub in quotes.get(f, ""))

    contradiction_expected = bool(contradiction_fields)
    contradiction_detected = contradiction_fields.issubset(actual_contradictions)

    status_match = result.status == exp["status"]

    # B. Deterministically validated: the validator ran and let nothing
    #    unverifiable through (no unsupported facts, not a provider failure).
    validator_passed = (result.status != V.STATUS_FAILED and unsupported == 0)
    # C. Benchmark-correct: matches expected status/fields/unknowns/contradiction
    #    and introduces no forbidden inference.
    benchmark_correct = (status_match and recall >= 1.0 and forbidden_inference_count == 0
                         and unsupported == 0
                         and (not contradiction_expected or contradiction_detected))
    # D. Publication-eligible: a clean COMPLETED research result with an official
    #    source, no contradiction, and no forbidden inference -- ready to ENTER
    #    the Atlas publication-review pipeline (still never auto-marked READY).
    has_official_source = bool(result.selected_source_url)
    publication_eligible = (benchmark_correct and result.status == V.STATUS_COMPLETED
                            and validator_passed and has_official_source
                            and not result.contradictions and forbidden_inference_count == 0)

    if result.status == V.STATUS_FAILED:
        category = "failed"
    elif result.status == V.STATUS_NO_OFFICIAL_SOURCE:
        category = "no_source"
    elif result.status in (V.STATUS_NEEDS_REVIEW, V.STATUS_CONTRADICTORY):
        category = "human_review"
    else:
        category = "completed"

    return {
        "case_id": case.case_id, "case_kind": case.case_kind,
        "expected_status": exp["status"], "actual_status": result.status,
        "status_match": status_match, "precision": round(precision, 4), "recall": round(recall, 4),
        "correct_fields": correct, "expected_field_count": len(exp_supported),
        "produced_supported": len(actual), "forbidden_inference_count": forbidden_inference_count,
        "unsupported_fact_count": unsupported, "evidence_expected": ev_total, "evidence_hits": ev_hits,
        "contradiction_expected": contradiction_expected, "contradiction_detected": contradiction_detected,
        "has_official_source": has_official_source, "status_category": category,
        "validator_passed": validator_passed, "benchmark_correct": benchmark_correct,
        "publication_eligible": publication_eligible, "result_hash": result.result_hash,
    }


def run_benchmark(provider: ResearchProvider, *, model: str, benchmark_path: Optional[str] = None,
                  pricing_table: Optional[Dict[str, ModelPricing]] = None,
                  output_token_cap: int = V.DEFAULT_OUTPUT_TOKEN_CAP,
                  timeout_s: float = V.DEFAULT_TIMEOUT_SECONDS,
                  max_retries: int = V.DEFAULT_MAX_RETRIES,
                  budget: Optional["Budget"] = None) -> Dict:
    benchmark_id, cases = load_benchmark(benchmark_path)
    pricing = pricing_for(pricing_table or {}, provider.name, model)
    pricing_known = pricing is not None

    per_case: List[Dict] = []
    results: List[WorkerResult] = []
    structured_valid = 0
    tot_in = tot_out = 0
    tot_latency = 0
    tot_cost = 0.0
    budget_stopped = False
    stop_reason = ""
    for i, case in enumerate(cases):
        # Stop BEFORE issuing the next call if a cap is already reached.
        if budget is not None:
            reason = budget.exceeded(ran=i, input_tokens=tot_in, output_tokens=tot_out, cost=tot_cost)
            if reason:
                budget_stopped = True
                stop_reason = reason
                break
        proposal = provider.propose(case.assignment, model=model, output_token_cap=output_token_cap,
                                    timeout_s=timeout_s, max_retries=max_retries)
        result = validate_proposal(case.assignment, proposal, provider=provider.name, model=model)
        results.append(result)
        if proposal.structured_output_valid:
            structured_valid += 1
        tot_in += result.input_tokens
        tot_out += result.output_tokens
        tot_latency += result.latency_ms
        tot_cost += estimate_cost(pricing, input_tokens=result.input_tokens,
                                  output_tokens=result.output_tokens,
                                  cached_input_tokens=result.cached_input_tokens)
        per_case.append(score_case(case, result))

    n = len(per_case)
    # Yield categories (Stage 4). Named precisely so a valid research result is
    # never confused with a publication-eligible one.
    structured_valid_results = structured_valid
    validator_passed_results = sum(1 for c in per_case if c["validator_passed"])
    benchmark_correct_results = sum(1 for c in per_case if c["benchmark_correct"])
    publication_eligible_results = sum(1 for c in per_case if c["publication_eligible"])
    human_review_results = sum(1 for c in per_case if c["status_category"] == "human_review")
    no_source_results = sum(1 for c in per_case if c["status_category"] == "no_source")
    failed_results = sum(1 for c in per_case if c["status_category"] == "failed")

    forbidden_total = sum(c["forbidden_inference_count"] for c in per_case)
    unsupported_total = sum(c["unsupported_fact_count"] for c in per_case)
    ev_total = sum(c["evidence_expected"] for c in per_case)
    ev_hits = sum(c["evidence_hits"] for c in per_case)
    contra_expected = sum(1 for c in per_case if c["contradiction_expected"])
    contra_detected = sum(1 for c in per_case if c["contradiction_expected"] and c["contradiction_detected"])
    macro_precision = sum(c["precision"] for c in per_case) / n if n else 0.0
    macro_recall = sum(c["recall"] for c in per_case) / n if n else 0.0

    def _rate(a, b):
        return round(a / b, 4) if b else 1.0

    def _cost_per(k):
        return round(tot_cost / k, 6) if (pricing_known and k) else None

    return {
        "benchmark_id": benchmark_id, "benchmark_kind": "offline_pipeline_validator_benchmark",
        "provider": provider.name, "model": model, "pricing_known": pricing_known,
        "note": ("Fake/offline run proves the CONTRACTS, VALIDATOR, REPOSITORY and SCORER only. "
                 "It does NOT select or validate a production AI model; a live-model comparison "
                 "is a separate authorized phase."),
        "budget_stopped": budget_stopped, "stop_reason": stop_reason,
        "assignments_attempted": n,
        "structured_valid_results": structured_valid_results,
        "validator_passed_results": validator_passed_results,
        "benchmark_correct_results": benchmark_correct_results,
        "publication_eligible_results": publication_eligible_results,
        "human_review_results": human_review_results,
        "no_source_results": no_source_results,
        "failed_results": failed_results,
        "structured_output_validity": _rate(structured_valid_results, n),
        "validator_pass_rate": _rate(validator_passed_results, n),
        "status_match_rate": _rate(sum(1 for c in per_case if c["status_match"]), n),
        "exact_evidence_match_rate": _rate(ev_hits, ev_total),
        "field_precision": round(macro_precision, 4),
        "field_recall": round(macro_recall, 4),
        "unsupported_fact_count": unsupported_total,
        "forbidden_inference_count": forbidden_total,
        "contradiction_detection_rate": _rate(contra_detected, contra_expected),
        "cost_per_validator_passed_result": _cost_per(validator_passed_results),
        "cost_per_benchmark_correct_result": _cost_per(benchmark_correct_results),
        "cost_per_publication_eligible_result": _cost_per(publication_eligible_results),
        "avg_input_tokens": round(tot_in / n, 2) if n else 0,
        "avg_output_tokens": round(tot_out / n, 2) if n else 0,
        "total_tokens": tot_in + tot_out,
        "total_estimated_cost_usd": round(tot_cost, 6) if pricing_known else None,
        "avg_latency_ms": round(tot_latency / n, 2) if n else 0,
        "cases": per_case,
    }
