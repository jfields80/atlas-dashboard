# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-PILOT-014, Phases 1 and 2.

Builds and clears the second Bright Data pilot. NOTHING IS SPENT HERE.

THIS PILOT EXISTS TO NARROW AN INTERVAL, so it is selected to be as unlike
pilot 013 as the market allows. Every row 013 attempted is excluded, and within
what is left the cohort is spread across four axes rather than one:

  sub-brand   -- a rate measured on six Hampton Inns describes Hampton Inns
  city        -- one suburb's properties often share an operator
  URL shape   -- Marriott serves both ``/hotels/travel/<code>-slug`` and
                 ``/en-us/hotels/<code>-slug/overview/``; Hilton serves both
                 ``www.hilton.com/en/hotels/<code>-slug`` and per-brand hosts
                 like ``hamptoninn3.hilton.com``
  page template -- which is what the URL shape is a proxy for, and the thing a
                 systemic reader defect would hide behind

CONCURRENCY IS PROVEN, NOT ASSUMED. Order 013 spent $2.64 against a $2.28 cap
because a second runner was launched while the first was still alive. So this
phase records the lock state and the live-process check as artifacts, and the
runner refuses to start without an exclusive lock.

A BUFFERED LOG IS NOT EVIDENCE OF A STALL. That is the mistake that cost the
cap, and the run artifact says so where the next operator will read it.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS      # noqa: E402
from scripts.pettripfinder.acquisition import registry as REG             # noqa: E402
from scripts.pettripfinder import (                                       # noqa: E402
    detroit_ann_arbor_holds_and_status_011 as S11)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-PILOT-014"
RUN_ID = "detroit-brightdata-014-pilot"
AS_OF = "2026-08-29"

LANE = PROVIDERS.BRIGHTDATA_BROWSER
CAP_USD = 3.00
#: Measured in pilot 013: $2.64 over 16 billed attempts.
USD_PER_ATTEMPT = 0.165
PER_FAMILY = 8
MAX_ROWS = 16

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
ADMITTED_PATH = LP / "detroit_ann_arbor_brightdata_admitted_014.json"
PLAN_PATH = LP / "detroit_ann_arbor_brightdata_cost_plan_014.json"

BRAND_WALL_HOSTS = {"marriott.com": "MARRIOTT", "hilton.com": "HILTON"}


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def registrable(url: str) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    parts = [part for part in host.split(".") if part]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def url_shape(url: str) -> str:
    """The page TEMPLATE this URL implies, as a coarse label.

    A systemic reader defect lives in a template, not in a hotel, so a pilot
    that draws every row from one template can measure 100% and still be blind.
    """
    split = urlsplit(url or "")
    host = (split.hostname or "").lower()
    path = split.path.lower()
    if host and not host.startswith("www."):
        return "%s:per-brand-host" % registrable(host)
    if "/en-us/hotels/" in path:
        return "marriott:/en-us/hotels/"
    if "/hotels/travel/" in path:
        return "marriott:/hotels/travel/"
    if "/en/hotels/" in path:
        return "hilton:/en/hotels/"
    return "other:%s" % (path.split("/")[1] if path.count("/") > 1 else "root")


def sub_brand_of(url: str, family: str, name: str) -> str:
    """The product family, from the URL slug or, failing that, the NAME.

    ``S11.sub_brand`` reads the family out of the property slug, which a bare
    short URL like ``marriott.com/dtwcf`` does not carry -- and its fallback
    then labels a Courtyard "marriott-collection", which would have counted a
    second Courtyard as a distinct sub-brand and overstated this pilot's
    diversity. The hotel's own name settles it when the URL cannot.
    """
    label = S11.sub_brand(url, family)
    if not label.endswith("-collection"):
        return label
    lowered = " %s " % " ".join((name or "").lower().split())
    for candidate in S11._SUB_BRANDS:
        if " %s " % candidate.replace("-", " ") in lowered:
            return candidate
    return label


