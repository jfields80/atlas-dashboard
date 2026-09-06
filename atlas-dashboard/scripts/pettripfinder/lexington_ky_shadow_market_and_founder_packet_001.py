"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phases 15, 16, 18 and 19.

Assembles the Lexington MARKET-LOCAL shadow market from this order's own
artifacts, builds ONE grouped founder packet, and sets PROMOTION_READY.

Nothing here writes shared production source, shared globals, shared pins or a
deployment artifact. The output is a shadow: a proposal for the serialized
promotion order that follows.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-LEXINGTON-KY-NEW-MARKET-001"
MARKET_ID = "lexington-ky"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
RECON = os.path.join(REPORTS, "lexington_ky_census_reconciliation_001.json")
ROUTING = os.path.join(REPORTS, "lexington_ky_routing_and_static_capture_001.json")
COMPETITOR = os.path.join(REPORTS, "lexington_ky_competitor_census_challenge_001.json")
CITY_PAGES = os.path.join(REPORTS, "lexington_ky_brand_city_page_lane_001.json")
PAID = os.path.join(REPORTS, "lexington_ky_paid_readiness_001.json")


def rj(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    args = ap.parse_args()

    recon = rj(RECON)
    routing = rj(ROUTING)
    comp = rj(COMPETITOR)
    city = rj(CITY_PAGES)
    paid = rj(PAID)

    recs = recon["records"]
    ident = routing["identities"]
    by_class = Counter(r["classification"] for r in recs)

    # ---------------- clean pending authority (phase 15) ------------------
    clean_pf = [r for r in ident if r.get("policy_class") == "CLEAN_PET_FRIENDLY"]
    clean_np = [r for r in ident if r.get("policy_class") == "CLEAN_VERIFIED_NO_PETS"]
    resolved = clean_pf + clean_np
    unresolved = [r for r in ident if r not in resolved]

    corridors = Counter(r["cell_id"] for r in ident)

    # ---------------- founder packet (phase 16) ---------------------------
    groups = OrderedDict()

    a_items = []
    for r in recs:
        if r["classification"] in ("IDENTITY_REVIEW_REQUIRED", "NAME_ONLY_UNRESOLVED",
                                   "DUPLICATE_LISTING"):
            a_items.append(OrderedDict([
                ("identity", r["name"] or "(unnamed OSM element %s)" % r["osm_element"]),
                ("evidence", OrderedDict([
                    ("osm_element", r["osm_element"]),
                    ("address_stated", r["address_line"] or None),
                    ("postal_stated", r["postal_code"] or None),
                    ("coordinates", [r["latitude"], r["longitude"]]),
                    ("county_polygon", r["county"]),
                    ("corridor", r["cell_id"]),
                    ("why", r["classification_why"]),
                ])),
                ("proposed_action",
                 "resolve on first-party address / phone / property code before admission"),
                ("recommendation",
                 "HOLD out of the clean cohort. Hilton's own Lexington city page proves the "
                 "market has TWO Embassy Suites and THREE Homewood Suites, so a bare chain "
                 "name here cannot be resolved by inspection."),
                ("census_effect", "excluded from the clean census until resolved"),
                ("authority_effect", "none -- no policy is bound to any of these rows"),
                ("routing_effect", "no route is bound on a name alone"),
                ("reversibility", "fully reversible; nothing is written to authority"),
                ("blocks_promotion", "NO"),
            ]))
    groups["A_identity_alias_successor_duplicate_same_campus"] = OrderedDict([
        ("count", len(a_items)), ("items", a_items)])

    b_items = []
    fringe = Counter()
    for r in recs:
        if r["classification"] == "OUTSIDE_MARKET":
            fringe[r["county"] or "(no polygon)"] += 1
    b_items.append(OrderedDict([
        ("identity", "The three fringe county seats named by the order"),
        ("evidence", OrderedDict([
            ("method",
             "OSM admin_level=6 county polygons extracted from the same Geofabrik Kentucky "
             "extract the census came from; every candidate placed by point-in-polygon"),
            ("counts_by_county", OrderedDict(sorted(fringe.items()))),
            ("georgetown_scott",
             "10 named hotels plus 5 unnamed elements, all postal 40324, all inside the Scott "
             "County polygon. Marriott markets one of them as 'Fairfield Inn & Suites "
             "Georgetown Lexington' -- brand marketing scope, not a market boundary."),
            ("nicholasville_jessamine",
             "Jessamine County polygon. NOTE the genuinely hard row: 'Hampton Inn "
             "Nicholasville Brannon Crossing' states city Nicholasville and postal 40356 but "
             "its coordinates fall inside the FAYETTE polygon, and Hilton's own Lexington city "
             "page lists it (lexbchx). Brannon Crossing straddles the county line."),
            ("versailles_woodford",
             "Woodford County polygon. Includes The Kentucky Castle, which a LEXINGTON cell "
             "found: cell membership is not market membership."),
        ])),
        ("proposed_action",
         "keep `included_municipalities` at Lexington alone; rule separately on each fringe "
         "town as its own market or as an explicit per-hotel admission"),
        ("recommendation",
         "EXCLUDE all three for now, consistent with the committed Louisville boundary review "
         "that excluded Lexington from Louisville as a 'Separate destination'. The "
         "explicit_hotel_admissions mechanism exists in the market config and is empty."),
        ("census_effect", "%d candidates held outside the market" % sum(fringe.values())),
        ("authority_effect", "none"),
        ("routing_effect", "none"),
        ("reversibility", "fully reversible; admitting one is a config edit plus a re-run"),
        ("blocks_promotion", "NO"),
    ]))
    groups["B_geography_fringe"] = OrderedDict([("count", len(b_items)), ("items", b_items)])

    c_items = [OrderedDict([
        ("identity", "Four Points by Sheraton - Lexington, 1938 Stanton Way"),
        ("evidence", OrderedDict([
            ("finding",
             "present in OSM with a street address, ABSENT from Marriott's global property "
             "sitemap (10,228 distinct property codes, walked 2026-09-02) under any Lexington "
             "slug, and absent from every free lane this order ran"),
            ("classification", "BRAND_INVENTORY_SILENT"),
        ])),
        ("proposed_action", "verify on a first-party page before any lifecycle claim"),
        ("recommendation",
         "HOLD. Brand-roster absence alone is NOT proof that a hotel closed -- that is a "
         "standing rule of this factory. It may be a rebrand, a franchise exit, or a sitemap "
         "gap. Do not mark it closed and do not publish it."),
        ("census_effect", "stays in the census as an unresolved identity"),
        ("authority_effect", "none"),
        ("routing_effect", "FREE_LANE_EXHAUSTED; needs attended routing or paid discovery"),
        ("reversibility", "fully reversible"),
        ("blocks_promotion", "NO"),
    ])]
    groups["C_closure_conversion_non_lodging"] = OrderedDict([
        ("count", len(c_items)), ("items", c_items)])

    d_items = [OrderedDict([
        ("identity", "THE WHOLE MARKET -- no publication-grade policy evidence exists yet"),
        ("evidence", OrderedDict([
            ("routed_rows", len([r for r in ident if r.get("route")])),
            ("static_outcomes", routing["totals"]["static_outcomes"]),
            ("clean_pet_friendly", 0),
            ("clean_verified_no_pets", 0),
            ("why",
             "The direct static lane returned zero publication-grade reads: 32 ACCESS_DENIED, "
             "5 NAVIGATION_FAILED, 4 UNHYDRATED, 2 UNEXPECTED_PAGE, 1 POLICY_NOT_FOUND, 1 "
             "IDENTITY_MISMATCH. Every one of those is a CHANNEL failure, not a statement "
             "about the hotel's policy, and source silence is not a withholding."),
            ("consequence",
             "35 of the 45 routed rows are Marriott or Hilton, which HARD-LANES-003 measured "
             "as a Firecrawl capability wall. The lane that answers them is the ATTENDED "
             "browser, which prior markets used to batch a whole brand by same-origin fetch."),
        ])),
        ("proposed_action",
         "run a dedicated Lexington policy order: attended browser for the Marriott/Hilton "
         "wall, plus the 10-row Firecrawl cohort the planner already identified"),
        ("recommendation",
         "This is the ONE blocker. It is not an ambiguity to rule on; it is acquisition work "
         "that has not been done, and this order stopped rather than infer policy from "
         "silence, from an amenity chip, or from the competitor directory."),
        ("census_effect", "none -- the census is complete and deterministic without it"),
        ("authority_effect", "there is no authority to write until policy evidence exists"),
        ("routing_effect", "none"),
        ("reversibility", "n/a"),
        ("blocks_promotion", "YES"),
    ])]
    groups["D_policy_ambiguity_reader_exception"] = OrderedDict([
        ("count", len(d_items)), ("items", d_items)])

    e_items = [OrderedDict([
        ("identity", "Competitor directory leads that Atlas cannot yet separate"),
        ("evidence", OrderedDict([
            ("headline_claim", comp["headline_count_trap"]["headline"]),
            ("rows_actually_served", comp["headline_count_trap"]["rows_actually_served_in_page_markup"]),
            ("classes", comp["reconciliation"]["classes"]),
            ("note",
             "The directory headlines 121 and its own markup serves 19. No Lexington number is "
             "derived from the headline. 4 rows are SAME_BRAND_SAME_CITY_REVIEW and 5 are "
             "IDENTITY_REVIEW_REQUIRED; 0 are confirmed missing identities."),
        ])),
        ("proposed_action", "resolve each against first-party evidence during the policy order"),
        ("recommendation",
         "No admission from this lane. A competitor directory is an AUDIT lane and never "
         "policy authority; its visible policy snippets were not read, quoted or stored."),
        ("census_effect", "none"),
        ("authority_effect", "none"),
        ("routing_effect", "none"),
        ("reversibility", "fully reversible"),
        ("blocks_promotion", "NO"),
    ])]
    groups["E_evidence_conflict"] = OrderedDict([("count", len(e_items)), ("items", e_items)])

    f_items = [OrderedDict([
        ("identity", "Cross-market identity collision check"),
        ("evidence", OrderedDict([
            ("louisville",
             "the committed Louisville boundary review explicitly EXCLUDES Lexington as a "
             "'Separate destination', and Louisville's discovery box (38.05..38.42 N, "
             "-85.95..-85.42 W) does not reach Fayette County (-84.66..-84.28 W)"),
            ("repository_scan",
             "3 files in the whole repository mention Lexington: the Louisville boundary "
             "review, the Louisville discovery config disclosure, and the Dayton Marriott "
             "sitemap. None carries a Lexington identity, route or policy fact."),
            ("marriott_prefix_check",
             "every non-Kentucky 'lexington' slug in Marriott's global sitemap resolves to "
             "another state -- Lexington MA (Boston), Lexington SC (Columbia), Lexington VA "
             "(Roanoke), Lexington Park MD, and The Lexington Hotel NYC"),
            ("collisions_found", 0),
        ])),
        ("proposed_action", "none"),
        ("recommendation", "no collision; Lexington is a genuinely new market"),
        ("census_effect", "none"), ("authority_effect", "none"), ("routing_effect", "none"),
        ("reversibility", "n/a"), ("blocks_promotion", "NO"),
    ])]
    groups["F_cross_market_identity_collision"] = OrderedDict([
        ("count", len(f_items)), ("items", f_items)])

    total_holds = sum(g["count"] for g in groups.values())
    blockers = [k for k, g in groups.items()
                for it in g["items"] if it["blocks_promotion"] == "YES"]

    # ---------------- promotion readiness (phase 19) ----------------------
    criteria = OrderedDict([
        ("deterministic_census_for_clean_rows", OrderedDict([
            ("met", True),
            ("why", "every one of the 91 candidates carries exactly one classification and one "
                    "county-polygon placement; 0 rows are geography-UNRESOLVED")])),
        ("no_duplicate_premises", OrderedDict([
            ("met", True),
            ("why", "1 DUPLICATE_LISTING found and folded; no two clean rows share a street "
                    "address")])),
        ("no_unresolved_cross_market_collision_in_clean_cohort", OrderedDict([
            ("met", True), ("why", "0 collisions; Louisville explicitly excludes Lexington")])),
        ("publication_grade_first_party_evidence", OrderedDict([
            ("met", False),
            ("why", "ZERO publication-grade policy observations exist. The direct static lane "
                    "returned only channel failures, and neither the Firecrawl cohort nor the "
                    "attended lane has been run.")])),
        ("held_ambiguity_excluded", OrderedDict([
            ("met", True), ("why", "8 held rows are outside the clean cohort by construction")])),
        ("deterministic_geography_or_explicit_hold", OrderedDict([
            ("met", True),
            ("why", "county polygons decide membership; the 3 fringe towns are an explicit "
                    "hold with an empty explicit_hotel_admissions mechanism ready for them")])),
        ("known_later_release_contract_inputs", OrderedDict([
            ("met", True),
            ("why", "census, corridors, routes and partition inputs all exist in this shadow")])),
        ("remaining_acquisition_optional", OrderedDict([
            ("met", False),
            ("why", "policy acquisition is REQUIRED, not optional: with 0 clean rows the market "
                    "would publish 0 profiles")])),
    ])
    ready = all(c["met"] for c in criteria.values())

    shadow = OrderedDict([
        ("schema", "ptf-shadow-market/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("nothing_entered_production_source", True),
        ("proposed_census", OrderedDict([
            ("candidates_discovered", len(recs)),
            ("classifications", OrderedDict(sorted(by_class.items()))),
            ("confirmed_active_identities", by_class.get("EXACT_UNIQUE_IDENTITY", 0)),
            ("duplicates", by_class.get("DUPLICATE_LISTING", 0)),
            ("successors", 0),
            ("same_campus", by_class.get("SAME_CAMPUS_DISTINCT_ENTITY", 0)),
            ("closed_or_converted", 0),
            ("outside_market", by_class.get("OUTSIDE_MARKET", 0)),
            ("identity_holds", by_class.get("IDENTITY_REVIEW_REQUIRED", 0)
             + by_class.get("NAME_ONLY_UNRESOLVED", 0)),
        ])),
        ("policy_authority", OrderedDict([
            ("clean_pet_friendly", len(clean_pf)),
            ("clean_verified_no_pets", len(clean_np)),
            ("resolved", len(resolved)),
            ("unresolved", len(unresolved)),
        ])),
        ("routes", routing["totals"]["route_classes"]),
        ("profiles_projected", len(clean_pf)),
        ("corridors", OrderedDict([
            ("count", len([c for c in corridors if c])),
            ("assignment", OrderedDict(sorted(corridors.items()))),
        ])),
        ("unresolved_queue", [OrderedDict([
            ("name", r["name"]), ("route_class", r["route_class"]),
            ("policy_class", r.get("policy_class", "NOT_ATTEMPTED")),
            ("static_outcome", (r.get("static") or {}).get("outcome", "")),
        ]) for r in unresolved]),
        ("founder_holds", total_holds),
        ("geography", OrderedDict([
            ("bounds", "37.85..38.28 N, -84.80..-84.25 W (OBSERVATION box, not an admission "
                       "boundary)"),
            ("included_municipalities", ["Lexington"]),
            ("admitting_cells", 10),
            ("observation_only_cells", 3),
            ("membership_test", "point-in-polygon against OSM admin_level=6 county boundaries"),
        ])),
    ])

    packet = OrderedDict([
        ("schema", "ptf-founder-packet/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("one_packet_no_row_by_row_loop", True),
        ("total_holds", total_holds),
        ("blocking_groups", sorted(set(blockers))),
        ("non_blocking_groups", sorted(set(groups) - set(blockers))),
        ("groups", groups),
    ])

    readiness = OrderedDict([
        ("schema", "ptf-promotion-readiness/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("PROMOTION_READY", "YES" if ready else "NO"),
        ("criteria", criteria),
        ("exact_blockers", [
            "ZERO publication-grade policy observations. 61 confirmed identities and 45 bound "
            "routes exist, but no hotel in Lexington has a first-party pet policy read yet, so "
            "a promotion would publish 0 profiles.",
        ] if not ready else []),
        ("what_is_NOT_a_blocker", [
            "the 8 identity holds -- excluded from the clean cohort by construction",
            "the 22 outside-market rows -- decided on county polygons, not guessed",
            "the 16 unrouted rows -- routing is not required to promote a row that has no policy",
            "the 10-row Firecrawl cohort -- bounded, costed and unspent",
        ]),
        ("next_order_required_before_promotion",
         "PTF-LEXINGTON-KY-POLICY-ACQUISITION-002: attended browser for the Marriott/Hilton "
         "capability wall (35 of 45 routed rows), plus the 10-row Firecrawl cohort "
         "(worst case 10 credits) that the committed planner already identified."),
        ("paid_readiness_summary", paid["totals"]),
    ])

    for name, obj in (("lexington_ky_shadow_market_001.json", shadow),
                      ("lexington_ky_founder_packet_001.json", packet),
                      ("lexington_ky_promotion_readiness_001.json", readiness)):
        p = os.path.join(REPORTS, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1)
            fh.write("\n")
        print("wrote", p)

    print()
    print("PROMOTION_READY =", readiness["PROMOTION_READY"])
    print("census:", shadow["proposed_census"]["confirmed_active_identities"],
          "| PF:", len(clean_pf), "| no-pets:", len(clean_np),
          "| holds:", total_holds, "| corridors:", shadow["corridors"]["count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
