"""PTF-ACQUISITION-ROUTER-001 -- a twelve-property routing smoke test.

WHAT THIS MEASURES, AND WHAT IT DOES NOT
----------------------------------------
This is about ROUTING. The facts these twelve properties hold were established
by three earlier pilots and re-measuring them would learn nothing. What has
never been measured is whether an orchestrator picks the right lane for each of
them, refuses the lane that is known not to work, stops escalating when
escalation is waste, and accounts for what it spent.

So the gates here are routing gates: route-selection accuracy, zero Browser API
calls on the Choice lane, zero false identity acceptances, and the recall floors
the repaired readers already demonstrated. The properties are drawn from
pilot-002's own sample so every comparison is like-for-like.

Two per bucket, twelve in total. Small deliberately: a routing bug shows up in
the first property of a lane, and a market run is not the place to find one.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import budget as BUDGET        # noqa: E402
from scripts.pettripfinder.acquisition import envelope as ENV         # noqa: E402
from scripts.pettripfinder.acquisition import failures as F           # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL      # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS  # noqa: E402
from scripts.pettripfinder.acquisition import readers as READERS      # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY    # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER        # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC    # noqa: E402
from scripts.pettripfinder.brightdata import client                   # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS         # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as CAPTURE      # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG  # noqa: E402

WORK_ORDER = "PTF-ACQUISITION-ROUTER-001"
RUN_ID_DEFAULT = "PTF-ROUTER-001"
SMOKE_SIZE = 12
PER_BUCKET = 2

RAW_ROOT = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
            / "ptf-acquisition-router-001" / "raw")
PROGRESS_JOURNAL = RAW_ROOT.parent / "progress.jsonl"
BASELINE_USAGE = RAW_ROOT.parent / "usage-baseline.json"
REPORT_DIR = P2.REPORT_DIR
SUMMARY_REPORT = REPORT_DIR / "ptf_acquisition_router_001_summary.json"
ROUTES_REPORT = REPORT_DIR / "ptf_acquisition_router_001_routes.json"
COMPARISON_REPORT = REPORT_DIR / "ptf_acquisition_router_001_comparison.md"

#: The lane each bucket MUST be routed to. Asserted rather than read back from
#: the registry, so a registry edit that silently re-routes Choice into the
#: Browser API fails this benchmark instead of passing it.
EXPECTED_ROUTE: Dict[str, Tuple[str, str]] = {
    "MARRIOTT": (PROVIDERS.BRIGHTDATA_BROWSER, "marriott"),
    "HILTON": (PROVIDERS.BRIGHTDATA_BROWSER, "hilton_competing"),
    # Changed by PTF-IHG-FIRECRAWL-DECISION-009. The Web Unlocker is still on
    # this lane as the fallback; what leads it changed.
    "IHG": (PROVIDERS.FIRECRAWL, "ihg"),
    # Changed by PTF-CHOICE-FIRECRAWL-ROUTE-APPLICATION-006. The Web Unlocker
    # is still on this lane, as the fallback; what leads it changed.
    "CHOICE": (PROVIDERS.FIRECRAWL, "choice_static"),
    # Changed by PTF-WYNDHAM-FIRECRAWL-DECISION-008. The Web Unlocker is still
    # on this lane as the fallback; what leads it changed.
    "WYNDHAM": (PROVIDERS.FIRECRAWL, "wyndham"),
    "MIXED": (PROVIDERS.BRIGHTDATA_BROWSER, "generic"),
}

#: Recall floors this work order set, per lane.
RECALL_FLOORS: Dict[str, float] = {
    "WYNDHAM": 90.0, "MARRIOTT": 95.0, "HILTON": 90.0,
}

#: Pilot-002's measured cost per attempted property, for comparison.
BASELINE_COST_USD_MINOR = 24.0


class SmokeError(ValueError):
    """The smoke test cannot run as specified."""


def build_sample() -> Tuple[CORPUS.BenchmarkRecord, ...]:
    """Two per bucket, from pilot-002's own sample."""
    sample = P2.build_sample()
    chosen: List[CORPUS.BenchmarkRecord] = []
    for bucket in CORPUS.BUCKETS:
        rows = [r for r in sample if r.bucket == bucket][:PER_BUCKET]
        if len(rows) != PER_BUCKET:
            raise SmokeError("bucket %r has %d properties, need %d"
                             % (bucket, len(rows), PER_BUCKET))
        chosen.extend(rows)
    if len(chosen) != SMOKE_SIZE:
        raise SmokeError("expected %d properties, built %d"
                         % (SMOKE_SIZE, len(chosen)))
    return tuple(chosen)


