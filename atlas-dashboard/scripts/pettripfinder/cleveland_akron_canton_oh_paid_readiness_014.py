"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phase 14.

Paid readiness for the rows the free lanes could not close. Nothing is
spent; no provider is called. Every rate is READ FROM THE CANONICAL
CROSS-RUN LEDGERS at run time (paid-attempt ledger for page fetches,
discovery-attempt ledger for lookups) -- never from a static constant. Where
the ledger records no spend for a lane, the lane is UNPRICED_BY_LEDGER and
its cost is refused rather than invented.

Inputs: the phase-7 rebuild, the phase-8 routing recovery, the phase-9 static
capture, the owned-evidence replay, and the two ledgers.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
SCHEMA = "ptf-paid-readiness-plan/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PAID_LEDGER = os.path.join(PKG, "ptf_paid_attempt_ledger_001.json")
DISC_LEDGER = os.path.join(PKG, "ptf_discovery_attempt_ledger_001.json")
BRIGHTDATA_BRANDS = ("MARRIOTT", "HILTON")
FREE_ATTENDED_PROVEN = ("IHG", "CHOICE", "WYNDHAM", "HILTON", "DRURY", "BEST_WESTERN", "RED_ROOF")


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def wilson_lower(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / float(n)
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - m) / d)


def measured_rates():
    paid = read_json(PAID_LEDGER)["attempts"] if os.path.exists(PAID_LEDGER) else []
    disc = read_json(DISC_LEDGER)["attempts"] if os.path.exists(DISC_LEDGER) else []
    lanes = OrderedDict()
    for lane in ("brightdata_browser", "brightdata_web_unlocker", "firecrawl"):
        rows = [x for x in paid if x.get("lane") == lane]
        billed = [x for x in rows if (x.get("cost_usd_minor") or 0) > 0]
        cost = sum(x.get("cost_usd_minor") or 0 for x in rows) / 100.0
        pg = sum(1 for x in rows if x.get("publication_grade"))
        lanes[lane] = OrderedDict([
            ("attempts", len(rows)), ("billed_attempts", len(billed)), ("usd_spent", round(cost, 2)),
            ("usd_per_billed_attempt", round(cost / len(billed), 4) if billed else None),
            ("unit_price_state", "MEASURED_FROM_LEDGER" if billed else "UNPRICED_BY_LEDGER"),
            ("publication_grade", pg), ("publication_grade_rate", round(pg / float(len(rows)), 4) if rows else None),
            ("publication_grade_rate_wilson_lower", round(wilson_lower(pg, len(rows)), 4) if rows else None),
        ])
    by_brand = {}
    for x in paid:
        if not (x.get("lane") or "").startswith("brightdata"):
            continue
        b = x.get("brand") or "INDEPENDENT"
        s = by_brand.setdefault(b, [0, 0])
        s[0] += 1
        s[1] += 1 if x.get("publication_grade") else 0
    brand_yield = OrderedDict((b, OrderedDict([("attempts", n), ("publication_grade", p), ("rate", round(p / float(n), 4)), ("rate_wilson_lower", round(wilson_lower(p, n), 4))]))
                              for b, (n, p) in sorted(by_brand.items()) if n >= 5)
    bound = sum(1 for x in disc if x.get("outcome") == DAL.BIND_BOUND)
    disc_cost = sum(x.get("cost_usd_minor") or 0 for x in disc)
    discovery = OrderedDict([
        ("provider", "GOOGLE_PLACES"), ("attempts", len(disc)), ("bound", bound),
        ("bind_rate", round(bound / float(len(disc)), 4) if disc else None), ("bind_rate_wilson_lower", round(wilson_lower(bound, len(disc)), 4) if disc else None),
        ("usd_recorded_in_ledger", disc_cost / 100.0),
        ("unit_price_state", "MEASURED_FROM_LEDGER" if disc_cost > 0 else "UNPRICED_BY_LEDGER"),
        ("why", "the discovery ledger records %s; a cap is meaningless against a number nobody read" % ("spend, so the unit price is the ledger's" if disc_cost > 0 else "no spend for any lookup, so this plan refuses to invent a per-request price -- read the live console rate before authorising any spend")),
    ])
    cleveland_paid = [x for x in paid if x.get("market_id") == MARKET_ID]
    cleveland_disc = [x for x in disc if x.get("market_id") == MARKET_ID]
    return lanes, brand_yield, discovery, OrderedDict([("paid_attempts_for_this_market", len(cleveland_paid)), ("discovery_attempts_for_this_market", len(cleveland_disc))])


