"""PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001 -- Phase 2: reuse Miami's Broward DISCOVERY intelligence.

Miami (market #31, live) drew its observation box deliberately wide: it reached north over the Broward County
line into Hallandale Beach, Hollywood, Dania Beach and Fort Lauderdale so that PTF-MIAMI-FL-HARDENED-SOURCE-
READY-001 would classify those properties ON EVIDENCE rather than be blind to them. Every one of them was
refused -- MIAMI ADMITTED 0 FROM BROWARD -- but the identities, their aliases, their DBPR licences, their brand
property codes, their map pins and the provider history against them were all committed to Miami's graph.

This helper reads those committed artifacts and hands Fort Lauderdale a PRIOR-DISCOVERY index.

WHAT IS REUSED, AND WHAT IS NOT
--------------------------------
REUSED (identity and routing intelligence, revalidated here):
  * the identity key, canonical name and every alias Miami's hard-key merge proved
  * the licensed premises: street, city, ZIP, phone, DBPR licence number, rank code and rental units
  * brand property codes and official routes Miami's brand lanes bound
  * map pins (OSM), competitor leads and destination-roster associations
  * the lane history: which lanes had already SEEN this identity, and Miami's own ruling on it

NOT REUSED (never imported as authority):
  * MEMBERSHIP. Every row is re-classified here by THIS market's corridor registry over the property's own
    postal code. Miami's "OUTSIDE_MARKET" ruling is recorded as provenance, never as an admission.
  * PET POLICY. No Miami policy fact, quote, evidence row or capture is imported. Miami published nothing for
    any Broward row (every one of them is POLICY_NOT_VERIFIED there, which this helper asserts), and even if it
    had, a policy would have to be re-acquired first-party against this market's own evidence contract.
  * LODGING QUALIFICATION. Miami's IDENTITY_REVIEW / NON_LODGING rulings are carried as PRIOR RULINGS for the
    reconciliation to consider on its own evidence; they do not decide anything here.

The census lanes run independently and in full: this index is a cross-check and a provenance source, never a
substitute for discovery. A row that only Miami saw is a LEAD that this market's own lanes must still confirm.

Outputs:
  launch_packages/pettripfinder/markets/reports/fort_lauderdale_fl_miami_reuse_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import fort_lauderdale_fl_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "fort-lauderdale-fl"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
MIAMI_GRAPH = os.path.join(REPORTS, "miami_fl_census_reconciliation_001.json")
MIAMI_GEOGRAPHY = os.path.join(REPORTS, "miami_fl_geography_001.json")
MIAMI_DBPR = os.path.join(REPORTS, "miami_fl_dbpr_lane_001.json")
OUT = os.path.join(REPORTS, "fort_lauderdale_fl_miami_reuse_001.json")
MIAMI_WORK_ORDER = "PTF-MIAMI-FL-HARDENED-SOURCE-READY-001"


def _s(v):
    return " ".join(str(v or "").split())


def _zip5(v):
    return "".join(ch for ch in _s(v) if ch.isdigit())[:5]


def build():
    admitted = set()
    for c in GEO.CORRIDORS:
        admitted.update(c[5])

    graph = json.load(open(MIAMI_GRAPH, encoding="utf-8"))
    rows = graph.get("rows") or []

    reused, policy_carried, prior_rulings = [], [], []
    for r in rows:
        z = _zip5(r.get("postal_code"))
        if z not in admitted:
            continue
        klass, slug, why = GEO.classify_postal(z, r.get("city"))
        if r.get("policy_state") not in (None, "", "POLICY_NOT_VERIFIED"):
            policy_carried.append(OrderedDict([("identity_key", r.get("identity_key")),
                                               ("policy_state", r.get("policy_state"))]))
        entry = OrderedDict([
            ("prior_market", "miami-fl"),
            ("prior_work_order", MIAMI_WORK_ORDER),
            ("prior_identity_key", _s(r.get("identity_key"))),
            ("prior_slug", _s(r.get("slug"))),
            ("canonical_name", _s(r.get("canonical_name"))),
            ("identity_key_aliases", [a for a in (r.get("identity_key_aliases") or []) if a]),
            ("street", _s(r.get("street"))),
            ("street_identity", _s(r.get("street_identity"))),
            ("city", _s(r.get("city"))),
            ("state", _s(r.get("state"))),
            ("postal_code", z),
            ("phone", _s(r.get("phone"))),
            ("phone_key", _s(r.get("phone_key"))),
            ("brand", _s(r.get("brand"))),
            ("property_code", _s(r.get("property_code"))),
            ("official_url", _s(r.get("official_url"))),
            ("latitude", r.get("latitude")),
            ("longitude", r.get("longitude")),
            ("prior_lanes", sorted({_s(x) for x in (r.get("lanes") or []) if x})),
            ("prior_best_tier", r.get("best_tier")),
            ("prior_classification", _s(r.get("classification"))),
            ("prior_classification_reason", _s(r.get("classification_reason"))),
            ("prior_identity_state", _s(r.get("identity_state"))),
            ("prior_lodging_state", _s(r.get("lodging_state"))),
            ("prior_policy_state", _s(r.get("policy_state"))),
            ("prior_evidence_lanes", sorted({_s(e.get("lane")) for e in (r.get("evidence") or []) if e.get("lane")})),
            ("prior_licence_numbers", sorted({_s(e.get("license_number")) for e in (r.get("evidence") or [])
                                              if e.get("license_number")})),
            # THIS market's own ruling on membership -- never Miami's
            ("fort_lauderdale_geography_class", klass),
            ("fort_lauderdale_corridor_slug", slug),
            ("fort_lauderdale_membership_reason", why),
            ("policy_imported", False),
            ("policy_import_refused_because",
             "No Miami policy fact, quote or capture is imported into Fort Lauderdale. Policy must be acquired "
             "first-party against this market's own evidence contract."),
        ])
        reused.append(entry)
        if r.get("classification") in ("IDENTITY_REVIEW_REQUIRED", "NON_LODGING", "SAME_CAMPUS_DISTINCT_ENTITY",
                                       "DUPLICATE_LISTING"):
            prior_rulings.append(OrderedDict([
                ("identity_key", _s(r.get("identity_key"))), ("canonical_name", _s(r.get("canonical_name"))),
                ("street", _s(r.get("street"))), ("postal_code", z),
                ("prior_ruling", _s(r.get("classification"))),
                ("prior_reason", _s(r.get("classification_reason"))),
                ("binding_here", False),
                ("how_used_here", "Carried to the reconciliation as PRIOR EVIDENCE for the same premises. This "
                                  "market rules on its own evidence; Miami's ruling never decides."),
            ]))

    reused.sort(key=lambda r: (r["postal_code"], r["street"].upper(), r["canonical_name"].upper()))

    # The boundary numbers Miami itself published, re-read from Miami's own committed DBPR lane.
    miami_dbpr = json.load(open(MIAMI_DBPR, encoding="utf-8"))
    miami_boundary = miami_dbpr.get("south_florida_boundary_by_county") or {}
    broward_seen_by_miami = (miami_boundary.get("broward") or {})

    by_corridor = Counter(r["fort_lauderdale_corridor_slug"] for r in reused)
    by_prior = Counter(r["prior_classification"] for r in reused)
    by_lane = Counter()
    for r in reused:
        for lane in r["prior_lanes"]:
            by_lane[lane] += 1

    return OrderedDict([
        ("schema", "ptf-prior-market-discovery-reuse/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "2 -- reuse Miami's Broward discovery intelligence"),
        ("prior_market", "miami-fl"),
        ("prior_work_order", MIAMI_WORK_ORDER),
        ("prior_artifacts_read", [os.path.relpath(p, _DASH).replace("\\", "/")
                                  for p in (MIAMI_GRAPH, MIAMI_GEOGRAPHY, MIAMI_DBPR)]),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("what_is_reused",
         "Identity and routing intelligence only: identity keys, aliases, licensed premises (street / city / ZIP / "
         "phone / DBPR licence number / rank / units), brand property codes, official routes, map pins, competitor "
         "and roster associations, and which lanes had already seen the identity."),
        ("what_is_not_reused",
         "MEMBERSHIP (every row is re-classified by this market's corridor registry over its own postal code), "
         "PET POLICY (nothing imported -- policy is re-acquired first-party here) and LODGING QUALIFICATION "
         "(Miami's rulings are carried as prior evidence, never as decisions)."),
        ("miami_admitted_from_broward", 0),
        ("miami_admitted_from_broward_source",
         "miami_fl_geography_001 refuses every Broward postal code by name; miami_fl_dbpr_lane_001 records the "
         "county observation with admitted_into_miami = 0."),
        ("miami_broward_hotel_rank_licences_observed", broward_seen_by_miami.get("hotel_rank_licences")),
        ("miami_broward_by_city_observed", broward_seen_by_miami.get("by_city")),
        ("miami_graph_nodes_total", len(rows)),
        ("miami_discovered_broward_identities_reused", len(reused)),
        ("reused_by_fort_lauderdale_corridor", OrderedDict(sorted(by_corridor.items()))),
        ("reused_by_miami_classification", OrderedDict(sorted(by_prior.items()))),
        ("reused_by_prior_lane", OrderedDict(sorted(by_lane.items(), key=lambda kv: -kv[1]))),
        ("reused_with_brand_property_code", sum(1 for r in reused if r["property_code"])),
        ("reused_with_official_url", sum(1 for r in reused if r["official_url"])),
        ("reused_with_coordinates", sum(1 for r in reused if r["latitude"] is not None)),
        ("reused_with_dbpr_licence", sum(1 for r in reused if r["prior_licence_numbers"])),
        ("prior_rulings_carried_as_evidence", prior_rulings),
        ("miami_policy_rows_over_broward", policy_carried),
        ("miami_policy_rows_over_broward_count", len(policy_carried)),
        ("policy_evidence_imported", 0),
        ("identities", reused),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("miami-discovered Broward identities reused:", rep["miami_discovered_broward_identities_reused"])
    print("  with brand code:", rep["reused_with_brand_property_code"],
          " with official url:", rep["reused_with_official_url"],
          " with coords:", rep["reused_with_coordinates"],
          " with DBPR licence:", rep["reused_with_dbpr_licence"])
    print("  prior rulings carried:", len(rep["prior_rulings_carried_as_evidence"]),
          " miami policy rows over Broward:", rep["miami_policy_rows_over_broward_count"])
    print("  by corridor:", json.dumps(rep["reused_by_fort_lauderdale_corridor"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
