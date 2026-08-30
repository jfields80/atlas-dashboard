# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-025, Phase 1.

Rebuilds the ROUTING_REPAIR_FIRST cohort from CURRENT state and sub-classifies
why each row needs repair, so the repair work can be aimed rather than guessed.

THE 31 IS RE-DERIVED, NOT INHERITED. Order 024 reported it while it was
applying authority; nine rows have resolved since and the routing shard has
moved. A cohort assembled from a previous order's count would work on rows that
no longer need it and miss rows that now do.

A ROW IS ADMITTED ONLY IF ROUTING IS GENUINELY THE BLOCKER. Source-silent rows
have a perfectly good route and a page that says nothing about pets; a founder
hold is a decision, not a defect. Sweeping either into a routing repair would
manufacture work and, worse, could quietly re-open something a founder settled.

NO PROVIDER IS CALLED AND NOTHING IS ACQUIRED.
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
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-025"
AS_OF = "2026-08-30"

LP = R11.LP
OUT = LP / "detroit_ann_arbor_routing_cohort_025.json"

#: Founder decisions. A routing repair may never re-open one.
FOUNDER_HOLDS = {
    "royal park hotel", "the siren hotel", "hyatt place detroit livonia",
}

#: Known-bad route shapes, established by this market's own captures.
DEAD_ROUTE_NOTES = {
    "roberts riverwalk hotel": (
        "HIJACKED_DOMAIN",
        "detroitriverwalkhotel.com 301s to bonanza88jpresmi.com, an "
        "online-gambling site. The domain lapsed and was re-registered."),
    "drury inn and suites": (
        "DEAD_LEGACY_HOST",
        "wwws.druryhotels.com/PropertyHotelServices.aspx?Property=0029 fails "
        "at the network layer; zero bytes of hotel content."),
    "radisson hotel detroit farmington hills": (
        "BRAND_INDEX_COLLAPSE",
        "the committed URL 302s to /en-us/brand/radisson, which names no "
        "building and carries no property policy."),
}

#: A path that names no building. A route ending at one of these is not a
#: property route however much of the hotel's name appears elsewhere in it.
BRAND_INDEX_RES = ("/brand/", "/hotels/travel/", "/find-hotels",
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
    silent = {row["identity_key"] for row in classification["rows"]
              if row["classification"] == "SOURCE_SILENT"}

    unresolved = sorted(set(census) - published - excluded)
    admitted, skipped = [], []
    for key in unresolved:
        crow = census[key]
        route = routes.get(key)
        url = (route or {}).get("official_property_url") or ""
        status = (route or {}).get("status") or ""
        host = registrable(url)

        if key in silent:
            skipped.append((key, "SOURCE_SILENT -- the route works; the page "
                                 "says nothing about pets"))
            continue
        if key in FOUNDER_HOLDS:
            skipped.append((key, "FOUNDER/GUARD HOLD -- a decision, not a "
                                 "routing defect"))
            continue

        if key in DEAD_ROUTE_NOTES:
            sub, why = DEAD_ROUTE_NOTES[key]
        elif route is None:
            sub, why = "NO_ROUTE", "no route record exists for this identity"
        elif status != "ROUTING_CONFIRMED":
            sub, why = "UNCONFIRMED_ROUTE", "route status is %s" % status
        elif not url:
            sub, why = "NO_ROUTE", "route record carries no URL"
        elif not url.lower().startswith("https://"):
            sub, why = ("UNUSABLE_ROUTE",
                        "not an absolute https first-party URL")
        elif any(frag in url.lower() for frag in BRAND_INDEX_RES):
            sub, why = ("BRAND_INDEX", "the routed path names no building")
        else:
            skipped.append((key, "holds a currently valid first-party route"))
            continue

        needs_identity = not (crow.get("address") or "").strip()
        admitted.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", crow.get("canonical_name") or ""),
            ("sub_classification",
             "IDENTITY_REVIEW_FIRST" if needs_identity else sub),
            ("why", why if not needs_identity else
             "the census cannot place this property; identity must be "
             "resolved before a route can be bound to it"),
            ("current_route", url),
            ("current_route_status", status or "(none)"),
            ("host", host),
            ("brand_hint", (crow.get("brand") or "").strip()),
            ("address", crow.get("address") or ""),
            ("city", crow.get("city") or ""),
            ("state", crow.get("state") or ""),
            ("postal_code", crow.get("postal_code") or ""),
            ("phone", crow.get("phone") or ""),
            ("slug", crow.get("slug") or ""),
        ]))

    counts = Counter(row["sub_classification"] for row in admitted)
    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-detroit-routing-cohort/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("rebuilt_from_current_state", True),
        ("unresolved_total", len(unresolved)),
        ("admitted", len(admitted)),
        ("counts", dict(counts)),
        ("excluded_from_the_cohort", [OrderedDict([("identity_key", k),
                                                   ("why", w)])
                                      for k, w in skipped]),
        ("rows", admitted),
    ]))

    print("=== Phase 1: routing cohort rebuilt from current state ===")
    print("  unresolved total          :", len(unresolved))
    print("  ROUTING_REPAIR_FIRST      :", len(admitted))
    for name, n in sorted(counts.items()):
        print("     %-24s %d" % (name, n))
    print("  not a routing problem     :", len(skipped))
    for reason, n in Counter(w.split(" --")[0] for _k, w in skipped).items():
        print("     %-44s %d" % (reason[:44], n))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
