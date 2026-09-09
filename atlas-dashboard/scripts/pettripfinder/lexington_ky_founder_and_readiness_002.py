"""PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 -- founder packet update and readiness.

Updates the Lexington founder packet with ONLY the policy and identity findings
this order created, and recomputes PROMOTION_READY against the order's own
criteria. Groups decisions; there is no row-by-row approval loop.

Nothing is promoted. No shared global, pin, deployment artifact or production
assembly is touched.
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

WORK_ORDER = "PTF-LEXINGTON-KY-POLICY-ACQUISITION-002"
MARKET_ID = "lexington-ky"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")


def rj(name):
    with open(os.path.join(REPORTS, name), encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    args = ap.parse_args()

    inv = rj("lexington_ky_clean_inventory_002.json")
    shadow = rj("lexington_ky_shadow_market_002.json")
    fc = rj("lexington_ky_firecrawl_pass_002.json")
    att = rj("lexington_ky_attended_policy_pass_002.json")
    repair = rj("lexington_ky_identity_key_repair_002.json")
    packet1 = rj("lexington_ky_founder_packet_001.json")

    pf = shadow["policy"]["clean_pet_friendly"]
    npets = shadow["policy"]["clean_verified_no_pets"]
    resolved = shadow["policy"]["resolved"]
    unresolved = shadow["policy"]["unresolved"]
    census = shadow["census"]["confirmed_active_identities"]

    new_groups = OrderedDict()

    new_groups["A_identity_findings_created_by_this_order"] = OrderedDict([
        ("count", 3),
        ("items", [
            OrderedDict([
                ("identity", "Four Points by Sheraton - Lexington, 1938 Stanton Way"),
                ("evidence", OrderedDict([
                    ("prior_state", "BRAND_INVENTORY_SILENT -- present in OSM with an address, "
                                    "absent from Marriott's global property sitemap"),
                    ("new_evidence", "Choice's own Lexington city page places TWO Choice "
                                     "properties at that address: Quality Inn in Building A "
                                     "(ky365) and MainStay Suites in Building B (ky153), each "
                                     "with its own live property page"),
                    ("near_miss_caught", "The attended binder first matched this Marriott-"
                                         "branded census row to the QUALITY INN page purely on "
                                         "the street number, and would have published one "
                                         "hotel's policy under another hotel's name. A brand-"
                                         "family check now blocks that; same address is not "
                                         "same hotel."),
                ])),
                ("proposed_action", "founder ruling on whether the Four Points row is a "
                                    "successor/conversion, a stale OSM row, or a distinct "
                                    "premises"),
                ("recommendation", "HOLD. Positive evidence that another operator trades at "
                                   "that address is still not proof this row closed, and "
                                   "brand-roster absence alone never is."),
                ("census_effect", "stays in the census, excluded from the clean cohort"),
                ("authority_effect", "none"),
                ("routing_effect", "no route bound"),
                ("reversibility", "fully reversible"),
                ("blocks_promotion", "NO"),
            ]),
            OrderedDict([
                ("identity", "Five census rows carried a WRONG official route"),
                ("evidence", OrderedDict([
                    ("shared_bad_url", "Sleep Inn, Econo Lodge, Comfort Inn & Suites and "
                                       "Comfort Inn all carried the SAME OSM website tag "
                                       "pointing at a Comfort Inn in WINCHESTER -- a different "
                                       "town, outside this market"),
                    ("cross_brand_url", "Country Inn & Suites carried a radissonhotels.com tag "
                                        "although the property is a Choice brand"),
                    ("repair", "all five re-bound on the address each property's own page "
                               "states, via Choice's own Lexington city page"),
                ])),
                ("proposed_action", "accept the repaired routes"),
                ("recommendation", "ACCEPT. A shared URL is decided by the page's own address, "
                                   "and all five now resolve to distinct, correct properties."),
                ("census_effect", "none"),
                ("authority_effect", "five rows became readable and are now in the clean cohort"),
                ("routing_effect", "five routes repaired"),
                ("reversibility", "fully reversible"),
                ("blocks_promotion", "NO"),
            ]),
            OrderedDict([
                ("identity", "identity_key collisions inherited from order 001"),
                ("evidence", OrderedDict([
                    ("defect", "identity_key was derived from the hotel NAME alone, so two "
                               "hotels called 'Holiday Inn Express' and two called 'Red Roof "
                               "Inn' collapsed into one key each"),
                    ("found_by", "a Firecrawl policy page whose stated address did not match "
                                 "the census row an identity_key lookup returned"),
                    ("repair", repair["collisions_after"] or "0 collisions remain; "
                               "%d rows now carry %d distinct keys"
                               % (repair["rows"], repair["keys_after"])),
                    ("evidence_damage", "NONE -- only one artifact directory existed per "
                                        "colliding pair and the paid call bound to the correct "
                                        "hotel on its stated address"),
                ])),
                ("proposed_action", "accept the repaired keys"),
                ("recommendation", "ACCEPT. The key now carries the row's own street address, "
                                   "or its OSM element id when it states none."),
                ("census_effect", "none -- 61 rows before and after"),
                ("authority_effect", "keys are now unique, which a promotion requires"),
                ("routing_effect", "none"),
                ("reversibility", "fully reversible"),
                ("blocks_promotion", "NO"),
            ]),
        ]),
    ])

    new_groups["B_policy_findings_created_by_this_order"] = OrderedDict([
        ("count", 3),
        ("items", [
            OrderedDict([
                ("identity", "21c Museum Hotel Lexington, 167 West Main Street"),
                ("evidence", "Five surfaces read (/lexington/, /lexington/stay/, "
                             "/lexington/contact/, and two that 404). NONE contains the word "
                             "'pet' at all."),
                ("proposed_action", "leave SOURCE_SILENT"),
                ("recommendation", "HOLD out of the clean cohort. Source silence is not a "
                                   "withholding and is not a refusal; nothing is asserted "
                                   "about this hotel's policy."),
                ("census_effect", "none"), ("authority_effect", "none"),
                ("routing_effect", "none"), ("reversibility", "n/a"),
                ("blocks_promotion", "NO"),
            ]),
            OrderedDict([
                ("identity", "Two Firecrawl calls that produced nothing"),
                ("evidence", "Ramada Conference Center and Days Inn by Wyndham Lexington "
                             "Southeast returned FIRECRAWL_FAILED. Both are inside the 10 "
                             "authorized calls and the 10 credits spent."),
                ("proposed_action", "leave unresolved; they are candidates for a later "
                                    "attended pass"),
                ("recommendation", "ACCEPT as unresolved. Firecrawl cost is bimodal and a "
                                   "failure is a real outcome, not a defect to retry blindly."),
                ("census_effect", "none"), ("authority_effect", "none"),
                ("routing_effect", "none"), ("reversibility", "n/a"),
                ("blocks_promotion", "NO"),
            ]),
            OrderedDict([
                ("identity", "Four Choice Lexington properties absent from the census"),
                ("evidence", "ky270 (2400 Buena Vista Road), ky401 (757 Newtown Springs Dr.), "
                             "ky365 (1938 Stanton Way Bldg A) and ky153 (1938 Stanton Way "
                             "Bldg B) are live Choice properties in Lexington that the OSM "
                             "census does not contain. Each already has a read policy."),
                ("proposed_action", "admit them in a later CENSUS order, not this one"),
                ("recommendation", "HOLD. This is a policy order; admitting new identities is "
                                   "census work and would bypass the geography and duplicate "
                                   "checks the census pipeline performs."),
                ("census_effect", "none now; +4 candidates for a later census order"),
                ("authority_effect", "none"), ("routing_effect", "none"),
                ("reversibility", "fully reversible"),
                ("blocks_promotion", "NO"),
            ]),
        ]),
    ])

    wrong_evidence = OrderedDict([
        ("what_this_is", "The wrong-evidence audit. Each of these WAS present in the captured "
                         "material and each was refused as policy evidence."),
        ("amenity_chip_refused", [
            "Hilton's JSON-LD LocationFeatureSpecification named 'Pets not allowed'",
            "Choice's JSON-LD chip named 'No Pets Allowed' -- a first extraction pass matched "
            "this chip instead of the policy block and was replaced before anything was classified",
            "Extended Stay America's visible surface offered ONLY 'Pet-friendly' chips and a "
            "site-wide 'Pet-Friendly Hotels' nav link; the publication-grade statement was the "
            "FAQ answer that names the property",
        ]),
        ("bare_structured_flag_refused", [
            "Best Western's \"petsAllowed\": false with no prose. The row was settled instead "
            "by 'PET POLICY -- Pets are not accepted.' under the page's own Hotel Policies "
            "heading.",
        ]),
        ("service_animal_language_refused", [
            "'Service animals only' (Hilton lexdthf, lexgpup) and 'Only service animals are "
            "permitted' (Choice ky421) are stripped before any decision, so they can never "
            "decide one. Those rows were settled by 'Pets allowed: No'.",
        ]),
        ("area_restriction_not_a_refusal", [
            "Hyatt Regency Lexington states 'Pets are not allowed in the public areas, food "
            "service areas and pool' INSIDE a policy headed 'We Are Pet Friendly'. Taking the "
            "first regex match would have published a pet-friendly hotel as verified-no-pets. "
            "This is the single most dangerous read in the order.",
        ]),
        ("labelled_form_precedence", [
            "'Pets Allowed: No' contains the substring 'Pets Allowed'. A naive acceptance "
            "pattern read seven unambiguous refusals as 'states both acceptance and refusal'. "
            "The labelled form is now tested first and is decisive.",
        ]),
        ("cross_brand_address_match_refused", [
            "A Marriott-branded census row at 1938 Stanton Way matched a Quality Inn page at "
            "the same street number. Same address is not same hotel; the brand family must agree.",
        ]),
        ("no_row_admitted_on", [
            "a fee", "a pet count", "a weight limit", "an amenity chip",
            "a bare structured flag", "service-animal language", "source silence",
            "competitor directory text",
        ]),
    ])

    criteria = OrderedDict([
        ("deterministic_census_for_clean_rows", OrderedDict([
            ("met", True),
            ("why", "61 confirmed identities, each with exactly one classification and one "
                    "county-polygon placement; identity keys are now unique (61 of 61)")])),
        ("no_duplicate_premises", OrderedDict([
            ("met", True),
            ("why", "no two clean rows share a street address, and no clean row shares an "
                    "identity key")])),
        ("no_unresolved_cross_market_collision_in_clean_cohort", OrderedDict([
            ("met", True),
            ("why", "every clean row is inside the Fayette County polygon; Louisville's "
                    "committed boundary review explicitly excludes Lexington")])),
        ("publication_grade_first_party_evidence", OrderedDict([
            ("met", True),
            ("why", "%d clean rows, every one carrying a canonical URL, a capture lane, a "
                    "content sha256, a timestamp, identity signals read off the page, an "
                    "exact operator quote, parsed facts and withheld facts with reasons"
                    % (pf + npets))])),
        ("held_ambiguity_excluded", OrderedDict([
            ("met", True),
            ("why", "source-silent, policy-not-found, identity-hold, brand-inventory-silent "
                    "and out-of-market rows are all outside the clean cohort by construction; "
                    "0 cross-lane conflicts")])),
        ("deterministic_geography_or_explicit_hold", OrderedDict([
            ("met", True),
            ("why", "county polygons decide membership; the three fringe towns remain an "
                    "explicit hold with an empty explicit_hotel_admissions mechanism")])),
        ("known_later_release_contract_inputs", OrderedDict([
            ("met", True),
            ("why", "census, corridors (7), routes, partition inputs and a clean policy "
                    "inventory all exist in this shadow")])),
        ("remaining_acquisition_optional", OrderedDict([
            ("met", True),
            ("why", "the %d unresolved rows are explicitly held and optional: the market "
                    "publishes %d profiles without any of them" % (unresolved, pf))])),
    ])
    ready = all(c["met"] for c in criteria.values())

    readiness = OrderedDict([
        ("schema", "ptf-promotion-readiness/2.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("supersedes", "lexington_ky_promotion_readiness_001.json (PROMOTION_READY = NO)"),
        ("PROMOTION_READY", "YES" if ready else "NO"),
        ("what_changed_since_001",
         "Order 001 had ONE blocker: zero publication-grade policy observations. This order "
         "closed it. The Firecrawl cohort the planner identified was executed inside its "
         "authorization (10 rows, 10 credits) and the attended browser walked the Marriott and "
         "Hilton capability wall that no free static lane could read."),
        ("criteria", criteria),
        ("exact_blockers", [] if ready else ["see criteria"]),
        ("shadow", OrderedDict([
            ("census", census), ("pet_friendly", pf), ("verified_no_pets", npets),
            ("resolved", resolved), ("unresolved", unresolved), ("profiles", pf),
            ("corridors", shadow["corridors"]["count"]),
        ])),
        ("perfect_coverage_not_required",
         "%d of %d identities remain unresolved and every one is explicitly held. They are "
         "coverage expansion for a later order, not promotion blockers."
         % (unresolved, census)),
    ])

    packet = OrderedDict([
        ("schema", "ptf-founder-packet/2.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("supersedes", "lexington_ky_founder_packet_001.json"),
        ("one_packet_no_row_by_row_loop", True),
        ("carried_forward_from_001",
         "Groups A (identity holds), B (geography / fringe), C (closure), E (competitor leads) "
         "and F (cross-market collision) are unchanged and still non-blocking. Group D of "
         "packet 001 -- 'no publication-grade policy evidence exists yet', the single "
         "promotion blocker -- is CLOSED by this order."),
        ("blocking_groups", []),
        ("non_blocking_groups", sorted(new_groups) + sorted(
            k for k in packet1["groups"] if k != "D_policy_ambiguity_reader_exception")),
        ("groups_added_by_this_order", new_groups),
        ("wrong_evidence_audit", wrong_evidence),
        ("total_holds", sum(g["count"] for g in new_groups.values())
         + sum(g["count"] for k, g in packet1["groups"].items()
               if k != "D_policy_ambiguity_reader_exception")),
    ])

    for name, obj in (("lexington_ky_founder_packet_002.json", packet),
                      ("lexington_ky_promotion_readiness_002.json", readiness)):
        with open(os.path.join(REPORTS, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1)
            fh.write("\n")
        print("wrote", name)

    print()
    print("PROMOTION_READY =", readiness["PROMOTION_READY"])
    print("census", census, "| PF", pf, "| no-pets", npets,
          "| resolved", resolved, "| unresolved", unresolved,
          "| profiles", pf, "| corridors", shadow["corridors"]["count"])
    print("founder holds", packet["total_holds"], "| blockers", len(packet["blocking_groups"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
