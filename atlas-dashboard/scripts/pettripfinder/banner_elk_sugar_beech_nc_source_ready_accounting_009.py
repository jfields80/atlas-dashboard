"""PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001 -- complete accounting.

Cloned from the Boone - Blowing Rock NC accounting helper. Every discovered
candidate, every census identity in exactly one disposition, every hold by class,
per-corridor and per-town coverage, lane yields, the vacation-rental filter's
refusals, the owned evidence reused, the shadow seal's reproducibility, the FAST
outcome, measured timings and the release stop -- computed from the committed
market-local documents, never typed (the timings and the FAST outcome are the
wall-clock observations of this run, recorded as observed).

Output:
  launch_packages/pettripfinder/markets/reports/banner_elk_sugar_beech_nc_source_ready_accounting_009.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "banner-elk-sugar-beech-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "banner_elk_sugar_beech_nc_source_ready_accounting_009.json")
INPUTS_COMMIT = "e7684f853571bcf5fa597aa808fbcc947f3b4ba2"

#: Measured wall-clock facts of this run (UTC), recorded as observed.
TIMINGS = OrderedDict([
    ("BANNER_ELK_START_TIMESTAMP", "2026-09-14T13:22:48Z (2026-09-14T09:22:48-04:00)"),
    ("precheck_and_template_read", "13:22Z-13:30Z (branch base 7b630cfa = the Jacksonville-live parent, tree clean; the Boone "
                                   "source-ready chain 7adbafd1 / 20dbda61 read and cloned)"),
    ("geography_and_corridor_model", "by 13:36Z (3 corridors: 1 CORE / 1 CORRIDOR / 1 FRINGE, 6 admitted ZIPs; Boone's "
                                     "postal codes refused by name)"),
    ("osm_lane", "413.2 s (North Carolina extract, hard link of the Boone run's copy; 226 lodging elements in the box)"),
    ("brand_inventory_lane", "93 free requests (Marriott NC sitemap page, 14 Hilton city pages, 16 family sitemaps)"),
    ("destination_rosters", "99 free requests (Banner Elk TDA, Beech Mountain Visitor Center, Avery County Chamber, High "
                            "Country Host, Sugar Mountain Resort) + 42 Explore Boone rows owned at zero requests"),
    ("static_and_policy_page_lanes", "static 25.4 s (27 targets); policy pages 25.2 s (47 sites, 119 documents)"),
    ("attended_browser_evidence", "The Lodge at Banner Elk and 4 Seasons at Beech Mountain (same-origin fetch, row digests "
                                  "verified); beechmountaininns.com and thebannerelkinn.com not permitted in the browser"),
    ("first_inputs_committed", "2026-09-14T13:54:56Z (b31d1f5e, census 14)"),
    ("first_seal_and_fast", "13:55:08Z-13:55:55Z: sealed twice in-process (pkg ...778cd82b, equal digests); the FAST lane's "
                            "cold bundle build REFUSED -- NOT LAUNCH READY, 4 ready pet-friendly listings against the "
                            "market's own declared minimum_published_hotels = 5; no receipt; the unreceipted package was "
                            "removed; clean-worktree reproduction of b31d1f5e also matched (13:56Z-13:59Z)"),
    ("last_acquisition_probe", "13:59Z-14:01Z: remaining independents re-probed; Beech Alpen Inn's own site states its "
                               "address (identity opened, policy silent); no fifth pet-friendly read found"),
    ("source_inputs_committed", "2026-09-14T14:01:3xZ (e7684f85, census 15)"),
    ("shadow_seal_and_fast", "14:01:37Z-14:02Z: sealed twice in-process (pkg ...eb8d7487, equal digests); FAST cold bundle "
                             "build REFUSED again -- NOT LAUNCH READY (4 < 5); no receipt; unreceipted package removed"),
    ("independent_reproduction", "14:04Z-14:05Z (clean git worktree at e7684f85: geography, capture, census, clean set, "
                                 "staged authority, partition and staged shard rebuilt from committed captures with zero "
                                 "content difference -- only the CRLF checkout of the eol-unattributed discovery config -- and "
                                 "a separate-process digest-only seal reproduced sha256:eb8d7487...)"),
    ("ZERO_TO_SOURCE_READY", "NOT REACHED -- the market stops at the launch-inventory floor; first refusal 33 min 07 s after "
                             "start (13:22:48Z -> 13:55:55Z), confirmed on the final inputs at 14:02Z"),
])

#: The FAST outcome observed on this run (the lane aborted before it wrote a receipt).
FAST_OUTCOME = OrderedDict([
    ("package_id", "pkg-banner-elk-sugar-beech-nc-eb8d7487a044a10a"),
    ("package_digest", "sha256:eb8d7487a044a10afb80b84c4790530099e954d89df7c9f381ea01124b242fa2"),
    ("execution_zone", "SHADOW_UNTIL_REGISTERED"),
    ("created_from_source_sha", "e7684f853571bcf5fa597aa808fbcc947f3b4ba2"),
    ("parent_live_state", "the Jacksonville-live release at the branch base (live deploy 6aa77cb84f4fd6b6926c5445, rollback "
                          "6aa76e5d940d5025e8262319); Atlanta is live on its own branch, so rule N would fail it regardless"),
    ("superseded_first_seal", "pkg-banner-elk-sugar-beech-nc-778cd82b7f33f5ab (inputs b31d1f5e, census 14)"),
    ("reproducible_in_process", "YES"),
    ("reproducible_clean_worktree_separate_process", "YES"),
    ("fast_result", "ABORTED_AT_COLD_BUNDLE_BUILD -- 0 / 15 rules completed, no receipt"),
    ("refusal", "NOT LAUNCH READY: real inventory is below the approved launch threshold (ready_total 4, "
                "minimum_total_listings 5 from the market's own minimum_published_hotels). Refusing to build the public site."),
    ("why_not_lowered", "minimum_published_hotels = 5 was authored before any inventory existed and is the floor every "
                        "registered PetTripFinder market carries; lowering it to fit a count is weakening the standard, "
                        "and the order forbids it"),
    ("package_committed", "NO -- a sealed package with no FAST receipt is not lifecycle-safe to keep"),
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
    """The order's named towns, by the property's own stated municipality, then its pin. Reporting only."""
    from scripts.pettripfinder import banner_elk_sugar_beech_nc_geography_001 as GEO
    towns = OrderedDict((a, []) for a in ("Banner Elk", "Sugar Mountain", "Beech Mountain", "Seven Devils",
                                          "Linville / Grandfather", "Newland", "Elk Park"))
    unplaced = []
    for h in hotels:
        state = ("PUBLISHED_PET_FRIENDLY" if h["identity_key"] in pf
                 else "VERIFIED_NO_PETS" if h["identity_key"] in np_ else "UNRESOLVED")
        row = OrderedDict([("canonical_name", h["canonical_name"]), ("state", state), ("city", h.get("city"))])
        p = _pin(h) or (None, None)
        area = GEO.route_overlay((h.get("corridor") or "").split("__")[-1], h.get("street"), p[0], p[1], h.get("city"))
        row["basis"] = "own stated municipality, then pin (geography route_overlay)"
        (towns[area] if area in towns else unplaced).append(row)

    def summary(rows):
        return OrderedDict([("census", len(rows)),
                            ("pet_friendly", sum(1 for r in rows if r["state"] == "PUBLISHED_PET_FRIENDLY")),
                            ("verified_no_pets", sum(1 for r in rows if r["state"] == "VERIFIED_NO_PETS")),
                            ("unresolved", sum(1 for r in rows if r["state"] == "UNRESOLVED")),
                            ("identities", rows)])
    return OrderedDict([
        ("what_it_is", "Coverage for the order's named towns. Reporting only; Banner Elk, Sugar Mountain, Beech Mountain "
                       "and Seven Devils share 28604 and one corridor."),
        ("towns", OrderedDict((a, summary(rows)) for a, rows in towns.items())),
        ("unplaced", summary(unplaced)),
    ])


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "banner_elk_sugar_beech_nc_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "banner_elk_sugar_beech_nc_geography_001.json"))
    capture = _load(os.path.join(REPORTS, "banner_elk_sugar_beech_nc_attended_capture_001.json"))
    clean = _load(os.path.join(REPORTS, "banner_elk_sugar_beech_nc_clean_authority_001.json"))
    recon = _load(os.path.join(REPORTS, "banner_elk_sugar_beech_nc_census_reconciliation_001.json"))
    gaps = _load(os.path.join(REPORTS, "banner_elk_sugar_beech_nc_competitor_gap_matrix_001.json"))
    osm = _load(os.path.join(REPORTS, "banner_elk_sugar_beech_nc_osm_lane_001.json"))
    brand = _load(os.path.join(REPORTS, "banner_elk_sugar_beech_nc_brand_inventory_001.json"))
    roster = _load(os.path.join(REPORTS, "banner_elk_sugar_beech_nc_destination_roster_001.json"))
    boone = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_census_reconciliation_001.json"))

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
    neighbour = names("OUTSIDE_MARKET", lambda r: "NEIGHBOUR_MARKET" in reason(r))
    non_hotel = [r for r in non_admitted if r["classification"] == "NON_LODGING"]

    def nh_class(r):
        why = reason(r).lower()
        if "timeshare" in why:
            return "TIMESHARE_VACATION_OWNERSHIP"
        if "condominium" in why:
            return "CONDO_COMPLEX_OR_UNIT"
        if "rental-portfolio" in why or "property-management" in why:
            return "RENTAL_COMPANY_OR_PLATFORM"
        if "destination roster files" in why:
            return "ROSTER_TYPED_CABIN_CONDO_VACATION_HOME"
        if "campground" in why or "summer camp" in why:
            return "CAMP_RETREAT_CAMPGROUND_RV"
        if "tourism=" in why or "cabin" in why or "cottage" in why:
            return "CABIN_COTTAGE_CHALET"
        if "competitor short-term-rental" in why:
            return "COMPETITOR_RENTAL_LISTING"
        return "OTHER_NON_LODGING"

    holds = OrderedDict([
        ("IDENTITY_HOLDS", OrderedDict([
            ("count", len(review) + len(names("NAME_ONLY_UNRESOLVED")) + len(names("SAME_IDENTITY_REBRAND_SUCCESSOR"))),
            ("identity_review_required", review),
            ("name_only_unresolved", names("NAME_ONLY_UNRESOLVED")),
            ("rebrand_unresolved", names("SAME_IDENTITY_REBRAND_SUCCESSOR"))])),
        ("ROUTING_HOLDS", OrderedDict([("count", states.get("AWAITING_OFFICIAL_URL", 0)),
                                       ("identities", by_state.get("AWAITING_OFFICIAL_URL", []))])),
        ("ACCESS_BLOCKED", OrderedDict([("count", states.get("ACCESS_BLOCKED", 0)),
                                        ("identities", by_state.get("ACCESS_BLOCKED", []))])),
        ("EVIDENCE_HOLDS", OrderedDict([("count", states.get("AWAITING_POLICY_OBSERVATION", 0)),
                                        ("identities", by_state.get("AWAITING_POLICY_OBSERVATION", [])),
                                        ("rejected_reads_by_class", clean["counts"]["rejected_by_class"])])),
        ("GEOGRAPHY_HOLDS", OrderedDict([("count", len(geo_holds)), ("identities", geo_holds)])),
        ("PAID_HOLDS", OrderedDict([("count", 0), ("note", "No row is blocked by a brand family whose surface refused; "
                                                           "PAID PROVIDER BUDGET was $0 and no paid lane was used.")])),
        ("FOUNDER_HOLDS", OrderedDict([
            ("count", 0),
            ("note", "No row requires a founder ruling. The Mast Farm Inn (Valle Crucis beside 28604) is a GEOGRAPHY "
                     "hold decided by the geography's stated rule; the release floor is a standing contract value, "
                     "not a per-row ruling.")])),
        ("CLOSED_OR_RETIRED", OrderedDict([
            ("count", 1),
            ("identities", ["Best Western Mountain Lodge (former flag of The Lodge at Banner Elk; the map's Best Western "
                            "route is superseded by the property's own site)"]),
            ("note", "The Inn at Elk River is listed CLOSED by a third-party directory only; no first-party or roster "
                     "source in this order names it, so it is recorded here and never entered the census.")])),
        ("OUTSIDE", OrderedDict([("count", len(names("OUTSIDE_MARKET"))),
                                 ("live_neighbour_boone_blowing_rock", len(neighbour)),
                                 ("neighbour_identities", neighbour)])),
        ("NON_HOTEL", OrderedDict([("count", len(non_hotel)),
                                   ("by_kind", OrderedDict(sorted(Counter(nh_class(r) for r in non_hotel).items()))),
                                   ("identities", sorted(r["canonical_name"] for r in non_hotel))])),
    ])

    pf = {i["identity_key"] for i in items if i["final_state"] == "PUBLISHED_PET_FRIENDLY"}
    np_ = {i["identity_key"] for i in items if i["final_state"] == "VERIFIED_NO_PETS"}
    market = _load(os.path.join(PKG, "markets", "proposed", "%s.json" % MARKET_ID))
    minimum = {c["corridor_id"]: c.get("minimum_hotel_count", 5) for c in market["corridors"]}
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

    boone_preserved = [r for r in boone["rows"] if "FUTURE_SUBMARKET" in (r.get("classification_reason") or "")
                       or r["postal_code"] in ("28604", "28646", "28657", "28622")]
    carried = OrderedDict()
    mine = {r["canonical_name"].lower(): r for r in recon["rows"]}
    for r in boone_preserved:
        m = mine.get(r["canonical_name"].lower())
        carried[r["canonical_name"]] = m["classification"] if m else "NOT_SEEN_BY_THIS_ORDER_UNDER_THAT_NAME"

    doc = OrderedDict([
        ("schema", "ptf-market-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("display_market", "Banner Elk – Sugar Mountain – Beech Mountain, North Carolina"),
        ("state", "NOT_SOURCE_READY -- census, evidence and staged authority built and reproducible; the FAST cold bundle "
                  "build refuses below the market's own minimum_published_hotels (4 verified pet-friendly of 5)"),
        ("inputs_commit", INPUTS_COMMIT),
        ("timings", TIMINGS),
        ("accounting", OrderedDict([
            ("TOTAL_DISCOVERED", census["total_candidates"]),
            ("total_discovered_note",
             "Distinct candidate identities in the identity graph after merging every lane. Not counted: %d unnamed map "
             "elements (condo buildings and chalets), the Hilton national-navigation codes the city pages carry for "
             "other states." % sum(1 for e in osm["elements"] if not (e.get("tags") or {}).get("name"))),
            ("classification_counts", census["classification_counts"]),
            ("PROPOSED_CENSUS", census["count"]),
            ("VALID_PET_FRIENDLY", states.get("PUBLISHED_PET_FRIENDLY", 0)),
            ("VALID_VERIFIED_NO_PETS", states.get("VERIFIED_NO_PETS", 0)),
            ("RESOLVED", partition["resolved"]), ("UNRESOLVED", partition["unresolved"]),
            ("partition_counts_by_state", OrderedDict(sorted(states.items()))),
            ("every_census_identity_has_exactly_one_disposition",
             len(items) == census["count"] and len({i["identity_key"] for i in items}) == census["count"]),
            ("every_census_identity_key_unique", len({h["identity_key"] for h in hotels}) == len(hotels)),
            ("cross_market_identity_collisions", recon.get("cross_market_identity_collisions")),
        ])),
        ("holds_by_class", holds),
        ("corridor_coverage", coverage),
        ("corridor_pages_meeting_threshold", sum(1 for c in coverage if c["corridor_page_publishes"])),
        ("town_coverage", town_coverage(hotels, pf, np_)),
        ("lane_yields", OrderedDict([
            ("osm_elements", osm["element_count"]),
            ("brand_inventory_leads", brand["lead_count"]),
            ("brand_family_dispositions", brand.get("dispositions")),
            ("destination_rosters", OrderedDict([("listings", roster["listing_count"]),
                                                 ("by_source", roster["listings_by_source"]),
                                                 ("by_subcategory", roster["lodging_by_subcategory"])])),
            ("census_lane_observations", recon["lane_yields"]),
            ("first_party_reads", capture["counts"]),
            ("clean_set", clean["counts"]),
        ])),
        ("competitor_gap_challenge", gaps["counts"]),
        ("owned_evidence", OrderedDict([
            ("OWNED_IDENTITIES", "%d rows the Boone - Blowing Rock build preserved for this market (FUTURE_SUBMARKET or an "
                                 "Avery postal code); each re-classified here: %s" % (len(boone_preserved), dict(carried))),
            ("OWNED_ROUTES", "1 -- Courtyard Sugar Mountain Banner Elk (tribc) from Marriott's NC sitemap; the national "
                             "harvest carries no Avery County route"),
            ("OWNED_VALID_POLICY_EVIDENCE", "1 -- the Boone attended pass's Courtyard Sugar Mountain Banner Elk Marriott "
                                            "row (2026-09-13, sha256 76b23af4...), carried verbatim"),
            ("OWNED_ROSTER_ROWS", "42 Explore Boone listing-service rows inside the observation box, read at zero requests"),
        ])),
        ("package", FAST_OUTCOME),
        ("identity_findings", [
            "The Lodge at Banner Elk is the former Best Western Mountain Lodge (Banner Elk TDA: 'formerly the Best Western "
            "Mountain Lodge'); the map still carries the Best Western name and route, superseded by the property's own site.",
            "The Lodge at Banner Elk's FAQ page is titled 'FAQ | Bridge Creek Inn' (an operator template shared with a Clayton "
            "GA property) and states two different pet fees; only the named acceptance ('The Lodge at Banner Elk is a "
            "pet-friendly hotel.') is published, no fee.",
            "The Mast Farm Inn's own page states 'Valle Crucis, NC 28604'; Taylor House Inn's states 'Banner Elk NC 28604' "
            "while calling itself a Valle Crucis B&B. The stated municipality decides: Taylor House admitted, Mast Farm held.",
            "Linville Falls Lodge & Cottages' own site states postal code 28647 (the map says Newland 28657): OUTSIDE.",
            "A map 'Pineola Motel' 600 m from The Pineola is held for identity review rather than merged or duplicated.",
        ]),
        ("shared_factory_notes_recorded_not_repaired", [
            "The shared first-party reader does not read 'Pet Policy - We do not allow pets.' (4 Seasons at Beech Mountain) "
            "or 'However, we cannot accommodate any pets at the present time.' (Taylor House Inn) as operative refusals; "
            "both are held with the gate's class, never reworded.",
            "The site builder's launch-inventory floor (the market's minimum_published_hotels) is applied inside the FAST "
            "cold bundle build, so a below-floor shadow market aborts FAST with no receipt rather than failing a named rule.",
        ]),
        ("factory_code_changed", "NO"),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the "
                                 "generated globals, release contracts, identity_resolutions.json and the market registry are unchanged"),
        ("what_would_make_it_source_ready", [
            "One more operative first-party pet-friendly read in an admitted corridor (5 of 5). The open candidates: The "
            "Banner Elk Inn (own site did not resolve), Beech Alpen Inn (own pages silent) / Top of the Beech Inn (operator "
            "site 403; attended browser not permitted), The Inn at Shady Lawn, Huskins Court, Pixie Motor Inn (no own site).",
            "Or an operative refusal the shared reader reads for 4 Seasons at Beech Mountain / Taylor House Inn (does not "
            "raise the pet-friendly count).",
            "Or a geography ruling on The Mast Farm Inn (Valle Crucis 28604), whose own policies page is an operative acceptance.",
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
        print(c["corridor_id"].split("__")[1], c["geography_class"], c["census"], c["pet_friendly"], c["verified_no_pets"], c["unresolved"])
    print("towns", {k: (v["census"], v["pet_friendly"], v["verified_no_pets"], v["unresolved"]) for k, v in doc["town_coverage"]["towns"].items()},
          "unplaced", doc["town_coverage"]["unplaced"]["census"])
    print(a["every_census_identity_has_exactly_one_disposition"], a["every_census_identity_key_unique"], a["cross_market_identity_collisions"])
    print("gap", doc["competitor_gap_challenge"])
    print("owned", doc["owned_evidence"]["OWNED_IDENTITIES"][:900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
