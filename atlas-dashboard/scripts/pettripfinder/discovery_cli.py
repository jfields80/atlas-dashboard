"""AES-DATA-004A -- CLI: Columbus multi-source market discovery.

Dry-run (no network, no operational output):

    python scripts/pettripfinder/discovery_cli.py plan --market columbus-oh

Capped live run (only as many requests as explicitly allowed):

    python scripts/pettripfinder/discovery_cli.py run \\
      --market columbus-oh --providers google,overpass \\
      --categories veterinary,boarding \\
      --max-google-requests 2 --max-overpass-requests 1 \\
      --output-root data/discovery/live_validation_data004a \\
      --observed-at 2026-07-18

Regenerate the human-readable report from an already-persisted run (no
network calls):

    python scripts/pettripfinder/discovery_cli.py report \\
      --market columbus-oh --output-root data/discovery/live_validation_data004a

A run's provider budgets default to 0 -- Google/Overpass are only spent
when explicitly capped above 0 (mission: "no automatic production
population", "every live provider call must be capped").
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import progress_gate as PG
from scripts.pettripfinder.discovery.coverage import build_coverage_summary, render_coverage_html, render_coverage_json
from scripts.pettripfinder.discovery.google_places import api_key_present as google_key_present
from scripts.pettripfinder.discovery.import_plan import (
    build_import_plan,
    dumps_import_plan,
    next_action_counts,
)
from scripts.pettripfinder.discovery.known_inventory import (
    compute_recall,
    load_known_hotels,
    recall_summary_counts,
)
from scripts.pettripfinder.discovery.runner import RunConfig, dry_run_report, execute_run
from scripts.pettripfinder.discovery.serialization import coverage_from_dict, dumps_candidates

_PROVIDER_ALIASES = {
    "google": C.PROVIDER_GOOGLE_PLACES, "google_places": C.PROVIDER_GOOGLE_PLACES,
    "overpass": C.PROVIDER_OPENSTREETMAP, "osm": C.PROVIDER_OPENSTREETMAP,
    "openstreetmap": C.PROVIDER_OPENSTREETMAP,
    "foursquare": C.PROVIDER_FOURSQUARE,
}


def _parse_providers(value: str) -> tuple:
    if not value:
        return tuple(C.DISCOVERY_PROVIDERS)
    out = []
    for token in value.split(","):
        token = token.strip().lower()
        if token not in _PROVIDER_ALIASES:
            raise SystemExit("ERROR: unknown provider %r (use google, overpass, foursquare)" % token)
        out.append(_PROVIDER_ALIASES[token])
    return tuple(out)


def _parse_categories(value: str) -> tuple:
    if not value:
        return tuple(C.DISCOVERY_CATEGORIES)
    out = []
    for token in value.split(","):
        token = token.strip().lower()
        if token not in C.DISCOVERY_CATEGORY_SET:
            raise SystemExit("ERROR: unknown category %r (see constants.DISCOVERY_CATEGORIES)" % token)
        out.append(token)
    return tuple(out)


def _foursquare_key_present() -> bool:
    return bool(os.environ.get(C.FOURSQUARE_API_KEY_ENV, "").strip())


def _print_planner_report(report) -> None:
    print("market                          : %s" % report.market_id)
    print("total planned queries           : %d" % report.total_planned_queries)
    print("queries by provider             : %s" % dict(report.queries_by_provider))
    print("queries by category             : %s" % dict(report.queries_by_category))
    print("queries by cell                 : %s" % dict(report.queries_by_cell))
    print("max possible paginated requests : %d" % report.max_possible_paginated_requests)
    print("est. upper-bound Google calls   : %d" % report.estimated_upper_bound_google_billable_calls)
    print("est. upper-bound Overpass calls : %d" % report.estimated_upper_bound_overpass_requests)
    print("credentials available           : %s" % dict(report.credentials_available))
    print("blocked (missing credential)    : %d" % len(report.blocked_queries_missing_credential))
    if report.google_templates_by_category:
        print("Google templates used           : %s" % dict(report.google_templates_by_category))
    if report.overlapping_cell_pairs:
        print("predicted overlapping cell pairs: %d (duplicate-cost risk; absorbed by "
              "same-Place-ID dedup, not a correctness risk)" % len(report.overlapping_cell_pairs))
        for a, b, overlap_m in report.overlapping_cell_pairs:
            print("  %s <-> %s (~%dm overlap)" % (a, b, overlap_m))


def _add_common_run_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--market", required=True)
    p.add_argument("--providers", default="")
    p.add_argument("--categories", default="")
    p.add_argument("--output-root", default=C.DEFAULT_DISCOVERY_ROOT)
    p.add_argument("--observed-at", default="")
    p.add_argument("--max-pages-per-query", type=int, default=C.DEFAULT_MAX_PAGES_PER_QUERY)
    p.add_argument("--max-google-requests", type=int, default=C.DEFAULT_MAX_GOOGLE_REQUESTS)
    p.add_argument("--max-overpass-requests", type=int, default=C.DEFAULT_MAX_OVERPASS_REQUESTS)
    p.add_argument("--cache-only", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overpass-endpoint",
                   default=os.environ.get(C.OVERPASS_ENDPOINT_ENV, "").strip(),
                   help="ask ONE named Overpass mirror and never fall back "
                        "(PTF-INDIANAPOLIS-HARDENED-RECENSUS-002, written when "
                        "the public default went dark). Defaults to $%s, and "
                        "to EMPTY -- not to the public endpoint -- because an "
                        "empty value is what selects the resilient registry "
                        "added by PTF-DISCOVERY-OVERPASS-RESILIENCE-001. "
                        "Defaulting it to one endpoint would silently disable "
                        "that registry on every run." % C.OVERPASS_ENDPOINT_ENV)
    p.add_argument("--overpass-registry", default="",
                   help="an approved-endpoint registry other than the committed "
                        "default (discovery/config/overpass_endpoints.json)")
    p.add_argument("--osm-extract-index", default="",
                   help="a ptf-osm-extract-index document; Overpass cells are "
                        "answered from it locally and no public server is asked")
    p.add_argument("--override-progress-gate", action="store_true",
                   help="make live Overpass requests for THIS run even though the "
                        "forward-progress gate is closed (N resume cycles completed "
                        "no cell); a human decision, never a default")
    p.add_argument("--progress-stall-cycles", type=int, default=PG.DEFAULT_STALL_CYCLES,
                   help="consecutive attempting resume cycles with zero newly "
                        "completed cells before the gate closes (default %d)"
                        % PG.DEFAULT_STALL_CYCLES)


def cmd_state(args) -> int:
    """The free-discovery state: exhausted, runnable, or waiting. Offline."""
    from scripts.pettripfinder.discovery import discovery_state as DS
    from scripts.pettripfinder.discovery import overpass_endpoints as OE
    root = Path(args.output_root)
    registry = (OE.EndpointRegistry.load(Path(args.overpass_registry))
                if args.overpass_registry else None)
    document = DS.build(
        args.market, cache_root=root / C.CACHE_SUBDIR, registry=registry,
        health_ledger_path=root / OE.HEALTH_LEDGER_FILENAME,
        google_key_present=google_key_present())
    if args.out:
        DS.write(document, Path(args.out))
    print("state                  : %s" % document["state"])
    print("cells total/cached/rem : %d / %d / %d"
          % (document["OVERPASS_CELLS_TOTAL"], document["OVERPASS_CELLS_CACHED"],
             document["OVERPASS_CELLS_REMAINING"]))
    print("endpoints available    : %d of %d enabled (%s)"
          % (document["OVERPASS_ENDPOINTS_AVAILABLE"],
             document["OVERPASS_ENDPOINTS_ENABLED"],
             ", ".join(document["available_endpoint_ids"]) or "none"))
    if document["earliest_cooldown_expiry"]:
        print("earliest cooldown ends : %s" % document["earliest_cooldown_expiry"])
    print("failure domains avail. : %d of %d (%s)"
          % (document["OVERPASS_FAILURE_DOMAINS_AVAILABLE"],
             document["OVERPASS_FAILURE_DOMAINS_ENABLED"],
             ", ".join(document["available_failure_domains"]) or "none"))
    progress = document["forward_progress"]
    print("forward progress       : %s (%d consecutive zero-progress cycles; gate at %d)"
          % (progress["status"], progress["consecutive_zero_progress_cycles"],
             progress["stall_cycles"]))
    if document["waiting_reason"]:
        print("waiting because        : %s" % document["waiting_reason"])
    print("cached by endpoint     : %s" % dict(document["cached_cells_by_endpoint"]))
    print("paid fallback          : %s" % document["paid_discovery_fallback"]["state"])
    if args.out:
        print("written                : %s" % args.out)
    return 0


def cmd_plan(args) -> int:
    config = RunConfig(
        market_id=args.market, providers=_parse_providers(args.providers),
        categories=_parse_categories(args.categories), output_root=args.output_root,
        observed_at=args.observed_at or date.today().isoformat(),
        max_pages_per_query=args.max_pages_per_query,
    )
    _market, _queries, report = dry_run_report(config)
    _print_planner_report(report)
    return 0


def _print_run_preamble(config) -> None:
    print("output root                     : %s" % config.output_root)
    print("observation date                : %s" % config.observed_at)
    print("max pages per query             : %d" % config.max_pages_per_query)
    print("max Google requests (cap)       : %d" % config.max_google_requests)
    print("max Overpass requests (cap)     : %d" % config.max_overpass_requests)
    print("Anthropic calls                 : 0 (never used by discovery)")


def cmd_run(args) -> int:
    providers = _parse_providers(args.providers)
    categories = _parse_categories(args.categories)
    observed_at = args.observed_at or date.today().isoformat()
    config = RunConfig(
        market_id=args.market, providers=providers, categories=categories,
        output_root=args.output_root, observed_at=observed_at,
        max_pages_per_query=args.max_pages_per_query,
        max_google_requests=args.max_google_requests,
        max_overpass_requests=args.max_overpass_requests,
        cache_only=args.cache_only, resume=args.resume,
        overpass_registry_path=args.overpass_registry,
        overpass_endpoint=args.overpass_endpoint,
        osm_extract_index=args.osm_extract_index,
        override_progress_gate=args.override_progress_gate,
        progress_stall_cycles=args.progress_stall_cycles,
    )

    if args.dry_run:
        _market, _queries, report = dry_run_report(config)
        _print_planner_report(report)
        _print_run_preamble(config)
        return 0

    _print_run_preamble(config)

    if C.PROVIDER_GOOGLE_PLACES in providers and config.max_google_requests <= 0:
        print("WARNING: --max-google-requests not set above 0 -- no live Google "
              "requests will be made this run (cache hits only).")
    if C.PROVIDER_OPENSTREETMAP in providers and config.max_overpass_requests <= 0:
        print("WARNING: --max-overpass-requests not set above 0 -- no live "
              "Overpass requests will be made this run (cache hits only).")

    market, queries, results, candidates = execute_run(config)

    candidates_path = (Path(config.output_root) / C.CANDIDATES_SUBDIR
                       / ("%s_candidates.json" % config.market_id))
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidates_path.write_text(dumps_candidates(candidates), encoding="utf-8")

    import_plan_entries = build_import_plan(candidates)
    import_plan_path = Path(config.output_root) / "import_plan.json"
    import_plan_path.write_text(dumps_import_plan(import_plan_entries), encoding="utf-8")
    next_actions = next_action_counts(import_plan_entries)

    known_recall_counts = ()
    if C.CATEGORY_HOTEL in categories:
        known_hotels = load_known_hotels()
        if known_hotels:
            recall = compute_recall(known_hotels, candidates)
            known_recall_counts = recall_summary_counts(recall)

    summary = build_coverage_summary(
        market=market, observed_at=observed_at, providers_enabled=providers,
        google_key_present=google_key_present(),
        foursquare_key_present=_foursquare_key_present(),
        planned_queries=queries, query_results=results, candidates=candidates,
        known_inventory_recall=known_recall_counts,
        import_plan_next_action_counts=next_actions,
    )
    reports_dir = Path(config.output_root) / C.REPORTS_SUBDIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / ("%s_coverage.json" % config.market_id)
    html_path = reports_dir / ("%s_coverage.html" % config.market_id)
    json_path.write_text(render_coverage_json(summary), encoding="utf-8")
    html_path.write_text(render_coverage_html(summary), encoding="utf-8")

    google_requests = sum(r.requests_made for r in results if r.provider == C.PROVIDER_GOOGLE_PLACES)
    overpass_requests = sum(r.requests_made for r in results if r.provider == C.PROVIDER_OPENSTREETMAP)
    print("candidates              : %d" % len(candidates))
    print("candidates json         : %s" % candidates_path)
    print("import plan json        : %s" % import_plan_path)
    print("next-action counts      : %s" % dict(next_actions))
    if known_recall_counts:
        print("known-hotel recall      : %s" % dict(known_recall_counts))
    print("coverage json           : %s" % json_path)
    print("coverage html           : %s" % html_path)
    print("google requests made    : %d" % google_requests)
    print("overpass requests made  : %d" % overpass_requests)
    stats_path = Path(config.output_root) / "overpass_run_stats.json"
    if stats_path.is_file():
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        print("overpass endpoint       : %s (switches %s, timeouts %s, rate "
              "limits %s, waited %ss)"
              % (stats.get("current_endpoint_id") or "-",
                 stats.get("endpoint_switches", 0), stats.get("timeouts", 0),
                 stats.get("rate_limits", 0), stats.get("waited_seconds", 0)))
        if stats.get("all_endpoints_unhealthy"):
            print("WARNING: every approved Overpass endpoint was unhealthy; "
                  "remaining cells were NOT attempted (earliest cooldown ends "
                  "%s). Run `discovery_cli.py state` for the waiting report."
                  % (stats.get("earliest_cooldown_expiry") or "unknown"))
    progress = PG.summary(PG.load(Path(config.output_root) / PG.FILENAME),
                          config.progress_stall_cycles)
    print("forward progress        : %s (%d consecutive zero-progress cycles; gate at %d)"
          % (progress["status"], progress["consecutive_zero_progress_cycles"],
             progress["stall_cycles"]))
    if any(PG.WARNING_PROGRESS_GATE in r.warnings for r in results):
        print("WARNING: the forward-progress gate is CLOSED; no live Overpass request "
              "was made. Free discovery is WAITING_FOR_FREE_DISCOVERY. A human may "
              "override ONE run with --override-progress-gate, or answer the cells "
              "from a local OSM extract (--osm-extract-index).")
    print("next : python scripts/pettripfinder/discovery_cli.py report "
          "--market %s --output-root %s" % (config.market_id, config.output_root))
    return 0


def cmd_report(args) -> int:
    reports_dir = Path(args.output_root) / C.REPORTS_SUBDIR
    json_path = reports_dir / ("%s_coverage.json" % args.market)
    if not json_path.exists():
        print("ERROR: no coverage summary at %s -- run `run` first" % json_path)
        return 2
    summary = coverage_from_dict(json.loads(json_path.read_text(encoding="utf-8")))
    html_path = reports_dir / ("%s_coverage.html" % args.market)
    html_path.write_text(render_coverage_html(summary), encoding="utf-8")
    print("coverage html regenerated (no network calls): %s" % html_path)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Columbus multi-source market discovery.")
    sub = p.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan", help="Dry-run: show request exposure, no network calls.")
    plan_p.add_argument("--market", required=True)
    plan_p.add_argument("--providers", default="")
    plan_p.add_argument("--categories", default="")
    plan_p.add_argument("--output-root", default=C.DEFAULT_DISCOVERY_ROOT)
    plan_p.add_argument("--observed-at", default="")
    plan_p.add_argument("--max-pages-per-query", type=int, default=C.DEFAULT_MAX_PAGES_PER_QUERY)
    plan_p.set_defaults(func=cmd_plan)

    run_p = sub.add_parser("run", help="Execute a capped discovery run.")
    _add_common_run_args(run_p)
    run_p.set_defaults(func=cmd_run)

    report_p = sub.add_parser("report", help="Regenerate the HTML report (no network calls).")
    report_p.add_argument("--market", required=True)
    report_p.add_argument("--output-root", default=C.DEFAULT_DISCOVERY_ROOT)
    report_p.set_defaults(func=cmd_report)

    state_p = sub.add_parser("state", help="Free-discovery state: exhausted, runnable "
                                           "or waiting on endpoint health (offline).")
    state_p.add_argument("--market", required=True)
    state_p.add_argument("--output-root", default=C.DEFAULT_DISCOVERY_ROOT)
    state_p.add_argument("--overpass-registry", default="")
    state_p.add_argument("--out", default="")
    state_p.set_defaults(func=cmd_state)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
