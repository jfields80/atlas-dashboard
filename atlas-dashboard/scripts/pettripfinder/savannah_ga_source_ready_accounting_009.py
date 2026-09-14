"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- complete accounting.

Cloned from the Atlanta GA accounting helper. Every discovered candidate, every
census identity in exactly one disposition, every hold by class, per-corridor and
per-town coverage, lane yields, the vacation-rental filter's refusals, the shadow
package's identity, its independent reproduction, measured timings and the release
stop -- computed from the committed market-local documents, never typed (the
timings are the wall-clock observations of this run, recorded as observed).

Output:
  launch_packages/pettripfinder/markets/reports/savannah_ga_source_ready_accounting_009.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "savannah-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "savannah_ga_source_ready_accounting_009.json")

#: Measured wall-clock facts of this run (UTC), recorded as observed.
TIMINGS = OrderedDict([
    ("BOONE_BLOWING_ROCK_START_TIMESTAMP", "2026-09-14T00:29:27Z (2026-09-13T20:29:27-04:00)"),
    ("precheck_and_template_read", "00:29Z-00:36Z (worktree, branch, HEAD e312caa6 = the Asheville-live parent, tree clean; Outer Banks / Atlanta / Jacksonville shadow chains read)"),
    ("geography_and_corridor_model", "by 00:41Z (5 corridors: 2 CORE / 2 CORRIDOR / 1 FRINGE, 9 admitted ZIPs; Banner Elk / Sugar / Beech / Seven Devils and Avery County OUTSIDE, preserved for banner-elk-sugar-beech-nc)"),
    ("osm_lane", "404.3 s (North Carolina extract, hard link of the 2026-09-10 snapshot; 301 hotel / motel / guest_house / chalet / apartment elements)"),
    ("brand_inventory_lane", "97 free requests (Marriott NC sitemap page, 18 Hilton city pages, Wyndham sitemap walk, family probes)"),
    ("destination_roster", "Explore Boone (Boone TDA) listing service, 8 'Hotels & Cabins' sub-categories, 9 requests at Crawl-delay 2; High Country Host regional visitor-center roster read once"),
    ("attended_browser_evidence", "Hilton 2, Marriott 5, IHG 4 (same-origin, payload digests verified); Choice closed with bot-challenge shells; Best Western route not reached"),
    ("static_first_party_lanes", "Wyndham property service 8.4 s (6 routes: 1 read, 5 retired); static home pages 31 s (22 targets); policy-page lane 17.3 s (40 sites, 114 documents)"),
    ("source_ready_inputs_committed", "2026-09-14T00:57:43Z (7adbafd1)"),
    ("shadow_package_sealed_and_fast", "00:57:52Z-00:58:40Z (sealed twice in-process, FAST 15/15)"),
    ("independent_reproduction", "00:59:00Z-01:01Z (clean git worktree at 7adbafd1: separate-process digest-only seal = same digest; geography, brand pages, capture, census, clean set, staged authority, partition and staged shard rebuilt from committed captures -- zero content difference, the discovery config differs only by the worktree's CRLF checkout of an eol-unattributed file; same digest a third time)"),
    ("ZERO_TO_SOURCE_READY", "29 min 13 s (00:29:27Z -> 00:58:40Z, FAST-passed sealed shadow package)"),
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


def town_coverage(hotels, pf, np_):
    """The order's named towns: the property's OWN stated municipality where it names one,
    else the nearest-anchor overlay on its pin. Reporting only -- Kitty Hawk, Southern
    Shores and Duck share one postal code and one corridor."""
    from scripts.pettripfinder import savannah_ga_geography_001 as GEO
    towns = OrderedDict((a, []) for a in (
        "Boone Downtown / App State", "Boone US-321", "Boone US-421", "Boone NC-105 / Foscoe",
        "Blowing Rock village", "Blue Ridge Parkway / resort corridor", "Valle Crucis / Vilas", "Deep Gap",
        "Sugar Grove / Zionville / Todd"))
    unplaced = []
    for h in hotels:
        state = ("PUBLISHED_PET_FRIENDLY" if h["identity_key"] in pf
                 else "VERIFIED_NO_PETS" if h["identity_key"] in np_ else "UNRESOLVED")
        row = OrderedDict([("canonical_name", h["canonical_name"]), ("state", state), ("street", h.get("street"))])
        p = _pin(h) or (None, None)
        area = GEO.route_overlay((h.get("corridor") or "").split("__")[-1], h.get("street"), p[0], p[1])
        basis = "own stated street, then pin (geography route_overlay)"
        row["basis"] = basis
        (towns[area] if area in towns else unplaced).append(row)

    def summary(rows):
        return OrderedDict([("census", len(rows)),
                            ("pet_friendly", sum(1 for r in rows if r["state"] == "PUBLISHED_PET_FRIENDLY")),
                            ("verified_no_pets", sum(1 for r in rows if r["state"] == "VERIFIED_NO_PETS")),
                            ("unresolved", sum(1 for r in rows if r["state"] == "UNRESOLVED")),
                            ("identities", rows)])
    return OrderedDict([
        ("what_it_is", "Coverage for the order's named towns. Reporting only; membership and corridor come from the "
                       "postal partition. Boone's road corridors all sit in 28607."),
        ("towns", OrderedDict((a, summary(rows)) for a, rows in towns.items())),
        ("unplaced", summary(unplaced)),
    ])


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "savannah_ga_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "savannah_ga_geography_001.json"))
    capture = _load(os.path.join(REPORTS, "savannah_ga_attended_capture_001.json"))
    clean = _load(os.path.join(REPORTS, "savannah_ga_clean_authority_001.json"))
    recon = _load(os.path.join(REPORTS, "savannah_ga_census_reconciliation_001.json"))
    gaps = _load(os.path.join(REPORTS, "savannah_ga_competitor_gap_matrix_001.json"))
    osm = _load(os.path.join(REPORTS, "savannah_ga_osm_lane_001.json"))
    brand = _load(os.path.join(REPORTS, "savannah_ga_brand_inventory_001.json"))
    wyn = _load(os.path.join(REPORTS, "savannah_ga_wyndham_lane_001.json"))
    roster = _load(os.path.join(REPORTS, "savannah_ga_destination_roster_001.json"))
    shadow = _load(os.path.join(REPORTS, "savannah_ga_shadow_package_008.json"))

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
    access_families = Counter()
    for i in items:
        if i["final_state"] == "ACCESS_BLOCKED":
            access_families["BRAND_FAMILY" if "this family gave" in (i.get("next_action") or "") else "OWN_SITE"] += 1
    future = names("OUTSIDE_MARKET", lambda r: "FUTURE_SUBMARKET" in reason(r))
    non_hotel = [r for r in non_admitted if r["classification"] == "NON_LODGING"]

    def nh_class(r):
        why = reason(r).lower()
        subs = {x for o in r.get("evidence") or ()
                for x in (o.get("bureau_all_subcategories") or [o.get("bureau_subcategory")]) if x}
        if "timeshare" in why:
            return "TIMESHARE_VACATION_OWNERSHIP"
        if "Cabin Rental Company" in subs:
            return "CABIN_RENTAL_COMPANY"
        if "RV & Campgrounds" in subs:
            return "CAMPGROUND_RV"
        if "Farm Stays" in subs:
            return "FARM_STAY"
        if "Cabins, Cottages & Condos" in subs:
            return "CABIN_COTTAGE_CONDO_RENTAL"
        if "tourism=" in why or "cottage" in why:
            return "MAP_CABIN_CHALET_CONDO_UNIT"
        return "OTHER_NON_HOTEL"

    holds = OrderedDict([
        ("IDENTITY_HOLDS", OrderedDict([
            ("count", len(review) + len(names("NAME_ONLY_UNRESOLVED")) + len(names("SAME_IDENTITY_REBRAND_SUCCESSOR"))),
            ("identity_review_required", review),
            ("name_only_unresolved", names("NAME_ONLY_UNRESOLVED")),
            ("rebrand_unresolved", names("SAME_IDENTITY_REBRAND_SUCCESSOR")),
            ("note", "Not census identities and never published: lodging-category-unconfirmed rows (Art of Living "
                     "Retreat Center, Willow Valley Resort), map rows with no postal code (Blowing Rock Lodge, Hotel "
                     "Portofino), a name-only lead tied between two Courtyards, and names with no address of their "
                     "own (Chetola, Green Park Inn, Homestead Inn, Best Western Blue Ridge Plaza, Scottish Inns, "
                     "Greenes Motel, Inn at the Ponds, Park Vista Inn).")])),
        ("ROUTING_HOLDS", OrderedDict([("count", states.get("AWAITING_OFFICIAL_URL", 0)),
                                       ("identities", by_state.get("AWAITING_OFFICIAL_URL", []))])),
        ("ACCESS_BLOCKED", OrderedDict([("count", states.get("ACCESS_BLOCKED", 0)),
                                        ("by_cause", dict(access_families)),
                                        ("identities", by_state.get("ACCESS_BLOCKED", []))])),
        ("EVIDENCE_HOLDS", OrderedDict([("count", states.get("AWAITING_POLICY_OBSERVATION", 0)),
                                        ("identities", by_state.get("AWAITING_POLICY_OBSERVATION", [])),
                                        ("rejected_reads_by_class", clean["counts"]["rejected_by_class"])])),
        ("GEOGRAPHY_HOLDS", OrderedDict([("count", len(geo_holds)), ("identities", geo_holds)])),
        ("PAID_HOLDS", OrderedDict([
            ("count", access_families.get("BRAND_FAMILY", 0)),
            ("note", "The ACCESS_BLOCKED identities whose brand family (Choice: Comfort Suites, Quality Inn, Sleep Inn; "
                     "Radisson: Country Inn & Suites) refused this client are the "
                     "paid-lane candidates. Same rows as ACCESS_BLOCKED, not an additional disposition; PAID PROVIDER "
                     "BUDGET was $0 and no paid lane was used or reserved.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", 0),
            ("note", "No row requires a founder ruling. Conflicts, single-suite exceptions and reads the shared reader "
                     "does not interpret are EVIDENCE holds.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", len(wyn.get("retired_routes") or [])),
            ("wyndham_retired_routes", wyn.get("retired_routes")),
            ("note", "Wyndham routes that redirect to the brand's search: Days Inn Blowing Rock (Boone area), Super 8 "
                     "Boone and the legacy La Quinta Boone route (the property trades on its live La Quinta Inn & Suites "
                     "Boone University route), plus Days Inn West Jefferson and Days Inn Lenoir outside. Routes, not "
                     "census identities.")])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET"))),
                                 ("future_submarket_banner_elk_sugar_beech", len(future)),
                                 ("future_submarket_identities", future)])),
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
        ("display_market", "Boone \u2013 Blowing Rock, North Carolina"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("release_queue", "Fayetteville (founder-authorized, host deploy blocked) -> Jacksonville -> Greenville -> "
                          "Atlanta -> Outer Banks -> Boone - Blowing Rock"),
        ("timings", TIMINGS),
        ("accounting", OrderedDict([
            ("TOTAL_DISCOVERED", census["total_candidates"]),
            ("total_discovered_note",
             "Distinct candidate identities in the identity graph after merging every lane. Not counted: %d unnamed map "
             "elements, %d retired Wyndham routes, the Hilton national-navigation codes the city pages carry for other "
             "states, and non-lodging bureau listing pages." % (
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
        ("town_coverage", town_coverage(hotels, pf, np_)),
        ("lane_yields", OrderedDict([
            ("osm_elements", osm["element_count"]),
            ("brand_inventory_leads", brand["lead_count"]),
            ("brand_family_dispositions", brand.get("dispositions")),
            ("destination_roster", OrderedDict([("coverage", roster.get("coverage")),
                                                ("listing_pages_read", roster.get("listing_pages_read")),
                                                ("lodging_listings", roster["listing_count"]),
                                                ("by_subcategory", roster["lodging_by_subcategory"])])),
            ("census_lane_observations", recon["lane_yields"]),
            ("first_party_reads", capture["counts"]),
            ("wyndham_property_service", OrderedDict([("routes", wyn["routes_selected"]), ("read", wyn["read"]),
                                                      ("retired", wyn["retired"]), ("errors", wyn["errors"])])),
            ("clean_set", clean["counts"]),
        ])),
        ("competitor_gap_challenge", gaps["counts"]),
        ("owned_evidence", OrderedDict([
            ("OWNED_IDENTITIES", "0 -- no committed census held any Boone - Blowing Rock identity."),
            ("OWNED_ROUTES", "0 -- the committed national harvest carries no High Country route."),
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
        ("factory_code_changed", "NO -- every changed path is a savannah_ga_* helper, the market's discovery config, or a "
                                 "document under the market's own proposed / staging / report paths"),
        ("shared_factory_notes_recorded_not_repaired", [
            "The shared first-party reader does not read '... is not pet-friendly ...' (The 1850 Hotel, The Windmoor "
            "Hotel, The Blowing Rock Manor), 'All of our rooms are non-smoking and pet-free.' (Hemlock Inn), 'The Village "
            "Inns of Blowing Rock allows dogs at ...' or 'No, our facility does not permit pets' as operative, and reads "
            "Rhode's Motor Lodge's and The Inn at Crestwood's dog policies as FEE_ONLY; those rows are held with the "
            "gate's class, never reworded.",
            "The Windmoor Hotel's and The Blowing Rock Manor's JSON-LD carry The 1850 Hotel's Boone address (a shared "
            "operator template); the census binds each to the street its own page text states.",
        ]),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("next_order", [
            "Wait until Netlify is restored and Fayetteville, Jacksonville, Greenville, Atlanta and Outer Banks are live; read that live parent.",
            "Rebase worker/ptf-savannah-ga-market-001 onto it; copy markets/proposed/savannah-ga.json -> markets/savannah-ga.json, "
            "identity_census_proposed/savannah-ga.json -> identity_census/savannah-ga.json and the staged launch_package documents "
            "(hotel_policy_facts_savannah-ga.json, partition, authority shard) into their registered paths.",
            "market_registration_cli --write, build_global_authority --write then --check, release contract, registration_release_lane "
            "register + seal --work-order (a NEW package id against the new parent; this shadow package's FAST rule N fails by design once the parent moves).",
            "regression_delta classify (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, prepare the founder "
            "packet, deploy only on founder authorization.",
            "Before sealing, re-probe Choice (Comfort Suites, Quality Inn, Sleep Inn), Country Inn & Suites, Best Western "
            "Blue Ridge Plaza, Ridgeway Inn, Homestead Inn and Yonahlossee; find first-party addresses for Chetola and Green Park Inn.",
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
    print("towns", {k: (v["census"], v["pet_friendly"], v["verified_no_pets"], v["unresolved"]) for k, v in doc["town_coverage"]["towns"].items()},
          "unplaced", doc["town_coverage"]["unplaced"]["census"])
    print(doc["package"]["PACKAGE_DIGEST"], a["every_census_identity_has_exactly_one_disposition"], a["every_census_identity_key_unique"])
    print("gap", doc["competitor_gap_challenge"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
