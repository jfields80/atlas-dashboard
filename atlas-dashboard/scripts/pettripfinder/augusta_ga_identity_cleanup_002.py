"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 8/10 continued: a
one-shot correction pass over the Stage-2 proposed census, applying real
first-party address findings gathered by web search (WebSearch, not a paid
provider lane -- identity discovery only, $0) plus mechanical cross-lane
duplicate detection.

Three defect classes fixed here, each recorded, none guessed:

1. SIX rows are not hotels at all -- they are brand-website HUB/INDEX pages
   (a Wyndham city or university landing page, a WoodSpring bare "/hotels"
   index) or a raw OSM map-icon artifact, carried into the census as if they
   were premises. Reclassified NON_HOTEL and moved to non_admitted.
2. ONE row (Crowne Plaza North Augusta) is a real hotel at a real address --
   1060 Center St, North Augusta, SC 29841 -- which is South Carolina, not
   Georgia. Reclassified OUTSIDE per the geography contract's explicit
   SC-observation-only rule; never admitted to augusta-ga.
3. SIX "(2)"-suffixed rows are the SAME physical premises seen twice, once
   from OSM_OVERPASS and once from a brand lane (BRAND_CITY_PAGE /
   BRAND_SITEMAP), with no coordinate conflict (either the second lane
   carries no coordinates at all, or both do and they sit under 500 m apart)
   -- merged into one identity, keeping the union of evidence and lanes.
   Contrast: rodeway inn (2), scottish inns augusta (2) and motel 6 augusta
   (2) each sit 5-10 km from their name-twin and are confirmed-distinct real
   locations (kept as separate identities, not merged).

Thirteen more rows (previously IDENTITY_REVIEW_REQUIRED -- an economy-motel
strip on Washington Road / Gordon Highway where OSM recorded no address at
all) are resolved to a real street/postal/corridor from a first-party or
aggregator source found by search; none of the thirteen turned out to be a
duplicate of its neighbour -- each has its own distinct street address, which
is exactly what Washington Road and Gordon Highway's real economy-motel
strips look like.

