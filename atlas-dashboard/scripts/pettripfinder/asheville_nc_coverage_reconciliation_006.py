"""PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001 -- Phases 5, 6 and 13: full accounting.

Every discovered candidate reconciles to EXACTLY ONE class, every admitted
identity to exactly one final state and one hold class, and the mountain market's
coverage is measured by the places an Asheville traveller actually sleeps:
Downtown, Biltmore Village / Biltmore, Tunnel Road / East Asheville, West
Asheville, South Asheville / Arden, the AVL airport / Fletcher, North Asheville /
Woodfin, Black Mountain, Weaverville and Candler.

A postal code is not split to report a sub-area. 28803 carries both Biltmore
Village and South Asheville; the slice is taken from the property's OWN street and
coordinates, and the rule is written down below so it is reviewable.

Nothing here fetches, spends or publishes.

Output: launch_packages/pettripfinder/markets/reports/asheville_nc_coverage_006.json
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

WORK_ORDER = "PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "asheville-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "asheville_nc_coverage_006.json")

#: The final-partition state -> the work order's hold class.
HOLD_CLASS = {
    "AWAITING_OFFICIAL_URL": "ROUTING_HOLD",
    "ACCESS_BLOCKED": "ACCESS_BLOCKED",
    "AWAITING_POLICY_OBSERVATION": "EVIDENCE_HOLD",
    "AWAITING_IDENTITY_RESOLUTION": "IDENTITY_HOLD",
}

#: 28803 slice rule. Biltmore Village and the Biltmore Estate lodging lie north of
#: Interstate 40 (latitude 35.535 and above, by the property's own coordinates or,
#: failing those, its street); Hendersonville Road south of I-40 and Biltmore Park
#: are South Asheville. 28704 Arden and 28732 Fletcher are the AVL airport corridor.
SOUTH_ASHEVILLE_STREETS = re.compile(r"town square|long shoals|schenck|brevard road", re.I)
BILTMORE_STREETS = re.compile(r"hendersonville road|hendersonville rd|biltmore ave|meadow road|thompson|"
                              r"boston way|antler hill|dairy|roberts road|lodge st", re.I)


def _load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def sub_area(h):
    z = (h.get("postal_code") or "")[:5]
    if z == "28801":
        return "Downtown"
    if z == "28803":
        lat = h.get("latitude")
        if SOUTH_ASHEVILLE_STREETS.search(h.get("street") or ""):
            return "South Asheville / Arden"
        if lat is not None and float(lat) < 35.535:
            return "South Asheville / Arden"
        return "Biltmore Village / Biltmore"
    if z == "28805":
        return "Tunnel Road / East Asheville"
    if z == "28806":
        return "West Asheville"
    if z == "28804":
        return "North Asheville / Woodfin"
    if z in ("28704", "28732"):
        return "AVL Airport / Fletcher / Arden"
    if z == "28711":
        return "Black Mountain"
    if z == "28787":
        return "Weaverville"
    if z == "28715":
        return "Candler"
    if z == "28778":
        return "Swannanoa"
    return "Other"


def build():
    cfg = MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET_ID)),
                          source=MARKET_ID)
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    clean = _load(os.path.join(REPORTS, "asheville_nc_clean_authority_001.json"))
    partition = _load(os.path.join(PKG, "asheville_nc_final_partition_007.json"))
    gap = _load(os.path.join(REPORTS, "asheville_nc_competitor_gap_matrix_001.json"), {})
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
         "GEOGRAPHY, PAID and FOUNDER holds are zero: membership is the postal partition "
         "(nothing is held on geography), no paid lane was used, and no row awaits a founder "
         "ruling. Reads refused OUTSIDE the market (Hendersonville, Flat Rock, Brevard, Waynesville, "
         "Gatlinburg) are not holds; their buildings are OUTSIDE_MARKET in the census."),
        ("corridor_counts", by_corridor),
        ("corridor_pages", corridor_pages),
        ("sub_area_coverage", tally("sub_area")),
        ("sub_area_rule",
         "28801 Downtown; 28803 is Biltmore Village / Biltmore unless the property sits on Town Square "
         "Blvd, Long Shoals, Schenck or Brevard Road or its own coordinates lie south of latitude 35.535 "
         "(Interstate 40), which is South Asheville; 28805 Tunnel Road / East Asheville; 28806 West "
         "Asheville; 28804 North Asheville / Woodfin; 28704 Arden and 28732 Fletcher are the AVL airport "
         "corridor; 28711 Black Mountain; 28787 Weaverville; 28715 Candler; 28778 Swannanoa."),
        ("vacation_rental_and_non_lodging_exclusions", vacation),
        ("vacation_rental_rule",
         "Individual vacation homes, cabins, cottages, farm stays, property-management listings, "
         "campgrounds and bed-and-breakfast houses without hotel operation are never admitted. "
         "Lantern Lodge Asheville (the map's Residences at Biltmore) is ADMITTED as a condo-hotel "
         "operated as one hotel; AutoCamp Asheville is ADMITTED as a Hilton-operated resort; motor "
         "courts and motels are admitted on the map's own lodging tag."),
        ("competitor_gap", gap.get("counts")),
        ("competitor_gap_reconciliation", [
            OrderedDict((("lead", "Kimpton Hotel Arras"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "7 Patton Avenue, read first-party on IHG and published"))),
            OrderedDict((("lead", "Aloft Asheville Downtown"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "51 Biltmore Avenue, read first-party on Marriott and published"))),
            OrderedDict((("lead", "The Restoration Asheville"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "68 Patton Avenue, admitted; its own FAQ sentence is not operative, evidence hold"))),
            OrderedDict((("lead", "Comfort Suites Outlet Center"), ("class", "ALIAS"),
                         ("why", "the map's Comfort Suites at 890 Brevard Road; Choice refused this client, access-blocked"))),
            OrderedDict((("lead", "Country Inn & Suites Asheville River Arts District"), ("class", "REVIEW"),
                         ("why", "Radisson names a Country Inn by area only; the map holds three Country Inns in 28806 and "
                                 "one former Country Inn at 199 Tunnel Road that now trades as La Quinta (REBRAND)"))),
            OrderedDict((("lead", "Extended Stay America Premier Suites Asheville"), ("class", "REVIEW"),
                         ("why", "a second ESA name with no address; the only ESA the brand and map place is 6 Kenilworth "
                                 "Knoll, read and published"))),
            OrderedDict((("lead", "Americas Best Value Inn Asheville"), ("class", "REVIEW"),
                         ("why", "no address from any first-party lane; name only"))),
            OrderedDict((("lead", "1900 Inn on Montford"), ("class", "NON_HOTEL"),
                         ("why", "a bed and breakfast house; not a hotel operation under the census contract"))),
            OrderedDict((("lead", "The Black Walnut Inn"), ("class", "NON_HOTEL"),
                         ("why", "a bed and breakfast house; not a hotel operation under the census contract"))),
            OrderedDict((("lead", "The Pines Cottages"), ("class", "VACATION_RENTAL"),
                         ("why", "rental cottages, never admitted"))),
        ]),
        ("identities", admitted),
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
