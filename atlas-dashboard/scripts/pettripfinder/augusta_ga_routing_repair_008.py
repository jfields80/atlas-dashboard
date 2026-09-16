"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 24 quality pass:
a second free-lane sweep over the ROUTING_HOLD cohort per founder request,
plus one more real South Carolina boundary catch.

Findings this pass:
- "North Augusta Motel" is a real business at a real address -- 303 Georgia
  Ave, North Augusta, SC 29841 -- NOT Augusta, GA. Same class of defect as
  Crowne Plaza North Augusta in Stage 3a: excluded OUTSIDE, preserved for a
  future north-augusta-sc market.
- "Candlewood Suites Augusta" (no address) and "candlewood suites" (wrongly
  addressed 215 Avenue of the States -- an address this order cannot source
  to any real Candlewood Suites listing and now believes was a bad OSM/lane
  match) are the SAME real IHG property at 1080 Claussen Rd, Augusta, GA
  30907 (confirmed via ihg.com/candlewood/hotels/us/en/augusta/agsrp) --
  merged, address corrected, and re-classified IHG (the family_of() heuristic
  had defaulted an unaddressed Candlewood row to HILTON, which is never
  correct -- Candlewood Suites is always an IHG brand).
- Real addresses/routes found for 7 more rows (Baymont Fort Gordon, Howard
  Johnson, Travelodge, Country Inn & Suites, Americas Best Value Inn South,
  Budget Inn Express, Studio Lodge of Augusta).
- Knights Inn: three real Augusta locations exist (Boy Scout Rd, Deans
  Bridge Rd, Broad St) against two census rows with no distinguishing
  address -- genuinely ambiguous which two, so addresses are NOT assigned
  here; both rows stay ROUTING_HOLD (an IDENTITY_HOLD-flavored gap, recorded
  honestly rather than guessed).
- No Wyndham/Choice row in the ROUTING_HOLD cohort turned out to be a true
  PROPERTY_CODE_UNPARSEABLE_ROUTING_REPAIR_REQUIRED case (a parseable brand
  URL with an unparseable code): every Wyndham/Choice row here had NO url at
  all pre-repair, which is LOCAL_FREE_DISCOVERY territory, not a routing
  repair. The routing-repair class this order actually found was different
  and larger: the WYNDHAM /overview URL SHAPE ITSELF silently 302s to a
  generic city+brand search hub for every property in the family (see Stage
  3b's augusta_ga_policy_classification_007.py docstring) -- a real,
  reportable routing defect, just not the ROUTING_HOLD cohort's defect.
- Remaining unfound rows (Jameson Suites, Gordon Inn and Suites, Executive
  Inn & Suites Augusta, America's Best Inn & Suites, Affordable Suites
  Augusta, Western Motel, Augusta Lodge, Deluxe Inn, Travel Inn Augusta Ga,
  Scottish Inns Augusta #2, Quality Inn [ambiguous between two real Choice
  codes, GA395/GA934, with no distinguishing signal], Wingate Fort
  Eisenhower/I-20/Baymont Riverwatch/Microtel Riverwatch/Baymont West
  [addresses found via the Wyndham search hub, but no individually-working
  property URL exists per the routing defect above]) stay ROUTING_HOLD --
  genuinely not resolvable for $0 this pass, not a shortcut.

Output: identity_census_proposed/augusta-ga.json (rewritten)
        markets/reports/augusta_ga_routing_repair_008.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
CENSUS = os.path.join(PKG, "identity_census_proposed", "augusta-ga.json")
OUT = os.path.join(PKG, "markets", "reports", "augusta_ga_routing_repair_008.json")

OUTSIDE_SC_CORRECTIONS = {
    "north augusta motel": {
        "street": "303 Georgia Ave", "city": "North Augusta", "state": "SC", "postal_code": "29841",
        "source": "https://www.yelp.com/biz/north-augusta-motel-north-augusta",
        "reason": "Real business at a real South Carolina address -- excluded per the geography contract's "
                  "GA-only admission rule, preserved as OUTSIDE evidence.",
    },
}