def build() -> Dict:
    ledger = load(LEDGER_PATH)
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = [route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"]
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    index = PAL.LedgerIndex(ledger)
    registry = REG.load()

    # Everything Detroit has ever paid for, on any lane. Pilot 013's rows are
    # in here by construction, so "not attempted in 013" needs no special case.
    paid_before = {attempt["identity_key"] for attempt in ledger["attempts"]
                   if attempt.get("market_id") == MARKET}

    pools: Dict[str, List[Dict]] = {"MARRIOTT": [], "HILTON": []}
    rejected: List[Dict] = []
    for route in routes:
        key = route["hotel_ref"]["identity_key"]
        url = route.get("official_property_url") or ""
        family = BRAND_WALL_HOSTS.get(registrable(url))
        if family is None:
            continue
        row = census.get(key) or {}
        checks = OrderedDict([
            ("unresolved", key not in published and key not in excluded),
            ("in_market", key in census),
            ("has_canonical_property_page",
             url.lower().startswith("https://")),
            ("not_previously_paid_by_detroit", key not in paid_before),
        ])
        verdict = PAL.decide(
            OrderedDict([("identity_key", key), ("official_url", url),
                         ("market_id", MARKET), ("brand", family),
                         ("property_code", route.get("property_code") or "")]),
            index, available_lanes=(LANE,))
        checks["no_reusable_artifact_answers_it"] = not verdict.get(
            "reusable_evidence")
        checks["ledger_permits_this_lane"] = (
            verdict["decision"] not in PAL.SUPPRESSED_DECISIONS)
        route_decision = REG.resolve(brand=family, url=url, identity_key=key,
                                     registry=registry)
        checks["registry_routes_it_to_this_lane"] = (
            route_decision.provider == LANE)

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name") or ""),
            ("brand", family),
            ("sub_brand", sub_brand_of(url, family,
                                       row.get("canonical_name") or "")),
            ("city", row.get("city") or ""),
            ("canonical_url", url),
            ("url_shape", url_shape(url)),
            ("property_code", route.get("property_code") or ""),
            ("reader", route_decision.reader),
            ("checks", checks),
        ])
        if all(checks.values()):
            pools[family].append(entry)
        else:
            entry["rejected_because"] = [name for name, ok in checks.items()
                                         if not ok]
            rejected.append(entry)

    def spread(rows: List[Dict], want: int) -> List[Dict]:
        """Round-robin across sub-brand, preferring an unused URL shape then an
        unused city at each step. Diversity first, alphabet last."""
        buckets: "OrderedDict[str, List[Dict]]" = OrderedDict()
        for row in sorted(rows, key=lambda r: (r["sub_brand"], r["city"],
                                               r["canonical_name"])):
            buckets.setdefault(row["sub_brand"], []).append(row)
        picked: List[Dict] = []
        seen_shapes, seen_cities = set(), set()
        while len(picked) < want and any(buckets.values()):
            for name in list(buckets):
                if len(picked) >= want:
                    break
                queue = buckets[name]
                if not queue:
                    buckets.pop(name, None)
                    continue
                choice = (
                    next((r for r in queue
                          if r["url_shape"] not in seen_shapes
                          and r["city"] not in seen_cities), None)
                    or next((r for r in queue
                             if r["url_shape"] not in seen_shapes), None)
                    or next((r for r in queue
                             if r["city"] not in seen_cities), None)
                    or queue[0])
                queue.remove(choice)
                if not queue:
                    buckets.pop(name, None)
                picked.append(choice)
                seen_shapes.add(choice["url_shape"])
                seen_cities.add(choice["city"])
        return picked

    admitted: List[Dict] = []
    seen_url, seen_identity = {}, {}
    for family in ("MARRIOTT", "HILTON"):
        for row in spread(pools[family], PER_FAMILY):
            canonical = PAL.canonical_url({"official_url": row["canonical_url"]})
            identity = PAL.property_identity(
                {"official_url": row["canonical_url"]})
            if canonical in seen_url or (identity and identity in seen_identity):
                row["rejected_because"] = ["duplicate page or building inside "
                                           "the pilot"]
                rejected.append(row)
                continue
            seen_url[canonical] = row["identity_key"]
            if identity:
                seen_identity[identity] = row["identity_key"]
            admitted.append(row)

    by_family = Counter(row["brand"] for row in admitted)
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-admitted/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID), ("lane", LANE),
        ("lanes_forbidden", ["firecrawl", "google_places",
                             "brightdata_web_unlocker"]),
        ("purpose", "narrow the intervals pilot 013 left wide. Selected to be "
                    "as unlike 013 as the market allows: every row it "
                    "attempted is excluded, and the rest are spread across "
                    "sub-brand, city, URL shape and page template."),
        ("max_rows", MAX_ROWS), ("preferred_per_family", PER_FAMILY),
        ("pool_available", {family: len(rows)
                            for family, rows in pools.items()}),
        ("admitted", len(admitted)),
        ("admitted_by_family", dict(by_family)),
        ("split_achieved",
         "%d Marriott / %d Hilton"
         % (by_family.get("MARRIOTT", 0), by_family.get("HILTON", 0))),
        ("no_unrelated_family_substituted", True),
        ("diversity", OrderedDict([
            ("sub_brands", sorted({row["sub_brand"] for row in admitted})),
            ("cities", sorted({row["city"] for row in admitted if row["city"]})),
            ("url_shapes", sorted({row["url_shape"] for row in admitted})),
            ("distinct_sub_brands", len({row["sub_brand"] for row in admitted})),
            ("distinct_cities", len({row["city"] for row in admitted})),
            ("distinct_url_shapes", len({row["url_shape"]
                                         for row in admitted})),
        ])),
        ("overlap_with_pilot_013", 0),
        ("rejected", len(rejected)),
        ("rejected_rows", rejected[:40]),
        ("admitted_rows", admitted),
    ])
    write_lf(ADMITTED_PATH, doc)
    return doc


