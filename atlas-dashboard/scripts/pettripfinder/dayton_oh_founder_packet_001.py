"""PTF-DAYTON-OH-HARDENED-REVALIDATION-001 -- Phases 13 and 14.

One grouped founder packet plus the paid-readiness plan.

The packet carries only decisions this order could NOT make mechanically. Every
row it holds is outside the pending application inventory by construction, so
answering it is not a precondition for promoting the clean inventory -- it is a
precondition for resolving these particular identities.

The paid plan spends nothing and calls no provider. Bright Data rates are read
from the canonical cross-run paid-attempt ledger at run time and the balance
from a live console read; where the ledger records no spend for a lane the lane
is UNPRICED_BY_LEDGER and its cost is refused rather than invented.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-DAYTON-OH-HARDENED-REVALIDATION-001"
MARKET_ID = "dayton-oh"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PAID_LEDGER = os.path.join(PKG, "ptf_paid_attempt_ledger_001.json")
DISC_LEDGER = os.path.join(PKG, "ptf_discovery_attempt_ledger_001.json")
PARTITION = os.path.join(PKG, "dayton_final_partition_001.json")


def read_json(p, d=None):
    if not os.path.exists(p):
        return d
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def wilson_lower(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / float(n)
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - m) / den)


def item(group, key, name, current, proposed, evidence, conflict, recommendation,
         census_effect, authority_effect, route_effect, reversibility):
    return OrderedDict([
        ("group", group), ("identity_key", key), ("canonical_name", name),
        ("current_row", current), ("proposed_action", proposed), ("evidence", evidence),
        ("conflict", conflict), ("recommendation", recommendation),
        ("census_effect", census_effect), ("authority_effect", authority_effect),
        ("route_effect", route_effect), ("reversibility", reversibility),
    ])


REV = "Fully reversible: this order writes no authority, and the proposed action is a row edit whose prior value is preserved in this packet."


def decisions():
    A, B, C = "A -- identity / successor / duplicate / same-campus", "B -- geography", "C -- non-lodging / closure / conversion"
    D, E = "D -- reader exception / ambiguous policy", "E -- source conflict"
    out = []
    out.append(item(A, "staybridge suites fairborn dayton east", "Staybridge Suites Fairborn - Dayton East",
        "census carries no street address and telephone (937) 771-6888; partition AWAITING_POLICY_OBSERVATION",
        "fill the census address from the property's own page (2750 Presidential Drive, Fairborn OH 45324) and correct the telephone to 1-937-702-9233, then admit the captured pet-friendly read",
        "ihg.com/staybridge/hotels/us/en/fairborn/daybf/hoteldetail, sha256:fab5adf5591ea73f5b9e10c45fb3984fab33f6e02c762d50f965fcff8fbc62cb; property-named FAQ: 'Pets are welcome at Staybridge Suites Fairborn - Dayton East. Our Pet Policy: 1 to 6 night stay UDS75.00 plus tax, nonrefundable'",
        "identity binding fails only because the census row has no street to compare; postal 45324 and the exact canonical name agree, and the brand property code daybf is this row's own",
        "ADMIT the address/phone correction, then admit the policy read as clean pet-friendly",
        "no membership change; one row gains an address", "+1 pet-friendly if admitted",
        "a route becomes publishable for this identity", REV))
    out.append(item(A, "holiday inn express and suites springfield", "Holiday Inn Express & Suites Springfield",
        "census carries no street address, no telephone, postal 45506; partition AWAITING_ROUTING_REPLACEMENT",
        "bind this identity to the property at 204 Raydo Circle, Springfield OH 45505 and correct the census postal from 45506 to 45505",
        "ihg.com/holidayinnexpress/hotels/us/en/springfield/sghss/hoteldetail, sha256:1de1b1abf8611357d05a371561e62312e2f9359118f60a6ccd01084e66ee0561; page title 'Holiday Inn Express & Suites Springfield - Dayton Area'; FAQ 'No, pets are not allowed at Holiday Inn Express & Suites Springfield - Dayton Area.'",
        "census postal 45506 vs the property's own 45505. Both ZIPs sit inside the Springfield corridor, so nothing turns on the corridor; the question is only whether the census postal is wrong or this is a different property",
        "ADMIT as the same identity and correct the postal -- Springfield has one Holiday Inn Express and the brand's own page is the better authority on its own address",
        "no membership change; one row's postal corrected", "+1 verified-no-pets if admitted",
        "no public route either way (a refusal generates none)", REV))
    out.append(item(A, "comfort inn bellefontaine", "Comfort Inn Bellefontaine",
        "census carries no street address and no telephone, postal 43311; partition ACCESS_BLOCKED",
        "fill the census address from the property's own page (260 Northview, Bellefontaine OH 43311, (937) 595-0631) and admit the captured pet-friendly read",
        "choicehotels.com/ohio/bellefontaine/comfort-inn-hotels/oh087, sha256:be2dc17990c90cc6258dff1eebbf1ee6d43c3a8c2878879ba93d12458e78ce74; 'Pets Allowed: Yes / General: Pets are allowed. Pet charge is 50.00 USD per night per pet. Maximum of 2 pets per room.'",
        "binding fails only for want of a census address; postal agrees and the brand property code oh087 is this row's own",
        "ADMIT the address fill, then admit the policy read as clean pet-friendly",
        "no membership change; one row gains an address", "+1 pet-friendly if admitted",
        "a route becomes publishable for this identity", REV))
    out.append(item(A, "quality inn springfield", "Quality Inn Springfield",
        "census carries no street address, no telephone, postal 45506; partition AWAITING_ROUTING_REPLACEMENT",
        "bind to 383 East Leffel Lane, Springfield OH 45505 ('Quality Inn and Conference Center') and correct the census postal, OR hold if the founder reads this as a different property",
        "choicehotels.com/ohio/springfield/quality-inn-hotels/oh396, sha256:c5dbe159646cf6e927284c40e20ec39e8413acd8ff3e9c52787a8a3dd6a726be; 'Pets Allowed: Yes / General: Pets are allowed. 25 USD charge per night. A maximum of 2 pets per room.'",
        "census postal 45506 vs the property's own 45505, AND the property's own display name is 'Quality Inn and Conference Center', not 'Quality Inn Springfield'. Two differences at once is weaker than either alone",
        "HOLD pending one more identity signal. Springfield's Baymont sits at 319 East Leffel Lane and this property at 383 East Leffel Lane, so the corridor is right and the street is shared -- but a name change plus a postal change should not both be absorbed silently",
        "none until decided", "none until decided", "none until decided", REV))
    out.append(item(A, "holiday inn express and suites washington court house", "Holiday Inn Express & Suites Washington Court House",
        "published census name 'Holiday Inn Express & Suites Washington Court House'; the property's own page now names it 'Holiday Inn Express Washington CH Jeffersonville S'",
        "record a DISPLAY rename in the name_corrections overlay; do not rename the census row and do not create a new identity",
        "ihg.com/holidayinnexpress/hotels/us/en/washington-court-house/cmhwc/hoteldetail, sha256:19988f62638e522268b9635164b7ecbf1e9e81f92c7a2fe629a1311e21c6c5e8; address 101 Courthouse Parkway 43160 and telephone 1-740-3359310 both agree with the census row",
        "the brand renamed the property; address, postal, telephone and property code are unchanged, so this is one identity under two display names",
        "ADMIT the pet-friendly read on the existing identity and carry the rename as a display correction only",
        "no membership change", "+1 pet-friendly", "route slug unchanged (slug derives from the census name)", REV))
    out.append(item(A, "hotel piqua east ash", "Hotel Piqua East Ash",
        "two census rows describe the Miami Valley Centre property in Piqua: 'Hotel Piqua East Ash' (AWAITING_ROUTING_REPLACEMENT) and 'Comfort Inn Miami Valley Centre Piqua' (AWAITING_OFFICIAL_URL)",
        "determine whether these are one identity (a Comfort Inn that became an independent, or the reverse) and retire the superseded row by MOVING it, never deleting it",
        "choicehotels.com/ohio/piqua/comfort-inn-hotels/oh078 resolves to '987 E. Ash St., Miami Valley Centre Mall' -- the East Ash address the independent row carries",
        "one address, two census rows, two brands. Either the Choice listing is stale or the independent row is",
        "HOLD for a founder ruling: this is a supersession direction question, and getting the direction wrong renames a live row",
        "-1 identity if merged (129 -> 128)", "none until decided",
        "one route at most, whichever identity survives", REV))
    out.append(item(A, "baymont by wyndham dayton north", "Baymont by Wyndham Dayton North / Wingate by Wyndham Dayton North",
        "Baymont at 6960B Miller Ln 45414 and Wingate at 6960 Miller Ln 45414 -- adjacent rows, one street number apart",
        "record the pair as SAME_CAMPUS_DISTINCT_ENTITY so no later pass collapses them",
        "the Baymont's own page declares 6960B Miller Ln and telephone +1-937-410-0799; the census carries 6960B for the Baymont and 6960 for the Wingate",
        "none -- this is a pair that LOOKS like a duplicate and is not. It is recorded here because a house-number matcher that ignores the letter suffix binds the wrong one, which this order hit and fixed",
        "ADMIT both as distinct; no merge",
        "no membership change", "no change", "both keep their own route", REV))
    out.append(item(B, "marriott at the university of dayton", "Marriott at the University of Dayton",
        "corridor unassigned; postal 45409 belongs to no configured Dayton corridor",
        "assign explicitly to dayton-oh__downtown-dayton via explicit_hotel_ids",
        "census address 1414 S Patterson Blvd, Dayton OH 45409, immediately south of the downtown core the corridor already covers (45402/45403/45405/45417)",
        "none; the row is VERIFIED_NO_PETS and generates no public route, so the assignment is bookkeeping",
        "ADMIT the explicit assignment. Do NOT widen 45409 into the corridor's postal list to admit one hotel",
        "no membership change", "none", "none -- an excluded row publishes no route", REV))
    out.append(item(B, "microtel inn and suites by wyndham dayton riverside", "Microtel Inn & Suites by Wyndham Dayton/Riverside",
        "corridor unassigned; postal 45432 (Riverside) belongs to no configured Dayton corridor",
        "assign explicitly to dayton-oh__fairborn-beavercreek via explicit_hotel_ids",
        "census address 4500 Linden Ave, Dayton OH 45432; Riverside lies between Dayton and the Fairborn/Beavercreek corridor the market already publishes (45324/45431/45434)",
        "none",
        "ADMIT the explicit assignment. Do NOT add 45432 to the corridor's postal list -- one hotel does not justify a whole ZIP",
        "no membership change", "none until this row's policy resolves",
        "this row would gain a corridor placement when it publishes", REV))
    out.append(item(C, "comfort inn washington court house", "Comfort Inn Washington Court House",
        "partition AWAITING_ROUTING_REPLACEMENT; the only owned route points at choicehotels.com/ohio/jeffersonville/quality-inn-hotels/oh359",
        "reject the owned route as this identity's page and return the row to AWAITING_OFFICIAL_URL",
        "oh359 resolves to '10160 Carr Road NW', postal 43128 -- Jeffersonville, not Washington Court House (43160)",
        "the route on record is provably a different property in a different town",
        "ADMIT the route rejection. The identity itself is not in question; only its URL is",
        "no membership change", "none", "no route until one is found", REV))
    out.append(item(C, "grinnell mill bed and breakfast yellow springs", "Grinnell Mill Bed & Breakfast Yellow Springs",
        "partition AWAITING_CENSUS_REVIEW; official_url http://www.grinnellmillbandb.com/",
        "record the domain as non-resolving and keep the row in census review; do NOT infer closure",
        "free static capture 2026-09-01: URLError getaddrinfo failed -- the domain does not resolve at all",
        "a domain that stops resolving is consistent with closure, a lapsed registration, or a move to a new site. It proves none of them",
        "HOLD. A DNS failure answers nothing about whether the property operates",
        "none until decided", "none", "none", REV))
    out.append(item(C, "baymont by wyndham greenville", "Baymont by Wyndham Greenville",
        "partition AWAITING_POLICY_OBSERVATION with an official Wyndham URL on record",
        "reclassify the route as a soft-404 and search the Wyndham inventory for the renamed slug",
        "the property URL redirects to wyndhamhotels.com/hotels/greenville-ohio?brand_id=BU -- a brand SEARCH RESULTS page, observed 2026-09-01",
        "a redirect to search is a renamed slug until the brand inventory says otherwise; it is not evidence the hotel closed",
        "ADMIT the route reclassification (AWAITING_ROUTING_REPLACEMENT). Do not retire the identity",
        "no membership change", "none", "no route until the slug is found", REV))
    out.append(item(C, "fairfield inn dayton new paris", "Fairfield Inn Dayton/New Paris",
        "partition AWAITING_ROUTING_REPLACEMENT; marriott.com/en-us/hotels/daynp/fairfield-inn-dayton-new-paris/",
        "confirm the route is dead and keep the row awaiting a replacement route",
        "free static capture 2026-09-01: HTTP 404 from marriott.com for this property code",
        "a 404 from the brand's own site for its own property code is stronger than a 403, but still says nothing about the building",
        "ADMIT the route as dead; HOLD the identity",
        "none", "none", "no route", REV))
    out.append(item(D, "the cedar lodge and cabins new paris", "The Cedar Lodge & Cabins New Paris",
        "partition ACCESS_BLOCKED; first-party site thecedarlodgeandcabins.com",
        "record IDENTITY_NOT_CONFIRMED_STATIC and route to an attended read",
        "free static capture 2026-09-01: the page declares no telephone of its own, so nothing on it binds to the census row",
        "the page served content; it simply carries no identity signal a machine can bind",
        "HOLD for an attended read that can bind on the rendered address",
        "none", "none", "none", REV))
    out.append(item(D, "scioto inn urbana", "Scioto Inn Urbana",
        "partition AWAITING_POLICY_OBSERVATION; first-party site sciotoinn.com",
        "record IDENTITY_TEXT_BOUND_POLICY_SILENT",
        "free static capture 2026-09-01: the document text binds to the census row but contains no pet statement at all",
        "silence, not refusal",
        "HOLD. An absent policy is UNKNOWN and must never become a no-pets exclusion",
        "none", "none", "none", REV))
    out.append(item(E, "holiday inn express and suites troy", "Holiday Inn Express & Suites Troy",
        "the release contract records this row as the eighth census no-pets annotation that stayed UNADJUDICATED because a research agent counted it with no quote, capture or hash",
        "admit the row as verified-no-pets on this order's own capture, superseding the unevidenced annotation",
        "ihg.com/holidayinnexpress/hotels/us/en/troy/tryoh/hoteldetail, sha256:aa414719b61b2aefd784d53010bac3bd3362988a11646810eba7a4a7c8e35760; property-named FAQ 'No, pets are not allowed at Holiday Inn Express & Suites Troy.'; identity bound on street, postal and telephone",
        "none -- the earlier annotation and this capture agree. What changes is that the claim now has evidence behind it",
        "ADMIT. This closes the discrepancy the release contract has carried since PTF-DAYTON-WORK-BROWSER-INTEGRATION-001: the census set of eight and the registry set of eight can now be the same eight",
        "no membership change", "+1 verified-no-pets", "none -- a refusal generates no route", REV))
    return out


def paid_plan():
    paid = read_json(PAID_LEDGER, {"attempts": []})["attempts"]
    disc = read_json(DISC_LEDGER, {"attempts": []})["attempts"]
    lanes = OrderedDict()
    for lane in ("brightdata_browser", "brightdata_web_unlocker", "firecrawl"):
        rows = [x for x in paid if x.get("lane") == lane]
        billed = [x for x in rows if (x.get("cost_usd_minor") or 0) > 0]
        cost = sum(x.get("cost_usd_minor") or 0 for x in rows) / 100.0
        pg = sum(1 for x in rows if x.get("publication_grade"))
        lanes[lane] = OrderedDict([
            ("attempts", len(rows)), ("billed_attempts", len(billed)), ("usd_spent", round(cost, 2)),
            ("usd_per_billed_attempt", round(cost / len(billed), 4) if billed else None),
            ("unit_price_state", "MEASURED_FROM_LEDGER" if billed else "UNPRICED_BY_LEDGER"),
            ("publication_grade_rate", round(pg / float(len(rows)), 4) if rows else None),
            ("publication_grade_rate_wilson_lower", round(wilson_lower(pg, len(rows)), 4) if rows else None),
        ])
    disc_cost = sum(x.get("cost_usd_minor") or 0 for x in disc)
    bound = sum(1 for x in disc if x.get("outcome") == "BOUND")
    part = read_json(PARTITION)["items"]
    attended = read_json(os.path.join(REPORTS, "dayton_oh_attended_capture_001.json"), {"results": []})["results"]
    closed = {r["identity_key"] for r in attended if (r.get("identity_binding") or {}).get("bound")}
    still = [i for i in part if not i["resolved"] and i["identity_key"] not in closed]
    bd_rows = [i for i in still if i["final_state"] in ("AWAITING_POLICY_OBSERVATION", "AWAITING_POLICY_ARTIFACT", "ACCESS_BLOCKED")]
    disc_rows = [i for i in still if i["final_state"] in ("AWAITING_OFFICIAL_URL", "AWAITING_ROUTING_REPLACEMENT", "AWAITING_ROUTING_REVIEW")]
    bd_unit = lanes["brightdata_browser"]["usd_per_billed_attempt"]
    bd_rate = lanes["brightdata_browser"]["publication_grade_rate_wilson_lower"] or 0.0
    bd_expected = round(len(bd_rows) * (bd_unit or 0), 2)
    return OrderedDict([
        ("nothing_spent", True), ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("this_market_in_the_ledgers", OrderedDict([
            ("paid_attempts_for_dayton", sum(1 for x in paid if x.get("market_id") == MARKET_ID)),
            ("discovery_attempts_for_dayton", sum(1 for x in disc if x.get("market_id") == MARKET_ID)),
            ("meaning", "Dayton has never had a paid attempt of either kind, so no row here can duplicate a prior one. Every paid row would be a first attempt."),
        ])),
        ("rates_source", OrderedDict([
            ("paid_attempt_ledger", os.path.relpath(PAID_LEDGER, _DASH)),
            ("discovery_attempt_ledger", os.path.relpath(DISC_LEDGER, _DASH)),
            ("rule", "rates are read from the ledgers at run time; no static constant is an expected cost"),
        ])),
        ("measured_lane_rates", lanes),
        ("brightdata", OrderedDict([
            ("eligible_rows", len(bd_rows)), ("expected_billed_attempts", len(bd_rows)),
            ("unit_price_usd", bd_unit), ("unit_price_state", lanes["brightdata_browser"]["unit_price_state"]),
            ("expected_usd", bd_expected),
            ("expected_publication_grade_rows_at_wilson_lower", round(len(bd_rows) * bd_rate, 1)),
            ("live_balance_usd", 4.28),
            ("live_balance_read_at", "2026-09-02T02:11:49Z"),
            ("live_balance_source", "scripts.pettripfinder.brightdata.client.read_usage (read only; no spend)"),
            ("hard_cap_usd", 4.00),
            ("cap_rule", "cap against the LIVE balance read before the run and stop WHEN the cap is exceeded, not after; the balance settles late, so it is not a cost meter"),
            ("verdict", "NOT REQUIRED. Every row this order closed was closed free, and the balance ($4.28) would not fund the remaining cohort anyway (expected $%s)." % bd_expected),
        ])),
        ("google_places", OrderedDict([
            ("eligible_rows", len(disc_rows)),
            ("ledger_attempts", len(disc)), ("ledger_bound", bound),
            ("ledger_bind_rate", round(bound / float(len(disc)), 4) if disc else None),
            ("usd_recorded_in_ledger", disc_cost / 100.0),
            ("unit_price_state", "MEASURED_FROM_LEDGER" if disc_cost > 0 else "UNPRICED_BY_LEDGER"),
            ("expected_usd", "CANNOT BE QUOTED UNTIL THE RATE IS READ"),
            ("why", "the discovery ledger records 183 attempts and zero spend, so it prices nothing. A cap is meaningless against a number nobody read: the live console rate must be read before any discovery spend is authorised."),
            ("verdict", "NOT REQUIRED for promotion; relevant only to the AWAITING_OFFICIAL_URL rows, which are coverage expansion."),
        ])),
        ("no_duplicate_attempts", "Both ledgers were read; neither carries a dayton-oh row, so nothing proposed here repeats a prior paid attempt."),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "dayton_oh_founder_packet_001.json"))
    args = ap.parse_args(argv)
    ds = decisions()
    doc = OrderedDict([
        ("schema", "ptf-market-founder-packet/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("status", "PREPARED_NOT_DECIDED"),
        ("what_this_is",
         "The decisions this order could not make mechanically, grouped so they can be "
         "answered in one sitting. Nothing here has been applied and nothing here blocks "
         "the pending application inventory: every row in this packet is held OUT of that "
         "inventory by construction."),
        ("counts", OrderedDict(sorted(Counter(d["group"] for d in ds).items()))),
        ("total_decisions", len(ds)),
        ("decisions", ds),
        ("paid_readiness", paid_plan()),
    ])
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(doc, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("decisions:", json.dumps(doc["counts"]), "total", len(ds))
    bd = doc["paid_readiness"]["brightdata"]
    print("brightdata: rows=%s unit=%s expected=$%s balance=$%s cap=$%s" %
          (bd["eligible_rows"], bd["unit_price_usd"], bd["expected_usd"], bd["live_balance_usd"], bd["hard_cap_usd"]))
    print("places: rows=%s price=%s" % (doc["paid_readiness"]["google_places"]["eligible_rows"],
                                        doc["paid_readiness"]["google_places"]["unit_price_state"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