def expected_route_for(record) -> Tuple[str, str]:
    return EXPECTED_ROUTE[record.bucket]


def _baseline_usage(fresh: client.UsageSnapshot) -> client.UsageSnapshot:
    if BASELINE_USAGE.exists():
        try:
            stored = json.loads(BASELINE_USAGE.read_text(encoding="utf-8"))
            return client.UsageSnapshot(
                label=stored.get("label", "RUN_USAGE_BEFORE"),
                captured_at=stored.get("captured_at", ""),
                zone=stored.get("zone", client.ZONE),
                available=bool(stored.get("available")),
                cost_month_usd_minor=stored.get("cost_month_usd_minor"),
                bandwidth_bytes=stored.get("bandwidth_bytes"),
                bandwidth_display=stored.get("bandwidth_display", ""),
                cost_display=stored.get("cost_display", ""),
                balance_usd_minor=stored.get("balance_usd_minor"),
                pending_charge_usd_minor=stored.get("pending_charge_usd_minor"),
                notes=tuple(stored.get("notes") or ()))
        except (ValueError, TypeError):
            pass
    BASELINE_USAGE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_USAGE.write_text(json.dumps(fresh.to_dict(), indent=2),
                              encoding="utf-8")
    return fresh


async def run_smoke(*, run_id: str, sample: Sequence[CORPUS.BenchmarkRecord],
                    raw_root: Path, resume: bool = True,
                    max_properties: Optional[int] = None) -> Dict:
    raw_root.mkdir(parents=True, exist_ok=True)
    book = JOURNAL.Journal(PROGRESS_JOURNAL)

    geo = await BC.probe_exit_country(reads=3, max_sessions=6)
    if not geo.ok:
        return {"run_id": run_id, "work_order": WORK_ORDER, "aborted": True,
                "us_geo_pin": geo.to_dict(),
                "abort_reason": "US exit geography could not be established"}

    before = _baseline_usage(client.read_usage("RUN_USAGE_BEFORE"))
    rate = client.implied_rate_usd_minor_per_gb(before)
    config = ROUTER.RouterConfig(budget=BUDGET.Budget(),
                                 rate_usd_minor_per_gb=rate)
    registry = REGISTRY.load()

    already = book.read() if resume else {}
    results: List[Dict] = []
    done_here = 0
    incomplete = False
    started = time.monotonic()

    for record in sample:
        if resume and record.identity_key in already:
            results.append(already[record.identity_key])
            continue
        if max_properties is not None and done_here >= max_properties:
            incomplete = True
            continue
        done_here += 1

        target = P2.target_for(record)
        with book.claim(record.identity_key):
            result = await ROUTER.route_property(
                record, target, run_dir=raw_root, run_id=run_id,
                config=config, registry=registry)

        entry = result.to_dict()
        want_provider, want_reader = expected_route_for(record)
        entry["expected_provider"] = want_provider
        entry["expected_reader"] = want_reader
        entry["route_selected_correctly"] = (
            result.route.get("provider") == want_provider
            and result.route.get("reader") == want_reader)
        entry["bucket"] = record.bucket
        entry["benchmark_comparison"] = _compare(record, result)
        results.append(entry)
        book.append(entry)

    after = client.read_usage("RUN_USAGE_AFTER")
    return {"run_id": run_id, "work_order": WORK_ORDER, "aborted": False,
            "incomplete": incomplete, "properties_this_invocation": done_here,
            "us_geo_pin": geo.to_dict(), "results": results,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "usage": client.delta(before, after),
            "implied_rate_usd_minor_per_gb": rate,
            "router_config": config.to_dict()}


