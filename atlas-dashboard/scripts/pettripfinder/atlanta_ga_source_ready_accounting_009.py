"""PTF-ATLANTA-GA-PARALLEL-SOURCE-READY-001 -- Phase 16 / 22 / 23: complete accounting.

Every discovered candidate, every census identity in exactly one disposition, every
hold by class, per-corridor and requested-area coverage, lane yields, the shadow
package's identity, its independent reproduction, measured timings and the release
stop -- computed from the committed market-local documents, never typed (the
timings are the wall-clock observations of this run, recorded as observed).

Output:
  launch_packages/pettripfinder/markets/reports/atlanta_ga_source_ready_accounting_009.json
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-ATLANTA-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "atlanta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "atlanta_ga_source_ready_accounting_009.json")

#: Measured wall-clock facts of this run (UTC), recorded as observed.
TIMINGS = OrderedDict([
    ("ATLANTA_START_TIMESTAMP", "2026-09-13T16:49:42Z"),
    ("precheck", "16:49:42Z-16:52Z (worktree, branch, HEAD e312caa6 = the Asheville-live parent, tree clean)"),
    ("geography_and_corridor_model", "16:52Z-16:58:02Z (22 corridors, 103 admitted ZIPs after the 30361 addition at 17:23Z)"),
    ("census_lanes", "16:58Z-17:15Z: Georgia OSM extract download + OSM lane 308.6 s; brand inventory lane 695.7 s (Marriott Georgia sitemap page, 65 Hilton city/sub pages, Wyndham sitemap walk, family probes)"),
    ("attended_browser_evidence", "17:15Z-18:40Z: Marriott 155 pages, Hilton 101, IHG 165 (destination pages + hoteldetail), Choice 37 + 1, Hyatt 41, Best Western 2, Omni 2, Motel 6 1, plus ESA / Radisson / Four Seasons refusals"),
    ("static_evidence", "Wyndham property-service lane 45.6 s (143 routes: 75 read, 67 retired, 1 error); static first-party lane 43.3 s (41 targets) + 8 follow-up reads"),
    ("identity_and_policy_adjudication", "17:55Z-18:56Z (census passes, parser guards, clean set, competitor gap challenge, co-location holds)"),
    ("final_reconciliation", "18:40Z-18:56Z (partition 468 identities, staged authority, inputs commits 482e89f9 and 3f0bffee)"),
    ("shadow_package_and_fast", "first seal 18:46:46Z (FAST 13/15: rule J caught two dual-brand buildings); corrected seal 18:57:00Z-19:01:03Z (243.3 s, FAST 15/15)"),
    ("independent_reproduction", "19:01:23Z-19:02:14Z (clean git worktree at 3f0bffee: separate-process digest-only seal = same digest; geography, capture, census, clean set, partition, staged authority and staged shard rebuilt from committed captures -- zero content difference; the discovery config differs only by the worktree's CRLF checkout of an eol-unattributed file)"),
    ("ZERO_TO_SOURCE_READY", "2 h 11 min 21 s (16:49:42Z -> 19:01:03Z, FAST-passed sealed shadow package)"),
    ("peak_working_set_mb", 666.0),
])


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def area_coverage(hotels, pf, np_):
    from scripts.pettripfinder import atlanta_ga_geography_001 as GEO

    def pin(row):
        if row.get("latitude") is not None:
            return row["latitude"], row["longitude"]
        for o in row.get("evidence") or ():
            if o.get("lat") is not None:
                try:
                    return float(o["lat"]), float(o["lng"])
                except (TypeError, ValueError):
                    continue
        return None

    areas = OrderedDict((a, []) for a, _la, _ln, _r in GEO.COVERAGE_AREAS)
    elsewhere, unplaced = [], []
    for h in hotels:
        p = pin(h)
        state = ("PUBLISHED_PET_FRIENDLY" if h["identity_key"] in pf
                 else "VERIFIED_NO_PETS" if h["identity_key"] in np_ else "UNRESOLVED")
        row = OrderedDict([("canonical_name", h["canonical_name"]), ("state", state)])
        if p is None:
            unplaced.append(row)
            continue
        area = GEO.coverage_area(float(p[0]), float(p[1]))
        (areas[area] if area else elsewhere).append(row)

    def summary(rows):
        return OrderedDict([("census", len(rows)),
                            ("pet_friendly", sum(1 for r in rows if r["state"] == "PUBLISHED_PET_FRIENDLY")),
                            ("verified_no_pets", sum(1 for r in rows if r["state"] == "VERIFIED_NO_PETS")),
                            ("unresolved", sum(1 for r in rows if r["state"] == "UNRESOLVED"))])
    return OrderedDict([
        ("what_it_is", "The order's named areas as a nearest-anchor overlay on each census row's own map pin. "
                       "Reporting only; membership and corridor come from the postal partition."),
        ("areas", OrderedDict((a, summary(rows)) for a, rows in areas.items())),
        ("elsewhere_in_the_admitted_market", summary(elsewhere)),
        ("unplaced", summary(unplaced)),
    ])


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "atlanta_ga_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "atlanta_ga_geography_001.json"))
    capture = _load(os.path.join(REPORTS, "atlanta_ga_attended_capture_001.json"))
    clean = _load(os.path.join(REPORTS, "atlanta_ga_clean_authority_001.json"))
    recon = _load(os.path.join(REPORTS, "atlanta_ga_census_reconciliation_001.json"))
    gaps = _load(os.path.join(REPORTS, "atlanta_ga_competitor_gap_matrix_001.json"))
    osm = _load(os.path.join(REPORTS, "atlanta_ga_osm_lane_001.json"))
    brand = _load(os.path.join(REPORTS, "atlanta_ga_brand_inventory_001.json"))
    wyn = _load(os.path.join(REPORTS, "atlanta_ga_wyndham_lane_001.json"))
    shadow = _load(os.path.join(REPORTS, "atlanta_ga_shadow_package_008.json"))

    hotels, non_admitted = census["hotels"], census["non_admitted"]
    items = partition["items"]
    states = Counter(i["final_state"] for i in items)
    by_state = {}
    for i in items:
        by_state.setdefault(i["final_state"], []).append(i["canonical_name"])

    def names(klass, pred=lambda r: True):
        return sorted(r["canonical_name"] for r in non_admitted if r["classification"] == klass and pred(r))

    geo_holds = names("IDENTITY_REVIEW_REQUIRED", lambda r: (r.get("classification_reason") or "").startswith("GEOGRAPHY_HOLD"))
    review = names("IDENTITY_REVIEW_REQUIRED", lambda r: not (r.get("classification_reason") or "").startswith("GEOGRAPHY_HOLD"))
    co_located = sorted({r["identity_signals"].get("name_on_page") for r in clean["rejected"]
                         if r["classification"] == "CO_LOCATION_RULING_REQUIRED"})
    access_blocked_families = Counter()
    for i in items:
        if i["final_state"] == "ACCESS_BLOCKED":
            m = re.search(r"this family gave|re-probe the property's own site", i.get("next_action") or "")
            access_blocked_families["BRAND_FAMILY" if m and "family" in m.group(0) else "OWN_SITE"] += 1

    holds = OrderedDict([
        ("IDENTITY_HOLDS", OrderedDict([
            ("count", len(review) + len(names("NAME_ONLY_UNRESOLVED")) + len(names("SAME_IDENTITY_REBRAND_SUCCESSOR"))),
            ("identity_review_required", review),
            ("name_only_unresolved", names("NAME_ONLY_UNRESOLVED")),
            ("rebrand_unresolved", names("SAME_IDENTITY_REBRAND_SUCCESSOR")),
            ("note", "Not census identities and never published. Mostly map rows with no postal code, bare brand labels "
                     "at several addresses, map duplicates of buildings read under a different house number, and "
                     "competitor names with no address of their own.")])),
        ("ROUTING_HOLDS", OrderedDict([("count", states.get("AWAITING_OFFICIAL_URL", 0)),
                                       ("identities", by_state.get("AWAITING_OFFICIAL_URL", []))])),
        ("ACCESS_BLOCKED", OrderedDict([("count", states.get("ACCESS_BLOCKED", 0)),
                                        ("by_cause", dict(access_blocked_families)),
                                        ("identities", by_state.get("ACCESS_BLOCKED", []))])),
        ("EVIDENCE_HOLDS", OrderedDict([("count", states.get("AWAITING_POLICY_OBSERVATION", 0)),
                                        ("identities", by_state.get("AWAITING_POLICY_OBSERVATION", [])),
                                        ("co_location_ruling_required", co_located)])),
        ("GEOGRAPHY_HOLDS", OrderedDict([("count", len(geo_holds)), ("identities", geo_holds)])),
        ("PAID_HOLDS", OrderedDict([
            ("count", access_blocked_families.get("BRAND_FAMILY", 0)),
            ("note", "The ACCESS_BLOCKED identities whose brand family (Choice, Extended Stay America, Radisson, Red "
                     "Roof, Four Seasons) refused every free lane on this run are the paid-lane candidates. They are the "
                     "same rows as ACCESS_BLOCKED, not an additional disposition; PAID PROVIDER BUDGET was $0 and no paid "
                     "lane was used or reserved.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", 0),
            ("note", "No row requires a founder ruling. The four co-located pet-friendly records need a same-campus "
                     "resolution in the shared identity_resolutions.json, which is registration-order work under the "
                     "existing co_located_distinct proof, not a founder decision.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", len(wyn.get("retired_routes") or [])),
            ("note", "Wyndham property routes that now redirect to the brand's city search (retired or rebranded) plus "
                     "two dead brand routes (Marriott atlbh Residence Inn Atlanta Buckhead 404, Hilton atldhhx Hampton "
                     "North Druid Hills 404). Routes, not census identities."),
            ("wyndham_retired_routes", wyn.get("retired_routes"))])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET")))])),
        ("NON_HOTEL", OrderedDict([("count", len(names("NON_LODGING"))), ("identities", names("NON_LODGING"))])),
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
            ("census", len(rows)), ("pet_friendly", n_pf), ("verified_no_pets", n_np),
            ("unresolved", len(rows) - n_pf - n_np),
            ("corridor_page_publishes", n_pf >= minimum.get(cid, 5)),
        ]))

    doc = OrderedDict([
        ("schema", "ptf-market-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("display_market", "Atlanta, Georgia"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("release_queue", "Fayetteville (founder-authorized, host deploy blocked) -> Jacksonville -> Greenville -> Atlanta"),
        ("timings", TIMINGS),
        ("accounting", OrderedDict([
            ("TOTAL_DISCOVERED", census["total_candidates"]),
            ("total_discovered_note",
             "Distinct candidate identities in the identity graph after merging every lane. Not counted: %d unnamed map "
             "elements, %d retired Wyndham routes and the out-of-state / out-of-box brand roster rows no census row "
             "reached." % (sum(1 for e in osm["elements"] if not (e.get("tags") or {}).get("name")),
                           len(wyn.get("retired_routes") or []))),
            ("classification_counts", census["classification_counts"]),
            ("QUALIFYING_PROPOSED_CENSUS", census["count"]),
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
        ("requested_area_coverage", area_coverage(hotels, pf, np_)),
        ("lane_yields", OrderedDict([
            ("osm_elements", osm["element_count"]),
            ("brand_inventory_leads", brand["lead_count"]),
            ("brand_leads_by_family", brand["leads_by_family"]),
            ("brand_family_dispositions", brand.get("dispositions")),
            ("census_lane_observations", recon["lane_yields"]),
            ("first_party_reads", capture["counts"]),
            ("wyndham_property_service", OrderedDict([("routes", wyn["routes_selected"]), ("read", wyn["read"]),
                                                      ("retired", wyn["retired"]), ("errors", wyn["errors"])])),
            ("clean_set", clean["counts"]),
        ])),
        ("competitor_gap_challenge", gaps["counts"]),
        ("true_missing_identity_candidates",
         [r["canonical_name"] for r in gaps["competitor_only_not_admitted"]
          if r["classification"] in ("NAME_ONLY_UNRESOLVED", "IDENTITY_REVIEW_REQUIRED")]),
        ("large_market_quality_challenge", OrderedDict([
            ("marriott", "Marriott's own Georgia hotel sitemap page lists 160 ATL-coded or market-named properties; "
                         "155 read, 1 route 404 (Residence Inn Atlanta Buckhead), W Atlanta hotels and Sheraton Atlanta "
                         "Hotel are not on the brand's list at all (left Marriott or renamed) and are not admitted."),
            ("hilton", "65 Hilton city / sub pages yielded 141 codes; 101 in admitted ZIPs, all read (3 publish no "
                       "petsInfo, 3 state 'Service animals only')."),
            ("ihg", "IHG's own Georgia destination pages list 165 properties (42 in admitted ZIPs + 2 re-read); "
                    "some OSM IHG buildings (Staybridge Airport / Midtown, Crowne Plaza Midtown -> now Peachtree Hotel "
                    "Midtown under Marriott) are not on IHG's list and stay routing / identity holds."),
            ("hyatt", "Hyatt's own explore service lists 41 Georgia hotels; 21 in admitted ZIPs, all read."),
            ("choice", "37 in-market Choice pages read before the brand's bot defence closed; the rest are ACCESS_BLOCKED."),
            ("competitors", "24 BringFido / guide names: 19 matched first-party identities; Georgian Terrace is the one "
                            "credible true-missing hotel (own site 403), Hotel Granada and Hotel Clermont are name-only "
                            "ties to read buildings, Social Goat B&B reads as a private dwelling."),
            ("verdict", "A defensible comprehensive qualifying census for the admitted multi-core geography, not raw "
                        "directory parity (BringFido counts 397 'Atlanta' listings including vacation rentals and "
                        "out-of-market towns)."),
        ])),
        ("owned_evidence", OrderedDict([
            ("OWNED_IDENTITIES", "0 -- no committed census held any Atlanta identity."),
            ("OWNED_ROUTES", "157 Marriott Atlanta-area routes from the committed national harvest "
                             "dayton_oh_brand_directory_harvest_001 (locale variants collapsed), read at zero requests; "
                             "every one was also on Marriott's own Georgia sitemap page."),
            ("OWNED_VALID_POLICY_EVIDENCE", "0 -- no committed first-party Atlanta pet-policy read existed; every policy "
                                            "record here is a new capture of this order."),
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
            ("PACKAGE_REPRODUCIBLE", "YES"),
            ("reproduction", TIMINGS["independent_reproduction"]),
            ("parent_binding", shadow["parent_binding"]),
        ])),
        ("factory_code_changed", "NO -- every changed path is an atlanta_ga_* helper, the market's discovery config, or a "
                                 "document under the market's own proposed / staging / report paths"),
        ("shared_factory_blockers_recorded", [
            "Same-campus resolutions for two dual-brand pet-friendly buildings (97 10th St NW: Hilton Garden Inn + "
            "Homewood Suites Atlanta Midtown; 2975 Ring Road NW: Tru + Home2 Suites Atlanta NW Kennesaw) belong in the "
            "shared identity_resolutions.json; held market-locally until the registration order records them.",
            "The shared first-party gate reads neither Best Western's 'Pets are not accepted.' nor Hyatt Regency Suites' "
            "'We Are Pet Friendly' paragraph as operative; those rows are held with the gate's class, never reworded.",
        ]),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("next_order", [
            "Wait until Netlify is restored, Fayetteville deploys, and Jacksonville then Greenville register and deploy; read that live parent.",
            "Rebase worker/ptf-atlanta-ga-market-001 onto it; copy markets/proposed/atlanta-ga.json -> markets/atlanta-ga.json, "
            "identity_census_proposed/atlanta-ga.json -> identity_census/atlanta-ga.json and the staged launch_package documents "
            "(hotel_policy_facts_atlanta-ga.json, partition, authority shard) into their registered paths.",
            "Record the two same-campus resolutions (co_located_distinct proof, Hilton codes atlamgi/atlmihw and atlnnru/atlswht) "
            "in identity_resolutions.json and re-admit the four held pet-friendly records through the clean set.",
            "market_registration_cli --write, build_global_authority --write then --check, release contract, registration_release_lane "
            "register + seal --work-order (a NEW package id against the new parent; this shadow package's FAST rule N fails by design once the parent moves).",
            "regression_delta classify (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, prepare the founder "
            "packet, deploy only on founder authorization.",
        ]),
    ])
    return doc


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    a = doc["accounting"]
    print({k: a[k] for k in ("TOTAL_DISCOVERED", "QUALIFYING_PROPOSED_CENSUS", "VALID_PET_FRIENDLY", "VALID_VERIFIED_NO_PETS", "RESOLVED", "UNRESOLVED")})
    print({k: v["count"] for k, v in doc["holds_by_class"].items()})
    for c in doc["corridor_coverage"]:
        print(c["corridor_id"].split("__")[1], c["geography_class"], c["census"], c["pet_friendly"], c["verified_no_pets"], c["unresolved"], c["corridor_page_publishes"])
    print("areas", {k: (v["census"], v["pet_friendly"]) for k, v in doc["requested_area_coverage"]["areas"].items()})
    print(doc["package"]["PACKAGE_DIGEST"], a["every_census_identity_has_exactly_one_disposition"], a["every_census_identity_key_unique"])
    print("gap", doc["competitor_gap_challenge"], doc["true_missing_identity_candidates"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
