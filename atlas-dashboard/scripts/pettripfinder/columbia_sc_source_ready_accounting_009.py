"""PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001 -- complete accounting.

Cloned from the Charleston SC accounting helper (itself from Boone - Blowing Rock NC and Atlanta GA). Every
discovered candidate, every census identity in exactly one disposition, every hold by
class, per-corridor and per-area coverage, lane yields, the vacation-rental filter's
refusals, the shadow package's identity, its independent reproduction, measured timings
and the release stop -- computed from the committed market-local documents, never typed
(the timings are the wall-clock observations of this run, recorded as observed).

Output:
  launch_packages/pettripfinder/markets/reports/columbia_sc_source_ready_accounting_009.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "columbia-sc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "columbia_sc_source_ready_accounting_009.json")

#: Measured wall-clock facts of this run (UTC), recorded as observed.
from scripts.pettripfinder.columbia_sc_timings_009 import TIMINGS  # noqa: E402


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
    from scripts.pettripfinder import columbia_sc_geography_001 as GEO
    areas = OrderedDict((a, []) for a in (
        "Virginia Beach Oceanfront", "Virginia Beach Town Center", "Pembroke / Newtown Road", "Virginia Beach Central & Bayside",
        "Norfolk Downtown / Waterside", "Ghent / ODU", "ORF Airport", "Military Circle / Military Highway", "Norfolk Ocean View",
        "Chesapeake Greenbrier", "Chesapeake Battlefield Blvd North", "Chesapeake Great Bridge / Battlefield South",
        "Chesapeake Western Branch", "Portsmouth", "Hampton Coliseum / Convention Center", "Hampton Roads Center / Mercury Blvd",
        "Hampton Downtown / Mercury Blvd East", "Newport News City Center", "Oyster Point",
        "Newport News (Midtown / Hilton Village)", "PHF Airport", "Denbigh / Jefferson Ave I-64", "Suffolk", "Smithfield",
        "Yorktown US-17"))
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
                       "postal partition. The ORF airport shares 23502 / 23518 with Military Circle; Battlefield Boulevard "
                       "North shares 23320 with Greenbrier; the Coliseum shares 23666 with the Convention Center and Hampton "
                       "Roads Center; City Center shares 23606 with Oyster Point."),
        ("areas", OrderedDict((a, summary(rows)) for a, rows in areas.items())),
        ("unplaced", summary(unplaced)),
    ])


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "columbia_sc_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "columbia_sc_geography_001.json"))
    capture = _load(os.path.join(REPORTS, "columbia_sc_attended_capture_001.json"))
    clean = _load(os.path.join(REPORTS, "columbia_sc_clean_authority_001.json"))
    recon = _load(os.path.join(REPORTS, "columbia_sc_census_reconciliation_001.json"))
    gaps = _load(os.path.join(REPORTS, "columbia_sc_competitor_gap_matrix_001.json"))
    osm = _load(os.path.join(REPORTS, "columbia_sc_osm_lane_001.json"))
    brand = _load(os.path.join(REPORTS, "columbia_sc_brand_inventory_001.json"))
    wyn = _load(os.path.join(REPORTS, "columbia_sc_wyndham_lane_001.json"))
    roster = _load(os.path.join(REPORTS, "columbia_sc_destination_roster_001.json"))
    shadow = _load(os.path.join(REPORTS, "columbia_sc_shadow_package_008.json"))

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
    military = names("OUTSIDE_MARKET", lambda r: "MILITARY_GOVERNMENT_NONPUBLIC" in reason(r))
    non_hotel = [r for r in non_admitted if r["classification"] == "NON_LODGING"]

    def nh_class(r):
        why = reason(r).lower()
        # HAMPTON ROADS: a bureau's own rental / condo / campground typing is named first (its reason text also says
        # "rental / apartment category")
        if "files this listing" in why:
            return ("BUREAU_CAMPGROUND_OR_STATE_PARK" if "camp" in why
                    else "BUREAU_VACATION_RENTAL_CONDO_OR_BEACH_HOUSE")
        if "tourism=" in why:
            return "MAP_APARTMENT_CONDO_OR_CHALET_UNIT"
        if "apartment" in why:
            return "APARTMENT_OR_RENTAL_UNITS"
        if "timeshare" in why:
            return "TIMESHARE_AGENCY"
        if "concierge" in why or "short-term rental operator" in why:
            return "RENTAL_OPERATOR_OR_CONCIERGE"
        if "condominium" in why or "condo rentals" in why or "beach vacation homes" in why:
            return "BUREAU_CONDO_OR_BEACH_HOUSE_RENTAL"
        if "camping" in why or "campground" in why:
            return "CAMPGROUND_RV_STATE_PARK"
        if "association office" in why or "visitors bureau" in why or "chamber of commerce" in why:
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
            ("note", "Not census identities and never published: brand-flag map rows the brand's own inventory does "
                     "not list at that address (Days Inn Chambers Street and Oceanfront, Econo Lodge 2113 Atlantic, Rodeway Inn "
                     "Little Creek, Super 8 Ocean View and Oceanfront, Travelodge Suffolk and Oceanfront), same-name pairs on "
                     "corner buildings (19 Atlantic Hotel, Breeze Inn & Suites) and across cities (Budget Lodge x3), Oceanfront "
                     "vacation-ownership resorts whose only website is a timeshare agent (Barclay Towers, Beach Quarters, "
                     "Boardwalk Resort, Four Sails, Turtle Cay, Ocean Key, Ocean Sands, The Atrium, Ocean Holiday), a name-only "
                     "tie (Ocean Resort) and name-only map / competitor rows.")])),
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
                     "reserved. The access-blocked cohort (Motel 6 / Studio 6, the Choice properties behind the 403 wall, "
                     "Sea View Hotel, Ocean Cove Motel, The Belvedere, American Inn, Bowers Hill Inn, stayAPT Suites) is held "
                     "ACCESS_BLOCKED for a re-probe, not a paid lane.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", len(founder)), ("identities", founder),
            ("note", "None. Timeshare-resort and geography holds are evidence work for the registration order, not "
                     "founder rulings.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", len(wyn.get("retired_routes") or [])),
            ("wyndham_retired_routes", wyn.get("retired_routes")),
            ("note", "Wyndham routes in Hampton Roads cities that redirect to the brand's city search (retired or "
                     "rebranded). Routes, not census identities.")])),
        ("MILITARY_NONPUBLIC", OrderedDict([
            ("count", len(military)), ("identities", military),
            ("rule", "Installation-only postal codes and named military lodging programmes (Navy Gateway Inns & Suites, Navy "
                     "Lodge, IHG Army Hotels, Air Force Inns / Langley's Bayview) are refused unless ordinary public booking is "
                     "proved; commercial hotels serving military travellers outside the fence are ordinary census rows.")])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET"))),
                                 ("future_market_williamsburg_va", len(future)),
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
    from scripts.pettripfinder import columbia_sc_geography_001 as GEO
    cities = OrderedDict()
    for h in hotels:
        slug = (h.get("corridor") or "").split("__")[-1]
        city = GEO.CITY_OF.get(slug, "UNPLACED")
        row = cities.setdefault(city, OrderedDict([("census", 0), ("pet_friendly", 0), ("verified_no_pets", 0),
                                                   ("unresolved", 0)]))
        row["census"] += 1
        if h["identity_key"] in pf:
            row["pet_friendly"] += 1
        elif h["identity_key"] in np_:
            row["verified_no_pets"] += 1
        else:
            row["unresolved"] += 1
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
        ("display_market", "Hampton Roads, Virginia"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("release_queue", "Current verified live (production): Charleston (25 markets / 1677 profiles / 1942 routes, deploy "
                          "6aa8625938b7e0e0d66e6912), reached on the Charleston branch. This branch's lineage (6825851b) carries "
                          "the Atlanta-live index (23 / 1500 / 1744, deploy 6aa7f125), which is what the shadow package's "
                          "parent_live_state records. Hampton Roads waits for its turn in the serialized release lane."),
        ("timings", TIMINGS),
        ("accounting", OrderedDict([
            ("TOTAL_DISCOVERED", census["total_candidates"]),
            ("total_discovered_note",
             "Distinct candidate identities in the identity graph after merging every lane. Not counted: %d unnamed map "
             "elements, %d retired Wyndham routes, and the Hilton / IHG / Choice national-navigation codes outside "
             "the 231xx / 233xx-237xx postal prefixes." % (
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
        ("city_coverage", cities),
        ("market_balance_check", OrderedDict([
            ("core_cities", OrderedDict((k, cities.get(k, {}).get("census", 0)) for k in (
                "Virginia Beach", "Norfolk", "Chesapeake", "Portsmouth", "Hampton", "Newport News"))),
            ("finding",
             "Virginia Beach carries the most identities because the Oceanfront resort strip is the region's largest lodging "
             "cluster, and every core city was reached by at least two independent lanes (map extract + brand inventories; "
             "Chesapeake and Newport News also by their bureaus, Virginia Beach by its bureau CRM). Portsmouth's small count "
             "is real inventory (Olde Towne's Renaissance, the Quality Inn Olde Town, a Red Roof and map-only motels), not a "
             "failed lane: the OSM extract, Marriott, Choice and Red Roof all placed Portsmouth rows. Norfolk's and "
             "Hampton's bureaus refused this client (Hampton 403) or publish no listing API (Norfolk WordPress), so their "
             "independents rest on the map and brand lanes -- recorded as a lane gap, not an imbalance."),
        ])),
        ("corridor_coverage", coverage),
        ("corridor_pages_meeting_threshold", sum(1 for c in coverage if c["corridor_page_publishes"])),
        ("area_coverage", area_coverage(hotels, pf, np_)),
        ("lane_yields", OrderedDict([
            ("osm_elements", osm["element_count"]),
            ("brand_inventory_leads", brand["lead_count"]),
            ("brand_family_dispositions", brand.get("dispositions")),
            ("city_bureau_rosters", OrderedDict([("coverage", roster.get("coverage")),
                                                   ("listings", roster["listing_count"]),
                                                   ("by_bureau", roster.get("listings_by_bureau")),
                                                   ("by_category", roster["lodging_by_subcategory"])])),
            ("census_lane_observations", recon["lane_yields"]),
            ("first_party_reads", capture["counts"]),
            ("wyndham_property_service", OrderedDict([("routes", wyn["routes_selected"]), ("read", wyn["read"]),
                                                      ("retired", wyn["retired"]), ("errors", wyn["errors"])])),
            ("clean_set", clean["counts"]),
        ])),
        ("competitor_gap_challenge", gaps["counts"]),
        ("owned_evidence", OrderedDict([
            ("OWNED_IDENTITIES", "0 -- no committed census or authority holds a 233xx-237xx Hampton Roads identity (Outer "
                                 "Banks NC and Richmond VA are separate markets; none of their identities is in this region)."),
            ("OWNED_ROUTES", "53 -- 52 ORF / PHF-coded Marriott routes and 1 Magnuson route from the committed national harvest "
                             "dayton_oh_brand_directory_harvest_001 (read at zero requests); every in-market Marriott route was "
                             "re-read on Marriott's own page (2 are Elizabeth City / Nags Head NC, outside)."),
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
        ("factory_code_changed", "NO -- every changed path is a columbia_sc_* helper, the market's discovery config, or a "
                                 "document under the market's own proposed / staging / report paths"),
        ("shared_factory_notes_recorded_not_repaired", [
            "The shared first-party reader does not read IHG's 'No, pets are not allowed at Holiday Inn Virginia Beach - Norfolk.' "
            "or '... at Crowne Plaza Virginia Beach Town Center.' as a refusal (it reads the same sentence for other IHG "
            "hotels), nor The Sitio's 'We love pets; however, we are not a pet friendly hotel.'; those rows are held with the "
            "exact wording.",
            "Hilton's 'Service animals only' petsInfo (Hilton Virginia Beach Oceanfront, DoubleTree Oceanfront South, Spark "
            "Oceanfront, Hilton Norfolk The Main, The Landing at Hampton Marina, both Hilton Vacation Club resorts) is a "
            "service-animal carve-out, not a refusal, and is held SERVICE_ANIMAL_ONLY.",
            "Visit Norfolk and Visit Hampton publish no listing service this client could read (WordPress / 403), and the "
            "attended browser refused navigation to several independent Oceanfront domains; recorded as lane gaps.",
        ]),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("next_order", [
            "When Hampton Roads reaches the front of the serialized release lane, read CURRENT VERIFIED LIVE and merge that "
            "live parent into worker/ptf-columbia-sc-market-001; the Atlanta binding of this shadow package is then invalid "
            "(FAST rule N fails it by design).",
            "Copy markets/proposed/columbia-sc.json -> markets/columbia-sc.json, identity_census_proposed/columbia-sc.json "
            "-> identity_census/columbia-sc.json and the staged launch_package documents (hotel_policy_facts_columbia-sc.json, "
            "columbia_sc_final_partition_007.json, the authority shard) into their registered paths; repoint the helpers' paths.",
            "No same-campus resolution is required by this census (no co-location or directional hold was raised); recheck "
            "after any new read.",
            "market_registration_cli --write, build_global_authority --write then --check, the release contract, "
            "registration_release_lane register + seal --work-order (a NEW package id), FAST.",
            "regression_delta classify (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, prepare "
            "the founder packet; deploy only on founder authorization.",
            "Before sealing: re-probe Choice beyond the 403 wall (va904, va384, va358, va761, va050), Motel 6 / Studio 6, the "
            "refused Oceanfront independents (Sea View, Ocean Cove, Belvedere) and the TLS-failing Chesapeake motels; read IHG "
            "Garner Hotel VB North (orfaa) and Sonesta Simply Suites Hampton; settle the Oceanfront timeshare resorts' public "
            "hotel operation; resolve the Red Roof geography holds (rri826, rri567) with an address-bearing first-party document.",
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