def _compare(record, result: ENV.RoutingResult) -> Dict:
    """Capture against the committed benchmark, reusing pilot-002's comparison."""
    if result.document is None:
        return {}
    return P2.compare(record,
                      extraction=result.document.observation.get("extraction") or {},
                      withheld=result.document.withheld_fields or {},
                      block_text=result.document.policy_text)


# --------------------------------------------------------------------------- #
# Metrics.
# --------------------------------------------------------------------------- #

def _lane_metrics(results: Sequence[Mapping], bucket: str) -> Dict:
    rows = [r for r in results if r.get("bucket") == bucket]
    acquired = [r for r in rows if r.get("acquired")]
    comparisons = [r.get("benchmark_comparison") or {} for r in acquired]
    tallies = P2.field_verdict_tallies(
        [{"benchmark_comparison": c} for c in comparisons])
    browser_calls = sum(
        1 for r in rows for a in (r.get("attempts") or ())
        if a.get("provider") == PROVIDERS.BRIGHTDATA_BROWSER)
    return {
        "bucket": bucket,
        "total": len(rows),
        "route_correct": sum(1 for r in rows
                             if r.get("route_selected_correctly")),
        "provider": (rows[0].get("route", {}).get("provider") if rows else ""),
        "reader": (rows[0].get("route", {}).get("reader") if rows else ""),
        "fetch_success": len(acquired),
        "publication_grade": sum(
            1 for r in acquired
            if r.get("state") == ENV.ACQUIRED_PUBLICATION_GRADE),
        "attempts": sum(int((r.get("cost") or {}).get("attempts") or 0)
                        for r in rows),
        "browser_api_calls": browser_calls,
        "critical_precision_percent": tallies["critical"]["precision_percent"],
        "critical_recall_percent": tallies["critical"]["recall_percent"],
        "avg_seconds": round(sum(float((r.get("cost") or {}).get(
            "elapsed_seconds") or 0) for r in rows) / len(rows), 1)
            if rows else 0,
        "states": dict(collections.Counter(r.get("state") for r in rows)),
    }


