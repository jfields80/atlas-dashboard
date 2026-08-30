# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FREE-CAPTURE-AND-ROUTING-026, Phase 1.

Rebuilds both cohorts from CURRENT state before any browsing.

THE KNOWN IDENTITY DEFECTS ARE HELD OUT BY KEY. Order 025 established that
"Trumbell and Porter" and "Comfort Suites" are probable duplicates of published
identities and that "Woodland Direct" is not lodging, and that Drury Troy and
Radisson Farmington Hills need identity review. Routing any of them would spend
effort discovering a route for a hotel that either already exists in authority
under another key or is not a hotel at all -- and the duplicate case is the
dangerous one, because a misspelled key is invisible to every duplicate check
that keys on identity.

NO PROVIDER IS CALLED AND NOTHING IS BROWSED IN THIS PHASE.
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

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-CAPTURE-AND-ROUTING-026"
AS_OF = "2026-08-30"

LP = R11.LP
RESULTS_025 = LP / "detroit_ann_arbor_routing_results_025.json"
OUT = LP / "detroit_ann_arbor_cohorts_026.json"

#: Hosts attended Chrome has already opened successfully in this market.
FREE_PROVEN_HOSTS = {
    "extendedstayamerica.com", "redroof.com", "sonesta.com", "hyatt.com",
    "woodspring.com", "bestwestern.com", "motel6.com",
}
#: Families this market PROVED refuse an anonymous fetch. hilton.com stays
#: here even though attended Chrome DID open one Hilton property at $0 during
#: the 45-row pass: the committed classifier calls these rows
#: BRIGHTDATA_QUALIFIED, and quietly promoting a whole family into the free
#: lane on one success would expand this order's scope by four properties on
#: my own say-so. The free-probe opportunity is REPORTED instead.
PAID_ONLY_HOSTS = {"marriott.com", "ihg.com", "choicehotels.com",
                   "wyndhamhotels.com", "hilton.com"}

#: Routes that must never enter a capture cohort whatever their status says.
#: detroitriverwalkhotel.com lapsed and now redirects to an online-gambling
#: site, and the shard STILL carries it as ROUTING_CONFIRMED -- so any cohort
#: builder keying on "confirmed route" picks it up, which is exactly what
#: happened on this order's first run.
POISONED_HOSTS = {"detroitriverwalkhotel.com"}

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
    results = R11.load(RESULTS_025)

    # Identities order 025 determined are NOT routing work.
    held_out = {}
    for row in results["rows"]:
        cls = row.get("classification")
        if cls in ("IDENTITY_REVIEW_FIRST", "PROPERTY_CLOSED_OR_CONVERTED"):
            held_out[row["identity_key"]] = cls
    # Roberts Riverwalk stays eligible: it is ROUTING_UNRESOLVED, not an
    # identity defect -- the building exists, its domain was stolen.

    triage_020 = R11.load(LP / "detroit_ann_arbor_attended_triage_020.json")
    captured_ok = {row["identity_key"] for row in triage_020["results"]
                   if row.get("outcome") in ("PUBLICATION_CANDIDATE",)}

    unresolved = sorted(set(census) - published - excluded)
    free_capture, routing_search, withheld = [], [], []

    for key in unresolved:
        crow = census[key]
        route = routes.get(key)
        url = (route or {}).get("official_property_url") or ""
        status = (route or {}).get("status") or ""
        host = registrable(url)
        confirmed = (route is not None and status == "ROUTING_CONFIRMED"
                     and url.lower().startswith("https://")
                     and not any(f in url.lower()
                                 for f in BRAND_INDEX_FRAGMENTS))

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", crow.get("canonical_name") or ""),
            ("canonical_url", url), ("host", host),
            ("address", crow.get("address") or ""),
            ("city", crow.get("city") or ""),
            ("state", crow.get("state") or ""),
            ("postal_code", crow.get("postal_code") or ""),
            ("phone", crow.get("phone") or ""),
            ("slug", crow.get("slug") or ""),
        ])

        if key in held_out:
            entry["withheld_because"] = (
                "order 025 determined %s; a routing order does not resolve "
                "identity" % held_out[key])
            withheld.append(entry)
            continue
        if by_class.get(key) == "SOURCE_SILENT":
            entry["withheld_because"] = (
                "SOURCE_SILENT -- reached at $0, the site publishes no pet "
                "policy; the route is fine and re-capturing changes nothing")
            withheld.append(entry)
            continue
        if by_class.get(key) == "AWAITING_FOUNDER_RULING":
            entry["withheld_because"] = "founder/guard hold"
            withheld.append(entry)
            continue
        if key in captured_ok:
            entry["withheld_because"] = "already captured successfully"
            withheld.append(entry)
            continue
        if host in POISONED_HOSTS:
            entry["withheld_because"] = (
                "POISONED ROUTE -- the domain lapsed and now redirects to an "
                "online-gambling site. It must never be opened or captured, "
                "and its shard status of ROUTING_CONFIRMED is itself a defect "
                "this order corrects")
            entry["route_status_defect"] = True
            withheld.append(entry)
            continue

        if confirmed and host in FREE_PROVEN_HOSTS:
            entry["lane"] = "FREE_ATTENDED_QUALIFIED"
            free_capture.append(entry)
        elif confirmed and host in PAID_ONLY_HOSTS:
            entry["lane"] = "BRIGHTDATA_QUALIFIED"
            withheld.append(dict(entry, withheld_because=(
                "holds a good route on a family this market PROVED refuses an "
                "anonymous fetch; it is a paid row, not routing work")))
        elif confirmed:
            entry["lane"] = "FREE_ATTENDED_UNTESTED"
            free_capture.append(entry)
        else:
            entry["needs_route"] = (
                "no route" if route is None else
                "status %s" % status if status != "ROUTING_CONFIRMED" else
                "brand-index or unusable URL")
            routing_search.append(entry)

    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-detroit-cohorts-026/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("unresolved_total", len(unresolved)),
        ("free_capture_cohort", OrderedDict([
            ("count", len(free_capture)),
            ("by_host", dict(Counter(r["host"] for r in free_capture))),
            ("rows", free_capture),
        ])),
        ("routing_search_cohort", OrderedDict([
            ("count", len(routing_search)),
            ("rows", routing_search),
        ])),
        ("withheld", OrderedDict([
            ("count", len(withheld)),
            ("reasons", dict(Counter(
                (r["withheld_because"].split(" --")[0].split(";")[0])[:52]
                for r in withheld))),
            ("rows", withheld),
        ])),
    ]))

    print("=== Phase 1: cohorts rebuilt from current state ===")
    print("  unresolved total        :", len(unresolved))
    print("  A. FREE_CAPTURE cohort  :", len(free_capture))
    for host, n in sorted(Counter(r["host"] for r in free_capture).items()):
        print("       %-30s %d" % (host, n))
    for row in free_capture:
        print("       - %s" % row["canonical_name"])
    print("  B. ROUTING_SEARCH cohort:", len(routing_search))
    print("  withheld                :", len(withheld))
    for reason, n in sorted(Counter(
            (r["withheld_because"].split(" --")[0].split(";")[0])[:52]
            for r in withheld).items()):
        print("       %-54s %d" % (reason, n))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
