# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PAID-OFFICIAL-URL-DISCOVERY-007, phase 2 -- the nine exceptions.

Every ruling here is read out of evidence already on disk. Nothing is fetched
and nothing is decided: each row carries the evidence, a PROPOSED ruling and
whether a machine could have made it, and the founder rules.

THE RESULT IS COUNTER-INTUITIVE AND WORTH SAYING PLAINLY
--------------------------------------------------------
Resolving these nine does not route more of Indianapolis. It routes LESS of it.
Four of the nine are wrong routes -- census rows pointing at another building's
page -- and clearing them moves those rows out of the routable pool and into the
unroutable one, taking the URL-less count from 143 to 146. That is the market
becoming more honest rather than more covered, and it is the right direction: a
row with no URL is honestly unrouted, while a row with somebody else's URL
publishes somebody else's pet policy under this hotel's name.

Two of the nine are duplicates that dissolve on the strongest key the repo has
-- a shared telephone, and in one case a shared brand property code as well.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
SCHEMA = "ptf-founder-exception-resolution/1.0"
WORK_ORDER = "PTF-INDIANAPOLIS-PAID-OFFICIAL-URL-DISCOVERY-007"
MARKET = "indianapolis-in"

MACHINE = "MACHINE_DECIDABLE_ON_A_SANCTIONED_KEY"
JUDGEMENT = "NEEDS_A_FOUNDER_RULING"
NEEDS_EVIDENCE = "NEEDS_NEW_EVIDENCE"


def _load(name):
    return json.loads((LP / name).read_text(encoding="utf-8"))