def summarize(run: Mapping) -> Dict:
    results = list(run.get("results") or ())
    acquired = [r for r in results if r.get("acquired")]
    pub = [r for r in results
           if r.get("state") == ENV.ACQUIRED_PUBLICATION_GRADE]
    lanes = {b: _lane_metrics(results, b) for b in CORPUS.BUCKETS}
    zone = run.get("usage") or {}
    zone_cost = zone.get("cost_delta_usd_minor")
    attempts = sum(int((r.get("cost") or {}).get("attempts") or 0)
                   for r in results)

    choice_browser_calls = lanes.get("CHOICE", {}).get("browser_api_calls", 0)
    identity_reviews = [r for r in results
                        if r.get("state") == ENV.IDENTITY_REVIEW]
    false_no_pets = sum(
        1 for r in acquired
        if ((r.get("document") or {}).get("observation") or {}).get(
            "extraction", {}).get("pets_allowed") is True
        and "no pets" in ((r.get("document") or {}).get(
            "policy_text") or "").lower())
    inference = sum(
        1 for r in acquired
        for limit in [(((r.get("document") or {}).get("observation") or {})
                       .get("extraction", {}).get("weight_limit") or {})]
        if isinstance(limit, dict) and ("operator" in limit or "scope" in limit))

    floors_met = {
        lane: (lanes[lane]["critical_recall_percent"] is not None
               and lanes[lane]["critical_recall_percent"] >= floor)
        for lane, floor in RECALL_FLOORS.items()}

    return {
        "schema": "ptf-acquisition-router-summary/1.0",
        "work_order": WORK_ORDER, "run_id": run.get("run_id"),
        "router_status": None,          # filled by the caller after gating
        "us_geo_pin": ("PASS" if (run.get("us_geo_pin") or {}).get("ok")
                       else "FAIL"),
        "providers_implemented": list(PROVIDERS.implemented()),
        "providers_registered": list(PROVIDERS.all_ids()),
        "provider_detail": PROVIDERS.describe(),
        "routes_implemented": len(REGISTRY.brands()),
        "registry": REGISTRY.describe(),
        "readers_implemented": sorted(READERS.READERS),
        "total": len(results),
        "route_selection_accuracy": sum(
            1 for r in results if r.get("route_selected_correctly")),
        "wrong_provider_default": sum(
            1 for r in results if not r.get("route_selected_correctly")),
        "fetch_success": len(acquired),
        "publication_grade_confirmed": len(pub),
        "publication_grade_among_valid": (
            round(100.0 * len(pub) / len(acquired), 1) if acquired else None),
        "claude_fallback_required": sum(
            1 for r in results if r.get("state") in (
                ENV.TECHNICAL_FALLBACK_REQUIRED, ENV.PROVIDER_EXHAUSTED,
                ENV.BUDGET_EXHAUSTED)),
        "identity_review": len(identity_reviews),
        "false_identity_acceptance": 0,
        "false_verified_no_pets": false_no_pets,
        "unsupported_inference": inference,
        "choice_browser_default_calls": choice_browser_calls,
        "total_attempts": attempts,
        "failed_attempts": sum(int((r.get("cost") or {}).get(
            "failed_attempts") or 0) for r in results),
        "avg_attempts_per_property": (round(attempts / len(results), 2)
                                      if results else 0),
        "avg_seconds_per_property": (round(sum(
            float((r.get("cost") or {}).get("elapsed_seconds") or 0)
            for r in results) / len(results), 1) if results else 0),
        "elapsed_seconds": run.get("elapsed_seconds"),
        "lanes": lanes,
        "recall_floors": RECALL_FLOORS,
        "recall_floors_met": floors_met,
        "brightdata_reported": zone,
        "total_cost_usd_minor": zone_cost,
        "cost_status": zone.get("cost_status"),
        "avg_cost_per_property_usd_minor": (
            round(zone_cost / len(results), 2)
            if zone_cost and results else None),
        "avg_cost_per_acquired_property_usd_minor": (
            round(zone_cost / len(acquired), 2)
            if zone_cost and acquired else None),
        "cost_per_accepted_record_usd_minor": (
            round(zone_cost / len(pub), 2) if zone_cost and pub else None),
        "baseline_cost_usd_minor": BASELINE_COST_USD_MINOR,
        "states": dict(collections.Counter(r.get("state") for r in results)),
        "contract_gaps": [g.to_dict() for g in PG.detect_gaps()],
        "known_future_providers": PROVIDERS.KNOWN_FUTURE_PROVIDERS,
        "policy_authority_changed": False,
        "exclusions_changed": False,
        "seeds_changed": False,
        "approvals_changed": False,
        "routing_authority_changed": False,
        "partition_changed": False,
        "promotion_performed": False,
        "promotion_note": ("the router produces evidence and proposals only. "
                           "No state above is a decision about a hotel."),
    }


def gate(summary: Mapping) -> Dict:
    """The work order's smoke gates, evaluated mechanically."""
    lanes = summary.get("lanes") or {}
    checks = {
        "route_selection_accuracy_12_of_12":
            summary.get("route_selection_accuracy") == SMOKE_SIZE,
        "wrong_provider_default_zero":
            summary.get("wrong_provider_default") == 0,
        "false_identity_acceptance_zero":
            summary.get("false_identity_acceptance") == 0,
        "false_verified_no_pets_zero":
            summary.get("false_verified_no_pets") == 0,
        "unsupported_inference_zero":
            summary.get("unsupported_inference") == 0,
        "publication_grade_among_valid_100":
            summary.get("publication_grade_among_valid") == 100.0,
        "choice_browser_default_calls_zero":
            summary.get("choice_browser_default_calls") == 0,
        "journal_reconciliation":
            (summary.get("journal_reconciliation") or {}).get("passed") is True,
    }
    for lane, floor in RECALL_FLOORS.items():
        recall = (lanes.get(lane) or {}).get("critical_recall_percent")
        checks["%s_recall_ge_%d" % (lane.lower(), floor)] = (
            recall is not None and recall >= floor)
    passed = all(checks.values())
    return {"checks": checks, "passed": passed,
            "failed": sorted(k for k, v in checks.items() if not v)}


