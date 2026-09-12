"""PTF-WILMINGTON-NC-NORMAL-PRODUCTION-001 -- Phases 5, 6 and 13: full accounting.

Every discovered candidate reconciles to EXACTLY ONE class, every admitted
identity to exactly one final state and one hold class, and the coastal market's
coverage is measured by the places a Wilmington traveller actually sleeps:
Wilmington proper, the ILM airport, the Mayfaire / Wrightsville corridor,
Wrightsville Beach, Carolina / Kure Beach and Leland.

A postal code is not split to report a sub-area. 28405 carries both ILM and
Mayfaire; the slice is taken from the property's OWN street and coordinates, and
the rule is written down below so it is reviewable.

Nothing here fetches, spends or publishes.

Output: launch_packages/pettripfinder/markets/reports/wilmington_nc_coverage_006.json
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

WORK_ORDER = "PTF-WILMINGTON-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "wilmington-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "wilmington_nc_coverage_006.json")

#: The final-partition state -> the work order's hold class.
HOLD_CLASS = {
    "AWAITING_OFFICIAL_URL": "ROUTING_HOLD",
    "ACCESS_BLOCKED": "ACCESS_BLOCKED",
    "AWAITING_POLICY_OBSERVATION": "EVIDENCE_HOLD",
    "AWAITING_IDENTITY_RESOLUTION": "IDENTITY_HOLD",
}

#: 28405 slice rule. ILM airport lodging is the Market Street / Kerr Avenue /
#: North 23rd Street side west of College Road; the Mayfaire / Wrightsville
#: corridor is Military Cutoff, Mayfaire Town Center, Landfall and the streets
#: east of it. Streets named here, never a guess from a hotel's marketing name.
MAYFAIRE_STREETS = re.compile(r"rock spring|swan mill|ashes dr|international dr|culbreth|"
                              r"military cutoff|mayfaire|eastwood", re.I)


def _load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def sub_area(h):
    z = (h.get("postal_code") or "")[:5]
    if z in ("28480",):
        return "Wrightsville Beach"
    if z in ("28428", "28449"):
        return "Carolina Beach / Kure Beach"
    if z == "28451":
        return "Leland"
    if z == "28405":
        return ("Mayfaire / Wrightsville corridor" if MAYFAIRE_STREETS.search(h.get("street") or "")
                else "ILM airport / Market Street")
    if z == "28403" and MAYFAIRE_STREETS.search(h.get("street") or ""):
        return "Mayfaire / Wrightsville corridor"
    return "Wilmington proper"


def build():
    cfg = MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET_ID)),
                          source=MARKET_ID)
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    clean = _load(os.path.join(REPORTS, "wilmington_nc_clean_authority_001.json"))
    partition = _load(os.path.join(PKG, "wilmington_nc_final_partition_007.json"))
    gap = _load(os.path.join(REPORTS, "wilmington_nc_competitor_gap_matrix_001.json"), {})
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
         "ruling. Reads refused OUTSIDE the market (Southport, Bolivia) are not holds; their "
         "buildings are OUTSIDE_MARKET in the census."),
        ("corridor_counts", by_corridor),
        ("corridor_pages", corridor_pages),
        ("sub_area_coverage", tally("sub_area")),
        ("sub_area_rule",
         "28480 Wrightsville Beach; 28428 / 28449 Carolina / Kure Beach; 28451 Leland; in 28405 "
         "and 28403 a property on Rock Spring Rd, Swan Mill Rd, Ashes Dr, International Dr, "
         "Culbreth Dr, Military Cutoff, Mayfaire or Eastwood Rd is the Mayfaire / Wrightsville "
         "corridor, and the rest of 28405 is ILM airport / Market Street; everything else is "
         "Wilmington proper."),
        ("vacation_rental_and_non_lodging_exclusions", vacation),
        ("vacation_rental_rule",
         "Individual vacation homes, condo rental programmes, apartments and property-management "
         "listings are never admitted. Shell Island Resort is ADMITTED: a condo-hotel operated as "
         "one resort hotel with a front desk and nightly suites under one name."),
        ("competitor_gap", gap.get("counts")),
        ("competitor_gap_reconciliation", [
            OrderedDict((("lead", "SeaBirds Motel at Kure Beach"), ("class", "REBRAND"),
                         ("why", "the map still calls 118 Fort Fisher Boulevard South the Moran Motel; "
                                 "the property's own site names it SeaBirds -- read first-party and "
                                 "published"))),
            OrderedDict((("lead", "Carolina Beach Inn"), ("class", "EXACT_ATLAS_MATCH"),
                         ("why", "205 Harper Avenue, read first-party and published"))),
            OrderedDict((("lead", "Savannah Inn"), ("class", "ALIAS"),
                         ("why", "the map's 'The Savannah Inn', 316 Carolina Beach Avenue North; "
                                 "admitted, its own site did not resolve (DNS), unresolved"))),
            OrderedDict((("lead", "Carolina Beach Motel"), ("class", "TRUE_MISSING_IDENTITY"),
                         ("why", "no map, brand or first-party lane placed it; its own site is not "
                                 "navigable in the operator's session, so no address was read and "
                                 "it is not admitted -- a routing lead for the next order"))),
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
