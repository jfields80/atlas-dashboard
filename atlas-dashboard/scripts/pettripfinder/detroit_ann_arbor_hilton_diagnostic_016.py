# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HILTON-DIAGNOSTIC-016, Phases 1 and 2.

Builds the final Hilton diagnostic cohort and clears it to spend. NOTHING IS
SPENT HERE.

THIS COHORT IS BUILT TO EXPLAIN FAILURES, NOT TO FLATTER A RATE. Hilton's two
pilots left four non-acquisitions with no shared pattern, and the open question
is whether those were transient or systemic. So the selection deliberately
REACHES FOR the shapes implicated by the misses -- in particular the legacy
per-brand hosts like ``hamptoninn3.hilton.com``, where one NAVIGATION_FAILED
sat -- rather than quietly drawing ten easy rows off the modern template and
declaring the family healthy.

THE COST RATE IS THE BALANCE-DERIVED ONE. Order 015 found Bright Data's
month-to-date zone meter restating DOWNWARD while bandwidth rose, so the
prepaid balance is what this project now plans against: $4.28 over 48 billed
attempts, $0.089 each. Ten attempts is about $0.89 against a $1.50 cap.

But a rate is still an assumption, so the runner does not rely on it: the cap
is enforced during the run against ACTUAL BALANCE MOVEMENT, and the run stops
before an attempt that could carry cumulative spend past $1.50.
"""
from __future__ import annotations

import json
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
    detroit_ann_arbor_brightdata_pilot_014 as P14)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-HILTON-DIAGNOSTIC-016"
RUN_ID = "detroit-brightdata-016-hilton-diagnostic"
AS_OF = "2026-08-30"
FAMILY = "HILTON"

LANE = PROVIDERS.BRIGHTDATA_BROWSER
CAP_USD = 1.50
MAX_ROWS = 10
#: Balance-derived, per order 015: $4.28 over 48 billed attempts.
USD_PER_ATTEMPT = 0.0892

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
ADMITTED_PATH = LP / "detroit_ann_arbor_hilton_admitted_016.json"
PLAN_PATH = LP / "detroit_ann_arbor_hilton_cost_plan_016.json"

PRIOR_CLASSIFICATIONS = (
    LP / "detroit_ann_arbor_brightdata_classification_013.json",
    LP / "detroit_ann_arbor_brightdata_classification_014.json",
)


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def hostname(url: str) -> str:
    return (urlsplit(url or "").hostname or "").lower()


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

    prior_keys = set()
    for path in PRIOR_CLASSIFICATIONS:
        for row in load(path)["results"]:
            prior_keys.add(row["identity_key"])
    paid_any = {attempt["identity_key"] for attempt in ledger["attempts"]
                if attempt.get("market_id") == MARKET}
    paid_won = {attempt["identity_key"] for attempt in ledger["attempts"]
                if attempt.get("market_id") == MARKET
                and attempt.get("publication_grade")}

    pool, rejected = [], []
    for route in routes:
        key = route["hotel_ref"]["identity_key"]
        url = route.get("official_property_url") or ""
        if P14.registrable(url) != "hilton.com":
            continue
        row = census.get(key) or {}
        checks = OrderedDict([
            ("unresolved", key not in published and key not in excluded),
            ("in_market", key in census),
            ("hilton_family", True),
            ("canonical_property_page", url.lower().startswith("https://")),
            ("not_previously_paid_successfully", key not in paid_won),
            ("not_captured_in_013_or_014", key not in prior_keys),
            ("never_paid_at_all", key not in paid_any),
        ])
        verdict = PAL.decide(
            OrderedDict([("identity_key", key), ("official_url", url),
                         ("market_id", MARKET), ("brand", FAMILY),
                         ("property_code", route.get("property_code") or "")]),
            index, available_lanes=(LANE,))
        checks["ledger_permits_this_lane"] = (
            verdict["decision"] not in PAL.SUPPRESSED_DECISIONS)
        checks["no_reusable_artifact_answers_it"] = not verdict.get(
            "reusable_evidence")
        decision = REG.resolve(brand=FAMILY, url=url, identity_key=key,
                               registry=registry)
        checks["registry_routes_it_to_this_lane"] = decision.provider == LANE

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name") or ""),
            ("brand", FAMILY),
            ("sub_brand", P14.sub_brand_of(url, FAMILY,
                                           row.get("canonical_name") or "")),
            ("city", row.get("city") or ""),
            ("hostname", hostname(url)),
            ("canonical_url", url),
            ("url_shape", P14.url_shape(url)),
            ("property_code", route.get("property_code") or ""),
            ("reader", decision.reader),
            ("legacy_per_brand_host",
             bool(hostname(url)) and not hostname(url).startswith("www.")),
            ("checks", checks),
        ])
        if all(checks.values()):
            pool.append(entry)
        else:
            entry["rejected_because"] = [name for name, ok in checks.items()
                                         if not ok]
            rejected.append(entry)

    # SELECT FOR EXPLANATORY POWER. Every legacy per-brand host first -- those
    # are the shape a prior NAVIGATION_FAILED sat on and the single most useful
    # thing this diagnostic can test -- then spread across sub-brand and city.
    legacy = [row for row in pool if row["legacy_per_brand_host"]]
    modern = [row for row in pool if not row["legacy_per_brand_host"]]

    def spread(rows: List[Dict], want: int, seen_brands: set,
               seen_cities: set) -> List[Dict]:
        buckets: "OrderedDict[str, List[Dict]]" = OrderedDict()
        for row in sorted(rows, key=lambda r: (r["sub_brand"], r["city"],
                                               r["canonical_name"])):
            buckets.setdefault(row["sub_brand"], []).append(row)
        picked: List[Dict] = []
        while len(picked) < want and any(buckets.values()):
            for name in list(buckets):
                if len(picked) >= want:
                    break
                queue = buckets[name]
                if not queue:
                    buckets.pop(name, None)
                    continue
                choice = (next((r for r in queue
                                if r["sub_brand"] not in seen_brands
                                and r["city"] not in seen_cities), None)
                          or next((r for r in queue
                                   if r["city"] not in seen_cities), None)
                          or queue[0])
                queue.remove(choice)
                if not queue:
                    buckets.pop(name, None)
                picked.append(choice)
                seen_brands.add(choice["sub_brand"])
                seen_cities.add(choice["city"])
        return picked

    seen_brands, seen_cities = set(), set()
    admitted = spread(legacy, min(len(legacy), MAX_ROWS), seen_brands,
                      seen_cities)
    admitted += spread(modern, MAX_ROWS - len(admitted), seen_brands,
                       seen_cities)

    seen_url, seen_identity, deduped = {}, {}, []
    for row in admitted:
        canonical = PAL.canonical_url({"official_url": row["canonical_url"]})
        identity = PAL.property_identity({"official_url": row["canonical_url"]})
        if canonical in seen_url or (identity and identity in seen_identity):
            row["rejected_because"] = ["duplicate page or building in cohort"]
            rejected.append(row)
            continue
        seen_url[canonical] = row["identity_key"]
        if identity:
            seen_identity[identity] = row["identity_key"]
        deduped.append(row)
    admitted = deduped

    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-admitted/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID), ("lane", LANE), ("family", FAMILY),
        ("scope", "HILTON ONLY. Marriott is closed and the 43 registry-"
                  "deferred rows are out of scope; neither is touched."),
        ("purpose",
         "settle whether Hilton's four prior non-acquisitions were transient "
         "or systemic. Selection reaches FOR the implicated shapes rather than "
         "away from them."),
        ("eligible_pool", len(pool)),
        ("planned_rows", MAX_ROWS),
        ("admitted", len(admitted)),
        ("full_cohort_constructible", len(admitted) == MAX_ROWS),
        ("overlap_with_013_014", 0),
        ("diversity", OrderedDict([
            ("sub_brands", sorted({row["sub_brand"] for row in admitted})),
            ("cities", sorted({row["city"] for row in admitted if row["city"]})),
            ("hostnames", sorted({row["hostname"] for row in admitted})),
            ("url_shapes", sorted({row["url_shape"] for row in admitted})),
            ("legacy_per_brand_hosts_included",
             sum(1 for row in admitted if row["legacy_per_brand_host"])),
            ("legacy_per_brand_hosts_available", len(legacy)),
        ])),
        ("rejected", len(rejected)),
        ("admitted_rows", admitted),
        ("rejected_rows", rejected[:30]),
    ])
    write_lf(ADMITTED_PATH, doc)
    return doc


def cost_plan(admitted: List[Dict], usage) -> Dict:
    balance = (usage.balance_usd_minor or 0) / 100.0
    projected = len(admitted) * USD_PER_ATTEMPT
    #: A margin, because a rate is an assumption and a balance is not. The run
    #: also checks actual balance movement before every attempt.
    safety_multiple = 2.0
    sufficient = balance >= projected * safety_multiple
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-cost-plan/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("authorisation", OrderedDict([
            ("lane", LANE), ("family", FAMILY),
            ("hard_cap_usd", CAP_USD), ("max_rows", MAX_ROWS),
            ("firecrawl", "FORBIDDEN"), ("google_places", "FORBIDDEN"),
            ("web_unlocker", "FORBIDDEN"),
            ("marriott", "OUT OF SCOPE -- CLOSED"),
            ("other_families", "OUT OF SCOPE"),
        ])),
        ("unit_cost", OrderedDict([
            ("usd_per_attempt", USD_PER_ATTEMPT),
            ("basis", "BALANCE-DERIVED, per order 015: $4.28 of prepaid "
                      "balance consumed over 48 billed attempts. The vendor's "
                      "month-to-date zone meter restated DOWNWARD during 015 "
                      "while bandwidth rose, so it is not used for planning."),
        ])),
        ("cohort", OrderedDict([
            ("admitted", len(admitted)),
            ("rows_this_run", len(admitted)),
            ("truncated_before_spending", False),
        ])),
        ("projected", OrderedDict([
            ("attempts", len(admitted)),
            ("expected_usd", round(projected, 2)),
            ("margin_under_cap", round(CAP_USD - projected, 2)),
        ])),
        ("balance_safety", OrderedDict([
            ("balance_usd", balance),
            ("required_usd", round(projected, 2)),
            ("safety_multiple_applied", safety_multiple),
            ("sufficient_to_complete_the_whole_cohort", sufficient),
            ("rule", "the order requires STOPPING BEFORE SPENDING if the "
                     "balance cannot safely carry the entire admitted cohort. "
                     "A balance exhausted mid-run does not merely halt a "
                     "diagnostic -- it fills the remainder with authentication "
                     "failures that would read as Hilton misses, which is "
                     "precisely the question this order exists to answer."),
        ])),
        ("cap_enforcement", OrderedDict([
            ("method", "ACTUAL BALANCE MOVEMENT, checked before each attempt"),
            ("why", "a per-attempt rate is an assumption; the balance is a "
                    "measurement. The run stops before an attempt that could "
                    "carry cumulative spend past the cap."),
        ])),
        ("concurrency", OrderedDict([
            ("exclusive_lock", "REQUIRED before the first paid call"),
            ("one_runner_only", True),
            ("if_stdout_goes_quiet", "DO NOT RELAUNCH -- watch the process, "
                                     "the lock and the ledger. That misreading "
                                     "cost order 013 its cap."),
        ])),
    ])
    write_lf(PLAN_PATH, doc)
    return doc


def run() -> None:
    from scripts.pettripfinder.brightdata import client

    doc = build()
    print("=== Phase 1: Hilton diagnostic cohort ===")
    print("  eligible pool     :", doc["eligible_pool"])
    print("  ADMITTED          :", doc["admitted"],
          "(full 10 constructible: %s)" % doc["full_cohort_constructible"])
    print("  overlap with 013/014:", doc["overlap_with_013_014"])
    d = doc["diversity"]
    print("  sub-brands        :", len(d["sub_brands"]), d["sub_brands"])
    print("  cities            :", len(d["cities"]))
    print("  hostnames         :", d["hostnames"])
    print("  legacy per-brand hosts: %d included of %d available"
          % (d["legacy_per_brand_hosts_included"],
             d["legacy_per_brand_hosts_available"]))
    print()
    for row in doc["admitted_rows"]:
        print("   %-18s %-40s %-17s %s" % (row["sub_brand"],
                                           row["canonical_name"][:40],
                                           row["city"][:17], row["hostname"]))

    usage = client.read_usage("pre-%s" % RUN_ID)
    plan = cost_plan(doc["admitted_rows"], usage)
    print()
    print("=== Phase 2: pre-spend safety ===")
    print("  expected spend    : $%.2f of $%.2f (margin $%.2f)"
          % (plan["projected"]["expected_usd"], CAP_USD,
             plan["projected"]["margin_under_cap"]))
    print("  prepaid balance   : $%.2f"
          % plan["balance_safety"]["balance_usd"])
    print("  balance sufficient (2x margin):",
          plan["balance_safety"]["sufficient_to_complete_the_whole_cohort"])
    if not plan["balance_safety"]["sufficient_to_complete_the_whole_cohort"]:
        raise SystemExit("STOP BEFORE SPENDING: the prepaid balance cannot "
                         "safely carry the whole admitted cohort.")
    print("wrote", ADMITTED_PATH.name, "and", PLAN_PATH.name)


if __name__ == "__main__":
    run()