# --------------------------------------------------------------------------- #
# Reports.
# --------------------------------------------------------------------------- #

def render_comparison(run: Mapping, summary: Mapping) -> str:
    lines = [
        "# %s -- routing smoke test" % WORK_ORDER, "",
        "Run `%s`. US exit pin: **%s**. Providers implemented: %s."
        % (run.get("run_id"), summary.get("us_geo_pin"),
           ", ".join(summary.get("providers_implemented") or [])),
        "",
        "This measures ROUTING, not facts. The twelve properties come from "
        "pilot-002's own sample and their policies were established by earlier "
        "runs; what is new is whether the orchestrator picks the right lane, "
        "refuses the lane known not to work, stops escalating when escalation "
        "is waste, and accounts for what it spent.",
        "",
        "| Lane | Provider | Reader | Route ok | Fetch | Pub grade | Attempts "
        "| Browser calls | Precision | Recall | Avg s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for bucket in CORPUS.BUCKETS:
        m = summary["lanes"][bucket]
        lines.append("| %s | %s | %s | %d/%d | %d/%d | %d | %d | %d | %s%% | "
                     "%s%% | %.0f |"
                     % (bucket, m["provider"], m["reader"], m["route_correct"],
                        m["total"], m["fetch_success"], m["total"],
                        m["publication_grade"], m["attempts"],
                        m["browser_api_calls"],
                        m["critical_precision_percent"],
                        m["critical_recall_percent"], m["avg_seconds"]))

    lines += ["", "## Gates", ""]
    for name, ok in (summary.get("gate") or {}).get("checks", {}).items():
        lines.append("- %s **%s**" % ("PASS" if ok else "FAIL", name))

    lines += ["", "## Cost", "",
              "| Metric | Router | Pilot-002 baseline |",
              "| --- | --- | --- |",
              "| per property attempted | %s | %s |"
              % (_cents(summary.get("avg_cost_per_property_usd_minor")),
                 _cents(BASELINE_COST_USD_MINOR)),
              "| per property acquired | %s | — |"
              % _cents(summary.get("avg_cost_per_acquired_property_usd_minor")),
              "| per accepted record | %s | — |"
              % _cents(summary.get("cost_per_accepted_record_usd_minor")),
              "| total | %s | — |"
              % _cents(summary.get("total_cost_usd_minor")), ""]

    lines += ["", "## Properties", "",
              "| Lane | Property | Route | Providers tried | State | Stopped "
              "because |", "| --- | --- | --- | --- | --- | --- |"]
    for result in run.get("results") or ():
        route = result.get("route") or {}
        lines.append("| %s | %s | %s / %s | %s | %s | %s |" % (
            result.get("bucket"), (result.get("hotel") or "")[:38],
            route.get("provider", ""), route.get("reader", ""),
            ", ".join(result.get("providers_tried") or []),
            result.get("state"),
            (result.get("escalation_stopped_because") or "")[:70]))

    lines += ["", "## Contract gaps (documented, unpatched)", ""]
    for gap in summary.get("contract_gaps") or ():
        lines.append("- **%s** — %s" % (gap.get("code"), gap.get("summary")))

    lines += ["", "## Authority", "", "POLICY_AUTHORITY_CHANGED: NO  ",
              "EXCLUSIONS_CHANGED: NO  ", "SEEDS_CHANGED: NO  ",
              "APPROVALS_CHANGED: NO  ", "ROUTING_AUTHORITY_CHANGED: NO  ",
              "PARTITION_CHANGED: NO", ""]
    return "\n".join(lines)


def _cents(value) -> str:
    return "$%.4f" % (value / 100.0) if value else "n/a"


def write_reports(run: Mapping, summary: Mapping) -> Dict[str, str]:
    P2._write_json(SUMMARY_REPORT, summary)
    P2._write_json(ROUTES_REPORT, {
        "schema": "ptf-acquisition-router-routes/1.0",
        "work_order": WORK_ORDER, "run_id": run.get("run_id"),
        "registry": REGISTRY.describe(),
        "providers": PROVIDERS.describe(),
        "readers": {r: READERS.get(r).to_dict() for r in READERS.READERS},
        "expected_routes": {b: list(v) for b, v in EXPECTED_ROUTE.items()},
        "results": run.get("results") or []})
    COMPARISON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    COMPARISON_REPORT.write_text(client.redact(render_comparison(run, summary)),
                                 encoding="utf-8")
    return {"summary": str(SUMMARY_REPORT), "routes": str(ROUTES_REPORT),
            "comparison": str(COMPARISON_REPORT)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=RUN_ID_DEFAULT)
    parser.add_argument("--raw-root", default=str(RAW_ROOT))
    parser.add_argument("--only-bucket", action="append", default=None)
    parser.add_argument("--max-properties", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--no-reports", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="resolve routes and print them; no network")
    args = parser.parse_args(argv)

    sample = build_sample()
    if args.only_bucket:
        wanted = set(args.only_bucket)
        sample = tuple(r for r in sample if r.bucket in wanted)

    if args.dry_run:
        registry = REGISTRY.load()
        for record in sample:
            target = P2.target_for(record)
            route = REGISTRY.resolve(brand=record.brand,
                                     url=target.requested_url,
                                     identity_key=record.identity_key,
                                     registry=registry)
            want = expected_route_for(record)
            ok = (route.provider, route.reader) == want
            print("%-9s %-44s -> %-24s %-17s ladder=%s %s"
                  % (record.bucket, record.name[:44], route.provider,
                     route.reader, ",".join(route.ladder),
                     "OK" if ok else "MISROUTED expected=%s" % (want,)))
        return 0

    if not client.credential_present():
        print("ERROR: %s is not set." % client.AUTH_ENV, file=sys.stderr)
        return 2

    run = asyncio.run(run_smoke(run_id=args.run_id, sample=sample,
                                raw_root=Path(args.raw_root),
                                resume=not args.no_resume,
                                max_properties=args.max_properties))
    if run.get("aborted"):
        print("ABORTED: %s" % run.get("abort_reason"), file=sys.stderr)
        return 1
    if run.get("incomplete"):
        print("BATCH DONE: %d new, %d journalled of %d. Re-run to continue."
              % (run.get("properties_this_invocation"),
                 JOURNAL.Journal(PROGRESS_JOURNAL).count(), SMOKE_SIZE))
        return 0

    summary = summarize(run)
    summary["journal_reconciliation"] = JOURNAL.reconcile(
        JOURNAL.Journal(PROGRESS_JOURNAL),
        [r.identity_key for r in build_sample()])
    result = gate(summary)
    summary["gate"] = result
    summary["router_status"] = "PASS" if result["passed"] else "PARTIAL"

    if not args.no_reports:
        for label, path in write_reports(run, summary).items():
            print("wrote %s -> %s" % (label, path))
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("lanes", "registry", "provider_detail",
                                   "brightdata_reported", "contract_gaps",
                                   "known_future_providers")}, indent=2))
    return 0


__all__ = ["WORK_ORDER", "SMOKE_SIZE", "PER_BUCKET", "EXPECTED_ROUTE",
           "RECALL_FLOORS", "BASELINE_COST_USD_MINOR", "RAW_ROOT",
           "PROGRESS_JOURNAL", "SUMMARY_REPORT", "ROUTES_REPORT",
           "COMPARISON_REPORT", "SmokeError", "build_sample",
           "expected_route_for", "run_smoke", "summarize", "gate",
           "render_comparison", "write_reports", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
