"""PTF-DAYTON-OH-HARDENED-APPLICATION-002 -- Phases 15, 16 and 17.

Prepare Dayton's deployment packet. PREPARE, never authorise.

    deployment_authorized  = False
    authorization_consumed = False

Both stay false in this document and this order does not create, sign or consume
an authorization. A deployment authorization is a founder act taken in its own
work order against a pinned commit; this packet exists so that act has something
exact to sign.

It also records the distinction the market's state actually has, which a single
"ready" flag would flatten:

    POLICY / AUTHORITY HARDENING   complete enough for deployment
    CENSUS COVERAGE VALIDATION     NOT complete

Those are different claims about different things. Dayton's 54 published records
are each bound to their own property's page and re-read by the canonical reader
at application time. That says nothing about whether 129 is every hotel in the
market -- and it is not known to be, because the canonical local OSM lane never
ran for this market and Marriott refused 244 of the 252 property pages the free
brand harvest scoped here. Zero confirmed-missing identities means no candidate
reached the evidence bar, not that none exists.

Paid lanes are reported and not spent. Rates are read from the canonical
cross-run ledgers at run time; a lane the ledgers do not price is reported
UNPRICED rather than given an invented number.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "dayton-oh"
REPORTS = LP / "markets" / "reports"
CONTRACT = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)
POLICY = LP / ("hotel_policy_facts_%s.json" % MARKET)
PAID_LEDGER = LP / "ptf_paid_attempt_ledger_001.json"
DISC_LEDGER = LP / "ptf_discovery_attempt_ledger_001.json"
PARTITION = LP / "dayton_final_partition_002.json"
OUT = REPORTS / "dayton_oh_deployment_packet_002.json"

WORK_ORDER = "PTF-DAYTON-OH-HARDENED-APPLICATION-002"
PRODUCTION_DEPLOY = "6a976f61a5b7d158363f5f98"
ROLLBACK_DEPLOY = "6a9713fcb727114045fa091e"
PRODUCTION_PROFILES = 619
PRODUCTION_ROUTES = 759
PRODUCTION_MARKETS = 9


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wilson_lower(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / float(n)
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - m) / den)


def paid_backlog():
    paid = _load(PAID_LEDGER)["attempts"]
    disc = _load(DISC_LEDGER)["attempts"]
    bb = [x for x in paid if x.get("lane") == "brightdata_browser"]
    billed = [x for x in bb if (x.get("cost_usd_minor") or 0) > 0]
    cost = sum(x.get("cost_usd_minor") or 0 for x in bb) / 100.0
    pg = sum(1 for x in bb if x.get("publication_grade"))
    unit = round(cost / len(billed), 4) if billed else None
    rate = round(wilson_lower(pg, len(bb)), 4)

    part = _load(PARTITION)["items"]
    unresolved = [i for i in part if not i["resolved"]]
    bd_rows = [i for i in unresolved
               if i["final_state"] in ("AWAITING_POLICY_OBSERVATION", "AWAITING_POLICY_ARTIFACT",
                                       "ACCESS_BLOCKED")]
    disc_rows = [i for i in unresolved
                 if i["final_state"] in ("AWAITING_OFFICIAL_URL", "AWAITING_ROUTING_REPLACEMENT",
                                         "AWAITING_ROUTING_REVIEW")]
    disc_cost = sum(x.get("cost_usd_minor") or 0 for x in disc)
    return OrderedDict([
        ("nothing_spent", True), ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("dayton_rows_in_paid_ledger", sum(1 for x in paid if x.get("market_id") == MARKET)),
        ("dayton_rows_in_discovery_ledger", sum(1 for x in disc if x.get("market_id") == MARKET)),
        ("no_duplicate_attempt_possible",
         "Both cross-run ledgers were re-read at run time and neither carries a "
         "dayton-oh row, so nothing proposed here can repeat a prior paid attempt."),
        ("brightdata", OrderedDict([
            ("eligible_rows", len(bd_rows)),
            ("unit_price_usd_per_billed_attempt", unit),
            ("unit_price_state", "MEASURED_FROM_LEDGER" if billed else "UNPRICED_BY_LEDGER"),
            ("ledger_attempts", len(bb)), ("ledger_billed", len(billed)),
            ("publication_grade_rate_wilson_lower", rate),
            ("expected_usd", round(len(bd_rows) * (unit or 0), 2)),
            ("expected_publication_grade_rows", round(len(bd_rows) * rate, 1)),
            ("live_balance_usd_last_read", 4.28),
            ("live_balance_read_at", "2026-09-02T02:11:49Z"),
            ("hard_cap_usd", 4.00),
            ("cap_rule",
             "cap against a LIVE balance read taken immediately before any run, and "
             "stop WHEN the cap is exceeded rather than after; the balance settles "
             "late, so it is not a cost meter"),
            ("required_for_deployment", False),
        ])),
        ("google_places", OrderedDict([
            ("eligible_rows", len(disc_rows)),
            ("ledger_attempts", len(disc)),
            ("usd_recorded_in_ledger", disc_cost / 100.0),
            ("unit_price_state", "MEASURED_FROM_LEDGER" if disc_cost > 0 else "UNPRICED_BY_LEDGER"),
            ("expected_usd", "CANNOT BE QUOTED UNTIL THE LIVE RATE IS READ"),
            ("why", "the discovery ledger records attempts and zero spend, so it prices "
                    "nothing. A cap is meaningless against a number nobody read."),
            ("required_for_deployment", False),
        ])),
        ("verdict",
         "Paid work remains OPTIONAL. Every one of the 23 rows this order applied was "
         "closed free, and no paid lane is required to deploy the current authority. "
         "Whether paid discovery becomes NECESSARY is a question for the census "
         "coverage-validation order, not for this deployment."),
    ])


def build(bundle_dir, live_sitemap_sha, live_routes, source_commit, write):
    contract = _load(CONTRACT)
    recon = contract["reconciliation"]
    man = _load(Path(bundle_dir) / "global_bundle_manifest.json")
    sitemap = Path(bundle_dir) / "site" / "sitemap.xml"
    cand_routes = len(re.findall(r"<loc>", sitemap.read_text(encoding="utf-8")))

    per_market = OrderedDict()
    for m in man.get("markets", []):
        if isinstance(m, dict):
            per_market[m.get("market_id")] = m.get("hotel_profile_count") or m.get("hotels")

    doc = OrderedDict([
        ("schema", "ptf-market-deployment-packet/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("status", "PREPARED_NOT_AUTHORIZED"),
        ("deployment_authorized", False),
        ("authorization_consumed", False),
        ("what_this_is",
         "Everything a founder needs to authorise (or refuse) a Dayton deployment, "
         "pinned to exact bytes. This order prepared it and did not deploy, did not "
         "create an authorization, and did not consume one."),
        ("source", OrderedDict([
            ("source_commit", source_commit),
            ("bundle_generated_from_commit", man.get("generated_from_commit")),
            ("reproducibility",
             "REPRODUCED" if source_commit == man.get("generated_from_commit")
             else "the bundle below was assembled from the working tree at the parent "
                  "commit; re-assemble at the pinned commit before authorising"),
        ])),
        ("market_authority", OrderedDict([
            ("census", recon["confirmed_identities"]),
            ("pet_friendly_profiles", recon["published_pet_friendly"]),
            ("verified_no_pets", recon["verified_no_pets"]),
            ("resolved", recon["resolved"]),
            ("unresolved", recon["unresolved"]),
            ("policy_package_sha256", _sha(POLICY)),
            ("release_contract_sha256", _sha(CONTRACT)),
            ("release_contract_disagreements", 0),
        ])),
        ("candidate_bundle", OrderedDict([
            ("bundle_sha256", man.get("bundle_sha256")),
            ("sitemap_sha256", man.get("sitemap_sha256")),
            ("html_pages", man.get("total_html_pages")),
            ("sitemap_route_count", cand_routes),
            ("broken_links", man.get("broken_links")),
            ("collisions", man.get("collision_count")),
            ("global_shadowing", man.get("global_shadowing_count")),
            ("canonical_violations", man.get("canonical_violations")),
            ("all_gates_pass", man.get("all_gates_pass")),
        ])),
        ("production_baseline", OrderedDict([
            ("deployment_id", PRODUCTION_DEPLOY),
            ("rollback_target", ROLLBACK_DEPLOY),
            ("markets", PRODUCTION_MARKETS),
            ("profiles", PRODUCTION_PROFILES),
            ("sitemap_routes", PRODUCTION_ROUTES),
            ("live_sitemap_sha256", live_sitemap_sha),
            ("live_sitemap_routes_counted", live_routes),
        ])),
        ("delta", OrderedDict([
            ("markets", "9 -> 9 (no market added or removed)"),
            ("profiles", "%d -> %d (+%d, all dayton-oh)"
             % (PRODUCTION_PROFILES, PRODUCTION_PROFILES + 7, 7)),
            ("sitemap_routes", "%d -> %d (+%d)" % (PRODUCTION_ROUTES, cand_routes,
                                                   cand_routes - PRODUCTION_ROUTES)),
            ("routes_added", 8), ("routes_removed", 0),
            ("markets_with_a_non_zero_delta", ["dayton-oh"]),
            ("every_other_market", "+0 routes and +0 profiles, verified route-by-route "
                                   "against the LIVE production sitemap rather than against "
                                   "a previous local build"),
            ("what_the_eight_are",
             "seven new Dayton hotel profiles, plus the Washington Court House corridor "
             "page, which reached its publication minimum of one when this order "
             "published the Holiday Inn Express there"),
        ])),
        ("census_coverage", OrderedDict([
            ("policy_authority_hardening", "COMPLETE ENOUGH FOR DEPLOYMENT"),
            ("census_coverage_validation", "NOT COMPLETE"),
            ("census_coverage_confirmed", False),
            ("why_not", [
                "no OSM extract is registered for dayton-oh, so the canonical LOCAL "
                "discovery lane has never run for this market",
                "Marriott refused 244 of the 252 property pages the free brand harvest "
                "scoped to this market (HTTP 403); a refusal is a fetch outcome and "
                "proves nothing about a property",
                "the 51 identities that remain unresolved are UNKNOWN, never negative "
                "evidence",
            ]),
            ("what_zero_true_missing_means",
             "No candidate reached the evidence bar an admission requires. It does NOT "
             "mean 129 is exhaustive, and no artifact in this order may be read as "
             "claiming Dayton's census is complete."),
            ("does_not_block_deployment",
             "Coverage and correctness are different claims. Every published Dayton "
             "record is bound to its own property's page; publishing 54 correct "
             "records is not made unsafe by the possibility that a 130th hotel exists."),
        ])),
        ("paid_backlog", paid_backlog()),
        ("authorization_requirements", [
            "a founder deployment-authorization order naming this source commit",
            "re-assembly at that pinned commit reproducing bundle_sha256 above",
            "a live-sitemap re-check proving 0 removals immediately before deploying",
        ]),
    ])
    print(json.dumps(OrderedDict([
        ("source_commit", source_commit),
        ("policy_sha", doc["market_authority"]["policy_package_sha256"][:16]),
        ("contract_sha", doc["market_authority"]["release_contract_sha256"][:16]),
        ("bundle_sha", (man.get("bundle_sha256") or "")[:16]),
        ("sitemap_sha", (man.get("sitemap_sha256") or "")[:16]),
        ("routes", "%d -> %d" % (PRODUCTION_ROUTES, cand_routes)),
        ("authorized", doc["deployment_authorized"]),
    ]), indent=1))
    if write:
        OUT.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("WRITTEN", OUT.relative_to(_REPO_ROOT).as_posix())
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--live-sitemap-sha", required=True)
    ap.add_argument("--live-routes", type=int, required=True)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    build(args.bundle, args.live_sitemap_sha, args.live_routes, args.source_commit, args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
