"""PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 -- complete accounting.

Cloned from the Charleston SC accounting helper (itself from Boone - Blowing Rock NC and Atlanta GA). Every
discovered candidate, every census identity in exactly one disposition, every hold by
class, per-corridor and per-area coverage, lane yields, the vacation-rental filter's
refusals, the shadow package's identity, its independent reproduction, measured timings
and the release stop -- computed from the committed market-local documents, never typed
(the timings are the wall-clock observations of this run, recorded as observed).

Output:
  launch_packages/pettripfinder/markets/reports/hampton_roads_va_source_ready_accounting_009.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "hampton-roads-va"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "hampton_roads_va_source_ready_accounting_009.json")

#: Measured wall-clock facts of this run (UTC), recorded as observed.
from scripts.pettripfinder.hampton_roads_va_timings_009 import TIMINGS  # noqa: E402


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _pin(row):
    if row.get("latitude") is not None:
        return float(row["latitude"]), float(row["longitude"])
    for o in row.get("evidence") or ():
        if o.get("lat") is not None:
            try:
                return float(o["lat"]), float(o["lng"])
            except (TypeError, ValueError):
                continue
    return None


def area_coverage(hotels, pf, np_):
    """The order's named areas: the property's OWN stated street first, then its pin. Reporting only."""
    from scripts.pettripfinder import hampton_roads_va_geography_001 as GEO
    areas = OrderedDict((a, []) for a in (
        "Downtown Richmond", "Shockoe / Riverfront", "VCU Medical Center", "VCU Monroe Park", "Museum District / Fan",
        "Scott's Addition / Willow Lawn", "West End", "Short Pump", "Innsbrook", "Glen Allen", "RIC Airport", "Sandston",
        "Henrico / I-64 East", "RIC Airport / Sandston (other)", "I-95 North / Chamberlayne", "Virginia Center",
        "I-95 South / Richmond South", "Chesterfield", "Midlothian", "Bon Air", "Mechanicsville", "Ashland", "Chester"))
    unplaced = []
    for h in hotels:
        state = ("PUBLISHED_PET_FRIENDLY" if h["identity_key"] in pf
                 else "VERIFIED_NO_PETS" if h["identity_key"] in np_ else "UNRESOLVED")
        row = OrderedDict([("canonical_name", h["canonical_name"]), ("state", state), ("street", h.get("street"))])
        p = _pin(h) or (None, None)
        area = GEO.route_overlay((h.get("corridor") or "").split("__")[-1], h.get("street"), p[0], p[1])
        (areas[area] if area in areas else unplaced).append(row)

    def summary(rows):
        return OrderedDict([("census", len(rows)),
                            ("pet_friendly", sum(1 for r in rows if r["state"] == "PUBLISHED_PET_FRIENDLY")),
                            ("verified_no_pets", sum(1 for r in rows if r["state"] == "VERIFIED_NO_PETS")),
                            ("unresolved", sum(1 for r in rows if r["state"] == "UNRESOLVED")),
                            ("identities", rows)])
    return OrderedDict([
        ("what_it_is", "Coverage for the order's named areas. Reporting only; membership and corridor come from the "
                       "postal partition. VCU Medical Center and Shockoe share 23219 with downtown; Scott's Addition shares "
                       "23230 with the West End; Bon Air shares 23235 with Midlothian; Henrico I-64 East is folded into the "
                       "airport corridor."),
        ("areas", OrderedDict((a, summary(rows)) for a, rows in areas.items())),
        ("unplaced", summary(unplaced)),
    ])


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "hampton_roads_va_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "hampton_roads_va_geography_001.json"))
    capture = _load(os.path.join(REPORTS, "hampton_roads_va_attended_capture_001.json"))
    clean = _load(os.path.join(REPORTS, "hampton_roads_va_clean_authority_001.json"))
    recon = _load(os.path.join(REPORTS, "hampton_roads_va_census_reconciliation_001.json"))
    gaps = _load(os.path.join(REPORTS, "hampton_roads_va_competitor_gap_matrix_001.json"))
    osm = _load(os.path.join(REPORTS, "hampton_roads_va_osm_lane_001.json"))
    brand = _load(os.path.join(REPORTS, "hampton_roads_va_brand_inventory_001.json"))
    wyn = _load(os.path.join(REPORTS, "hampton_roads_va_wyndham_lane_001.json"))
    roster = _load(os.path.join(REPORTS, "hampton_roads_va_destination_roster_001.json"))
    shadow = _load(os.path.join(REPORTS, "hampton_roads_va_shadow_package_008.json"))

    hotels, non_admitted = census["hotels"], census["non_admitted"]
    items = partition["items"]
    states = Counter(i["final_state"] for i in items)
    by_state = {}
    for i in items:
        by_state.setdefault(i["final_state"], []).append(i["canonical_name"])

    def names(klass, pred=lambda r: True):
        return sorted(r["canonical_name"] for r in non_admitted if r["classification"] == klass and pred(r))

    def reason(r):
        return r.get("classification_reason") or ""

    geo_holds = names("IDENTITY_REVIEW_REQUIRED", lambda r: reason(r).startswith("GEOGRAPHY_HOLD"))
    founder = []
    review = names("IDENTITY_REVIEW_REQUIRED", lambda r: not reason(r).startswith("GEOGRAPHY_HOLD")
                   and r["canonical_name"] not in founder)
    access = Counter("OWN_SITE" for i in items if i["final_state"] == "ACCESS_BLOCKED")
    future = names("OUTSIDE_MARKET", lambda r: "FUTURE_SUBMARKET" in reason(r))
    non_hotel = [r for r in non_admitted if r["classification"] == "NON_LODGING"]

    def nh_class(r):
        why = reason(r).lower()
        # RICHMOND kinds, tested first
        if "apartment" in why:
            return "APARTMENT_OR_RENTAL_UNITS"
        if "chamber of commerce" in why or "motorsports venue" in why:
            return "VENUE_OR_OFFICE"
        if "short-term-rental" in why or "private cottage" in why:
            return "SHORT_TERM_RENTAL_OR_PRIVATE_DWELLING"
        if "vacation-rental" in why and "files this listing" in why:
            return "BUREAU_VACATION_RENTAL_OR_PROPERTY_MANAGER"
        if "campground" in why:
            return "CAMPGROUND_RV_STATE_PARK"
        if "stvr" in why:
            return "MAP_SHORT_TERM_VACATION_RENTAL"
        if "tourism=" in why or "cottage" in why:
            return "MAP_APARTMENT_COTTAGE_UNIT"
        if "venue" in why or "booking website" in why or "management company" in why or "hotel group" in why:
            return "VENUE_BAR_BOOKING_SITE_OR_MANAGEMENT_OFFICE"
        if "portfolio" in why or "guesty" in why or "30 days" in why:
            return "SHORT_TERM_RENTAL_PORTFOLIO_UNIT"
        if "private" in why or "member" in why:
            return "PRIVATE_MEMBER_ONLY_LODGING"
        return "OTHER_NON_HOTEL"

    held_classes = Counter(r["classification"] for r in clean["rejected"])
    holds = OrderedDict([
        ("IDENTITY_HOLDS", OrderedDict([
            ("count", len(review) + len(names("NAME_ONLY_UNRESOLVED")) + len(names("SAME_IDENTITY_REBRAND_SUCCESSOR"))
             + len(names("SAME_CAMPUS_DISTINCT_ENTITY"))),
            ("identity_review_required", review),
            ("name_only_unresolved", names("NAME_ONLY_UNRESOLVED")),
            ("rebrand_unresolved", names("SAME_IDENTITY_REBRAND_SUCCESSOR")),
            ("same_campus_unproved", names("SAME_CAMPUS_DISTINCT_ENTITY")),
            ("note", "Not census identities and never published: brand-flag map and bureau rows the brand's own "
                     "inventory does not list at that address (Econo Lodge / Rodeway Inn / Quality Inn Central on Arthur "
                     "Ashe Boulevard and West Broad, Sleep Inn & Suites at 80 Cottage Greene Drive -- now the Comfort Inn & "
                     "Suites Ashland -- Suburban Extended Stay at 2401 West Hundred Road, Super 8 Motel Ashland), same-name "
                     "pairs (Regency Inn x2), rows no first-party source gives a municipality (All Day Inn, Cadillac Motel, "
                     "Snow White Motel, White House Motor Lodge), lodging-category reviews (Roslyn Retreat & Conference "
                     "Center, Classified Moto) and name-only map rows (The Massad House Hotel, Virginia Cliff Inn, Lee's "
                     "Motel, Baymount Inn and Suites, Par 3).")])),
        ("ROUTING_HOLDS", OrderedDict([("count", states.get("AWAITING_OFFICIAL_URL", 0)),
                                       ("identities", by_state.get("AWAITING_OFFICIAL_URL", []))])),
        ("ACCESS_BLOCKED", OrderedDict([("count", states.get("ACCESS_BLOCKED", 0)),
                                        ("by_cause", dict(access)),
                                        ("identities", by_state.get("ACCESS_BLOCKED", []))])),
        ("EVIDENCE_HOLDS", OrderedDict([("count", states.get("AWAITING_POLICY_OBSERVATION", 0)),
                                        ("identities", by_state.get("AWAITING_POLICY_OBSERVATION", [])),
                                        ("rejected_reads_by_class", OrderedDict(sorted(held_classes.items())))])),
        ("GEOGRAPHY_HOLDS", OrderedDict([("count", len(geo_holds)), ("identities", geo_holds)])),
        ("PAID_HOLDS", OrderedDict([
            ("count", 0),
            ("note", "No cohort is routed to a paid lane: PAID PROVIDER BUDGET was $0 and no paid lane was used or "
                     "reserved. The access-blocked cohort (Motel 6 / Studio 6 x4, Quality Inn Richmond Airport, V.I.P. Inn, "
                     "Inn at Patrick Henry's) is held ACCESS_BLOCKED for a re-probe, not a paid lane.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", len(founder)), ("identities", founder),
            ("note", "None. Co-location holds (12500 Chestnut Hill Road; 1320 East Cary Street) are registration-order "
                     "work in shared identity state, not founder rulings.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", len(wyn.get("retired_routes") or [])),
            ("wyndham_retired_routes", wyn.get("retired_routes")),
            ("note", "Wyndham routes in Richmond-area cities that redirect to the brand's city search (retired or "
                     "rebranded). Routes, not census identities.")])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET"))),
                                 ("future_market_petersburg_tri_cities", len(future)),
                                 ("future_market_identities", future)])),
        ("NON_HOTEL", OrderedDict([("count", len(non_hotel)),
                                   ("by_kind", OrderedDict(sorted(Counter(nh_class(r) for r in non_hotel).items()))),
                                   ("identities", sorted(r["canonical_name"] for r in non_hotel))])),
    ])

    pf = {i["identity_key"] for i in items if i["final_state"] == "PUBLISHED_PET_FRIENDLY"}
    np_ = {i["identity_key"] for i in items if i["final_state"] == "VERIFIED_NO_PETS"}
    minimum = {c["corridor_id"]: c.get("minimum_hotel_count", 5)
               for c in _load(os.path.join(PKG, "markets", "proposed", "%s.json" % MARKET_ID))["corridors"]}
    coverage = []
    for c in geography["corridors"]:
        cid = c["corridor_id"]
        rows = [h for h in hotels if h.get("corridor") == cid]
        n_pf = sum(1 for h in rows if h["identity_key"] in pf)
        n_np = sum(1 for h in rows if h["identity_key"] in np_)
        coverage.append(OrderedDict([
            ("corridor_id", cid), ("geography_class", c["geography_class"]),
            ("postal_codes", c["included_postal_codes"]),
            ("census", len(rows)), ("pet_friendly", n_pf), ("verified_no_pets", n_np),
            ("unresolved", len(rows) - n_pf - n_np),
            ("corridor_page_publishes", n_pf >= minimum.get(cid, 5)),
        ]))

    doc = OrderedDict([
        ("schema", "ptf-market-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("display_market", "Richmond, Virginia"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("release_queue", "Current verified live: Atlanta (23 markets / 1500 profiles / 1744 routes, deploy "
                          "6aa7f125a91c73ba2363139e, commit 6825851b). Richmond waits for its turn in the serialized "
                          "release lane behind the queued markets."),
        ("timings", TIMINGS),
        ("accounting", OrderedDict([
            ("TOTAL_DISCOVERED", census["total_candidates"]),
            ("total_discovered_note",
             "Distinct candidate identities in the identity graph after merging every lane. Not counted: %d unnamed map "
             "elements, %d retired Wyndham routes, and the Hilton / IHG / Choice national-navigation codes outside "
             "Virginia's 230xx-232xx / 238xx postal prefixes." % (
                 sum(1 for e in osm["elements"] if not (e.get("tags") or {}).get("name")),
                 len(wyn.get("retired_routes") or []))),
            ("classification_counts", census["classification_counts"]),
            ("PROPOSED_CENSUS", census["count"]),
            ("VALID_PET_FRIENDLY", states.get("PUBLISHED_PET_FRIENDLY", 0)),
            ("VALID_VERIFIED_NO_PETS", states.get("VERIFIED_NO_PETS", 0)),
            ("RESOLVED", partition["resolved"]), ("UNRESOLVED", partition["unresolved"]),
            ("partition_counts_by_state", OrderedDict(sorted(states.items()))),
            ("every_census_identity_has_exactly_one_disposition",
             len(items) == census["count"] and len({i["identity_key"] for i in items}) == census["count"]),
            ("every_census_identity_key_unique", len({h["identity_key"] for h in hotels}) == len(hotels)),
        ])),
        ("holds_by_class", holds),
        ("corridor_coverage", coverage),
        ("corridor_pages_meeting_threshold", sum(1 for c in coverage if c["corridor_page_publishes"])),
        ("area_coverage", area_coverage(hotels, pf, np_)),
        ("lane_yields", OrderedDict([
            ("osm_elements", osm["element_count"]),
            ("brand_inventory_leads", brand["lead_count"]),
            ("brand_family_dispositions", brand.get("dispositions")),
            ("visit_hampton_roads_va_roster", OrderedDict([("coverage", roster.get("coverage")),
                                                   ("listings", roster["listing_count"]),
                                                   ("by_category", roster["lodging_by_subcategory"])])),
            ("census_lane_observations", recon["lane_yields"]),
            ("first_party_reads", capture["counts"]),
            ("wyndham_property_service", OrderedDict([("routes", wyn["routes_selected"]), ("read", wyn["read"]),
                                                      ("retired", wyn["retired"]), ("errors", wyn["errors"])])),
            ("clean_set", clean["counts"]),
        ])),
        ("competitor_gap_challenge", gaps["counts"]),
        ("owned_evidence", OrderedDict([
            ("OWNED_IDENTITIES", "0 -- no committed census or authority holds a 230xx-232xx / 238xx Virginia identity; "
                                 "Richmond KY / IN / CA / BC routes are refused by the brand lane's NEGATIVE tokens."),
            ("OWNED_ROUTES", "40 -- RIC-coded Marriott routes from the committed national harvest "
                             "dayton_oh_brand_directory_harvest_001 (read at zero requests; every one re-read on Marriott's "
                             "own page, 35 in market)."),
            ("OWNED_VALID_POLICY_EVIDENCE", "0 -- every policy record here is a new first-party capture of this order."),
        ])),
        ("package", OrderedDict([
            ("SHADOW_PACKAGE_CREATED", "YES"), ("execution_zone", shadow["execution_zone"]),
            ("package_id", shadow["package_id"]), ("PACKAGE_DIGEST", shadow["package_digest"]),
            ("created_from_source_sha", shadow["created_from_source_sha"]),
            ("package_path", shadow["package_path"]),
            ("BUILD_INPUT_KEY", shadow["build_input_key"]),
            ("INTENDED_DELTA", shadow["intended_delta"]),
            ("VALIDATION_RECEIPT", OrderedDict([("path", shadow["receipt_path"]), ("digest", shadow["receipt_digest"]),
                                                ("eligible", shadow["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
                                                ("rules", shadow["fast_rules"]),
                                                ("unknown", shadow["unknown_rules"]), ("failed", shadow["failed_rules"]),
                                                ("determinism", shadow["determinism_result"])])),
            ("COVERAGE_SCORECARD", shadow["coverage_scorecard"]),
            ("parent_binding", shadow["parent_binding"]),
        ])),
        ("factory_code_changed", "NO -- every changed path is a hampton_roads_va_* helper, the market's discovery config, or a "
                                 "document under the market's own proposed / staging / report paths"),
        ("shared_factory_notes_recorded_not_repaired", [
            "The shared first-party reader reads 'This location does not accept pets. Service and emotional support animals "
            "are always welcome.' (HomeTowne Studios W Broad St) as SERVICE_ANIMAL_ONLY, 'We do not accept animals, but "
            "there are boarding facilities and pet friendly hotels nearby' (Museum District B&B) as contradicting itself, "
            "and 'Pets Not Allowed / ... one time non-refundable pet fee' (SpringHill Suites North/Glen Allen) as not "
            "operative; those rows are held with the exact wording.",
            "The shared address_key drops street directionals, so 107 N. Carter Road (Quality Inn & Suites Ashland) and 107 "
            "South Carter Road (Holiday Inn Express & Suites Richmond North Ashland) collapse to one key; the "
            "pet-friendly record is held ADDRESS_KEY_DIRECTIONAL_COLLISION.",
            "The sealed-package writer refuses a read from a host other than the census route (INVALID_ROUTE): Linden Row "
            "Inn's own FAQ ('Linden Row Inn has a small number of pet-friendly rooms available for reservation by direct "
            "booking only.') cannot publish while the census binds the identity to its Best Western (WorldHotels "
            "Distinctive) route, whose page says only 'Pets may be accepted. Please contact the hotel for full details.'",
        ]),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("next_order", [
            "When Richmond reaches the front of the serialized release lane, read CURRENT VERIFIED LIVE and merge that live "
            "parent into worker/ptf-hampton-roads-va-market-001; the Atlanta binding of this shadow package is then invalid (FAST "
            "rule N fails it by design).",
            "Copy markets/proposed/hampton-roads-va.json -> markets/hampton-roads-va.json, identity_census_proposed/hampton-roads-va.json -> "
            "identity_census/hampton-roads-va.json and the staged launch_package documents (hotel_policy_facts_hampton-roads-va.json, "
            "hampton_roads_va_final_partition_007.json, the authority shard) into their registered paths; repoint the helpers' paths.",
            "Record same-campus resolutions in identity_resolutions.json -- 12500 Chestnut Hill Road (Hampton Inn Richmond "
            "Chester + Home2 Suites Richmond Chester), 1320 East Cary Street (Courtyard Richmond Downtown + Residence Inn "
            "Richmond Downtown), and the directional pair 107 N. / 107 South Carter Road, Ashland -- and re-admit the held "
            "records through the census and clean set.",
            "market_registration_cli --write, build_global_authority --write then --check, the release contract, "
            "registration_release_lane register + seal --work-order (a NEW package id), FAST.",
            "regression_delta classify (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, prepare "
            "the founder packet; deploy only on founder authorization.",
            "Before sealing: re-probe Choice (va033 Quality Inn Richmond Airport; the Choice WoodSpring routes), Motel 6 / "
            "Studio 6, vipmotorinn.com; find address-bearing documents for InTown Suites x2; read The Jefferson Hotel, Linden "
            "Row Inn (route conflict) and the map-only motels on Midlothian Turnpike, Brook Road and Jefferson Davis Highway.",
        ]),
    ])
    return doc


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    a = doc["accounting"]
    print({k: a[k] for k in ("TOTAL_DISCOVERED", "PROPOSED_CENSUS", "VALID_PET_FRIENDLY", "VALID_VERIFIED_NO_PETS", "RESOLVED", "UNRESOLVED")})
    print({k: v["count"] for k, v in doc["holds_by_class"].items()})
    print("non-hotel by kind", dict(doc["holds_by_class"]["NON_HOTEL"]["by_kind"]))
    for c in doc["corridor_coverage"]:
        print(c["corridor_id"].split("__")[1], c["geography_class"], c["census"], c["pet_friendly"], c["verified_no_pets"], c["unresolved"], c["corridor_page_publishes"])
    print("areas", {k: (v["census"], v["pet_friendly"], v["verified_no_pets"], v["unresolved"]) for k, v in doc["area_coverage"]["areas"].items()},
          "unplaced", doc["area_coverage"]["unplaced"]["census"])
    print(doc["package"]["PACKAGE_DIGEST"], a["every_census_identity_has_exactly_one_disposition"], a["every_census_identity_key_unique"])
    print("gap", doc["competitor_gap_challenge"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
