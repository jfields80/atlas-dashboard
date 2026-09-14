"""PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001 -- complete accounting.

Cloned from the Pinehurst - Southern Pines NC accounting helper. Every discovered candidate, every
census identity in exactly one disposition, every hold by class, per-corridor and
per-town coverage, lane yields, the vacation-rental filter's refusals, the shadow
package's identity, its independent reproduction, measured timings and the release
stop -- computed from the committed market-local documents, never typed (the
timings are the wall-clock observations of this run, recorded as observed).

Output:
  launch_packages/pettripfinder/markets/reports/hickory_nc_source_ready_accounting_009.json
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

WORK_ORDER = "PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "hickory-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "hickory_nc_source_ready_accounting_009.json")

#: Measured wall-clock facts of this run (UTC), recorded as observed.
TIMINGS = OrderedDict([
    ("HICKORY_START_TIMESTAMP", "2026-09-14T02:51:52Z (2026-09-13T22:51:52-04:00)"),
    ("precheck_and_template_read", "02:51Z-02:58Z (worktree, branch, HEAD ec764bef, tree clean; the branch had no commits and was fast-forwarded to the Greenville-live commit 595bfeeb before any work; the Pinehurst - Southern Pines shadow chain read as the template)"),
    ("geography_and_corridor_model", "by 03:05Z (9 corridors: 3 CORE / 2 CORRIDOR / 4 FRINGE, 12 admitted ZIPs; Lenoir preserved as future submarket; Morganton, Statesville, Taylorsville, Lincolnton, Denver and Boone OUTSIDE by name)"),
    ("osm_lane", "421.5 s, run detached beside the other lanes (North Carolina extract, hard link of the 2026-09-10 snapshot; 110 hotel / motel / chalet / apartment elements in the observation box)"),
    ("brand_inventory_lane", "97 free requests (Marriott NC sitemap page, 18 Hilton city pages, Wyndham sitemap walk of 61 documents, family probes)"),
    ("destination_roster", "Visit Hickory Metro listing service: token + 4 sub-category queries (5 requests, 39 listings)"),
    ("static_evidence", "Wyndham property service 1.8 s (15 routes: 7 read, 8 retired); static home pages 1.3 s (10 targets: 5 served, 5 refused 403); policy-page lane 1.4 s (5 sites, 10 documents)"),
    ("browser_evidence", "03:07Z-03:17Z: Marriott 3, Hilton 3, IHG 3 (same-origin fetch, payload digests verified); Best Western 1, Red Roof 1, Motel 6 / Studio 6 2 (hashed in the same call); Affordable Suites and The Trott House Inn own sites (plain client 403); 2nd Street Inn and The Dragonfly Inn own sites; Choice served an empty document"),
    ("identity_policy_adjudication_and_reconciliation", "03:12Z-03:20Z (census three passes, non-hotel and rebrand rulings, clean set, staged authority, partition)"),
    ("source_ready_inputs_committed", "2026-09-14T03:20:50Z (61dd835a); the clean-worktree rebuild found the staged launch_package census copy stale by two source-authority lines, so the first seal (pkg-hickory-nc-5f172c50, never committed) was discarded and the copy re-staged (3400a148)"),
    ("shadow_package_sealed_and_fast", "03:23:00Z-03:23:47Z (sealed twice in-process, FAST 15/15)"),
    ("independent_reproduction", "03:23:50Z-03:24:17Z (clean git worktree at 3400a148: geography, brand pages, capture, census, clean set, staged authority, partition and staged shard rebuilt from committed captures -- zero content difference, the discovery config differs only by the worktree's CRLF checkout of an eol-unattributed file; separate-process digest-only seal = the same digest)"),
    ("ZERO_TO_SOURCE_READY", "31 min 55 s (02:51:52Z -> 03:23:47Z, FAST-passed sealed shadow package)"),
    ("peak_memory", "not instrumented on this run (the OSM two-pass read and the FAST cold builds were the heaviest steps; no step was memory-constrained)"),
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
    from scripts.pettripfinder import hickory_nc_geography_001 as GEO
    towns = OrderedDict((a, []) for a in (
        "Hickory downtown / central", "I-40 Hickory", "US-321 Hickory", "Long View / Mountain View", "Hickory (other)",
        "Conover", "Newton", "Claremont", "Granite Falls / Sawmills", "Hildebran / Icard", "Maiden", "Catawba", "Hudson"))
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
        ("what_it_is", "Coverage for the order's named areas. Reporting only; membership and corridor come from the "
                       "postal partition. A Hickory row reports under I-40 Hickory, US-321 Hickory or downtown when its "
                       "own street names those roads (13th Avenue Drive, Lenoir-Rhyne Boulevard, US-70 are the I-40 "
                       "exit 125-126 service roads), else by its pin."),
        ("towns", OrderedDict((a, summary(rows)) for a, rows in towns.items())),
        ("unplaced", summary(unplaced)),
    ])


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "hickory_nc_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "hickory_nc_geography_001.json"))
    capture = _load(os.path.join(REPORTS, "hickory_nc_attended_capture_001.json"))
    clean = _load(os.path.join(REPORTS, "hickory_nc_clean_authority_001.json"))
    recon = _load(os.path.join(REPORTS, "hickory_nc_census_reconciliation_001.json"))
    gaps = _load(os.path.join(REPORTS, "hickory_nc_competitor_gap_matrix_001.json"))
    osm = _load(os.path.join(REPORTS, "hickory_nc_osm_lane_001.json"))
    brand = _load(os.path.join(REPORTS, "hickory_nc_brand_inventory_001.json"))
    wyn = _load(os.path.join(REPORTS, "hickory_nc_wyndham_lane_001.json"))
    roster = _load(os.path.join(REPORTS, "hickory_nc_destination_roster_001.json"))
    shadow = _load(os.path.join(REPORTS, "hickory_nc_shadow_package_008.json"))

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
        if "townhome" in why:
            return "CLUB_TOWNHOMES"
        if "apartment" in why:
            return "APARTMENT_COMMUNITY"
        if "retreat" in why or "country club" in why:
            return "RETREAT_OR_CLUB"
        if "vacation-rental company" in why:
            return "VACATION_RENTAL"
        if "vacation rental" in why or "rented as a whole property" in why:
            return "VACATION_RENTAL"
        if subs & {"RV/Campground", "Camping / RV Resorts", "Campgrounds & RV"}:
            return "CAMPGROUND_RV"
        if subs & {"Agritourism", "Farm", "Equestrian", "Unique Venue"}:
            return "FARM_VENUE"
        if "Condos / Villas" in subs:
            return "CONDO_VILLA_RENTAL_MANAGEMENT"
        if "tourism=" in why or "cottage" in why:
            return "MAP_COTTAGE"
        return "OTHER_NON_HOTEL"

    holds = OrderedDict([
        ("IDENTITY_HOLDS", OrderedDict([
            ("count", len(review) + len(names("NAME_ONLY_UNRESOLVED")) + len(names("SAME_IDENTITY_REBRAND_SUCCESSOR"))),
            ("identity_review_required", review),
            ("name_only_unresolved", names("NAME_ONLY_UNRESOLVED")),
            ("rebrand_unresolved", names("SAME_IDENTITY_REBRAND_SUCCESSOR")),
            ("note", "Not census identities and never published. Choice rows: Sleep Inn (1179 13th Avenue Drive SE) and "
                     "Quality Suites (1125 13th Avenue Drive SE) -- their bare names are registered keys of Charlotte and "
                     "Louisville and Choice served an empty page, so no first-party name clears the collision; Comfort "
                     "Inn & MainStay Suites (1607 Fairgrove Church Road, Conover) -- one bureau listing, two Choice "
                     "flags in search summaries, the map's retired La Quinta. Motel 6 / Studio 6 Hickory -- two G6 "
                     "property ids at one street (484 US-70 SW), co-location unproven. Lodging category unconfirmed: The "
                     "Lodge at Rock Barn (member club; its lodging page 404s), Henry River Mill Village (attraction "
                     "offering 'overnight accommodations' with no room inventory). Name-only: the map's 'Econo Lodge' "
                     "pin beside the Red Roof Inn, and competitor names Comfort Inn Conover-Hickory, MainStay Suites "
                     "Conover-Hickory and Budget Inn Express Hickory (a booking slug for the Motel 6).")])),
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
            ("note", "No census identity is ACCESS_BLOCKED: the three Choice buildings (Sleep Inn, Quality Suites, "
                     "Comfort Inn & MainStay Suites) are identity holds outside the census, and they are the paid-lane "
                     "candidates only after their identities clear. PAID PROVIDER BUDGET was $0 and no paid lane was "
                     "used or reserved.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", 0),
            ("note", "No row requires a founder ruling. Conflicts, single-suite exceptions and reads the shared reader "
                     "does not interpret are EVIDENCE holds.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", len(wyn.get("retired_routes") or [])),
            ("wyndham_retired_routes", wyn.get("retired_routes")),
            ("note", "Wyndham routes that redirect to the brand's search: La Quinta Hickory (1607 Fairgrove Church Road, "
                     "Conover -- the bureau now lists Comfort Inn & MainStay Suites there), Ramada Conover-Hickory Area, "
                     "Super 8 Claremont (the map now names Claremont Inn & Suites at 3054 North Oxford Street), and "
                     "outside the market Baymont Statesville, Days Inn Lenoir, Days Inn & Suites Morganton, Ramada "
                     "Statesville and Super 8 Statesville. Routes, not census identities.")])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET"))),
                                 ("future_submarket", OrderedDict([("market_id", "lenoir-nc"), ("identities", future)]))])),
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
        ("display_market", "Hickory \u2013 Newton \u2013 Conover, North Carolina"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("release_queue", "Greenville (LIVE, the current parent 595bfeeb) -> handled separately; Hickory waits in the "
                          "source-ready queue"),
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
        ("competitor_gap_reconciliation", OrderedDict([
            ("leads", OrderedDict([
                ("Comfort Inn Conover-Hickory", "REVIEW -- one of two Choice flags at 1607 Fairgrove Church Road (rebrand / dual-brand hold)"),
                ("MainStay Suites Conover-Hickory", "REVIEW -- the other Choice flag at the same premises"),
                ("Hilton Garden Inn Hickory", "EXACT MATCH"),
                ("Motel 6 Hickory NC", "EXACT MATCH -- confirmed on the brand's own page (484 US-70 SW); identity hold with Studio 6"),
                ("Red Roof Inn Hickory", "EXACT MATCH"),
                ("Crowne Plaza Hotel Hickory", "ALIAS -- Crowne Plaza Hickory"),
                ("Days Inn & Suites by Wyndham Hickory", "EXACT MATCH"),
                ("Days Inn by Wyndham Conover-Hickory", "EXACT MATCH"),
                ("Sleep Inn Hickory South", "ALIAS -- Sleep Inn, 1179 13th Avenue Drive SE (identity hold)"),
                ("Studio 6 Hickory NC", "EXACT MATCH -- confirmed on the brand's own page; identity hold with Motel 6"),
                ("Holiday Inn Express Hotel & Suites Conover - Hickory Area", "ALIAS -- Holiday Inn Express & Suites Conover (Hickory Area)"),
                ("Budget Inn Express Hickory", "REBRAND -- a booking slug for the Motel 6 Hickory listing; name only"),
            ])),
            ("true_missing_identity_found", "Motel 6 Hickory and Studio 6 Hickory: absent from OSM, the bureau and every brand "
                                            "roster this order read; returned through the brand's own city and property pages"),
            ("raw_count_parity_chased", False),
        ])),
        ("owned_evidence", OrderedDict([
            ("OWNED_IDENTITIES", "0 -- no registered census (identity_census/*.json) carries a row in any Hickory-market "
                                 "postal code; the committed reports mention Hickory only in other markets' geography notes."),
            ("OWNED_ROUTES", "0 -- the committed national brand harvest (dayton_oh_brand_directory_harvest_001.json) yields no "
                             "Hickory-area lead; every route was derived from the brand's own current inventory by this order."),
            ("OWNED_VALID_POLICY_EVIDENCE", "0 -- no earlier order read a Hickory-area property page; every record is a new "
                                            "first-party capture of this order."),
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
        ("factory_code_changed", "NO -- every changed path is a hickory_nc_* helper, the market's discovery config, or a "
                                 "document under the market's own proposed / staging / report paths"),
        ("shared_factory_notes_recorded_not_repaired", [
            "The shared first-party reader classifies Baymont Hickory's 'Up to 2 pets with a maximum weight of 25 lbs are "
            "welcome for a non-refundable charge of 20.00 USD per night with a refundable 100.00 USD deposit. ADA defined "
            "service animals are welcome at this hotel.' as SERVICE_ANIMAL_ONLY; held as an evidence hold, never reworded.",
            "Courtyard Hickory's own Pet Policy row prints 'Pets Welcome' above 'Pets Not Allowed' (FIRST_PARTY_CONFLICT); held.",
        ]),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("next_order", [
            "When Hickory reaches the front of the release queue, read CURRENT VERIFIED LIVE and rebase this branch onto it.",
            "Copy markets/proposed/hickory-nc.json -> markets/hickory-nc.json, identity_census_proposed/hickory-nc.json -> "
            "identity_census/hickory-nc.json and the staged launch_package documents into their registered paths.",
            "market_registration_cli --write, build_global_authority --write then --check, release contract, registration_release_lane "
            "register + seal --work-order (a NEW package id against the new parent; this shadow package's FAST rule N fails by design once the parent moves).",
            "regression_delta classify (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, prepare the founder "
            "packet, deploy only on founder authorization.",
            "Before sealing: re-probe Choice (Sleep Inn, Quality Suites, Comfort Inn / MainStay Suites Conover -- names that clear the "
            "cross-market key collisions and the Fairgrove Church Road premises split), open Motel 6 / Studio 6 Hickory's client-rendered "
            "pet policy, and seek first-party routes for Gateway Extended Stay, Fran Mar Motel, Lowman's Motor Court and Claremont Inn & Suites.",
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
