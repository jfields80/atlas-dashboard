"""ATLAS-WORKERS-001 -- worker CLI (Stage 9).

    python -m services.research_workers benchmark --provider fake
    python -m services.research_workers validate --result <path>

The CLI defaults to OFFLINE. A network client is never initialized unless the
spending airlock is fully satisfied: --live, --confirm-spend, an explicit
--provider and --model, and a matching API credential in the environment. API
keys are never read into output and the model is never silently switched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from services.research_workers import vocabulary as V
from services.research_workers.benchmark import Budget, run_benchmark
from services.research_workers.contracts import Assignment, WorkerResult
from services.research_workers.hotel_policy_worker import run_assignment
from services.research_workers.pricing import load_pricing
from services.research_workers.providers import (
    FakeProvider, LiveAuthorization, SpendingAirlockError, build_provider,
)
from services.research_workers.repository import WorkerRepository


def _build_provider(args) -> object:
    """Return a provider, enforcing the airlock for any non-fake/live path."""
    if args.provider == "fake" and not args.live:
        return FakeProvider()
    # Any other provider, or --live, must pass the full airlock.
    auth = LiveAuthorization(
        live=args.live, confirm_spend=args.confirm_spend, provider=args.provider,
        model=args.model or "", api_key_env=args.api_key_env)
    return build_provider(args.provider, auth=auth)   # raises SpendingAirlockError unless authorized


def _budget(args) -> Optional[Budget]:
    if not any((args.max_assignments, args.max_total_input_tokens,
                args.max_total_output_tokens, args.max_estimated_cost)):
        return None
    return Budget(
        max_assignments=args.max_assignments,
        max_total_input_tokens=args.max_total_input_tokens,
        max_total_output_tokens=args.max_total_output_tokens,
        max_estimated_cost=args.max_estimated_cost)


def _cmd_benchmark(args) -> int:
    provider = _build_provider(args)
    model = args.model or ("fake-extractor-v1" if provider.name == "fake" else "")
    if not model:
        raise SpendingAirlockError("a --model is required")
    pricing = load_pricing(args.pricing) if args.pricing else {}
    report = run_benchmark(
        provider, model=model, benchmark_path=args.benchmark, pricing_table=pricing,
        output_token_cap=args.output_token_cap, timeout_s=args.timeout,
        max_retries=args.max_retries, budget=_budget(args))
    if args.write_report:
        repo = WorkerRepository(Path(args.output_root) if args.output_root else None)
        path = repo.write_benchmark_report("%s_%s_%s" % (report["benchmark_id"], provider.name, model), report)
        report["_written_to"] = str(path)
    if args.json:
        print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    else:
        _print_summary(report)
    return 0


def _print_summary(r: dict) -> None:
    print("benchmark: %s (%s)   provider=%s model=%s"
          % (r["benchmark_id"], r["benchmark_kind"], r["provider"], r["model"]))
    print("  NOTE: %s" % r["note"])
    print("  assignments attempted        : %d" % r["assignments_attempted"])
    print("  structured_valid_results     : %d" % r["structured_valid_results"])
    print("  validator_passed_results     : %d" % r["validator_passed_results"])
    print("  benchmark_correct_results    : %d" % r["benchmark_correct_results"])
    print("  publication_eligible_results : %d" % r["publication_eligible_results"])
    print("  human_review_results         : %d" % r["human_review_results"])
    print("  no_source_results            : %d" % r["no_source_results"])
    print("  failed_results               : %d" % r["failed_results"])
    print("  exact evidence match rate    : %.3f" % r["exact_evidence_match_rate"])
    print("  field precision / recall     : %.3f / %.3f" % (r["field_precision"], r["field_recall"]))
    print("  unsupported / forbidden      : %d / %d" % (r["unsupported_fact_count"], r["forbidden_inference_count"]))
    print("  contradiction detection      : %.3f" % r["contradiction_detection_rate"])
    print("  avg tokens in/out            : %s / %s" % (r["avg_input_tokens"], r["avg_output_tokens"]))
    print("  total estimated cost         : %s" % ("(pricing not supplied)" if r["total_estimated_cost_usd"] is None
                                                   else "$%.6f" % r["total_estimated_cost_usd"]))
    for k in ("cost_per_validator_passed_result", "cost_per_benchmark_correct_result",
              "cost_per_publication_eligible_result"):
        print("  %-29s: %s" % (k, "n/a" if r[k] is None else "$%.6f" % r[k]))
    if r.get("budget_stopped"):
        print("  BUDGET STOPPED               : %s" % r["stop_reason"])


def _print_checkpoint(cp: dict) -> None:
    print("=== ATLAS-WORKERS-002 operator checkpoint (no paid call yet) ===")
    print("  planned request count      : %d" % cp["planned_request_count"])
    print("  output token cap           : %d" % cp["output_token_cap"])
    print("  worst-case estimated cost  : $%.6f" % cp["worst_case_estimated_cost_usd"])
    print("  max estimated cost ceiling : $%.2f" % cp["max_estimated_cost_usd"])
    print("  spend authorization env    : %s" % cp["spend_authorization_env"])
    print("  spend authorization present: %s" % cp["spend_authorization_present"])
    print("  output directory           : %s" % cp["output_dir"])
    print("  providers / credentials (presence only; values never read):")
    for p in cp["providers"]:
        print("    - %-9s %-24s env=%-16s present=%s"
              % (p["provider"], p["model_id"], p["credential_env"], p["credential_present"]))


def _cmd_evaluate(args) -> int:
    from services.research_workers.eval_config import DEFAULT_MODELS, select_model
    from services.research_workers.model_eval import (
        EvalCaps, build_run_manifest, operator_checkpoint, run_live_evaluation,
    )
    from services.research_workers.providers import SpendingAirlockError
    # Explicit single-model selection: --model (with --provider) targets exactly
    # one configured model and NEVER runs DEFAULT_MODELS or falls back to another
    # model. Omitting --model preserves the default multi-model bakeoff set.
    if args.model:
        try:
            models = [select_model(args.provider, args.model)]
        except KeyError as exc:
            raise SpendingAirlockError(str(exc))
    else:
        models = DEFAULT_MODELS
    caps = EvalCaps(repetitions=args.repetitions, max_assignments=args.max_assignments or 90,
                    max_estimated_cost=(args.max_estimated_cost if args.max_estimated_cost is not None else 1.00),
                    max_retries=args.max_retries, output_token_cap=args.output_token_cap,
                    timeout_s=args.timeout)
    cp = operator_checkpoint(models, caps, args.benchmark, case_id=args.case_id)
    _print_checkpoint(cp)

    repo = WorkerRepository(Path(args.output_root) if args.output_root else None)
    if not args.live:
        manifest = build_run_manifest(models, caps, args.benchmark, case_id=args.case_id)
        repo.write_benchmark_report("aw002_run_manifest", manifest)
        print("\nDRY RUN (no --live): manifest written; no network client constructed, no paid call.")
        return 0
    # Live path: the airlock decides. A missing credential blocks only that model.
    try:
        report = run_live_evaluation(models, caps, benchmark_path=args.benchmark,
                                     case_id=args.case_id)
    except SpendingAirlockError as exc:
        print("\nLIVE BENCHMARK BLOCKED BY AIRLOCK: %s" % exc)
        print("No network client was constructed and no paid call was made.")
        return 0
    path = repo.write_benchmark_report("aw002_live_bakeoff", report)
    print("\nlive bakeoff complete: calls=%d cost=$%.6f default_model=%s"
          % (report["calls_made"], report["cumulative_cost_usd"], report["default_model"]))
    print("report:", path)
    return 0


def _cmd_canary(args) -> int:
    """ONE live call through the SAME adapter + parser the benchmark uses.
    Prints a sanitized diagnostic report (never a key, header, or request
    body). Exit 0 when the model responded and parsed; 5 otherwise."""
    from services.research_workers.eval_config import select_model
    from services.research_workers.model_eval import run_canary
    if not (args.live and args.confirm_spend):
        raise SpendingAirlockError("canary makes ONE paid call: requires --live and --confirm-spend")
    try:
        model = select_model(args.provider, args.model)
    except KeyError as exc:
        raise SpendingAirlockError(str(exc))
    report = run_canary(model, output_token_cap=args.output_token_cap,
                        timeout_s=args.timeout, max_retries=args.max_retries)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 5


def _print_routing_summary(summary: dict, envelopes: list, written: int, wrote: bool) -> None:
    print("=== ATLAS-WORKERS-003 routing summary (offline; no model call, no production write) ===")
    print("  total routed        : %d" % summary["total"])
    for r in ("READY", "REVIEW", "RETRY", "REJECTED"):
        print("  %-20s: %d" % (r, summary["routes"].get(r, 0)))
    print("  reason codes:")
    for code, n in summary["reasons"].items():
        print("    - %-32s %d" % (code, n))
    print("  per assignment:")
    for e in envelopes:
        print("    - %-34s %-9s %s" % (e.assignment_id, e.route, ",".join(e.reason_codes)))
    if wrote:
        print("  wrote %d routing envelope(s) to the gitignored routing queue" % written)
    else:
        print("  DRY RUN: no envelopes written (pass --write to persist to the gitignored queue)")


def _cmd_route(args) -> int:
    """Deterministically route validated worker results into the
    READY/REVIEW/RETRY/REJECTED airlock. Offline: it evaluates the committed
    benchmark with the deterministic FakeProvider oracle (never a model call),
    validates each result, and routes it. Dry-run by default; --write persists
    immutable envelopes to the gitignored routing queue. No production write."""
    from services.research_workers.benchmark import load_benchmark
    from services.research_workers.evidence_validator import validate_proposal
    from services.research_workers.model_eval import VALIDATOR_VERSION, select_cases
    from services.research_workers.prompt import PROMPT_VERSION
    from services.research_workers.routing import route_result, summarize_envelopes

    provider = FakeProvider()          # offline oracle; routing itself never calls a model
    _bid, cases = load_benchmark(args.benchmark)
    cases = select_cases(cases, args.assignment_id)          # exact id or bench- alias; never substitutes
    prompt_version = args.prompt_version or PROMPT_VERSION
    validator_version = args.validator_version or VALIDATOR_VERSION

    envelopes = []
    for case in cases:
        proposal = provider.propose(case.assignment, model="fake-extractor-v1")
        result = validate_proposal(case.assignment, proposal, provider=provider.name,
                                   model="fake-extractor-v1")
        envelopes.append(route_result(
            case.assignment, result, proposal, prompt_version=prompt_version,
            validator_version=validator_version, observed_at=args.observed_at, run_id=args.run_id))

    summary = summarize_envelopes(envelopes)
    written = 0
    if args.write:
        repo = WorkerRepository(Path(args.output_root) if args.output_root else None)
        for env in envelopes:
            repo.write_routing_envelope(env)
            written += 1
    _print_routing_summary(summary, envelopes, written, wrote=args.write)
    if args.json:
        print(json.dumps({"summary": summary, "envelopes": [e.to_dict() for e in envelopes]},
                         sort_keys=True, ensure_ascii=False, indent=2))
    return 0


def _cmd_manifest(args) -> int:
    from services.research_workers.manifest import validate_manifest, verify_evidence_sync
    sync = verify_evidence_sync(args.benchmark)
    gates = validate_manifest(args.benchmark)
    problems = sync + gates
    if problems:
        print("BENCHMARK MANIFEST/EVIDENCE-SYNC FAILED:")
        for p in problems:
            print("  - %s" % p)
        return 4
    print("benchmark manifest OK: 10 cases, evidence in sync with the tracked launch package, all gates pass")
    return 0


def _cmd_validate(args) -> int:
    if args.result:
        result = WorkerResult.from_dict(json.loads(Path(args.result).read_text(encoding="utf-8")))
        expected = result.compute_hash()
        ok = (result.result_hash == expected)
        out = {"assignment_id": result.assignment_id, "status": result.status,
               "supported_facts": sum(1 for f in result.proposed_facts if f.state == V.SUPPORTED),
               "contradictions": list(result.contradictions),
               "stored_hash": result.result_hash, "recomputed_hash": expected,
               "hash_ok": ok}
        print(json.dumps(out, sort_keys=True, ensure_ascii=False, indent=2))
        return 0 if ok else 2
    if args.assignment:
        assignment = Assignment.from_dict(json.loads(Path(args.assignment).read_text(encoding="utf-8")))
        provider = _build_provider(args)
        model = args.model or ("fake-extractor-v1" if provider.name == "fake" else "")
        result = run_assignment(assignment, provider, model=model, output_token_cap=args.output_token_cap,
                                timeout_s=args.timeout, max_retries=args.max_retries)
        if args.write_report:
            WorkerRepository(Path(args.output_root) if args.output_root else None).write_result(result)
        print(json.dumps(result.to_dict(), sort_keys=True, ensure_ascii=False, indent=2))
        return 0
    raise SpendingAirlockError("validate requires --result <path> or --assignment <path>")


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--provider", default="fake", help="fake (offline default) | openai")
    p.add_argument("--model", default="")
    p.add_argument("--live", action="store_true", help="authorize a paid/live provider")
    p.add_argument("--confirm-spend", action="store_true", help="second required live confirmation")
    p.add_argument("--api-key-env", default="OPENAI_API_KEY",
                   help="env var holding the credential (value is never logged)")
    p.add_argument("--output-token-cap", type=int, default=V.DEFAULT_OUTPUT_TOKEN_CAP)
    p.add_argument("--timeout", type=float, default=V.DEFAULT_TIMEOUT_SECONDS)
    p.add_argument("--max-retries", type=int, default=V.DEFAULT_MAX_RETRIES)
    p.add_argument("--max-assignments", type=int, default=None)
    p.add_argument("--max-total-input-tokens", type=int, default=None)
    p.add_argument("--max-total-output-tokens", type=int, default=None)
    p.add_argument("--max-estimated-cost", type=float, default=None)
    p.add_argument("--output-root", default=None, help="worker runtime root (gitignored)")
    p.add_argument("--write-report", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="services.research_workers", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("benchmark", help="run the ten-hotel benchmark")
    _add_common(b)
    b.add_argument("--benchmark", default=None, help="benchmark JSON path (default: committed Columbus)")
    b.add_argument("--pricing", default=None, help="pricing JSON (provider/model -> per-1k rates)")
    b.add_argument("--json", action="store_true", help="print the full JSON report")
    b.set_defaults(func=_cmd_benchmark)

    v = sub.add_parser("validate", help="integrity-check a stored result, or run one assignment")
    _add_common(v)
    v.add_argument("--result", default=None, help="path to a stored WorkerResult JSON")
    v.add_argument("--assignment", default=None, help="path to an Assignment JSON to run (fake by default)")
    v.set_defaults(func=_cmd_validate)

    m = sub.add_parser("manifest", help="validate the benchmark manifest + evidence sync (offline)")
    m.add_argument("--benchmark", default=None, help="benchmark JSON path (default: committed Columbus)")
    m.set_defaults(func=_cmd_manifest)

    e = sub.add_parser("evaluate", help="live low-cost model bakeoff (ATLAS-WORKERS-002); dry-run without --live")
    _add_common(e)
    e.add_argument("--benchmark", default=None, help="benchmark JSON path (default: committed Columbus)")
    e.add_argument("--repetitions", type=int, default=3)
    e.add_argument("--case-id", default=None,
                   help="run exactly ONE named benchmark case (e.g. 01_rich_dogs_and_cats "
                        "or its alias bench-01_rich_dogs_and_cats); never substitutes")
    e.set_defaults(func=_cmd_evaluate)

    c = sub.add_parser("canary", help="ONE live adapter canary call (same adapter + parser as the benchmark)")
    c.add_argument("--provider", required=True)
    c.add_argument("--model", required=True)
    c.add_argument("--live", action="store_true", help="authorize the single paid call")
    c.add_argument("--confirm-spend", action="store_true", help="second required confirmation")
    c.add_argument("--output-token-cap", type=int, default=256)
    c.add_argument("--timeout", type=float, default=60.0)
    c.add_argument("--max-retries", type=int, default=0)
    c.set_defaults(func=_cmd_canary)

    r = sub.add_parser("route", help="route validated worker results (ATLAS-WORKERS-003; offline, dry-run default)")
    r.add_argument("--benchmark", default=None, help="benchmark JSON path (default: committed Columbus)")
    r.add_argument("--assignment-id", default=None,
                   help="route exactly ONE case (id or bench- alias); never substitutes")
    r.add_argument("--write", action="store_true",
                   help="persist envelopes to the gitignored routing queue (default: dry-run)")
    r.add_argument("--output-root", default=None, help="worker runtime root (gitignored)")
    r.add_argument("--prompt-version", default="", help="override recorded prompt_version (default: current)")
    r.add_argument("--validator-version", default="", help="override recorded validator_version (default: current)")
    r.add_argument("--observed-at", default="", help="explicit observation timestamp (no clock is read)")
    r.add_argument("--run-id", default="", help="optional run correlation id")
    r.add_argument("--json", action="store_true", help="print full JSON (summary + envelopes)")
    r.set_defaults(func=_cmd_route)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SpendingAirlockError as exc:
        sys.stderr.write("airlock: %s\n" % exc)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