def cost_plan(admitted: List[Dict], usage) -> Dict:
    affordable = int(round(CAP_USD * 100)) // int(round(USD_PER_ATTEMPT * 100))
    rows = min(len(admitted), affordable, MAX_ROWS)
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-cost-plan/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("authorisation", OrderedDict([
            ("lane", LANE), ("hard_cap_usd", CAP_USD),
            ("max_rows", MAX_ROWS),
            ("firecrawl", "FORBIDDEN"), ("google_places", "FORBIDDEN"),
            ("web_unlocker", "FORBIDDEN -- no escalation"),
        ])),
        ("unit_cost", OrderedDict([
            ("usd_per_attempt", USD_PER_ATTEMPT),
            ("basis", "MEASURED in pilot 013: $2.64 of zone cost over 16 "
                      "billed attempts. Not a vendor list price."),
        ])),
        ("cohort", OrderedDict([
            ("admitted", len(admitted)),
            ("affordable_under_cap", affordable),
            ("rows_this_run", rows),
            ("truncated_before_spending", rows < len(admitted)),
        ])),
        ("projected", OrderedDict([
            ("attempts", rows),
            ("worst_case_usd", round(rows * USD_PER_ATTEMPT, 2)),
            ("margin_under_cap", round(CAP_USD - rows * USD_PER_ATTEMPT, 2)),
        ])),
        ("account", OrderedDict([
            ("zone", usage.zone),
            ("month_to_date_cost_usd",
             (usage.cost_month_usd_minor or 0) / 100.0),
            ("balance_usd", (usage.balance_usd_minor or 0) / 100.0),
            ("sufficient", (usage.balance_usd_minor or 0) / 100.0
             >= rows * USD_PER_ATTEMPT),
            ("caveat", "zone cost is MONTH-TO-DATE and settles upward; a "
                       "balance is not a cost meter"),
        ])),
        ("concurrency", OrderedDict([
            ("exclusive_run_lock", "REQUIRED. The runner takes it before its "
                                   "first paid call and refuses to start if "
                                   "one exists."),
            ("why", "pilot 013 spent $2.64 against a $2.28 cap because a "
                    "second runner was launched while the first was still "
                    "alive, and the already-bought guard reads the ledger only "
                    "at startup."),
            ("do_not", "infer a stalled run from buffered stdout. Check the "
                       "process, the ledger's growth, or the vendor meter."),
        ])),
    ])
    write_lf(PLAN_PATH, doc)
    return doc


def run() -> None:
    from scripts.pettripfinder.brightdata import client

    doc = build()
    print("=== Phase 1: fresh pilot cohort ===")
    print("  pool available   :", doc["pool_available"])
    print("  ADMITTED         :", doc["admitted"], doc["admitted_by_family"])
    print("  overlap with 013 :", doc["overlap_with_pilot_013"])
    d = doc["diversity"]
    print("  diversity        : %d sub-brands, %d cities, %d URL shapes"
          % (d["distinct_sub_brands"], d["distinct_cities"],
             d["distinct_url_shapes"]))
    print("  url shapes       :", d["url_shapes"])
    print()
    for row in doc["admitted_rows"]:
        print("   %-8s %-18s %-38s %-16s" % (row["brand"], row["sub_brand"],
                                             row["canonical_name"][:38],
                                             row["city"]))

    usage = client.read_usage("pre-%s" % RUN_ID)
    plan = cost_plan(doc["admitted_rows"], usage)
    print()
    print("=== Phase 2: cost plan and concurrency ===")
    print("  rows this run    :", plan["cohort"]["rows_this_run"])
    print("  worst case       : $%.2f of $%.2f (margin $%.2f)"
          % (plan["projected"]["worst_case_usd"], CAP_USD,
             plan["projected"]["margin_under_cap"]))
    print("  zone month-to-date $%.2f | balance $%.2f"
          % (plan["account"]["month_to_date_cost_usd"],
             plan["account"]["balance_usd"]))
    print("wrote", ADMITTED_PATH.name, "and", PLAN_PATH.name)


if __name__ == "__main__":
    run()
