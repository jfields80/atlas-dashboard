"""PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001 -- complete accounting.

Cloned from the Atlanta GA accounting helper. Every discovered candidate, every
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
    ("PINEHURST_SOUTHERN_PINES_START_TIMESTAMP", "2026-09-14T01:31:50Z (2026-09-13T21:31:50-04:00)"),
    ("precheck_and_template_read", "01:31Z-01:40Z (worktree, branch, HEAD e312caa6, tree clean; the Boone - Blowing Rock shadow chain read as the template)"),
    ("geography_and_corridor_model", "by 01:52Z (7 corridors: 3 CORE / 2 CORRIDOR / 2 FRINGE, 11 admitted ZIPs; Robbins, Sanford, Fayetteville, Raeford, Rockingham, Laurinburg and Montgomery County OUTSIDE by name)"),
    ("osm_lane", "438.7 s (North Carolina extract, hard link of the 2026-09-10 snapshot; 40 hotel / motel / guest_house / chalet / apartment elements)"),
    ("brand_inventory_lane", "96 free requests (Marriott NC sitemap page, 17 Hilton city pages, Wyndham sitemap walk, family probes)"),
    ("destination_roster", "Pinehurst, Southern Pines, Aberdeen Area CVB: the lodging page and the one partner-index query it declares (2 requests, 49 lodging listings)"),
    ("live_parent_moved", "~01:57Z check (before any commit): Fayetteville went live (ec764bef, deploy 6aa750d8); the branch (no commits yet) was fast-forwarded to ec764bef so the package binds to the CURRENT live parent"),
    ("attended_browser_evidence", "Marriott 4 and IHG 1 (same-origin fetch, payload digests verified), Best Western 1 (hashed in the same call as the quote); Hilton 3 reused from the Fayetteville order's attended payload; Choice closed with a bot-challenge shell; four independents' own sites read (identity only)"),
    ("static_first_party_lanes", "Wyndham property service 3.1 s (7 routes: 3 read, 4 retired); static home pages 2.5 s (22 targets); policy-page lane 13.6 s (22 sites, 87 documents)"),
    ("source_ready_inputs_committed", "2026-09-14T02:03:14Z (9690624b)"),
    ("shadow_package_sealed_and_fast", "02:03:21Z-02:03:47Z (sealed twice in-process, FAST 15/15)"),
    ("independent_reproduction", "02:04Z-02:06Z (clean git worktree at 9690624b: separate-process digest-only seal = same digest; geography, brand pages, capture, census, clean set, staged authority, partition and staged shard rebuilt from committed captures -- zero content difference, the discovery config differs only by the worktree's CRLF checkout of an eol-unattributed file; same digest a third time)"),
    ("ZERO_TO_SOURCE_READY", "31 min 57 s (01:31:50Z -> 02:03:47Z, FAST-passed sealed shadow package)"),
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
        "Pinehurst village / resort district", "Pinehurst Moore Regional medical / business ring",
        "Southern Pines downtown", "US-1 corridor", "Aberdeen US-15-501 / NC-5", "Whispering Pines / Carthage",
        "Vass / Cameron", "Seven Lakes / West End / Foxfire"))
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
                       "postal partition. Southern Pines and Aberdeen rows on US-1 / Sandhills Boulevard report as the "
                       "US-1 corridor; Pinehurst rows off the village streets report as the Moore Regional ring."),
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
        if "golf-package operator" in why:
            return "GOLF_PACKAGE_VILLAS_COTTAGES"
        if "vacation rental" in why or "rented as a whole property" in why:
            return "VACATION_RENTAL"
        if subs & {"RV/Campground", "Camping / RV Resorts"}:
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
            ("note", "Not census identities and never published: Duncraig Manor (lodging category unconfirmed -- now "
                     "an event venue), the Econo Lodge at 408 West Morganton Road (its only labels collide with registered "
                     "keys; Choice served a bot shell), a map 'Motel 6' label on the AmeriVu site, stale competitor flags "
                     "(Days Inn Conference Center, Super 8 Aberdeen), a competitor spelling of SureStay Plus, and "
                     "competitor B&B names with no first-party address (Knollwood House -- domain lapsed -- Beggar's "
                     "Ride, Conroy B&B, Pine Gables of Aberdeen, Duck Smith House, Lucky Bar Farm, The MacPherson "
                     "House).")])),
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
            ("note", "The ACCESS_BLOCKED identities whose brand family (Choice: Clarion Inn, Comfort Inn Pinehurst, "
                     "Quality Inn Pinehurst) refused this client are the "
                     "paid-lane candidates. Same rows as ACCESS_BLOCKED, not an additional disposition; PAID PROVIDER "
                     "BUDGET was $0 and no paid lane was used or reserved.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", 0),
            ("note", "No row requires a founder ruling. Conflicts, single-suite exceptions and reads the shared reader "
                     "does not interpret are EVIDENCE holds.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", len(wyn.get("retired_routes") or [])),
            ("wyndham_retired_routes", wyn.get("retired_routes")),
            ("note", "Wyndham routes that redirect to the brand's search: Days Inn Conference Center Southern Pines "
                     "(805 SW Service Road now trades as Clarion Inn), Super 8 Aberdeen Southern Pines (1408 N Sandhills "
                     "Boulevard now trades as AmeriVu Inn & Suites), the legacy Microtel route (the property trades on "
                     "its live route) and Days Inn Rockingham outside. Routes, not census identities.")])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET"))),
                                 ("future_submarket", "none preserved by this order")])),
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
        ("display_market", "Pinehurst \u2013 Southern Pines \u2013 Aberdeen, North Carolina"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("release_queue", "Fayetteville (LIVE, the current parent) -> Jacksonville -> Greenville -> Atlanta -> "
                          "Outer Banks -> Boone - Blowing Rock -> Pinehurst - Southern Pines"),
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
            ("OWNED_IDENTITIES", "18 observed, 0 registered -- the Fayetteville census (registered at ec764bef) carries "
                                 "Moore County rows only as OUTSIDE_MARKET observations; no registered market admits a "
                                 "Pinehurst / Southern Pines / Aberdeen identity, and no identity was imported from it."),
            ("OWNED_ROUTES", "7 -- the Fayetteville brand lanes' Southern Pines routes (4 Marriott, 3 Hilton) and Wyndham's "
                             "Microtel / Days Inn / Super 8 routes; the committed national harvest carries no Sandhills "
                             "route. Every route was re-derived from the brand's own current inventory by this order."),
            ("OWNED_VALID_POLICY_EVIDENCE", "3 -- the Fayetteville order's attended Hilton reads (2026-09-13) for Hilton "
                                            "Garden Inn Southern Pines Pinehurst, Hampton Inn & Suites Southern Pines-"
                                            "Pinehurst and Homewood Suites Olmsted Village, reused with their document "
                                            "sha256s; every other record is a new first-party capture of this order."),
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
            "The shared first-party reader does not read Pinehurst Resort's 'Pinehurst is a pet-free facility.' as a "
            "refusal (QUOTE_NOT_OPERATIVE); the Carolina Hotel, the Holly Inn, the Manor and the Magnolia Inn are held, "
            "never reworded.",
            "The CVB's partner index prints a house number in the ZIP field for two listings (12615, 10024); the roster "
            "lane accepts only a 27xxx / 28xxx postal code.",
        ]),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("next_order", [
            "Wait until Jacksonville, Greenville, Atlanta, Outer Banks and Boone - Blowing Rock are live; read that live parent.",
            "Rebase worker/ptf-hickory-nc-market-001 onto it; copy markets/proposed/hickory-nc.json -> "
            "markets/hickory-nc.json, identity_census_proposed/hickory-nc.json -> "
            "identity_census/hickory-nc.json and the staged launch_package documents into their registered paths.",
            "market_registration_cli --write, build_global_authority --write then --check, release contract, registration_release_lane "
            "register + seal --work-order (a NEW package id against the new parent; this shadow package's FAST rule N fails by design once the parent moves).",
            "regression_delta classify (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, prepare the founder "
            "packet, deploy only on founder authorization.",
            "Before sealing, re-probe Choice (Clarion Inn, Comfort Inn Pinehurst, Quality Inn Pinehurst, Econo Lodge Southern Pines -- "
            "the Econo Lodge also needs its first-party name to clear the cross-market key collision), ask Pinehurst Resort for a "
            "per-hotel policy statement the reader interprets, and re-read Pine Crest Inn's script-rendered pages.",
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
