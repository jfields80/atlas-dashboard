"""AES-DATA-004C -- CLI: Columbus lodging scope cleanup and official-website
resolution.

Static-only pass (no network, always safe):

    python scripts/pettripfinder/lodging_resolution_cli.py plan \\
      --input-root data/discovery/columbus_wave1_lodging \\
      --output-root data/discovery/columbus_wave1_lodging/resolution

Capped live identity-fetch run (only as many HTTP requests as explicitly
allowed -- defaults to 0, i.e. static-only, unless --max-http-requests is
passed above 0):

    python scripts/pettripfinder/lodging_resolution_cli.py run \\
      --input-root data/discovery/columbus_wave1_lodging \\
      --output-root data/discovery/columbus_wave1_lodging/resolution \\
      --max-http-requests 40 --observed-at 2026-07-18

Regenerate reports from already-resolved data (no network):

    python scripts/pettripfinder/lodging_resolution_cli.py report \\
      --output-root data/discovery/columbus_wave1_lodging/resolution
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.import_batch_builder import (
    build_batch_index,
    build_batches,
    build_import_job,
    dumps_batch_manifest,
)
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.resolution_fetch_plan import build_fetch_plan
from scripts.pettripfinder.discovery.resolution_report import build_report_data, render_report_html, render_report_json
from scripts.pettripfinder.discovery.resolution_runner import (
    build_identity_review_ids,
    combine_lodging_candidate_pools,
    resolve_static,
    resolve_with_fetch,
)
from scripts.pettripfinder.discovery.serialization import candidate_from_dict, candidate_to_dict, loads_candidates
from scripts.pettripfinder.discovery.website_fetcher import DomainPacer, ResolutionCache
from scripts.pettripfinder.discovery.website_resolution import classify_candidate_urls_statically
from scripts.pettripfinder.importer.fetch import RequestsPageFetcher

_HOTEL_CANDIDATES_REL = "hotel/candidates/columbus-oh_candidates.json"
_MOTEL_CANDIDATES_REL = "motel/candidates/columbus-oh_candidates.json"


def _load_input_candidates(input_root: str):
    hotel_path = Path(input_root) / _HOTEL_CANDIDATES_REL
    motel_path = Path(input_root) / _MOTEL_CANDIDATES_REL
    hotel = loads_candidates(hotel_path.read_text(encoding="utf-8")) if hotel_path.exists() else ()
    motel = loads_candidates(motel_path.read_text(encoding="utf-8")) if motel_path.exists() else ()
    return combine_lodging_candidate_pools(hotel, motel)


def _resolved_to_dict(r):
    return {
        "candidate_id": r.candidate_id, "name": r.name, "category": r.category,
        "city": r.city, "state": r.state, "scope": r.scope,
        "identity_outcome": r.identity_outcome,
        "missing_website_action": r.missing_website_action,
        "resolution_outcome": r.resolution_outcome, "resolved_url": r.resolved_url,
        "is_confirmed": r.is_confirmed,
        "website_resolutions": [
            {
                "source_provider": ws.source_provider, "original_url": ws.original_url,
                "normalized_url": ws.normalized_url, "registrable_domain": ws.registrable_domain,
                "redirect_target": ws.redirect_target, "http_status": ws.http_status,
                "page_title": ws.page_title, "canonical_url": ws.canonical_url,
                "resolution_state": ws.resolution_state, "warnings": list(ws.warnings),
                "retrieved_at": ws.retrieved_at, "cache_reference": ws.cache_reference,
            }
            for ws in r.website_resolutions
        ],
    }


def _print_plan_summary(fetch_plan, *, max_http_requests) -> None:
    print("total candidates                : %d" % fetch_plan.total_candidates)
    print("static-only resolutions         : %d" % fetch_plan.static_only_count)
    print("fetch-required count            : %d" % fetch_plan.fetch_required_count)
    print("maximum HTTP requests (planned) : %d" % fetch_plan.max_http_requests)
    print("excluded by cap                 : %d" % fetch_plan.excluded_by_cap_count)
    print("blocked third-party URLs        : %d" % len(fetch_plan.blocked_third_party_urls))
    print("per-domain request counts       : %s" % dict(fetch_plan.per_domain_counts))
    print("approved HTTP ceiling           : %d" % max_http_requests)
    print("Google Places calls             : 0 (never made by this CLI)")
    print("Anthropic calls                 : 0 (never made by this CLI)")


def cmd_plan(args) -> int:
    candidates = _load_input_candidates(args.input_root)
    static_map = {c.candidate_id: classify_candidate_urls_statically(c) for c in candidates}
    identity_ids = build_identity_review_ids(candidates)
    fetch_plan = build_fetch_plan(
        candidates, static_map, identity_ids, max_total=args.max_http_requests,
        max_per_candidate=args.max_requests_per_candidate,
        max_per_domain=args.max_requests_per_domain,
    )
    _print_plan_summary(fetch_plan, max_http_requests=args.max_http_requests)
    print("output root (not written by plan): %s" % args.output_root)
    return 0


def _run_resolution(args, *, cache_only: bool):
    observed_at = args.observed_at or date.today().isoformat()
    market = load_market_config(args.market)
    candidates = _load_input_candidates(args.input_root)

    # --cache-only must replay everything already cached, never spend new
    # budget -- that guarantee comes from fetch_for_identity's own
    # cache_only flag (a structural no-op past the cache), NOT from
    # shrinking the plan. If the plan itself is built with the default
    # max_http_requests=0, it has zero items and cache-only mode has
    # nothing to replay, silently losing prior live-fetched results (bug
    # found and fixed live while regenerating Wave 1 output after a
    # classification fix). Plan at the full ceiling under --cache-only
    # unless the caller explicitly narrowed it.
    plan_cap = args.max_http_requests
    if cache_only and plan_cap <= 0:
        plan_cap = C.RESOLUTION_MAX_HTTP_REQUESTS

    static_map = {c.candidate_id: classify_candidate_urls_statically(c) for c in candidates}
    identity_ids = build_identity_review_ids(candidates)
    fetch_plan = build_fetch_plan(
        candidates, static_map, identity_ids, max_total=plan_cap,
        max_per_candidate=args.max_requests_per_candidate,
        max_per_domain=args.max_requests_per_domain,
    )

    output_root = Path(args.output_root)
    cache = ResolutionCache(output_root / "resolution_cache")
    fetcher = RequestsPageFetcher()
    pacer = DomainPacer(min_seconds=C.RESOLUTION_MIN_DOMAIN_PACING_SECONDS)

    if fetch_plan.items and not cache_only and args.max_http_requests <= 0:
        print("WARNING: fetch plan has %d fetchable items but "
              "--max-http-requests is 0 -- resolving statically only." % len(fetch_plan.items))

    resolved, stats = resolve_with_fetch(
        candidates, market, fetch_plan=fetch_plan, fetcher=fetcher, cache=cache,
        pacer=pacer, observed_at=observed_at, cache_only=cache_only,
    )

    output_root.mkdir(parents=True, exist_ok=True)
    resolved_path = output_root / "resolved_candidates.json"
    resolved_path.write_text(
        json.dumps([_resolved_to_dict(r) for r in resolved], sort_keys=True, indent=2),
        encoding="utf-8")

    hotel_jobs, motel_jobs = [], []
    for r in resolved:
        if r.resolution_outcome not in C.RESOLUTION_ELIGIBLE_FOR_BATCH:
            continue
        candidate = next(c for c in candidates if c.candidate_id == r.candidate_id)
        job = build_import_job(candidate, resolved_url=r.resolved_url, is_confirmed=r.is_confirmed)
        (motel_jobs if r.category == C.CATEGORY_MOTEL else hotel_jobs).append(job)

    hotel_manifests = build_batches(hotel_jobs, batch_id_prefix="columbus-wave1-hotel",
                                    batch_name_prefix="Columbus Wave 1 Hotel")
    motel_manifests = build_batches(motel_jobs, batch_id_prefix="columbus-wave1-motel",
                                    batch_name_prefix="Columbus Wave 1 Motel")

    batches_dir = output_root / "import_batches"
    batches_dir.mkdir(parents=True, exist_ok=True)
    hotel_paths, motel_paths = [], []
    for i, m in enumerate(hotel_manifests, start=1):
        p = batches_dir / ("hotel_batch_%03d.json" % i)
        p.write_text(dumps_batch_manifest(m), encoding="utf-8")
        hotel_paths.append(str(p))
    for i, m in enumerate(motel_manifests, start=1):
        p = batches_dir / ("motel_batch_%03d.json" % i)
        p.write_text(dumps_batch_manifest(m), encoding="utf-8")
        motel_paths.append(str(p))

    batch_index = build_batch_index(hotel_manifests, motel_manifests,
                                    hotel_paths=hotel_paths, motel_paths=motel_paths)
    (output_root / "batch_index.json").write_text(
        json.dumps(batch_index, sort_keys=True, indent=2), encoding="utf-8")

    unresolved = [r for r in resolved if r.resolution_outcome in
                 (C.RESOLUTION_REVIEW_IDENTITY, C.RESOLUTION_REVIEW_WEBSITE,
                  C.RESOLUTION_MISSING_OFFICIAL_WEBSITE, C.RESOLUTION_DEFER)]
    (output_root / "unresolved_queue.json").write_text(
        json.dumps([_resolved_to_dict(r) for r in unresolved], sort_keys=True, indent=2),
        encoding="utf-8")

    excluded = [r for r in resolved if r.resolution_outcome in
               (C.RESOLUTION_EXCLUDE_OUT_OF_SCOPE, C.RESOLUTION_EXCLUDE_CLOSED)]
    (output_root / "excluded_candidates.json").write_text(
        json.dumps([_resolved_to_dict(r) for r in excluded], sort_keys=True, indent=2),
        encoding="utf-8")

    batch_counts = (("hotel_batches", len(hotel_manifests)), ("motel_batches", len(motel_manifests)))
    report_data = build_report_data(resolved, market_id=args.market, observed_at=observed_at,
                                    batch_counts=batch_counts)
    (output_root / "website_resolution_report.json").write_text(
        render_report_json(report_data), encoding="utf-8")
    (output_root / "website_resolution_report.html").write_text(
        render_report_html(report_data), encoding="utf-8")

    return resolved, stats, fetch_plan, hotel_manifests, motel_manifests, output_root


def cmd_run(args) -> int:
    result = _run_resolution(args, cache_only=args.cache_only)
    resolved, stats, fetch_plan, hotel_manifests, motel_manifests, output_root = result
    print("resolved candidates      : %d" % len(resolved))
    print("HTTP requests (actual)   : %d" % stats.http_requests)
    print("cache hits               : %d" % stats.cache_hits)
    print("redirects                : %d" % stats.redirects)
    print("blocked                  : %d" % stats.blocked)
    print("confirmed                : %d" % stats.confirmed)
    print("probable                 : %d" % stats.probable)
    print("chain homepage only      : %d" % stats.chain_homepage)
    print("hotel batches            : %d" % len(hotel_manifests))
    print("motel batches            : %d" % len(motel_manifests))
    print("output root              : %s" % output_root)
    print("Google Places calls      : 0")
    print("Anthropic calls          : 0")
    return 0


def cmd_report(args) -> int:
    output_root = Path(args.output_root)
    resolved_path = output_root / "resolved_candidates.json"
    if not resolved_path.exists():
        print("ERROR: no resolved_candidates.json at %s -- run `run` first" % resolved_path)
        return 2
    # Report regeneration re-reads persisted JSON only -- no re-resolution,
    # no network.
    from scripts.pettripfinder.discovery.resolution_runner import ResolvedCandidate
    from scripts.pettripfinder.discovery.models import WebsiteResolution
    data = json.loads(resolved_path.read_text(encoding="utf-8"))
    resolved = tuple(
        ResolvedCandidate(
            candidate_id=d["candidate_id"], name=d["name"], category=d["category"],
            city=d["city"], state=d["state"], scope=d["scope"],
            identity_outcome=d["identity_outcome"],
            website_resolutions=tuple(
                WebsiteResolution(
                    candidate_id=d["candidate_id"], source_provider=w["source_provider"],
                    original_url=w["original_url"], normalized_url=w["normalized_url"],
                    registrable_domain=w["registrable_domain"], redirect_target=w["redirect_target"],
                    http_status=w["http_status"], page_title=w["page_title"],
                    canonical_url=w["canonical_url"], resolution_state=w["resolution_state"],
                    warnings=tuple(w["warnings"]), retrieved_at=w["retrieved_at"],
                    cache_reference=w["cache_reference"],
                )
                for w in d["website_resolutions"]
            ),
            missing_website_action=d["missing_website_action"],
            resolution_outcome=d["resolution_outcome"], resolved_url=d["resolved_url"],
            is_confirmed=d["is_confirmed"],
        )
        for d in data
    )
    report_data = build_report_data(resolved, market_id=args.market, observed_at=args.observed_at or "")
    (output_root / "website_resolution_report.json").write_text(
        render_report_json(report_data), encoding="utf-8")
    (output_root / "website_resolution_report.html").write_text(
        render_report_html(report_data), encoding="utf-8")
    print("report regenerated (no network calls): %s" % (output_root / "website_resolution_report.html"))
    return 0


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--market", default="columbus-oh")
    p.add_argument("--input-root", default="data/discovery/columbus_wave1_lodging")
    p.add_argument("--output-root", default="data/discovery/columbus_wave1_lodging/resolution")
    p.add_argument("--observed-at", default="")
    p.add_argument("--max-http-requests", type=int, default=0)
    p.add_argument("--max-requests-per-candidate", type=int, default=C.RESOLUTION_MAX_REQUESTS_PER_CANDIDATE)
    p.add_argument("--max-requests-per-domain", type=int, default=C.RESOLUTION_MAX_REQUESTS_PER_DOMAIN)
    p.add_argument("--cache-only", action="store_true")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Columbus lodging scope cleanup and website resolution.")
    sub = p.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan", help="Static-only fetch plan, no network calls.")
    _add_common_args(plan_p)
    plan_p.set_defaults(func=cmd_plan)

    run_p = sub.add_parser("run", help="Resolve candidates; live fetch only if --max-http-requests > 0.")
    _add_common_args(run_p)
    run_p.set_defaults(func=cmd_run)

    report_p = sub.add_parser("report", help="Regenerate reports from persisted data, no network.")
    report_p.add_argument("--market", default="columbus-oh")
    report_p.add_argument("--output-root", default="data/discovery/columbus_wave1_lodging/resolution")
    report_p.add_argument("--observed-at", default="")
    report_p.set_defaults(func=cmd_report)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