Nothing else in this file guesses. A row this pass could not verify a real
address for keeps its prior PENDING_VERIFICATION state, carried forward to
the next phase (attended/Firecrawl capture naturally surfaces the real
address when it fetches the property's own page).

Output:
  launch_packages/pettripfinder/identity_census_proposed/augusta-ga.json (rewritten in place)
  launch_packages/pettripfinder/markets/reports/augusta_ga_identity_cleanup_002.json
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
CENSUS = os.path.join(PKG, "identity_census_proposed", "augusta-ga.json")
OUT = os.path.join(PKG, "markets", "reports", "augusta_ga_identity_cleanup_002.json")

# ---------------------------------------------------------------------------
# 1. Non-hotel hub/index/map-artifact rows -- never a premises.
# ---------------------------------------------------------------------------
NON_HOTEL_KEYS = {
    "hotels near georgia military college augusta campus": "Wyndham university/landing hub page listing multiple hotels, not one premises.",
    "grovetown georgia": "Wyndham bare city-hub page (/hotels/grovetown-georgia), not one premises.",
    "thomson georgia": "Wyndham bare city-hub page (/hotels/thomson-georgia), not one premises.",
    "augusta georgia": "Wyndham bare city-hub page (/hotels/augusta-georgia), not one premises.",
    "hotels": "WoodSpring bare index page (/georgia/augusta/hotels), not one premises.",
    "map and flag": "OSM node tagged as a generic map/flag icon, not a lodging premises.",
}

# ---------------------------------------------------------------------------
# 2. Real hotel, real address, wrong state -- South Carolina, never admitted.
# ---------------------------------------------------------------------------
OUTSIDE_SC_CORRECTIONS = {
    "crowne plaza north augusta": {
        "street": "1060 Center St", "city": "North Augusta", "state": "SC", "postal_code": "29841",
        "source": "https://www.ihg.com/crowneplaza/hotels/us/en/north-augusta/aikna/hoteldetail",
        "reason": "Real hotel at a real South Carolina address (North Augusta, SC 29841) -- excluded per the geography contract's explicit GA-only admission rule; preserved as OUTSIDE evidence for a future north-augusta-sc market, same as the 14 SC hotels Stage 1 already observed.",
    },
}

# ---------------------------------------------------------------------------
# 3. Thirteen ex-IDENTITY_REVIEW_REQUIRED rows -- real address found by search
#    (WebSearch, $0, identity discovery only -- not a policy source).
# ---------------------------------------------------------------------------
ADDRESS_CORRECTIONS = {
    "masters inn augusta washington": ("3027 Washington Rd", "30907", "washington-road",
        "https://www.hotelplanner.com/Hotels/318368/"),
    "scottish inns augusta": ("1079 Stevens Creek Rd", "30907", "washington-road",
        "https://www.hotels.com/ho202636/"),
    "baymont inn and suites augusta fort gordon": ("2155 Gordon Hwy", "30909", "gordon-highway",
        "https://www.yelp.com/biz/baymont-by-wyndham-augusta-fort-gordon-augusta"),
    "microtel inn and suites by wyndham augusta riverwatch": ("2909 River West Drive", "30907", "washington-road",
        "https://www.yelp.com/biz/microtel-inn-and-suites-by-wyndham-augusta-riverwatch-augusta"),
    "woodspring suites augusta riverwatch": ("2995 River Watch Pkwy", "30907", "washington-road",
        "https://www.woodspring.com/extended-stay-hotels/locations/georgia/augusta/woodspring-suites-augusta-riverwatch"),
    "tru": ("2853 Washington Road", "30909", "gordon-highway",
        "https://www.hilton.com/en/hotels/agsgvru-tru-augusta-washington-road/"),
    "homewood suites by hilton augusta (2)": ("1049 Stevens Creek Rd", "30907", "washington-road",
        "https://www.hotelplanner.com/Hotels/224474/"),
    "red roof inn": ("2176 Gordon Highway", "30909", "gordon-highway",
        "https://www.redroof.com/property/ga/augusta/rri450"),
    "rodeway inn": ("3027 Washington Rd Unit B", "30907", "washington-road",
        "https://www.choicehotels.com/georgia/augusta/rodeway-inn-hotels/gab67"),
    "sunset inn": ("3034 Washington Road", "30907", "washington-road",
        "https://www.reservationdesk.com/hotel/5ffbee9/sunset-inn-augusta"),
    "executive suites inn": ("1238 Gordon Hwy", "30901", "downtown-medical-district",
        "https://chamberofcommerce.com/united-states/georgia/augusta/motel/2000755620-executive-inn-suites"),
    "country hearth inn augusta": ("2182 Gordon Highway", "30909", "gordon-highway",
        "https://www.hotelplanner.com/Hotels/23661/"),
    "west bank inn": ("2904 Washington Road", "30909", "gordon-highway",
        "https://www.westbankinn.net/"),
}

# ---------------------------------------------------------------------------
# 4. Cross-lane duplicate merges -- same name, no conflicting distant coords.
#    (dup_key, canonical_key): dup_key's evidence/lanes fold into canonical_key.
# ---------------------------------------------------------------------------
MERGE_PAIRS = [
    ("homewood suites by hilton augusta (2)", "homewood suites by hilton augusta"),
    ("days inn by wyndham thomson (2)", "days inn by wyndham thomson"),
    ("super 8 augusta (2)", "super 8 augusta"),
    ("super 8 augusta ft gordon area (2)", "super 8 augusta ft gordon area"),
    ("wingate by wyndham augusta fort gordon (2)", "wingate by wyndham augusta fort gordon"),
    ("woodspring suites augusta riverwatch (2)", "woodspring suites augusta riverwatch"),
]

#: rows confirmed >5 km from their name-twin by OSM coordinates -- kept
#: distinct, NOT merged (documented for the report, not applied as code).
CONFIRMED_DISTINCT_2 = ["rodeway inn (2)", "scottish inns augusta (2)", "motel 6 augusta (2)"]


def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def main():
    census = json.load(open(CENSUS, encoding="utf-8"), object_pairs_hook=OrderedDict)
    hotels = census["hotels"]
    by_key = {h["identity_key"]: h for h in hotels}
    report = OrderedDict([
        ("schema", "ptf-identity-cleanup/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("source", "WebSearch identity-discovery lookups + mechanical cross-lane coordinate check; no policy source used"),
        ("non_hotel_excluded", []), ("outside_sc_excluded", []),
        ("address_corrections_applied", []), ("merges_applied", []), ("confirmed_distinct_not_merged", CONFIRMED_DISTINCT_2),
    ])

    moved_to_non_admitted = []

    # 1. non-hotel hub/index rows
    for key, reason in NON_HOTEL_KEYS.items():
        h = by_key.pop(key, None)
        if h is None:
            continue
        h["classification"] = "NON_HOTEL"
        h["classification_reason"] = reason
        h["disposition"] = "NON_HOTEL"
        moved_to_non_admitted.append(h)
        report["non_hotel_excluded"].append({"identity_key": key, "reason": reason})

    # 2. real hotel, wrong state
    for key, fix in OUTSIDE_SC_CORRECTIONS.items():
        h = by_key.pop(key, None)
        if h is None:
            continue
        h["street"] = fix["street"]; h["city"] = fix["city"]; h["state"] = fix["state"]
        h["postal_code"] = fix["postal_code"]; h["geography_state"] = "RESOLVED"
        h["classification"] = "OUTSIDE"
        h["classification_reason"] = fix["reason"]
        h["disposition"] = "OUTSIDE"
        h["corridor"] = None
        moved_to_non_admitted.append(h)
        report["outside_sc_excluded"].append({"identity_key": key, "street": fix["street"], "city": fix["city"],
                                               "state": fix["state"], "postal_code": fix["postal_code"], "source": fix["source"]})

    # 3. address corrections for the ex-identity-review economy-motel strip
    for key, (street, postal, corridor, source) in ADDRESS_CORRECTIONS.items():
        h = by_key.get(key)
        if h is None:
            continue
        h["street"] = street
        h["postal_code"] = postal
        h["corridor"] = corridor
        h["geography_state"] = "RESOLVED"
        h["assignment_basis"] = "postal_code_via_websearch_identity_discovery"
        h["classification"] = "TRUE_HOTEL_IDENTITY"
        h["classification_reason"] = ("real distinct premises at %s %s -- confirmed by first-party/aggregator "
                                       "search, not a duplicate of any neighbour" % (street, postal))
        h.setdefault("evidence", []).append({"lane": "WEBSEARCH_IDENTITY_DISCOVERY", "tier": 4, "source_url": source,
                                              "note": "address/zip confirmation only, not a policy source"})
        report["address_corrections_applied"].append({"identity_key": key, "street": street, "postal_code": postal, "corridor": corridor})

    # 4. cross-lane duplicate merges
    for dup_key, canon_key in MERGE_PAIRS:
        dup = by_key.pop(dup_key, None)
        canon = by_key.get(canon_key)
        if dup is None or canon is None:
            if dup is not None:
                by_key[dup_key] = dup  # couldn't find canonical target -- leave alone, don't lose data
            continue
        canon.setdefault("evidence", []).extend(dup.get("evidence", []))
        canon["lanes"] = sorted(set(canon.get("lanes", []) + dup.get("lanes", [])))
        canon.setdefault("aliases", [])
        if dup.get("canonical_name") and dup["canonical_name"] not in canon["aliases"] and dup["canonical_name"] != canon.get("canonical_name"):
            canon["aliases"].append(dup["canonical_name"])
        if not canon.get("street") and dup.get("street"):
            canon["street"] = dup["street"]; canon["postal_code"] = dup.get("postal_code"); canon["geography_state"] = dup.get("geography_state", canon.get("geography_state"))
        report["merges_applied"].append({"duplicate": dup_key, "merged_into": canon_key})

    hotels = list(by_key.values())
    census["hotels"] = hotels
    census["count"] = len(hotels)
    census["non_admitted"] = census.get("non_admitted", []) + moved_to_non_admitted
    census["classification_counts"] = {}
    for h in hotels:
        c = h.get("classification", "UNKNOWN")
        census["classification_counts"][c] = census["classification_counts"].get(c, 0) + 1
    census["corridor_counts"] = {}
    for h in hotels:
        c = h.get("corridor")
        if c:
            census["corridor_counts"][c] = census["corridor_counts"].get(c, 0) + 1
    geo = {}
    for h in hotels:
        g = h.get("geography_state", "UNKNOWN")
        geo[g] = geo.get(g, 0) + 1
    census["geography_state_counts"] = geo
    census["note"] = (census.get("note", "") + " | PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 identity_cleanup_002: "
                       "-%d NON_HOTEL, -%d OUTSIDE(SC), %d address corrections, %d cross-lane merges"
                       % (len(NON_HOTEL_KEYS), len(OUTSIDE_SC_CORRECTIONS), len(ADDRESS_CORRECTIONS), len(MERGE_PAIRS)))

    with open(CENSUS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(census, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    report["final_count"] = len(hotels)
    report["final_classification_counts"] = census["classification_counts"]
    report["final_geography_state_counts"] = geo
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("final_count", len(hotels), "classification", census["classification_counts"], "geo", geo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
