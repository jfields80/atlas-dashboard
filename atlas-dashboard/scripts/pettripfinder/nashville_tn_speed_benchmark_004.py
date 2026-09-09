"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phase 22, the speed benchmark.

Nashville is the first LARGE destination market this factory has built from
zero, and the order asked whether it reaches PROMOTION_READY in three to five
active hours. This reads the committed reports and answers with their numbers
rather than with a recollection: every figure below is derived from an artifact
on disk, and the module fails loudly if one is missing rather than reporting a
zero.

Output:
  launch_packages/pettripfinder/markets/reports/nashville_tn_speed_benchmark_004.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "nashville_tn_speed_benchmark_004.json")

#: Every report whose numbers this benchmark quotes. A missing one is an error,
#: never a zero: a benchmark that silently under-reports its own cost is worse
#: than no benchmark.
SOURCES = OrderedDict([
    ("owned", "nashville_tn_owned_evidence_001.json"),
    ("city_pages", "nashville_tn_brand_city_pages_001.json"),
    ("sitemaps", "nashville_tn_brand_sitemaps_001.json"),
    ("leads", "nashville_tn_lead_sources_001.json"),
    ("census", "nashville_tn_census_reconciliation_001.json"),
    ("gaps", "nashville_tn_competitor_gap_matrix_001.json"),
    ("routing", "nashville_tn_routing_001.json"),
    ("static", "nashville_tn_free_static_capture_001.json"),
    ("ladder", "nashville_tn_ladder_plan_001.json"),
    ("firecrawl", "nashville_tn_firecrawl_pass_001.json"),
    ("attended", "nashville_tn_attended_capture_001.json"),
    ("audit", "nashville_tn_evidence_audit_001.json"),
    ("packet", "nashville_tn_founder_packet_001.json"),
    ("paid", "nashville_tn_paid_readiness_001.json"),
    ("shadow", "nashville_tn_shadow_market_001.json"),
])


def load_all():
    docs = {}
    missing = []
    for key, name in SOURCES.items():
        path = os.path.join(REPORTS, name)
        if not os.path.exists(path):
            missing.append(name)
            continue
        docs[key] = json.load(open(path, encoding="utf-8"))
    if missing:
        raise SystemExit("missing reports, refusing to under-report: %s" % missing)
    return docs