def build() -> OrderedDict:
    rebuild = read_json(os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_unresolved_rebuild_007.json"))
    routing_p = os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_routing_recovery_008.json")
    routing = read_json(routing_p) if os.path.exists(routing_p) else {"details": [], "routes_recovered": []}
    static_p = os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_free_static_capture_009.json")
    static = {r["identity_key"]: r for r in read_json(static_p)["rows"]} if os.path.exists(static_p) else {}
    attended_p = os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_attended_capture_009b.json")
    attended = {r["identity_key"]: r for r in read_json(attended_p)["results"]} if os.path.exists(attended_p) else {}
    routing_state = {r["identity_key"]: r for r in routing.get("details", [])}
    routed = {r["identity_key"]: r for r in routing.get("routes_recovered", [])}
    lanes, brand_yield, discovery, market_ledger = measured_rates()

    rows = []
    for r in rebuild["rows"]:
        key = r["identity_key"]
        fam = r["brand_family"]
        lane7 = r["lane"]
        st = static.get(key)
        rs = routing_state.get(key)
        at = attended.get(key)
        at_cls = (at or {}).get("classification", "")
        if at_cls in ("PET_FRIENDLY_STATED_ATTENDED", "NO_PETS_STATED_ATTENDED"):
            lane = "FREE_LANE_EXHAUSTED"
        elif at_cls in ("NON_LODGING_PAGE", "MULTI_PROPERTY_OPERATOR_NOT_A_SINGLE_PREMISES"):
            lane = "IDENTITY_REVIEW_FIRST"
        elif at_cls == "SOURCE_SILENT_ATTENDED":
            lane = "SOURCE_SILENT"
        elif at_cls == "AMENITY_CHIP_ONLY_NOT_EVIDENCE":
            lane = "SOURCE_SILENT"
        elif lane7 == "IDENTITY_REVIEW_FIRST":
            lane = "IDENTITY_REVIEW_FIRST"
        elif lane7 == "FOUNDER_HOLD":
            lane = "FOUNDER_HOLD"
        elif lane7 == "SOURCE_SILENT":
            lane = "SOURCE_SILENT"
        elif lane7 == "OWNED_EVIDENCE_REUSABLE":
            lane = "FREE_LANE_EXHAUSTED"  # nothing to buy; application only
        elif lane7 == "ROUTING_REPAIR_FIRST":
            if key in routed:
                lane = "FREE_LANE_EXHAUSTED" if (st and st.get("classification", "").startswith(("CLEAN", "PET_FRIENDLY_READ", "NO_PETS_READ"))) else "FREE_ATTENDED_QUALIFIED"
            elif rs and rs["state"] == "ROUTE_PROPOSED_ATTENDED_BINDING_REQUIRED":
                lane = "FREE_ATTENDED_QUALIFIED"
            elif fam == "INDEPENDENT":
                lane = "PAID_DISCOVERY_REQUIRED"
            elif fam in BRIGHTDATA_BRANDS:
                lane = "PAID_DISCOVERY_REQUIRED"
            else:
                lane = "PAID_DISCOVERY_REQUIRED"
        elif lane7 in ("FREE_STATIC_QUALIFIED", "FREE_ATTENDED_QUALIFIED"):
            cls = (st or {}).get("classification", "")
            if cls.startswith("CLEAN_") or cls.endswith("_TEXT_BOUND"):
                lane = "FREE_LANE_EXHAUSTED"
            elif cls in ("ACCESS_BLOCKED_PLAIN_CLIENT", "NEEDS_ATTENDED_RENDER", "IDENTITY_NOT_CONFIRMED_STATIC", "IDENTITY_TEXT_BOUND_POLICY_SILENT", "") or lane7 == "FREE_ATTENDED_QUALIFIED":
                lane = "FREE_ATTENDED_QUALIFIED" if fam not in BRIGHTDATA_BRANDS else "BRIGHTDATA_QUALIFIED"
            elif cls == "SOURCE_SILENT_STATIC":
                lane = "SOURCE_SILENT"
            else:
                lane = "OTHER"
        elif lane7 == "BRIGHTDATA_QUALIFIED":
            lane = "BRIGHTDATA_QUALIFIED"
        else:
            lane = "OTHER"
        if lane == "PAID_DISCOVERY_REQUIRED" and fam == "INDEPENDENT":
            sub = "INDEPENDENT"
        else:
            sub = fam
        rows.append(OrderedDict([("identity_key", key), ("canonical_name", r["canonical_name"]), ("brand_family", fam), ("phase7_lane", lane7),
                                 ("routing_state", (rs or {}).get("state")), ("static_classification", (st or {}).get("classification")), ("attended_classification", at_cls or None), ("lane", lane), ("segment", sub)]))

    counts = OrderedDict(sorted(Counter(r["lane"] for r in rows).items()))
    bd_rows = [r for r in rows if r["lane"] == "BRIGHTDATA_QUALIFIED"]
    disc_rows = [r for r in rows if r["lane"] == "PAID_DISCOVERY_REQUIRED"]
    bd_unit = lanes["brightdata_browser"]["usd_per_billed_attempt"]
    bd_rate = lanes["brightdata_browser"]["publication_grade_rate_wilson_lower"] or 0.0
    disc_rate = discovery["bind_rate_wilson_lower"] or 0.0
    # expected attempts: each Bright Data row is one billed attempt (retries are the escalation policy's, priced separately at 1.25x cap)
    bd_expected_attempts = len(bd_rows)
    bd_expected_usd = round(bd_expected_attempts * bd_unit, 2) if bd_unit else None
    bd_cap_usd = round(bd_expected_attempts * bd_unit * 1.25, 2) if bd_unit else None
    disc_expected_binds = round(len(disc_rows) * disc_rate, 1)
    pilot = OrderedDict([
        ("recommended_first_pilot", OrderedDict([
            ("brightdata_rows", min(len(bd_rows), 10)),
            ("brightdata_usd_expected", round(min(len(bd_rows), 10) * bd_unit, 2) if bd_unit else None),
            ("brightdata_hard_cap_usd", round(min(len(bd_rows), 10) * bd_unit * 1.25, 2) if bd_unit else None),
            ("discovery_rows", min(len(disc_rows), 10)),
            ("discovery_usd", discovery["unit_price_state"]),
            ("rule", "cap against a LIVE balance read before the run and stop WHEN the cap is exceeded, not after; the balance settles late so it is not a cost meter"),
        ])),
    ])
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("phase", "14 -- paid readiness (nothing spent)"), ("market_id", MARKET_ID), ("as_of", "2026-09-01"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("rates_source", OrderedDict([("paid_attempt_ledger", os.path.relpath(PAID_LEDGER, _DASH)), ("discovery_attempt_ledger", os.path.relpath(DISC_LEDGER, _DASH)),
                                      ("rule", "rates are read from the ledgers at run time; no static constant is an expected cost")])),
        ("measured_rates", OrderedDict([("lanes", lanes), ("brand_publication_grade_yield_brightdata", brand_yield), ("discovery", discovery), ("this_market_in_ledgers", market_ledger)])),
        ("lane_counts", counts),
        ("segments", OrderedDict((lane, OrderedDict(sorted(Counter(r["segment"] for r in rows if r["lane"] == lane).items()))) for lane in counts)),
        ("brightdata", OrderedDict([("eligible_rows", len(bd_rows)), ("expected_attempts", bd_expected_attempts), ("unit_price_usd", bd_unit),
                                    ("unit_price_state", lanes["brightdata_browser"]["unit_price_state"]), ("expected_usd", bd_expected_usd),
                                    ("conservative_hard_cap_usd", bd_cap_usd), ("expected_publication_grade_rows", round(bd_expected_attempts * bd_rate, 1)),
                                    ("publication_grade_rate_used", bd_rate)])),
        ("paid_discovery", OrderedDict([("eligible_rows", len(disc_rows)), ("expected_lookups", len(disc_rows)), ("expected_binds_at_measured_rate", disc_expected_binds),
                                        ("unit_price_state", discovery["unit_price_state"]), ("expected_usd", "CANNOT BE QUOTED UNTIL THE RATE IS READ" if discovery["unit_price_state"] == "UNPRICED_BY_LEDGER" else None),
                                        ("note", "you cannot buy a page you cannot address: discovery must bind a first-party URL before any policy acquisition is priced")])),
        ("firecrawl", OrderedDict([("eligible_rows", 0), ("why", "not a lane for this cohort: cannot reach Marriott or Hilton and the ledger records %d attempts" % lanes["firecrawl"]["attempts"])])),
        ("pilot", pilot),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_paid_readiness_014.json"))
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("lanes:", dict(rep["lane_counts"]))
    print("brightdata:", json.dumps(rep["brightdata"]))
    print("discovery:", json.dumps({k: v for k, v in rep["paid_discovery"].items() if k != "note"}))
    print("rates:", json.dumps({k: (v["usd_per_billed_attempt"], v["publication_grade_rate"], v["attempts"]) for k, v in rep["measured_rates"]["lanes"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
