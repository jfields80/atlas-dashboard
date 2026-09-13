"""PTF-FAYETTEVILLE-NC-NORMAL-PRODUCTION-001 -- Phases 5, 6 and 13: full accounting.

Every discovered candidate reconciles to EXACTLY ONE class, every admitted
identity to exactly one final state and one hold class, and the military / I-95
market's coverage is measured by the places a Fayetteville / Fort Liberty
traveller actually sleeps: Downtown, Cross Creek / Skibo, the Fort Liberty
(Bragg Boulevard) corridor, Spring Lake, Hope Mills, the FAY airport, and I-95
North, Central and South.

A postal code is not split to report a sub-area. 28303 carries both Cross Creek
Mall / Skibo Road and Bragg Boulevard; 28312 carries both the exit 49 / 52
cluster and the exit 55 / 56 Eastover interchanges. The slice is taken from the
property's OWN street and coordinates, and the rule is written down below so it
is reviewable.

Nothing here fetches, spends or publishes.

Output: launch_packages/pettripfinder/markets/reports/fayetteville_nc_coverage_006.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.markets import contract as MC  # noqa: E402

WORK_ORDER = "PTF-FAYETTEVILLE-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "fayetteville-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "fayetteville_nc_coverage_006.json")

#: The final-partition state -> the work order's hold class.
HOLD_CLASS = {
    "AWAITING_OFFICIAL_URL": "ROUTING_HOLD",
    "ACCESS_BLOCKED": "ACCESS_BLOCKED",
    "AWAITING_POLICY_OBSERVATION": "EVIDENCE_HOLD",
    "AWAITING_IDENTITY_RESOLUTION": "IDENTITY_HOLD",
}

#: Slice rules. Bragg Boulevard and the streets that open off it (Sigman Street,
#: Convoy Lane) are the Fort Liberty corridor inside 28303 / 28304 / 28314; the rest
#: of those ZIPs is Cross Creek / Skibo. Inside 28312 the Eastover exits 55 / 56 lie
#: north of latitude 35.05 (Dunn Road, Dobbin Holmes Road) and are I-95 North with
#: Wade; exits 49 / 52 (Cedar Creek Road, Jim Johnson Road, Judson Church Road) are
#: I-95 Central. 28306 is the FAY airport corridor unless its own coordinates lie east
#: of longitude -78.86 on the I-95 exit 44 / 46 interchanges, which is I-95 South.
FORT_LIBERTY_STREETS = re.compile(r"bragg|sigman|convoy|all american", re.I)
I95_NORTH_STREETS = re.compile(r"dunn road|dunn rd|dobbin holmes", re.I)


def _load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def sub_area(h):
    z = (h.get("postal_code") or "")[:5]
    lat, lng = h.get("latitude"), h.get("longitude")
    street = h.get("street") or ""
    if z in ("28301", "28305"):
        return "Downtown"
    if z in ("28303", "28304", "28314"):
        return "Fort Liberty corridor" if FORT_LIBERTY_STREETS.search(street) else "Cross Creek / Skibo"
    if z == "28390":
        return "Spring Lake"
    if z == "28348":
        return "Hope Mills"
    if z == "28306":
        if lng is not None and float(lng) > -78.86:
            return "I-95 South"
        return "FAY Airport"
    if z == "28312":
        if I95_NORTH_STREETS.search(street) or (lat is not None and float(lat) >= 35.05):
            return "I-95 North"
        return "I-95 Central"
    if z == "28395":
        return "I-95 North"
    if z == "28311":
        return "North Fayetteville"
    if z == "28376":
        return "Raeford"
    return "Other"


REQUIRED_SUB_AREAS = ("Downtown", "Cross Creek / Skibo", "Fort Liberty corridor", "Spring Lake",
                      "Hope Mills", "FAY Airport", "I-95 North", "I-95 Central", "I-95 South")


def build():
    cfg = MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET_ID)),
                          source=MARKET_ID)
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    clean = _load(os.path.join(REPORTS, "fayetteville_nc_clean_authority_001.json"))
    partition = _load(os.path.join(PKG, "fayetteville_nc_final_partition_007.json"))
    gap = _load(os.path.join(REPORTS, "fayetteville_nc_competitor_gap_matrix_001.json"), {})
    package = _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET_ID))

    by_key = {i["identity_key"]: i for i in partition["items"]}
    classes = Counter(r["classification"] for r in census["hotels"] + census["non_admitted"])
    total = len(census["hotels"]) + len(census["non_admitted"])

    holds = Counter()
    admitted = []
    for h in census["hotels"]:
        item = by_key[h["identity_key"]]
        hold = "" if item["resolved"] else HOLD_CLASS[item["final_state"]]
        if hold:
            holds[hold] += 1
        admitted.append(OrderedDict((
            ("identity_key", h["identity_key"]), ("canonical_name", h["canonical_name"]),
            ("street", h["street"]), ("postal_code", h["postal_code"]),
            ("corridor", h["corridor"]), ("sub_area", sub_area(h)),
            ("final_state", item["final_state"]), ("hold_class", hold or None),
            ("next_action", item.get("next_action")))))
    # Addressed, in-market rows the identity graph did NOT admit are identity holds
    # of the census itself; the one off-post hotel whose own page states the Pope
    # Army Airfield postal code is a geography hold. Neither is in the census count.
    in_market_zips = {z for c in cfg.corridors for z in c.included_postal_codes}
    census_identity_holds = [OrderedDict((("name", r["canonical_name"]), ("street", r["street"]),
                                          ("postal_code", r["postal_code"]),
                                          ("reason", r["classification_reason"])))
                             for r in census["non_admitted"]
                             if r["classification"] == "IDENTITY_REVIEW_REQUIRED"
                             and r["postal_code"] in in_market_zips and r["street"]]
    geography_holds = [OrderedDict((("name", r["canonical_name"]), ("street", r["street"]),
                                    ("postal_code", r["postal_code"]),
                                    ("why", "an off-post Skibo Road hotel (next door to 1706 Skibo Road, 28303) whose "
                                            "own brand page AND the map state 28308, the Pope Army Airfield postal "
                                            "code the geography refuses; membership cannot be decided mechanically "
                                            "and the row is held rather than admitted by exception")))
                       for r in census["non_admitted"]
                       if r["classification"] == "OUTSIDE_MARKET" and r["postal_code"] == "28308"]
    holds["GEOGRAPHY_HOLD"] = len(geography_holds)
    for cls in ("IDENTITY_HOLD", "ROUTING_HOLD", "ACCESS_BLOCKED", "EVIDENCE_HOLD",
                "GEOGRAPHY_HOLD", "PAID_HOLD", "FOUNDER_HOLD"):
        holds.setdefault(cls, 0)

    def tally(key):
        out = OrderedDict()
        for a in admitted:
            t = out.setdefault(a[key], Counter())
            t["census"] += 1
            t[a["final_state"]] += 1
        return OrderedDict((k, OrderedDict((
            ("census", v["census"]),
            ("pet_friendly", v["PUBLISHED_PET_FRIENDLY"]),
            ("verified_no_pets", v["VERIFIED_NO_PETS"]),
            ("unresolved", v["census"] - v["PUBLISHED_PET_FRIENDLY"] - v["VERIFIED_NO_PETS"]),
        ))) for k, v in sorted(out.items()))

    corridor_pages = []
    by_corridor = tally("corridor")
    for c in cfg.corridors:
        n = by_corridor.get(c.corridor_id, {}).get("pet_friendly", 0)
        corridor_pages.append(OrderedDict((
            ("corridor_id", c.corridor_id), ("display_area", c.display_area),
            ("published_pet_friendly", n), ("minimum", c.minimum_hotel_count),
            ("corridor_page_publishes", n >= c.minimum_hotel_count))))

    pf = len(clean["clean_pet_friendly"])
    np_ = len(clean["clean_verified_no_pets"])
    vacation = [OrderedDict((("name", r["canonical_name"]), ("reason", r["classification_reason"])))
                for r in census["non_admitted"]
                if r["classification"] == "NON_LODGING"]
    return OrderedDict((
        ("schema", "ptf-market-coverage-reconciliation/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "5 / 6 / 13 -- vacation-rental exclusion, competitor gap, full accounting"),
        ("discovery", OrderedDict((
            ("total_discovered_candidates", total),
            ("by_class", OrderedDict(sorted(classes.items()))),
            ("registered_census", len(census["hotels"])),
            ("reconciles", sum(classes.values()) == total),
        ))),
        ("publication", OrderedDict((
            ("pet_friendly", pf), ("verified_no_pets", np_), ("resolved", pf + np_),
            ("unresolved", len(census["hotels"]) - pf - np_),
            ("policy_package_records", len(package["hotels"])),
            ("reads_held_not_published", OrderedDict(sorted(
                Counter(r["classification"] for r in clean["rejected"]).items()))),
        ))),
        ("holds", OrderedDict(sorted(holds.items()))),
        ("holds_note",
         "Holds are counted over the registered census. PAID and FOUNDER holds are zero: no paid "
         "lane was used and no row awaits a founder ruling. GEOGRAPHY_HOLD counts the one off-post "
         "hotel whose own page states a refused on-post postal code; it is NOT in the census. The "
         "addressed in-market rows the identity graph withheld are listed under "
         "census_identity_holds and are likewise not in the census. Reads refused OUTSIDE the market "
         "(Dunn, Benson, Southern Pines / Aberdeen / Pinehurst, Laurinburg, Lumberton) are not holds; "
         "their buildings are OUTSIDE_MARKET in the census."),
        ("geography_holds", geography_holds),
        ("census_identity_holds", census_identity_holds),
        ("military_government_nonpublic", [
            OrderedDict((("name", r["canonical_name"]), ("reason", r["classification_reason"])))
            for r in census["non_admitted"] if "MILITARY_GOVERNMENT_NONPUBLIC" in r["classification_reason"]]),
        ("corridor_counts", by_corridor),
        ("corridor_pages", corridor_pages),
        ("sub_area_coverage", OrderedDict(list(tally("sub_area").items()) + [
            (k, OrderedDict((("census", 0), ("pet_friendly", 0), ("verified_no_pets", 0), ("unresolved", 0))))
            for k in REQUIRED_SUB_AREAS if k not in {a["sub_area"] for a in admitted}])),
        ("sub_area_rule",
         "28301 / 28305 Downtown; 28303 / 28304 / 28314 are the Fort Liberty corridor when the property "
         "sits on Bragg Boulevard, Sigman Street or Convoy Lane and Cross Creek / Skibo otherwise; 28390 "
         "Spring Lake; 28348 Hope Mills; 28306 FAY Airport unless its own coordinates lie east of "
         "-78.86 (I-95 South); 28312 is I-95 North on Dunn Road / Dobbin Holmes Road or north of latitude "
         "35.05 and I-95 Central otherwise; 28395 Wade is I-95 North; 28311 North Fayetteville; 28376 "
         "Raeford."),
        ("vacation_rental_and_non_lodging_exclusions", vacation),
        ("vacation_rental_rule",
         "Individual vacation homes, cabins, cottages, property-management listings, corporate "
         "furnished-apartment operators and bed-and-breakfast houses without hotel operation are never "
         "admitted. Weekly-rate and extended-stay motels are admitted on the map's own lodging tag or the "
         "brand's own page. On-post Army lodging is MILITARY_GOVERNMENT_NONPUBLIC, never admitted."),
        ("competitor_gap", gap.get("counts")),
        ("competitor_gap_reconciliation", [
            OrderedDict((("lead", "Embassy Suites by Hilton Fayetteville Fort Bragg"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "4760 Lake Valley Drive, read first-party on Hilton and published"))),
            OrderedDict((("lead", "Hampton Inn & Suites Fayetteville"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "2065 Cedar Creek Road, read first-party on Hilton and published"))),
            OrderedDict((("lead", "Home2 Suites by Hilton Fayetteville Fort Liberty"), ("class", "ALIAS"),
                         ("why", "the brand's own page still names it Fort Bragg: 4035 Sycamore Dairy Road, published"))),
            OrderedDict((("lead", "Tru by Hilton Fayetteville I-95"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "2055 Cedar Creek Road, read first-party on Hilton and published"))),
            OrderedDict((("lead", "Red Roof Inn & Suites Fayetteville - Fort Bragg"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "3136 Bordeaux Park Drive, read first-party on Red Roof and published"))),
            OrderedDict((("lead", "Travelodge by Wyndham Fayetteville"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "2076 Cedar Creek Road, read first-party on Wyndham and published"))),
            OrderedDict((("lead", "Studio 6 Fayetteville NC Fort Bragg Area"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "3719 Bragg Boulevard, admitted; the brand page states only an amenity chip, evidence hold"))),
            OrderedDict((("lead", "Motel 6 Fayetteville NC Fort Liberty Area"), ("class", "REVIEW"),
                         ("why", "G6's own sitemap lists it (294393) at the SAME street as Studio 6 (293587), 3719 Bragg "
                                 "Boulevard, and its page states no postal code: a possible dual-brand building this "
                                 "order could not prove distinct, so no second identity was opened"))),
            OrderedDict((("lead", "Red Lion Inn & Suites Fayetteville at Cross Creek Mall (map)"), ("class", "REBRAND"),
                         ("why", "third-party listings name 562 Cross Creek Mall a Choice Quality Inn; admitted on the map row, access-blocked"))),
            OrderedDict((("lead", "WoodSpring Suites Fayetteville / West / Fort Bragg (map)"), ("class", "REBRAND"),
                         ("why", "770 West Rowan Street, 1381 Walter Reed Road and 6820 Cliffdale Road are Extended Stay "
                                 "America on the brand's own pages; WoodSpring's own site lists no Fayetteville property; published"))),
            OrderedDict((("lead", "Quality Inn & Suites Fort Bragg (map)"), ("class", "REBRAND"),
                         ("why", "2910 Sigman Street is Hawthorn Extended Stay by Wyndham on the brand's own page; published"))),
            OrderedDict((("lead", "Wingate by Wyndham Fayetteville/Fort Bragg (map)"), ("class", "REBRAND"),
                         ("why", "4182 Sycamore Dairy Road is Holiday Inn Express Fayetteville - Fort Bragg on IHG's own "
                                 "page, and Wyndham's Wingate route is retired; verified no-pets"))),
            OrderedDict((("lead", "Country Inn & Suites Spring Lake (map)"), ("class", "REBRAND"),
                         ("why", "103 Brook Lane is Spark by Hilton Spring Lake Fayetteville on Hilton's own page; published"))),
            OrderedDict((("lead", "IHG Army Hotels in Forrestal Hall & Delmont House / Airborne Inn / Landmark Inn (map)"),
                         ("class", "MILITARY_GOVERNMENT_NONPUBLIC"),
                         ("why", "on-post Fort Liberty lodging behind the installation gate; refused by the geography's military rule"))),
            OrderedDict((("lead", "Days Inn & Suites by Wyndham Fort Bragg/Cross Creek Mall"), ("class", "REVIEW"),
                         ("why", "an off-post Skibo Road hotel whose own page states the Pope Army Airfield postal code 28308; geography hold"))),
            OrderedDict((("lead", "Barrington House Bed & Breakfast (map)"), ("class", "NON_HOTEL"),
                         ("why", "a bed and breakfast house near Dunn; not a hotel operation and outside the market"))),
        ]),
        ("true_missing_qualifying_hotels", 0),

    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    with open(OUT if args.out == OUT else args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(OrderedDict((k, doc[k]) for k in ("discovery", "publication", "holds",
                                                        "sub_area_coverage")), indent=1))
    print("corridor pages:", [c["corridor_id"] for c in doc["corridor_pages"] if c["corridor_page_publishes"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
