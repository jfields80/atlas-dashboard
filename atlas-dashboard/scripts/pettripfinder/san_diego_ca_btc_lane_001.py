"""PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001 -- Phase 7: the City of San Diego business-tax register lane.

WHAT IT IS, AND WHY IT IS WEAKER THAN FLORIDA'S DBPR
----------------------------------------------------
California licenses no hotel at the state level: there is no DBPR. The nearest public premises register is the
City of San Diego's own Business Tax Certificate file (data.sandiego.gov, "Business Listings",
``sd_businesses_active_datasd.csv``) -- every active certificate with its DBA name, owner, NAICS code and stated
business location. It was read ONCE with a plain client and persisted as bytes.

It was MEASURED before it was trusted, and it is a thin, noisy register for lodging:
  * only ~150 active certificates carry a non-short-term-rental lodging NAICS code (721 / 7211 / 72111 / 72119 /
    721191 / 721199), because hotels remit Transient Occupancy Tax on a separate City register that is not
    published;
  * the bare "721 ACCOMMODATION" code is dominated by MISFILED food businesses (Papa John's, Subway, Dairy Queen,
    taco trucks), so a NAICS code alone decides nothing;
  * a certificate's "location" is sometimes the operator's corporate or billing office (InterContinental San
    Diego at Ravinia Drive, ATLANTA; Hotel Z at Headquarters Drive, PLANO; Sonesta ES Suites at Centre Street,
    NEWTON MA), and an office suite (``#330`` on High Bluff Drive) is an office, not a hotel.

So the lane is deliberately conservative. A row becomes a LEAD only when ALL of these hold:
  1. its NAICS code is a lodging code (721*), and it is not a short-term rental (721192), rooming house (7213*),
     camp or RV park (7212*);
  2. its DBA name reads as lodging (hotel / motel / inn / suites / lodge / resort / hostel / bed & breakfast / a
     chain word) -- the misfiled food businesses fail here, recorded as ``NAICS_MISFILED_NOT_LODGING``;
  3. its stated location is a San Diego County street address (919 / 920 / 921 prefix) with NO suite / unit
     designator -- an out-of-county address is ``BILLING_OR_HEADQUARTERS_ADDRESS`` and a suite is
     ``OFFICE_OR_UNIT_ADDRESS``, both recorded and never admitted.
Every lead is TIER 3 -- the same weight as a map row -- never the tier-2 weight a state premises licence carries,
because the certificate's address is not proved to be the premises. A register row never carries a pet policy.

The short-term-rental certificates (NAICS 721192) are COUNTED by corridor for the vacation-rental wall and never
enter the graph.

Outputs:
  launch_packages/pettripfinder/markets/reports/san_diego_ca_btc_lane_001.json
  data/san_diego_ca/registry/sd_businesses_active_datasd.csv   (as returned)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import san_diego_ca_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001"
MARKET_ID = "san-diego-ca"
SRC = os.path.join(_DASH, "data", "san_diego_ca", "registry", "sd_businesses_active_datasd.csv")
SRC_URL = "https://seshat.datasd.org/business_tax_certificates/sd_businesses_active_datasd.csv"
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports", "san_diego_ca_btc_lane_001.json")

LODGING_NAICS = {"721", "7211", "72111", "72119", "721191", "721199"}
STR_NAICS = {"721192"}
ROOMING_NAICS = {"7213", "72131"}
CAMP_NAICS = {"7212", "72121", "721211", "721214"}

_LODGING_NAME = re.compile(
    r"\b(hotel|hotels|motel|motels|inn|inns|suites|lodge|resort|hostel|hostels|bed (and|&) breakfast|b ?& ?b|"
    r"bnb|marriott|hilton|hyatt|sheraton|westin|doubletree|embassy suites|hampton|courtyard|residence inn|"
    r"springhill|towneplace|fairfield|holiday inn|best western|la quinta|motel 6|days inn|travelodge|"
    r"super 8|ramada|sonesta|extended stay|kimpton|pendry|moxy|aloft|element|hotel z)\b", re.I)
#: Names that read as a lodging word but are a travel agency, a timeshare club or a vacation-owner association.
_NOT_A_HOTEL = re.compile(r"\b(travel|tours|vacation owner|resort development|worldmark|the club|billing|realty|"
                          r"property management|rooms for rent|independent living|guest home|nursing)\b", re.I)
_UNIT = re.compile(r"\S")


def street_of(r):
    parts = [r.get("address_no") or "", r.get("address_pd") or "", r.get("address_road") or "",
             r.get("address_sfx") or ""]
    return " ".join(p.strip() for p in parts if p and p.strip())


def classify(r):
    """(rank, why) -- the register row's class. Only HOTEL_LEAD becomes a lead."""
    code = (r.get("naics_code") or "").strip()
    name = (r.get("dba_name") or "").strip()
    if code in STR_NAICS:
        return "SHORT_TERM_RENTAL", "NAICS 721192 short-term rental certificate -- never a hotel identity"
    if code in ROOMING_NAICS:
        return "ROOMING_HOUSE", "NAICS 7213 rooming / boarding / independent-living home -- not public lodging"
    if code in CAMP_NAICS:
        return "CAMP_OR_RV", "NAICS 7212 camp or RV park -- not a hotel"
    if code not in LODGING_NAICS:
        return "NOT_LODGING_NAICS", "not a lodging NAICS code"
    if _NOT_A_HOTEL.search(name):
        return "NOT_A_HOTEL_BY_NAME", "the DBA name reads as a travel agency, timeshare club, rental or care home"
    if not _LODGING_NAME.search(name):
        return "NAICS_MISFILED_NOT_LODGING", ("a lodging NAICS code on a DBA name that reads as no lodging "
                                              "establishment (the 721 code carries misfiled food businesses)")
    postal = (r.get("address_zip") or "")[:5]
    if not postal.startswith(GEO.SAN_DIEGO_COUNTY_PREFIXES) or (r.get("address_state") or "").upper() != "CA":
        return "BILLING_OR_HEADQUARTERS_ADDRESS", ("the certificate's stated location is outside San Diego County "
                                                   "(%s %s) -- an operator's office, not the premises"
                                                   % (r.get("address_city"), postal))
    if not (r.get("address_no") or "").strip() or not (r.get("address_road") or "").strip():
        return "NO_STREET_ADDRESS", "the certificate states no street address"
    if (r.get("address_suite") or "").strip() or (r.get("address_pmb_box") or "").strip() or \
            (r.get("address_po_box") or "").strip():
        return "OFFICE_OR_UNIT_ADDRESS", ("the certificate's address carries a suite / unit / box designator "
                                          "(%r) -- an office or a unit inside a building, never a hotel premises"
                                          % (r.get("address_suite") or r.get("address_pmb_box") or
                                             r.get("address_po_box")))
    return "HOTEL_LEAD", "a lodging-named certificate at a San Diego County street address"


