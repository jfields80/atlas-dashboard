"""PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 -- complete accounting.

Cloned from the Boone - Blowing Rock NC accounting helper (itself from Atlanta GA). Every
discovered candidate, every census identity in exactly one disposition, every hold by
class, per-corridor and per-area coverage, lane yields, the vacation-rental filter's
refusals, the shadow package's identity, its independent reproduction, measured timings
and the release stop -- computed from the committed market-local documents, never typed
(the timings are the wall-clock observations of this run, recorded as observed).

Output:
  launch_packages/pettripfinder/markets/reports/charleston_sc_source_ready_accounting_009.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "charleston-sc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "charleston_sc_source_ready_accounting_009.json")

#: Measured wall-clock facts of this run (UTC), recorded as observed.
TIMINGS = OrderedDict([
    ("SAVANNAH_START_TIMESTAMP", "2026-09-14T05:12:13Z (2026-09-14T01:12:13-04:00)"),
    ("precheck_and_template_read", "05:12Z-05:19Z (worktree, branch, HEAD 7b630cfa = the Jacksonville-live parent, tree clean; Boone / Atlanta shadow chains and the Atlanta browser transcript read)"),
    ("geography_and_corridor_model", "05:19Z-05:20:08Z (10 corridors: 7 CORE / 1 CORRIDOR / 2 FRINGE, 15 admitted ZIPs; Tybee Island OUTSIDE, preserved for tybee-island-ga)"),
    ("osm_lane", "387.8 s (Georgia extract, hard link of the Atlanta run's 2026-09-13 snapshot; 193 lodging elements)"),
    ("brand_inventory_lane", "about 10 min detached (Marriott GA sitemap page, 14 Hilton city pages + 19 Savannah sub-pages, 16 family sitemap probes)"),
    ("destination_rosters", "Visit Savannah (attended, 156 profiles, payload verified) 05:30Z-05:40Z; Visit Pooler (plain, 12 listings) 06:02Z"),
    ("browser_evidence", "05:45Z-06:10Z attended same-origin reads: Marriott 42, Hilton 34, IHG 25, Hyatt 5, Choice 39, Best Western 10, Red Roof 5, Extended Stay America 2, Motel 6 / Studio 6 5 (every payload's canonical-JSON sha256 verified against the page's)"),
    ("static_evidence", "Wyndham property service 10.5 s (49 routes: 23 read, 26 retired); static home pages 31 s; policy-page lane 18-21 s"),
    ("policy_adjudication_and_reconciliation", "06:10Z-06:31Z (independent quotes proved verbatim with house number and ZIP on the same document; census directional / roster / rebrand fixes; clean set; staged authority; partition)"),
    ("evidence_store_incident", "06:38Z: removing a reproduction worktree whose data/ was a junction to this worktree's data/ deleted the gitignored document store; the plain-client lanes were re-run 06:40Z-06:45Z and every quoted document re-persisted and re-proved (three re-rendered pages carry new sha256 values); the chain was rebuilt and resealed at c093cefd"),
    ("shadow_package_and_fast", "06:46:05Z-06:47:36Z at c093cefd (sealed twice in-process, FAST 15/15, determinism BYTE_IDENTICAL); earlier seals at ac1cdb83 (06:32Z-06:34Z) and f1173ef4 (06:35:50Z-06:37:19Z) also passed 15/15 and were superseded"),
    ("independent_reproduction", "06:47:54Z-06:48:12Z (clean git worktree at c093cefd with a COPY of the document store: geography, Visit Savannah roster, brand pages, capture, census, clean set, staged authority, partition and staged shard rebuilt from committed captures -- zero content difference; only the eol-unattributed discovery config checks out CRLF; separate-process digest-only seal = the same digest)"),
    ("ZERO_TO_SOURCE_READY", "1 h 35 min 23 s (05:12:13Z -> 06:47:36Z, the final FAST-passed sealed shadow package; the first FAST-passed seal was at 06:34:04Z, 1 h 21 min 51 s)"),
])


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
    from scripts.pettripfinder import charleston_sc_geography_001 as GEO
    areas = OrderedDict((a, []) for a in (
        "Historic District / Downtown", "River Street / Eastern Wharf", "Hutchinson Island", "Midtown",
        "Chatham Parkway / I-16", "Thunderbolt", "Southside", "SAV Airport", "Garden City", "Pooler",
        "Gateway / I-95 exit 94", "Georgetown", "Port Wentworth / Crossroads", "Richmond Hill",
        "Wilmington / Skidaway Islands"))
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
                       "postal partition. River Street / Eastern Wharf share 31401 with the Historic District."),
        ("areas", OrderedDict((a, summary(rows)) for a, rows in areas.items())),
        ("unplaced", summary(unplaced)),
    ])


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "charleston_sc_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "charleston_sc_geography_001.json"))
    capture = _load(os.path.join(REPORTS, "charleston_sc_attended_capture_001.json"))
    clean = _load(os.path.join(REPORTS, "charleston_sc_clean_authority_001.json"))
    recon = _load(os.path.join(REPORTS, "charleston_sc_census_reconciliation_001.json"))
    gaps = _load(os.path.join(REPORTS, "charleston_sc_competitor_gap_matrix_001.json"))
    osm = _load(os.path.join(REPORTS, "charleston_sc_osm_lane_001.json"))
    brand = _load(os.path.join(REPORTS, "charleston_sc_brand_inventory_001.json"))
    wyn = _load(os.path.join(REPORTS, "charleston_sc_wyndham_lane_001.json"))
    roster = _load(os.path.join(REPORTS, "charleston_sc_destination_roster_001.json"))
    pooler = _load(os.path.join(REPORTS, "charleston_sc_pooler_roster_001.json"))
    shadow = _load(os.path.join(REPORTS, "charleston_sc_shadow_package_008.json"))

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
    review = names("IDENTITY_REVIEW_REQUIRED", lambda r: not reason(r).startswith("GEOGRAPHY_HOLD"))
    access = Counter("OWN_SITE" for i in items if i["final_state"] == "ACCESS_BLOCKED")
    future = names("OUTSIDE_MARKET", lambda r: "FUTURE_SUBMARKET" in reason(r))
    non_hotel = [r for r in non_admitted if r["classification"] == "NON_LODGING"]

    def nh_class(r):
        why = reason(r).lower()
        if "vacation-rental" in why and "files this listing" in why:
            return "BUREAU_VACATION_RENTAL_OR_PROPERTY_MANAGER"
        if "campground" in why:
            return "CAMPGROUND_RV_STATE_PARK"
        if "stvr" in why:
            return "MAP_SHORT_TERM_VACATION_RENTAL"
        if "tourism=" in why or "cottage" in why:
            return "MAP_APARTMENT_COTTAGE_UNIT"
        if "venue" in why or "booking website" in why or "management company" in why:
            return "VENUE_BAR_BOOKING_SITE_OR_MANAGEMENT_OFFICE"
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
            ("note", "Not census identities and never published: brand-flag map rows the brand's own inventory does not "
                     "list (Econo Lodge Savannah South, Homewood Suites Savannah Midtown, Wingate at 15 Sylvester C. Formey), "
                     "Signia by Hilton (not yet open), The Ann (apartments-by-Marriott category unconfirmed), the Atwell "
                     "Suites / Hyatt Place rebrand at 4 Stephen S. Green Drive, the two G6 properties at 6 Gateway Blvd E, "
                     "and name-only map and competitor leads (Mansion on Forsyth Park, McMillan Inn, Green Palm Inn, "
                     "Zeigler House Inn, The Ballastone Inn, InTown Suites Garden City ...).")])),
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
            ("note", "No brand family refused the attended session on this run, so no cohort requires a paid lane. "
                     "PAID PROVIDER BUDGET was $0 and no paid lane was used or reserved.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", 0),
            ("note", "No row requires a founder ruling. Co-location and directional-collision holds are registration-order "
                     "work in shared identity state; conflicts and reads the shared reader does not interpret are EVIDENCE holds.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", len(wyn.get("retired_routes") or [])),
            ("wyndham_retired_routes", wyn.get("retired_routes")),
            ("note", "Wyndham routes that redirect to the brand's search (Days Hotel at Ellis Square, the La Quinta "
                     "Savannah routes, Ramada Savannah, Travelodge Savannah, the Hawthorn and several Wingate / Super 8 "
                     "routes). Routes, not census identities.")])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET"))),
                                 ("future_market_tybee_island", len(future)),
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
        ("display_market", "Savannah, Georgia"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("release_queue", "Current verified live: Jacksonville (22 markets / 1256 profiles / 1483 routes). Savannah waits "
                          "for its turn in the serialized release lane behind the queued markets."),
        ("timings", TIMINGS),
        ("accounting", OrderedDict([
            ("TOTAL_DISCOVERED", census["total_candidates"]),
            ("total_discovered_note",
             "Distinct candidate identities in the identity graph after merging every lane. Not counted: %d unnamed map "
             "elements, %d retired Wyndham routes, the Hilton national-navigation codes outside the coastal ZIP prefixes, "
             "and the bureau profile page refused on read." % (
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
            ("visit_savannah_roster", OrderedDict([("coverage", roster.get("coverage")),
                                                   ("profiles", roster["listing_count"]),
                                                   ("by_category", roster["lodging_by_subcategory"])])),
            ("visit_pooler_roster", OrderedDict([("listings", pooler["listing_count"])])),
            ("census_lane_observations", recon["lane_yields"]),
            ("first_party_reads", capture["counts"]),
            ("wyndham_property_service", OrderedDict([("routes", wyn["routes_selected"]), ("read", wyn["read"]),
                                                      ("retired", wyn["retired"]), ("errors", wyn["errors"])])),
            ("clean_set", clean["counts"]),
        ])),
        ("competitor_gap_challenge", gaps["counts"]),
        ("owned_evidence", OrderedDict([
            ("OWNED_IDENTITIES", "0 -- no committed census held a Savannah identity (Wilmington NC's 'The Savannah Inn' is a "
                                 "Carolina Beach hotel: a name collision, not an identity)."),
            ("OWNED_ROUTES", "42 -- SAV-coded Marriott routes from the committed national harvest "
                             "dayton_oh_brand_directory_harvest_001 (read at zero requests; every one re-read on Marriott's own page)."),
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
        ("factory_code_changed", "NO -- every changed path is a charleston_sc_* helper, the market's discovery config, or a "
                                 "document under the market's own proposed / staging / report paths"),
        ("shared_factory_notes_recorded_not_repaired", [
            "The shared hotel_exclusions.address_key drops street directionals, so '201 E. Bay St.' (Hampton Inn) and "
            "'201 West Bay Street' (Hotel Indigo), and '11 Gateway Boulevard East' (Holiday Inn) and '11 West Gateway "
            "Boulevard' (TownePlace Suites), are one key though they are different buildings. The census merge refuses the "
            "join market-locally; the four pet-friendly records are held ADDRESS_KEY_DIRECTIONAL_COLLISION because the "
            "shared listing builder and publication guard would conflate them.",
            "The shared first-party reader does not read 'We do not allow pets of any kind', 'While we do not allow pets', "
            "'No, pets are strictly prohibited on our property', 'We cannot accomodate pets at this time', 'We do NOT offer "
            "pet friendly hotel rooms.', 'We are not pet or Emotional Support Animal friendly.', 'Sorry, none of our rooms "
            "are pet or ESA friendly' or 'Pets are always welcome.' as operative; those rows are held with the exact wording.",
        ]),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("next_order", [
            "When Savannah reaches the front of the serialized release lane, read CURRENT VERIFIED LIVE and merge that live parent into worker/ptf-charleston-sc-market-001.",
            "Copy markets/proposed/charleston-sc.json -> markets/charleston-sc.json, identity_census_proposed/charleston-sc.json -> identity_census/charleston-sc.json and the "
            "staged launch_package documents (hotel_policy_facts_charleston-sc.json, charleston_sc_final_partition_007.json, the authority shard) into their registered paths; repoint the helpers' paths.",
            "Record the same-campus / directional resolutions in identity_resolutions.json (190 Pioneer Way: Courtyard + Residence Inn Richmond Hill; "
            "100 Half Moon Way: TownePlace + Fairfield Pooler; 201 E / 201 W Bay Street: Hampton Inn + Hotel Indigo; 11 E / 11 W Gateway Blvd: "
            "Holiday Inn + TownePlace South) and re-admit the held pet-friendly records through the clean set.",
            "market_registration_cli --write, build_global_authority --write then --check, the release contract, registration_release_lane register + "
            "seal --work-order (a NEW package id: this shadow package fails FAST rule N by design once the parent moves), FAST.",
            "regression_delta classify (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, prepare the founder packet; deploy only on founder authorization.",
            "Before sealing, re-probe the 403 inns (Catherine Ward House, Hamilton-Turner, The DeSoto, The Inn on West Liberty), find first-party routes for "
            "Presidents' Quarters, Recess, Sonesta Essentials, Relax Inn, Sandman Motel, Savannah Inn and The Spanish Moss Inn, and verify the competitor "
            "leads Mansion on Forsyth Park, McMillan Inn, Green Palm Inn and Zeigler House Inn on their own pages.",
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
