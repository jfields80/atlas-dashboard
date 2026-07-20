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