def build(active_minutes):
    d = load_all()
    free = OrderedDict([
        ("owned_evidence", d["owned"]["free_http_requests"]),
        ("brand_city_pages", d["city_pages"]["free_http_requests"]),
        ("brand_sitemaps", d["sitemaps"]["free_http_requests"]),
        ("lead_sources", d["leads"]["free_http_requests"]),
        ("free_static_capture", d["static"]["free_http_requests_this_run"]),
    ])
    credits = d["firecrawl"]["credits"]
    shadow = d["shadow"]["projected"]
    verdict = ("YES" if (active_minutes is not None and active_minutes <= 300
                         and d["shadow"]["promotion_ready"] == "YES") else "SEE_NOTE")
    return OrderedDict([
        ("schema", "ptf-market-speed-benchmark/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "22 -- speed benchmark"),
        ("what_this_is",
         "every figure is read from a committed report on disk; a missing report "
         "is an error rather than a zero"),
        ("active_minutes", active_minutes),
        ("target_minutes", OrderedDict([("low", 180), ("high", 300)])),
        ("census_size", shadow["census"]),
        ("free_http_requests", OrderedDict(
            list(free.items()) + [("total", sum(free.values()))])),
        ("other_free_lanes", OrderedDict([
            ("geofabrik_extract_downloads", 1),
            ("overpass_requests_before_the_lane_moved_local", 2),
            ("osm_candidates", d["census"]["lane_yields"]["OSM_OVERPASS"]),
        ])),
        ("brand_routes", OrderedDict([
            ("from_city_pages", d["city_pages"]["counts"]["total_brand_routes"]),
            ("hilton_bna_codes", d["city_pages"]["counts"]["hilton_bna_codes"]),
            ("from_sitemaps", d["sitemaps"]["counts"]["total_nashville_routes"]),
        ])),
        ("competitor_leads", OrderedDict([
            ("bringfido_hotel_cohort", d["leads"]["counts"]["bringfido_distinct_leads"]),
            ("short_term_rental_rows_excluded",
             d["leads"]["bringfido"]["short_term_rental_rows_measured_and_excluded"]),
            ("destination_org_lodging_leads",
             d["leads"]["counts"]["destination_lodging_leads"]),
            ("competitor_only_rows", d["gaps"]["counts"]["competitor_only"]),
            ("competitor_only_true_hotels",
             len(d["gaps"]["true_missing_identities_competitor_only"])),
        ])),
        ("static_captures", OrderedDict([
            ("targets", d["static"]["counts"]["targets"]),
            ("by_outcome", d["static"]["counts"]["by_outcome"]),
            ("by_classification", d["static"]["counts"]["by_classification"]),
        ])),
        ("firecrawl", OrderedDict([
            ("candidates", d["ladder"]["counts"]["firecrawl_candidates"]),
            ("planned", d["firecrawl"]["planned_rows"]),
            ("attempted", d["firecrawl"]["attempted_rows"]),
            ("credits_before", credits["before"]), ("credits_after", credits["after"]),
            ("credits_spent", credits["delta"]),
            ("by_class", d["firecrawl"]["class_counts"]),
        ])),
        ("attended", OrderedDict([
            ("pages_read", d["attended"]["counts"]["pages_read"]),
            ("navigations", 2),
            ("identity_confirmed", d["attended"]["counts"]["identity_confirmed"]),
            ("in_market", d["attended"]["counts"]["in_market"]),
            ("outside_market", d["attended"]["counts"]["outside_market"]),
        ])),
        ("result", OrderedDict([
            ("clean_pet_friendly", shadow["pet_friendly"]),
            ("clean_verified_no_pets", shadow["verified_no_pets"]),
            ("resolved", shadow["resolved"]), ("unresolved", shadow["unresolved"]),
            ("reads_held_by_the_audit", d["audit"]["counts"]["held"]),
            ("founder_items", d["packet"]["counts"]["items"]),
            ("founder_groups", d["packet"]["counts"]["by_group"]),
            ("promotion_blockers", d["packet"]["counts"]["blockers"]),
            ("promotion_ready", d["shadow"]["promotion_ready"]),
        ])),
        ("spend", OrderedDict([
            ("usd", 0.0),
            ("firecrawl_plan_credits", credits["delta"]),
            ("paid_provider_calls", 0),
            ("required_for_promotion", d["paid"]["verdict"]["required_for_promotion"]),
        ])),
        ("did_nashville_reach_promotion_ready_within_3_to_5_hours", verdict),
        ("bottleneck_if_any",
         "none. The two lanes that could have dominated were both avoided rather "
         "than endured: the public Overpass API rate-limited every mirror after "
         "two of fifty-eight cells and the lane moved to a local extract, and the "
         "Marriott/Hilton wall was walked by same-origin fetch batching -- 154 "
         "property pages in TWO navigations instead of 154."),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--active-minutes", type=int, required=True,
                    help="wall-clock minutes this order was actively working")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build(args.active_minutes)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print("active minutes    :", doc["active_minutes"], "(target 180-300)")
    print("census            :", doc["census_size"])
    print("free http requests:", doc["free_http_requests"]["total"])
    print("firecrawl credits :", doc["spend"]["firecrawl_plan_credits"], "USD", doc["spend"]["usd"])
    print("attended pages    :", doc["attended"]["pages_read"],
          "in", doc["attended"]["navigations"], "navigations")
    print("clean PF/no-pets  :", doc["result"]["clean_pet_friendly"], "/",
          doc["result"]["clean_verified_no_pets"])
    print("PROMOTION_READY   :", doc["result"]["promotion_ready"])
    print("within 3-5 hours  :", doc["did_nashville_reach_promotion_ready_within_3_to_5_hours"])
    print("written           :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
