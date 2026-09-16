"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 8/11 continued:
first-party official URLs found by WebSearch identity-discovery ($0, not a
policy source) for the LOCAL_FREE_DISCOVERY cohort the acquisition-cost-plan
run (003) reported with no routable URL. One more cross-lane duplicate
caught here: "Red Roof Inn" and "Red Roof Inn & Suites Augusta South" both
resolve to the SAME official page (redroof.com/property/ga/augusta/rri450,
2176 Gordon Hwy) -- merged.

Rows with genuinely no findable first-party presence after this pass keep
LOCAL_FREE_DISCOVERY / become ROUTING_HOLD at the disposition stage -- never
guessed.

Output: identity_census_proposed/augusta-ga.json (rewritten in place)
        markets/reports/augusta_ga_url_resolution_004.json
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
OUT = os.path.join(PKG, "markets", "reports", "augusta_ga_url_resolution_004.json")

# identity_key -> (official_url, property_code_or_None)
URL_CORRECTIONS = {
    "hampton inn augusta gordon highway": ("https://www.hilton.com/en/hotels/agsghhx-hampton-augusta-gordon-highway/", "agsghhx"),
    "holiday inn express north agusta": ("https://www.ihg.com/holidayinnexpress/hotels/us/en/augusta/agsag/hoteldetail", "agsag"),
    "sheraton augusta hotel": ("https://www.marriott.com/en-us/hotels/agssi-sheraton-augusta-hotel/overview/", "agssi"),
    "fairfield inn and suites augusta washington rd i 20": ("https://www.marriott.com/en-us/hotels/agsnw-fairfield-inn-and-suites-augusta-washington-rd-i-20/overview/", "agsnw"),
    "ramada augusta downtown hotel and conference center": ("https://www.wyndhamhotels.com/ramada/augusta-georgia/ramada-augusta-conference-center/overview", None),
    "fairfield inn and suites augusta fort gordon area": ("https://www.marriott.com/en-us/hotels/agsaf-fairfield-inn-and-suites-augusta-fort-eisenhower-area/overview/", "agsaf"),
    "augusta marriott at the convention center": ("https://www.marriott.com/en-us/hotels/agsmc-augusta-marriott-at-the-convention-center/overview/", "agsmc"),
    "days inn by wyndham augusta fort gordon": ("https://www.wyndhamhotels.com/days-inn/augusta-georgia/days-inn-augusta-fort-eisenhower/overview", None),
    "comfort inn and suites": ("https://www.choicehotels.com/georgia/augusta/comfort-inn-hotels/ga800", None),
    "comfort suites augusta riverwatch": ("https://www.choicehotels.com/georgia/augusta/comfort-suites-hotels/ga579", None),
    "staybridge suites augusta": ("https://www.ihg.com/staybridge/hotels/us/en/augusta/agssb/hoteldetail", "agssb"),
    "wingate": ("https://www.wyndhamhotels.com/wingate/augusta-georgia/wingate-by-wyndham-augusta-washington-road/overview", None),
    "quality inn and suites augusta i 20": ("https://www.choicehotels.com/georgia/augusta/quality-inn-hotels/gaa72", None),
    "home2 suites by hilton augusta": ("https://www.hilton.com/en/hotels/agsawht-home2-suites-augusta-ga/", "agsawht"),
    "hyatt house augusta downtown": ("https://www.hyatt.com/hyatt-house/en-US/agsxa-hyatt-house-augusta-downtown", "agsxa"),
    "courtyard augusta": ("https://www.marriott.com/en-us/hotels/agsch-courtyard-augusta/overview/", "agsch"),
    "spark by hilton": ("https://www.hilton.com/en/hotels/agsggpe-spark-augusta/", "agsggpe"),
    "holiday inn express": ("https://www.ihg.com/holidayinnexpress/hotels/us/en/augusta/agsdt/hoteldetail", "agsdt"),
    "avid hotel": ("https://www.ihg.com/avidhotels/hotels/us/en/grovetown/agsav/hoteldetail", "agsav"),
    "econo lodge downtown": ("https://www.choicehotels.com/georgia/augusta/econo-lodge-hotels/ga584", None),
    "hyatt place augusta": ("https://www.hyatt.com/hyatt-place/en-US/agsza-hyatt-place-augusta", "agsza"),
    "candlewood suites": ("https://www.ihg.com/candlewood/hotels/us/en/augusta/agsrp/hoteldetail", "agsrp"),
    "woodspring suites": ("https://www.woodspring.com/extended-stay-hotels/locations/georgia/augusta/woodspring-suites-augusta-fort-gordon", None),
    "red roof inn and suites augusta south": ("https://www.redroof.com/property/ga/augusta/rri450", None),
}

# duplicate merges discovered this pass (dup_key -> canonical_key)
MERGE_PAIRS_004 = [
    ("red roof inn and suites augusta south", "red roof inn"),
]


def main():
    census = json.load(open(CENSUS, encoding="utf-8"), object_pairs_hook=OrderedDict)
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    applied = []
    for key, (url, code) in URL_CORRECTIONS.items():
        h = by_key.get(key)
        if h is None:
            continue
        h["official_url"] = url
        if code:
            h["property_code"] = code
        applied.append({"identity_key": key, "official_url": url, "property_code": code})

    merged = []
    for dup_key, canon_key in MERGE_PAIRS_004:
        dup = by_key.pop(dup_key, None)
        canon = by_key.get(canon_key)
        if dup is None or canon is None:
            if dup is not None:
                by_key[dup_key] = dup
            continue
        canon.setdefault("evidence", []).extend(dup.get("evidence", []))
        canon["lanes"] = sorted(set(canon.get("lanes", []) + dup.get("lanes", [])))
        canon.setdefault("aliases", [])
        if dup.get("canonical_name") not in canon["aliases"] and dup.get("canonical_name") != canon.get("canonical_name"):
            canon["aliases"].append(dup.get("canonical_name"))
        if not canon.get("official_url") and dup.get("official_url"):
            canon["official_url"] = dup["official_url"]
        merged.append({"duplicate": dup_key, "merged_into": canon_key,
                       "reason": "both resolve to the same official redroof.com property page / address"})

    hotels = list(by_key.values())
    census["hotels"] = hotels
    census["count"] = len(hotels)

    with open(CENSUS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(census, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    doc = OrderedDict([
        ("schema", "ptf-url-resolution/1.0"), ("work_order", WORK_ORDER), ("market_id", "augusta-ga"),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("source", "WebSearch identity-discovery lookups; no policy source used"),
        ("urls_applied", applied), ("merges_applied", merged), ("final_count", len(hotels)),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("applied", len(applied), "merged", len(merged), "final_count", len(hotels))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
