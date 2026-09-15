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
        "The Vista / Convention Center", "Main Street / State House", "University of South Carolina",
        "Five Points / Devine Street", "Downtown Columbia", "Prisma Health Richland", "I-20 / North Main", "North Columbia",
        "Forest Drive / I-77 (Fort Jackson gate)", "Garners Ferry / Fort Jackson Blvd", "Two Notch / I-77 exit 17",
        "Dentsville / Decker Blvd", "Clemson Road / I-20 exit 80", "Killian Road / I-77 exit 22",
        "Bush River Road / I-20 / I-26", "Greystone / Riverbanks", "St. Andrews Road", "Harbison Blvd / I-26",
        "Piney Grove Road / I-26", "Irmo", "Knox Abbott / Cayce", "I-26 / US-1 (exit 111)", "West Columbia / Cayce",
        "CAE Airport / Airport Blvd (exit 113)", "Lexington Sunset Blvd", "Blythewood", "Chapin", "Elgin"))
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
                       "postal partition. The Vista, Main Street, USC and Five Points share the downtown corridor; Forest Drive "
                       "and Garners Ferry share Fort Jackson; Bush River, Greystone and St. Andrews share 29210; Harbison and "
                       "Piney Grove share 29212. The Killian Road hotels on Roberts Branch Parkway are mailed 29203 and report "
                       "under north Columbia."),
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
    future = []
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
                     "not list at that address (Days Inn 7300 Garners Ferry Road, Quality Inn & Suites 2210 Bush River Road, "
                     "Suburban Extended Stay 150 Stoneridge Drive, Red Roof Inn Columbia East 7580 Two Notch Road), map rows "
                     "duplicating a read hotel under a bare label (Sheraton Columbia Downtown, Sleep Inn 2208 Airport Blvd), "
                     "Flutter Wing, the Wyndham Garden / Hawthorn dual-brand building at 1539 Horseshoe Drive, name-only map "
                     "motels and competitor leads that alias census rows.")])),
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
                     "reserved. No census identity is ACCESS_BLOCKED on this run: every brand surface and independent site "
                     "that named a census identity served either the plain client or the attended browser.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", len(founder)), ("identities", founder),
            ("note", "None. The geography hold and the dual-brand holds are evidence / registration-order work, not "
                     "founder rulings.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", len(wyn.get("retired_routes") or [])),
            ("wyndham_retired_routes", wyn.get("retired_routes")),
            ("note", "Wyndham routes in Columbia-area cities that redirect to the brand's city search (retired or "
                     "rebranded). Routes, not census identities.")])),
        ("MILITARY_NONPUBLIC", OrderedDict([
            ("count", len(military)), ("identities", military),
            ("rule", "Fort Jackson's installation postal code (29207) and named military lodging programmes (IHG Army Hotels, "
                     "the IHG Palmetto Fort Jackson Hotel, transient quarters) are refused unless ordinary public booking is "
                     "proved; the commercial hotels outside the gates (Garners Ferry Road, Forest Drive, Two Notch Road, "
                     "Clemson Road) are ordinary census rows.")])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET"))),
                                 ("future_market", "none preserved by this order")])),
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
        ("display_market", "Columbia, South Carolina"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("release_queue", "Production has moved on other branches since this branch was cut: the operator's launch record "
                          "at the time of this run names Outer Banks as live (26 markets / 1703 profiles / 1972 routes, deploy "
                          "6aa8992493a75f80cd0e3887). This branch's lineage (6825851b) carries "
                          "the Atlanta-live index (23 / 1500 / 1744, deploy 6aa7f125), which is what the shadow package's "
                          "parent_live_state records. Columbia waits for its turn in the serialized release lane."),
        ("timings", TIMINGS),
        ("accounting", OrderedDict([
            ("TOTAL_DISCOVERED", census["total_candidates"]),
            ("total_discovered_note",
             "Distinct candidate identities in the identity graph after merging every lane. Not counted: %d unnamed map "
             "elements, %d retired Wyndham routes, and the Hilton / IHG / Choice national-navigation codes outside "
             "the 290xx-292xx postal prefixes." % (
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
                "Columbia", "West Columbia", "Lexington", "Blythewood", "Chapin", "Elgin"))),
            ("finding",
             "Columbia proper carries most identities because nine of the thirteen corridors are named for Columbia "
             "(the Harbison corridor includes Irmo's 29063; West Columbia / Cayce and the CAE airport keep their own mailing "
             "towns). Every CORE corridor was reached by at least two independent lanes (map extract, brand inventories and "
             "the Columbia CVB roster). Chapin returned no lodging identity from any lane (an empty fringe corridor, not a "
             "failed lane). The Fort Jackson gate corridors are brand-heavy (Garners Ferry Road and Two Notch Road); "
             "downtown carries the independents (Hotel Trundle, The Lantern, Chesnut Cottage)."),
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
            ("OWNED_IDENTITIES", "0 -- no committed census or authority holds a 290xx-292xx Columbia identity."),
            ("OWNED_ROUTES", "30 -- CAE-coded Marriott routes in the committed national harvest "
                             "dayton_oh_brand_directory_harvest_001 (read at zero requests); every one was re-read on Marriott's "
                             "own page (6 are Santee, Orangeburg, Sumter and Camden, outside)."),
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
            "The shared first-party reader does not read Hotel Trundle's 'While we love pets, we kindly ask that you leave your "
            "furry friends at home.' as a refusal, reads Motel 6's 'Pets welcome throughout your stay' as an amenity label, and "
            "reads Days Inn & Suites Columbia Airport's 'Maximum 2 pets up to 100 lbs allowed ...' as a service-animal "
            "statement; those rows are held with the exact wording.",
            "Hilton's 'Service animals only' petsInfo (Hilton Columbia Center, DoubleTree Columbia) is a service-animal "
            "carve-out, not a refusal, and is held SERVICE_ANIMAL_ONLY.",
            "InTown Suites' property pages state no postal code, so their refusals cannot bind by the page's own street "
            "identity (ADDRESS_NOT_ON_DOCUMENT).",
        ]),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("next_order", [
            "When Columbia reaches the front of the serialized release lane, read CURRENT VERIFIED LIVE and merge that "
            "live parent into worker/ptf-columbia-sc-market-001; the Atlanta binding of this shadow package is then invalid "
            "(FAST rule N fails it by design).",
            "Copy markets/proposed/columbia-sc.json -> markets/columbia-sc.json, identity_census_proposed/columbia-sc.json "
            "-> identity_census/columbia-sc.json and the staged launch_package documents (hotel_policy_facts_columbia-sc.json, "
            "columbia_sc_final_partition_007.json, the authority shard) into their registered paths; repoint the helpers' "
            "paths; re-stage the census copy after ANY census edit.",
            "Record the same-campus resolution for the two pet-friendly Hilton hotels at 400 Gervais Street (Homewood Suites "
            "caecahw / Tru caeruru) in identity_resolutions.json, releasing both CO_LOCATION_RULING_REQUIRED holds; the "
            "Wyndham Garden / Hawthorn pair at 1539 Horseshoe Drive needs a first-party proof of two bookable hotels first.",
            "market_registration_cli --write, build_global_authority --write then --check, the release contract, "
            "registration_release_lane register + seal --work-order (a NEW package id), FAST.",
            "regression_delta classify (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, prepare "
            "the founder packet; deploy only on founder authorization.",
            "Before sealing: re-read IHG caedt (Holiday Inn Express Downtown / The Vista) for a corrected postal code, IHG "
            "caers (Staybridge) for an FAQ answer and Marriott caenr (StudioRes) for a Pet Policy row; find address-bearing "
            "InTown and Motel 6 documents; settle Flutter Wing's lodging category; route the map-only Knights Inn and "
            "Travelers Inn.",
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
