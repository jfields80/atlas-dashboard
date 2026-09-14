"""PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001 -- complete accounting.

Cloned from the Atlanta GA accounting helper. Every discovered candidate, every
census identity in exactly one disposition, every hold by class, per-corridor and
per-town coverage, lane yields, the vacation-rental filter's refusals, the shadow
package's identity, its independent reproduction, measured timings and the release
stop -- computed from the committed market-local documents, never typed (the
timings are the wall-clock observations of this run, recorded as observed).

Output:
  launch_packages/pettripfinder/markets/reports/boone_blowing_rock_nc_source_ready_accounting_009.json
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

WORK_ORDER = "PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "boone-blowing-rock-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "boone_blowing_rock_nc_source_ready_accounting_009.json")

#: Measured wall-clock facts of this run (UTC), recorded as observed.
TIMINGS = OrderedDict([
    ("OUTER_BANKS_START_TIMESTAMP", "2026-09-13T22:22:40Z"),
    ("precheck_and_template_read", "22:22:40Z-22:28Z (worktree, branch, HEAD e312caa6 = the Asheville-live parent, tree clean; Greenville / Atlanta shadow chains read)"),
    ("geography_and_corridor_model", "22:28Z-22:29:06Z (8 corridors: 4 CORE / 2 CORRIDOR / 2 FRINGE, 10 admitted ZIPs; Hatteras Island + Ocracoke OUTSIDE, preserved for hatteras-ocracoke-nc)"),
    ("osm_lane", "417.8 s (North Carolina extract, hard link of the 2026-09-10 snapshot; 220 hotel / motel / guest_house elements)"),
    ("brand_inventory_lane", "100 free requests (Marriott NC sitemap page, 21 Hilton city pages, Wyndham sitemap walk, family probes)"),
    ("attended_browser_evidence", "Hilton 5, Marriott 2, IHG 2 (same-origin, digests verified); Choice closed with bot-challenge shells; Tranquil House Inn 1"),
    ("destination_roster", "Outer Banks Visitors Bureau sitemap + every /listing/ page at the site's Crawl-delay: 2 (lodging slugs first, then the rest)"),
    ("static_first_party_lanes", "Wyndham property service 2.7 s (6 routes: 4 read, 2 retired); static home pages 7.4 s (40 targets); policy-page lane ~50 s (38 sites)"),
    ("source_ready_inputs_committed", "2026-09-13T23:40:12Z (e636dcd5)"),
    ("shadow_package_sealed_and_fast", "23:40:19Z-23:40:53Z (sealed twice in-process, FAST 15/15)"),
    ("independent_reproduction", "23:41:12Z-23:41:52Z (clean git worktree at e636dcd5: separate-process digest-only seal = same digest; geography, capture, census, clean set, partition, staged authority and staged shard rebuilt from committed captures -- zero content difference, the discovery config differs only by the worktree's CRLF checkout of an eol-unattributed file; same digest a third time)"),
    ("ZERO_TO_SOURCE_READY", "1 h 18 min 13 s (22:22:40Z -> 23:40:53Z, FAST-passed sealed shadow package)"),
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
    from scripts.pettripfinder import boone_blowing_rock_nc_geography_001 as GEO
    towns = OrderedDict((a, []) for a, _la, _ln, _r in GEO.COVERAGE_AREAS)
    unplaced = []
    for h in hotels:
        state = ("PUBLISHED_PET_FRIENDLY" if h["identity_key"] in pf
                 else "VERIFIED_NO_PETS" if h["identity_key"] in np_ else "UNRESOLVED")
        row = OrderedDict([("canonical_name", h["canonical_name"]), ("state", state)])
        area = GEO.municipality_area(h.get("city"))
        basis = "own stated municipality"
        if area is None:
            p = _pin(h)
            area = GEO.coverage_area(*p) if p else None
            basis = "nearest anchor on the row's pin"
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
                       "postal partition."),
        ("towns", OrderedDict((a, summary(rows)) for a, rows in towns.items())),
        ("unplaced", summary(unplaced)),
    ])


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "boone_blowing_rock_nc_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_geography_001.json"))
    capture = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_attended_capture_001.json"))
    clean = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_clean_authority_001.json"))
    recon = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_census_reconciliation_001.json"))
    gaps = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_competitor_gap_matrix_001.json"))
    osm = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_osm_lane_001.json"))
    brand = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_brand_inventory_001.json"))
    wyn = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_wyndham_lane_001.json"))
    roster = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_destination_roster_001.json"))
    shadow = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_shadow_package_008.json"))

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
        subs = {o.get("bureau_subcategory") for o in r.get("evidence") or () if o.get("bureau_subcategory")}
        if "timeshare" in why:
            return "TIMESHARE_VACATION_OWNERSHIP"
        if "Condos/Townhouses" in subs or "Condos / Townhouses" in subs:
            return "CONDO_UNITS"
        if "Campgrounds / RV Parks" in subs:
            return "CAMPGROUND_RV"
        if "Cottage Courts" in subs or "cottage collection" in why:
            return "COTTAGE_COLLECTION"
        if "Vacation Rentals" in subs or "vacation rental" in why or "vacation house" in why:
            return "VACATION_RENTAL_HOUSE_OR_AGENCY"
        return "OTHER_NON_HOTEL"

    holds = OrderedDict([
        ("IDENTITY_HOLDS", OrderedDict([
            ("count", len(review) + len(names("NAME_ONLY_UNRESOLVED")) + len(names("SAME_IDENTITY_REBRAND_SUCCESSOR"))),
            ("identity_review_required", review),
            ("name_only_unresolved", names("NAME_ONLY_UNRESOLVED")),
            ("rebrand_unresolved", names("SAME_IDENTITY_REBRAND_SUCCESSOR")),
            ("note", "Not census identities and never published: lodging-category-unconfirmed rows (Ocean Villas I/II, "
                     "Pierhouse B&B) and map names with no address of their own.")])),
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
            ("note", "The ACCESS_BLOCKED identities whose brand family (Choice) served only bot-challenge shells are the "
                     "paid-lane candidates. Same rows as ACCESS_BLOCKED, not an additional disposition; PAID PROVIDER "
                     "BUDGET was $0 and no paid lane was used or reserved.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", 0),
            ("note", "No row requires a founder ruling. Conflicts, single-suite exceptions and reads the shared reader "
                     "does not interpret are EVIDENCE holds.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", len(wyn.get("retired_routes") or [])),
            ("wyndham_retired_routes", wyn.get("retired_routes")),
            ("note", "Wyndham routes that redirect to the brand's search: Baymont Kitty Hawk and Days Inn & Suites Kill Devil "
                     "Hills Mariner (the building now trades as Mariner Inn & Suites on its own site). Routes, not "
                     "census identities.")])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET"))),
                                 ("future_submarket_hatteras_ocracoke", len(future)),
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
        ("display_market", "Outer Banks, North Carolina"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("release_queue", "Fayetteville (founder-authorized, host deploy blocked) -> Jacksonville -> Greenville -> "
                          "Atlanta -> Outer Banks"),
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
            ("OWNED_IDENTITIES", "0 -- no committed census held any Outer Banks identity."),
            ("OWNED_ROUTES", "0 -- the committed national harvest carries no Outer Banks route."),
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
        ("factory_code_changed", "NO -- every changed path is an boone_blowing_rock_nc_* helper, the market's discovery config, or a "
                                 "document under the market's own proposed / staging / report paths"),
        ("shared_factory_notes_recorded_not_repaired", [
            "The shared first-party reader does not read 'No guest pets allowed.' (Tranquil House Inn), 'Although pets cannot "
            "stay at the inn ...' (Cypress Moon Inn) or 'we welcome well behaved dogs and cats in select rooms' (Ocean Sands) "
            "as operative; those rows are held with the gate's class, never reworded.",
        ]),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("next_order", [
            "Wait until Netlify is restored and Fayetteville, Jacksonville, Greenville and Atlanta are live; read that live parent.",
            "Rebase worker/ptf-boone-blowing-rock-nc-market-001 onto it; copy markets/proposed/boone-blowing-rock-nc.json -> markets/boone-blowing-rock-nc.json, "
            "identity_census_proposed/boone-blowing-rock-nc.json -> identity_census/boone-blowing-rock-nc.json and the staged launch_package documents "
            "(hotel_policy_facts_boone-blowing-rock-nc.json, partition, authority shard) into their registered paths.",
            "market_registration_cli --write, build_global_authority --write then --check, release contract, registration_release_lane "
            "register + seal --work-order (a NEW package id against the new parent; this shadow package's FAST rule N fails by design once the parent moves).",
            "regression_delta classify (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, prepare the founder "
            "packet, deploy only on founder authorization.",
            "Before sealing, re-probe Choice (Comfort Inn On The Ocean, Comfort Inn South Oceanfront), Burrus House and White Doe Inn.",
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