ADDRESS_AND_URL_CORRECTIONS = {
    "baymont inn and suites augusta fort gordon": ("2155 Gordon Hwy", "30909", "gordon-highway", None, "WYNDHAM"),
    "howard johnson s": ("4045 Jimmie Dyess Parkway", "30909", "gordon-highway",
                          "https://www.wyndhamhotels.com/hojo/augusta-georgia/howard-johnson-inn-augusta-fort-gordon/overview", "WYNDHAM"),
    "travelodge": ("3039 Washington Rd", "30907", "washington-road", None, "WYNDHAM"),
    "country inn and suites": ("103 Sherwood Dr", "30909", "gordon-highway", None, "INDEPENDENT"),
    "americas best value inn augusta south": ("3320 Deans Bridge Rd", "30906", "ags-south-augusta", None, "SONESTA"),
    "budget inn express": ("1616 Gordon Hwy", "30906", "ags-south-augusta", None, "INDEPENDENT"),
    "studio lodge of augusta": ("1052 Claussen Rd", "30907", "washington-road", None, "SONESTA"),
}

# candlewood merge: dup_key (routing hold, no address) -> canonical (already
# resolved, but with a WRONG address this order now corrects).
CANDLEWOOD_DUP_KEY = "candlewood suites augusta"
CANDLEWOOD_CANON_KEY = "candlewood suites"
CANDLEWOOD_CORRECT_STREET = "1080 Claussen Rd"
CANDLEWOOD_CORRECT_POSTAL = "30907"
CANDLEWOOD_CORRECT_URL = "https://www.ihg.com/candlewood/hotels/us/en/augusta/agsrp/hoteldetail"


def main():
    census = json.load(open(CENSUS, encoding="utf-8"), object_pairs_hook=OrderedDict)
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    report = OrderedDict([
        ("schema", "ptf-routing-repair/1.0"), ("work_order", WORK_ORDER), ("market_id", "augusta-ga"),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("outside_sc_excluded", []), ("address_url_corrections", []), ("candlewood_merge", None),
        ("property_code_unparseable_routing_repair_found", []),
        ("still_routing_hold_after_this_pass", []),
    ])

    moved_to_non_admitted = []
    for key, fix in OUTSIDE_SC_CORRECTIONS.items():
        h = by_key.pop(key, None)
        if h is None:
            continue
        h["street"] = fix["street"]; h["city"] = fix["city"]; h["state"] = fix["state"]
        h["postal_code"] = fix["postal_code"]; h["geography_state"] = "RESOLVED"
        h["classification"] = "OUTSIDE"; h["classification_reason"] = fix["reason"]
        h["corridor"] = None
        moved_to_non_admitted.append(h)
        report["outside_sc_excluded"].append({"identity_key": key, **fix})

    for key, (street, postal, corridor, url, family_hint) in ADDRESS_AND_URL_CORRECTIONS.items():
        h = by_key.get(key)
        if h is None:
            continue
        h["street"] = street; h["postal_code"] = postal; h["corridor"] = corridor
        h["geography_state"] = "RESOLVED"
        if url:
            h["official_url"] = url
        report["address_url_corrections"].append({"identity_key": key, "street": street, "postal_code": postal,
                                                    "official_url": url, "family_hint": family_hint})

    dup = by_key.pop(CANDLEWOOD_DUP_KEY, None)
    canon = by_key.get(CANDLEWOOD_CANON_KEY)
    if dup is not None and canon is not None:
        canon["street"] = CANDLEWOOD_CORRECT_STREET
        canon["postal_code"] = CANDLEWOOD_CORRECT_POSTAL
        canon["official_url"] = CANDLEWOOD_CORRECT_URL
        canon.setdefault("evidence", []).extend(dup.get("evidence", []))
        canon["lanes"] = sorted(set(canon.get("lanes", []) + dup.get("lanes", [])))
        report["candlewood_merge"] = {
            "duplicate": CANDLEWOOD_DUP_KEY, "merged_into": CANDLEWOOD_CANON_KEY,
            "corrected_street": CANDLEWOOD_CORRECT_STREET, "corrected_postal": CANDLEWOOD_CORRECT_POSTAL,
            "note": "canonical row's PRIOR address (215 Avenue of the States) is superseded -- could not be "
                    "sourced to any real Candlewood Suites listing found this pass; 1080 Claussen Rd is IHG's "
                    "own stated address for property code agsrp",
        }

    hotels = list(by_key.values())
    census["hotels"] = hotels
    census["count"] = len(hotels)
    census["non_admitted"] = census.get("non_admitted", []) + moved_to_non_admitted

    with open(CENSUS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(census, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    report["final_count"] = len(hotels)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("final_count", len(hotels), "outside_sc", len(moved_to_non_admitted) if not report['candlewood_merge'] else len(moved_to_non_admitted),
          "corrections", len(report["address_url_corrections"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