def build():
    raw = open(SRC, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    rows = list(csv.DictReader(raw.decode("utf-8", "replace").splitlines()))
    ranks = Counter()
    leads, refused = [], []
    str_by_corridor = Counter()
    str_outside = 0
    for i, r in enumerate(rows, start=2):
        rank, why = classify(r)
        ranks[rank] += 1
        postal = (r.get("address_zip") or "")[:5]
        klass, slug, _reason = GEO.classify_postal(postal, r.get("address_city") or "")
        if rank == "SHORT_TERM_RENTAL":
            if slug:
                str_by_corridor[slug] += 1
            else:
                str_outside += 1
            continue
        if rank in ("NOT_LODGING_NAICS",):
            continue
        rec = OrderedDict([
            ("lane", "REGISTRY_SD_BTC"),
            ("license_number", "SD_BTC:%s" % (r.get("account_key") or "").split(".")[0]),
            ("property_code", "SD_BTC:%s" % (r.get("account_key") or "").split(".")[0]),
            ("rank_code", rank),
            ("naics_code", r.get("naics_code")),
            ("naics_description", r.get("naics_description")),
            ("name", (r.get("dba_name") or "").strip()),
            ("business_name", (r.get("dba_name") or "").strip()),
            ("licensee_name", (r.get("business_owner_name") or "").strip()),
            ("street", street_of(r)),
            ("suite", (r.get("address_suite") or "").strip()),
            ("city", (r.get("address_city") or "").strip()),
            ("state", (r.get("address_state") or "").strip()),
            ("postal_code", postal),
            ("lat", r.get("lat") or None), ("lng", r.get("lng") or None),
            ("certificate_effective", (r.get("date_cert_effective") or "")[:10]),
            ("business_start", (r.get("date_business_start") or "")[:10]),
            ("geography_class", klass), ("corridor_slug", slug),
            ("raw_pointer", "%s#row=%d" % (SRC_URL, i)),
            ("snapshot_sha256", sha),
            ("why", why),
        ])
        (leads if rank == "HOTEL_LEAD" else refused).append(rec)
    leads.sort(key=lambda x: x["license_number"])
    refused.sort(key=lambda x: (x["rank_code"], x["license_number"]))
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "7 -- the City of San Diego business-tax certificate register (a thin, tier-3 lodging lane)"),
        ("source", OrderedDict([("url", SRC_URL), ("file", "data/san_diego_ca/registry/sd_businesses_active_datasd.csv"),
                                ("bytes", len(raw)), ("sha256", sha), ("rows", len(rows)),
                                ("dataset", "https://data.sandiego.gov/datasets/business-listings/")])),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 2),
        ("a_certificate_is_not_a_policy", "A register row is identity and discovery evidence only."),
        ("a_licensee_name_is_not_a_hotel_name",
         "business_owner_name is the certificate holder (an LLC or a person); it is carried as licensee_name and "
         "never as a hotel name."),
        ("the_register_is_tier_three",
         "Unlike Florida's DBPR premises licence, a City business-tax certificate's address is not proved to be "
         "the hotel's premises (measured: corporate offices in Atlanta, Plano, Newton MA and Orlando; office "
         "suites in San Diego). Every lead is TIER 3, never tier 2."),
        ("the_register_is_city_only",
         "The City of San Diego certifies businesses located in the City (and some outside operators). Coronado, "
         "Del Mar, Carlsbad, Oceanside, Chula Vista, National City, La Mesa, El Cajon and the other cities keep "
         "their own registers; none is published as open data at this client's reach, so this lane says nothing "
         "about them."),
        ("rank_counts", dict(sorted(ranks.items()))),
        ("short_term_rental_certificates_by_corridor", dict(sorted(str_by_corridor.items()))),
        ("short_term_rental_certificates_outside", str_outside),
        ("lead_count", len(leads)),
        ("leads_by_corridor", dict(sorted(Counter(l["corridor_slug"] or "OUTSIDE" for l in leads).items()))),
        ("leads", leads),
        ("refused_lodging_rows", refused),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("rows:", doc["source"]["rows"], "ranks:", doc["rank_counts"])
    print("leads:", doc["lead_count"], doc["leads_by_corridor"])
    print("STR certificates by corridor:", doc["short_term_rental_certificates_by_corridor"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
