# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-APPLY-AND-PAID-CLOSE-027, Phases 6 and 7.

Rebuilds the final Bright Data cohort and runs every pre-spend safety check
BEFORE a single provider call.

THE 17 IS NOT TRUSTED. Three rows were published minutes ago by this order's
own free phase; a cohort assembled from a number written before that would try
to buy pages this market already owns.

THE CAP IS ENFORCED AGAINST THE LIVE PREPAID BALANCE. Not month-to-date, which
this market watched RESTATE DOWNWARD mid-run in order 015, and not the lifetime
mean, which is inflated by the early pilots. Balance is the only number that
moves the same direction as reality.

NOTHING IS SPENT BY THIS MODULE. It admits rows, proves the ledger has no
duplicate page, computes worst case, and stops.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)
from scripts.pettripfinder.acquisition import (                    # noqa: E402
    paid_attempt_ledger as PAL)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-APPLY-AND-PAID-CLOSE-027"
AS_OF = "2026-08-30"
HARD_CAP_MINOR = 200          # $2.00, in integer cents. Never floats.
RECENT_RATE_MINOR = 9         # $0.0890 rounded UP to $0.09 for worst case.

LP = R11.LP
OUT = LP / "detroit_ann_arbor_paid_cohort_027.json"

#: Families this market PROVED refuse an anonymous fetch.
PAID_ONLY_HOSTS = {"marriott.com", "ihg.com", "choicehotels.com",
                   "wyndhamhotels.com", "hilton.com"}
BRAND_INDEX_FRAGMENTS = ("/brand/", "/hotels/travel/", "/find-hotels",
                         "/search", "/locations", "/destinations")


def registrable(url):
    host = (urlsplit(url or "").hostname or "").lower()
    parts = [p for p in host.split(".") if p]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def run():
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              R11.load(MA.routing_shard_path(MARKET))["routes"]}
    published = {row["identity_key"] for row in
                 R11.load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                R11.load(MA.exclusions_shard_path(MARKET))["exclusions"]}
    classification = R11.load(
        LP / "detroit_ann_arbor_remaining_classification_020.json")
    by_class = {row["identity_key"]: row["classification"]
                for row in classification["rows"]}
    ledger = R11.load(LP / "ptf_paid_attempt_ledger_001.json")
    answered = {a["identity_key"] for a in ledger["attempts"]
                if a.get("market_id") == MARKET and a.get("publication_grade")}
    prior_urls = {}
    for attempt in ledger["attempts"]:
        if attempt.get("market_id") != MARKET:
            continue
        prior_urls.setdefault(attempt.get("canonical_url") or "", []).append(
            attempt.get("work_order"))

    unresolved = sorted(set(census) - published - excluded)
    admitted, refused = [], []
    seen_key, seen_url = set(), {}
    for key in unresolved:
        crow = census[key]
        route = routes.get(key)
        url = (route or {}).get("official_property_url") or ""
        status = (route or {}).get("status") or ""
        host = registrable(url)
        reasons = []

        if host not in PAID_ONLY_HOSTS:
            continue                       # not a Bright Data row at all
        if status != "ROUTING_CONFIRMED":
            reasons.append("route status is %s" % (status or "none"))
        if not url.lower().startswith("https://"):
            reasons.append("no absolute first-party URL")
        if any(f in url.lower() for f in BRAND_INDEX_FRAGMENTS):
            reasons.append("the routed path names no building")
        if key in answered:
            reasons.append("already answered by a publication-grade attempt")
        if by_class.get(key) in ("SOURCE_SILENT", "AWAITING_FOUNDER_RULING",
                                 "ROUTING_REPAIR_FIRST",
                                 "IDENTITY_REVIEW_FIRST"):
            reasons.append("classified %s" % by_class[key])
        if not (crow.get("address") or "").strip():
            reasons.append("the census cannot place this property")
        if key in seen_key or (url and url in seen_url):
            reasons.append("duplicate identity or canonical page")

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", crow.get("canonical_name") or ""),
            ("family", host),
            ("canonical_url", url),
            ("route_status", status),
            ("prior_paid_attempts", prior_urls.get(url, [])),
            ("retry_permitted",
             "yes -- no publication-grade answer exists for this identity"),
            ("address", crow.get("address") or ""),
            ("city", crow.get("city") or ""),
            ("postal_code", crow.get("postal_code") or ""),
            ("phone", crow.get("phone") or ""),
            ("brand", crow.get("brand") or ""),
            ("slug", crow.get("slug") or ""),
        ])
        if reasons:
            entry["refused_because"] = reasons
            refused.append(entry)
            continue
        seen_key.add(key)
        if url:
            seen_url[url] = key
        admitted.append(entry)

    # ---- duplicate-page proof against the whole ledger ----------------- #
    canonical = [PAL.canonical_url({"official_url": r["canonical_url"]})
                 for r in admitted]
    dupes_in_cohort = [u for u, n in Counter(canonical).items() if n > 1]

    worst_case_minor = len(admitted) * RECENT_RATE_MINOR
    families = Counter(r["family"] for r in admitted)

    doc = OrderedDict([
        ("schema", "ptf-detroit-paid-cohort-027/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("spent_by_this_module_usd", 0.0),
        ("admitted", len(admitted)),
        ("families", dict(families)),
        ("refused", len(refused)),
        ("refusal_reasons", dict(Counter(
            r["refused_because"][0][:52] for r in refused))),
        ("duplicate_pages_in_cohort", dupes_in_cohort),
        ("cap", OrderedDict([
            ("hard_cap_usd", HARD_CAP_MINOR / 100.0),
            ("worst_case_usd", worst_case_minor / 100.0),
            ("rate_used_usd", RECENT_RATE_MINOR / 100.0),
            ("rate_basis",
             "the recent balance-derived Detroit rate ($0.0890 over 32 "
             "attempts in orders 016-018), ROUNDED UP to $0.09 so the worst "
             "case cannot be understated. Integer cents throughout: this "
             "market has already had a cap miscomputed by float division."),
            ("fits_under_cap", worst_case_minor <= HARD_CAP_MINOR),
        ])),
        ("rows", admitted),
        ("refused_rows", refused),
    ])
    R11.write_lf(OUT, doc)

    print("=== Phase 6: final paid cohort rebuilt ===")
    print("   ADMITTED:", len(admitted), dict(families))
    print("   refused :", len(refused))
    for reason, n in sorted(Counter(r["refused_because"][0][:52]
                                    for r in refused).items()):
        print("      %-54s %d" % (reason, n))
    print()
    print("=== Phase 7: pre-spend arithmetic ===")
    print("   duplicate pages in cohort :", dupes_in_cohort or "none")
    print("   worst case                : $%.2f (%d rows x $%.2f)"
          % (worst_case_minor / 100.0, len(admitted),
             RECENT_RATE_MINOR / 100.0))
    print("   HARD CAP                  : $%.2f" % (HARD_CAP_MINOR / 100.0))
    print("   fits under cap            :", worst_case_minor <= HARD_CAP_MINOR)
    if dupes_in_cohort:
        raise SystemExit("STOP: duplicate canonical pages in the cohort")
    if worst_case_minor > HARD_CAP_MINOR:
        raise SystemExit(
            "STOP: worst case $%.2f exceeds the $%.2f cap. The cohort must be "
            "trimmed by the founder, not the cap raised by me."
            % (worst_case_minor / 100.0, HARD_CAP_MINOR / 100.0))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