def build() -> Dict:
    census = _load("identity_census/indianapolis-in.json")
    by_key = {h["identity_key"]: h for h in census["hotels"]}

    def row(key):
        h = by_key.get(key, {})
        return OrderedDict((("identity_key", key),
                            ("street", h.get("address", "")),
                            ("postal_code", h.get("postal_code", "")),
                            ("telephone", h.get("phone", "")),
                            ("official_url", h.get("official_url", ""))))

    E: List[Dict] = []

    E.append(OrderedDict((
        ("n", 1), ("identity_key", "fairfield inn and suites indianapolis airport"),
        ("kind", "RETIRED_ROW_WITH_SURVIVING_EVIDENCE"),
        ("proposed_ruling", "REINSTATE as VERIFIED_NO_PETS"),
        ("identity_evidence", "saved pass-1 artifact attempt-01; the page's own "
                              "FAQ reads 'No, pets are not allowed at Fairfield "
                              "by Marriott Inn & Suites Indianapolis Airport' and "
                              "the located policy block reads 'Pet Policy Pets Not "
                              "Allowed Non Refundable Cleaning Fee of $100.00 due "
                              "at check-in.'"),
        ("decidable", JUDGEMENT),
        ("why", "PROMOTION-004 retired this exclusion for lack of fresh evidence "
                "and the artifact contradicts that. The $100 cleaning fee printed "
                "beside a refusal is why the run recorded SOURCE_CONTRADICTORY, "
                "and reinstating a row the founder retired is the founder's call."),
        ("resolvable_without_spend", True),
        ("creates_a_newly_routable_property", False),
        ("creates_a_new_pet_friendly_candidate", False),
        ("rows", [row("fairfield inn and suites indianapolis airport")]),
    )))

    E.append(OrderedDict((
        ("n", 2), ("identity_key", "baymont by wyndham plainfield indianapolis airport area"),
        ("kind", "SHARED_PAGE"),
        ("proposed_ruling", "KEEP the URL on this row"),
        ("identity_evidence", "the page titles itself 'Baymont by Wyndham "
                              "Plainfield/ Indianapolis Arpt Area', which is this "
                              "row's name, and DECLARES telephone 1-317-8379000, "
                              "which is this row's census number 3178379000."),
        ("decidable", MACHINE),
        ("why", "name and declared telephone both point here. The page's street "
                "(6010 Gateway Drive) is the OTHER row's census address, so one "
                "of the two census streets is wrong -- but that is an address "
                "correction, not a routing question."),
        ("resolvable_without_spend", True),
        ("creates_a_newly_routable_property", False),
        ("creates_a_new_pet_friendly_candidate", False),
        ("rows", [row("baymont by wyndham plainfield indianapolis airport area")]),
    )))

    E.append(OrderedDict((
        ("n", 3), ("identity_key", "baymont inn and suites plainfield indianapolis airport"),
        ("kind", "WRONG_ROUTE"),
        ("proposed_ruling", "CLEAR the URL; leave the row unrouted"),
        ("identity_evidence", "it carries the same Wyndham page as row 2, and the "
                              "page names row 2 and declares row 2's telephone. "
                              "This row's own number 3172039321 appears only as "
                              "one of several the site prints."),
        ("decidable", JUDGEMENT),
        ("why", "the URL is certainly wrong for this row. Whether the row is a "
                "SECOND hotel or the same one carried under Baymont's retired "
                "brand name is not decidable here: the two rows state DIFFERENT "
                "telephones, and brand plus address may propose a match but must "
                "never decide one, or a dual-brand building loses a hotel."),
        ("resolvable_without_spend", True),
        ("creates_a_newly_routable_property", False),
        ("makes_a_row_unroutable", True),
        ("creates_a_new_pet_friendly_candidate", False),
        ("rows", [row("baymont inn and suites plainfield indianapolis airport")]),
    )))

    E.append(OrderedDict((
        ("n", 4), ("identity_key", "comfort suites indianapolis airport"),
        ("kind", "WRONG_ROUTE_AND_ABSORBED_SECOND_PROPERTY"),
        ("proposed_ruling", "CLEAR the URL; consider splitting the held candidate "
                            "back out as its own identity"),
        ("identity_evidence", "the in293 page states street '2750 Fortune Circle "
                              "West' and telephone '(317) 759-2371'. This row "
                              "holds '2181 West Southern Avenue' and 3174810700. "
                              "NOTHING physical agreed. The census's own "
                              "identity_key_collisions record for this very key "
                              "kept 2181 West Southern Avenue and held a candidate "
                              "at 2750 Fortune Circle West for review."),
        ("decidable", JUDGEMENT),
        ("why", "the page belongs to the HELD candidate, not the kept row, so the "
                "census absorbed two Comfort Suites into one key and then gave "
                "the survivor the other one's URL. Clearing the URL is mechanical; "
                "splitting an absorbed candidate back into its own census identity "
                "changes the census and is the founder's call."),
        ("resolvable_without_spend", True),
        ("creates_a_newly_routable_property", False),
        ("makes_a_row_unroutable", True),
        ("creates_a_new_pet_friendly_candidate", False),
        ("rows", [row("comfort suites indianapolis airport")]),
    )))

    E.append(OrderedDict((
        ("n", 5), ("identity_key", "residence inn indianapolis airport"),
        ("kind", "DUPLICATE_IDENTITY"),
        ("proposed_ruling", "MERGE: one property, two census rows. Keep one, "
                            "retire the other, and take 5224 from the first-party "
                            "page."),
        ("identity_evidence", "'residence inn by marriott indianapolis airport' "
                              "(5224 West Southern Avenue) and 'residence inn "
                              "indianapolis airport' (5228 West Southern Avenue) "
                              "state the SAME telephone 3172441500 and BOTH URLs "
                              "resolve to the same Marriott property code indap "
                              "-- one as marriott.com/indap and one as the legacy "
                              "marriott.com/hotels/travel/indap-... shape. The "
                              "page itself states 5224."),
        ("decidable", MACHINE),
        ("why", "this was carried as a 5224-versus-5228 address dispute. It is "
                "not: two sanctioned keys agree that these are one building, and "
                "the strongest of them is a shared telephone. Retiring a census "
                "row is still founder-visible, so the merge is proposed, not "
                "applied."),
        ("resolvable_without_spend", True),
        ("creates_a_newly_routable_property", False),
        ("creates_a_new_pet_friendly_candidate", False),
        ("rows", [row("residence inn by marriott indianapolis airport"),
                  row("residence inn indianapolis airport")]),
    )))

    E.append(OrderedDict((
        ("n", 6), ("identity_key", "towneplace suites"),
        ("kind", "UNDER_NAMED_IDENTITY"),
        ("proposed_ruling", "NO RULING AVAILABLE from saved evidence"),
        ("identity_evidence", "the census row is a bare two-word brand name at "
                              "'708 South Meridian Street' 46225 with telephone "
                              "4632097300 and the URL marriott.com/indtd. The "
                              "indtd page states '629 Russell Avenue'. The market "
                              "holds one other TownePlace, at 5802 West 71st "
                              "Street, so this is not that one."),
        ("decidable", NEEDS_EVIDENCE),
        ("why", "one of the two streets is wrong and nothing on disk says which. "
                "This row DOES state a telephone, so it is one of the few that a "
                "Places lookup could bind on the strong key -- it belongs in the "
                "Option A sample rather than in a ruling."),
        ("resolvable_without_spend", False),
        ("creates_a_newly_routable_property", False),
        ("creates_a_new_pet_friendly_candidate", False),
        ("rows", [row("towneplace suites")]),
    )))

    E.append(OrderedDict((
        ("n", 7), ("identity_key", "hampton inn indianapolis southwest plainfield"),
        ("kind", "DUPLICATE_IDENTITY"),
        ("proposed_ruling", "MERGE into 'hampton inn indianapolis sw plainfield', "
                            "which already holds the route"),
        ("identity_evidence", "both rows state telephone 3178399993. The routed "
                              "twin carries hilton.com/en/hotels/indpfhx-hampton-"
                              "indianapolis-sw-plainfield; this row carries no URL. "
                              "The streets are written differently -- '2244 East "
                              "Main Street' here, '2244 East Hadley Road' there -- "
                              "with the same house number."),
        ("decidable", MACHINE),
        ("why", "a shared telephone is the strongest binding key this repo "
                "recognises, and it is what the 006 recovery bound on. Merging "
                "removes one row from the unroutable pool without buying anything."),
        ("resolvable_without_spend", True),
        ("creates_a_newly_routable_property", False),
        ("removes_a_row_from_the_unroutable_pool", True),
        ("creates_a_new_pet_friendly_candidate", False),
        ("rows", [row("hampton inn indianapolis southwest plainfield"),
                  row("hampton inn indianapolis sw plainfield")]),
    )))

    E.append(OrderedDict((
        ("n", 8), ("identity_key", "comfort suites"),
        ("kind", "WRONG_ROUTE"),
        ("proposed_ruling", "CLEAR the URL; leave the row unrouted"),
        ("identity_evidence", "the row sits at '4125 Kildeer Drive' 46237 with "
                              "telephone 3178006346 and carries "
                              "choicehotels.com/indiana/shelbyville/"
                              "econo-lodge-hotels -- a city-search page, for a "
                              "different brand, in a different town."),
        ("decidable", MACHINE),
        ("why", "census_url_recovery.url_names_the_property refuses it outright: "
                "no distinctive word of the property's name appears in the URL. "
                "Nothing about it is this hotel."),
        ("resolvable_without_spend", True),
        ("creates_a_newly_routable_property", False),
        ("makes_a_row_unroutable", True),
        ("creates_a_new_pet_friendly_candidate", False),
        ("rows", [row("comfort suites")]),
    )))

    E.append(OrderedDict((
        ("n", 9), ("identity_key", "hyatt house indianapolis downtown"),
        ("kind", "DUAL_BRAND_BUILDING"),
        ("proposed_ruling", "the Place keeps indzi; CLEAR the House's URL and let "
                            "discovery find its own"),
        ("identity_evidence", "'hyatt house indianapolis downtown' and 'hyatt "
                              "place indianapolis downtown' both carry "
                              "hyatt.com/.../hyatt-place-indianapolis-downtown/indzi "
                              "at '130 South Pennsylvania Street' with telephone "
                              "3177629000. The page's own slug and property code "
                              "name the PLACE."),
        ("decidable", JUDGEMENT),
        ("why", "two hotels share one building and one switchboard, so address "
                "and telephone cannot separate them -- they agree for both. The "
                "slug says 'place', but the distinctive-token vocabulary treats "
                "'house' as a generic word, so no sanctioned key affirmatively "
                "says the House is mis-routed. A one-line founder ruling settles "
                "it and returns the Place to the payable cohort."),
        ("resolvable_without_spend", True),
        ("creates_a_newly_routable_property", True),
        ("makes_a_row_unroutable", True),
        ("creates_a_new_pet_friendly_candidate", False),
        ("rows", [row("hyatt house indianapolis downtown"),
                  row("hyatt place indianapolis downtown")]),
    )))

    unroutable_before = 143
    cleared = sum(1 for e in E if e.get("makes_a_row_unroutable"))
    merged_away = sum(1 for e in E if e.get("removes_a_row_from_the_unroutable_pool"))
    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("nothing_was_fetched", True), ("usd_spent", 0.0),
        ("nothing_is_decided_by_this_file",
         "Every ruling here is PROPOSED. No census row, authority row or founder "
         "decision is changed by this document."),
        ("exceptions", len(E)),
        ("by_decidability", OrderedDict(sorted(Counter(e["decidable"] for e in E).items()))),
        ("resolvable_without_spend", sum(1 for e in E if e["resolvable_without_spend"])),
        ("need_new_evidence", sum(1 for e in E if not e["resolvable_without_spend"])),
        ("newly_routable_properties", sum(1 for e in E if e["creates_a_newly_routable_property"])),
        ("new_pet_friendly_candidates", 0),
        ("effect_on_the_unroutable_pool", OrderedDict((
            ("before", unroutable_before),
            ("rows_whose_wrong_url_is_cleared", cleared),
            ("rows_merged_away", merged_away),
            ("after", unroutable_before + cleared - merged_away),
            ("note", "resolving the exceptions makes the market MORE honest and "
                     "LESS routed. A row with no URL is honestly unrouted; a row "
                     "with another building's URL publishes that building's pet "
                     "policy under this hotel's name."),
        ))),
        ("payable_effect", OrderedDict((
            ("before", 33),
            ("after_if_every_proposal_is_accepted", 34),
            ("what_changes", "only the Hyatt ruling moves the number: it returns "
                             "'hyatt place indianapolis downtown' to the cohort. "
                             "The rest clear wrong routes or dissolve duplicates, "
                             "neither of which adds a payable row."),
        ))),
        ("rulings", E),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    result = build()
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("exceptions                  %d" % result["exceptions"])
    print("by decidability             %s" % dict(result["by_decidability"]))
    print("resolvable without spend    %d" % result["resolvable_without_spend"])
    print("need new evidence           %d" % result["need_new_evidence"])
    print("newly routable              %d" % result["newly_routable_properties"])
    print("new pet-friendly candidates %d" % result["new_pet_friendly_candidates"])
    pool = result["effect_on_the_unroutable_pool"]
    print("unroutable pool  %d -> %d" % (pool["before"], pool["after"]))
    print("payable          %d -> %d" % (result["payable_effect"]["before"],
                                         result["payable_effect"]["after_if_every_proposal_is_accepted"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
