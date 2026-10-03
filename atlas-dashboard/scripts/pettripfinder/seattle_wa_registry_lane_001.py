"""PTF-SEATTLE-WA-HARDENED-SOURCE-READY-001 -- Phase 7: the Seattle lodging register lane (Active Business License
Tax Certificates).

WHAT THIS IS
------------
The City of Seattle publishes every ACTIVE business license tax certificate on its open data portal
(data.seattle.gov dataset ``wnbq-64tb``, "Active Business License Tax Certificate"): the business's LEGAL name, its
TRADE name, ownership type, NAICS code, the licence start date, its street address, city, state, ZIP, business phone,
city account number and UBI. Every business that operates in Seattle -- every Seattle hotel among them -- holds one,
so it is the independent municipal register the order's "Washington / local lodging inventories" lane asks for.

The statewide alternative was measured first and refused: the Washington Department of Health's "Transient
Accommodations (Lodging)" listing on data.wa.gov (``9vm5-7kxk``) was last updated 2018-03-12 and answers "no row or
column access to non-tabular tables" -- it is not a tabular, current register. No King County, Bellevue or
Snohomish County lodging register is published on a Socrata portal (catalog search 2026-10-03: "transient
accommodation", "hotel motel", "lodging"). The Eastside, airport and south-county cities are covered by the brand
inventories, OSM, the bureau and Places instead.

WHAT IT IS USED FOR, AND WHAT IT NEVER DECIDES
----------------------------------------------
Tier-3 IDENTITY evidence:
  * an active certificate under NAICS 721110 (hotels and motels) at an admitted postal code is a census LEAD with a
    full premises;
  * a certificate under 721191 (bed-and-breakfast inns), 721199 (other traveller accommodation) or 721310 (rooming
    houses) is a LEAD only when its own TRADE name says it is a hotel, motel, inn, lodge, suites, hostel or B&B --
    Seattle's short-term-rental hosts license under 721191 / 721199 by the thousand, so every other row is COUNTED as
    short-term-rental inventory and is never a hotel lead;
  * 531110 / 531311 residential lessors and property managers are counted, never a lead.
The certificate's LEGAL name (often an LLC: "1000 FIRST AVENUE LLC") is kept as the licensee name and never
outranks the trade name ("HOTEL 1000"); a row with no trade name carries its legal name and is marked as a licensee
identity, so the census never prefers it to a proven hotel trade name. A certificate carries no pet policy, admits
nothing by itself (the corridor registry over its postal code does that) and never outranks the property's own page.
This register lists ACTIVE certificates only, so it is never closure evidence.

A register lane is free and read-only: the Socrata API is paged 5,000 rows at a time.

Output:
  launch_packages/pettripfinder/markets/reports/seattle_wa_registry_lane_001.json
  data/acquisition/seattle_wa_registry_001/<sha256>.json   (every page as returned)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import seattle_wa_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-SEATTLE-WA-HARDENED-SOURCE-READY-001"
MARKET_ID = "seattle-wa"
DATASET = "wnbq-64tb"
ENDPOINT = "https://data.seattle.gov/resource/%s.json" % DATASET
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "seattle_wa_registry_001")
OUT = os.path.join(REPORTS, "seattle_wa_registry_lane_001.json")
PAGE = 5000
UA = "PetTripFinder census lane (read-only; data.seattle.gov open data)"

HOTEL_NAICS = {"721110"}
NAMED_LODGING_NAICS = {"721191", "721199", "721310"}
NAICS_LABEL = {
    "721110": "Hotels (except casino hotels) and motels", "721191": "Bed-and-breakfast inns",
    "721199": "All other traveler accommodation", "721211": "RV parks and campgrounds",
    "721214": "Recreational and vacation camps", "721310": "Rooming and boarding houses",
    "531110": "Lessors of residential buildings", "531311": "Residential property managers",
}
#: A 721191 / 721199 / 721310 certificate is a lead only when its OWN trade name says what it is.
_LODGING_WORDS = re.compile(r"\b(hotel|motel|inn|lodge|suites|hostel|b\s*&\s*b|bed\s*(?:&|and)\s*breakfast|"
                            r"guest\s*house|motor\s*court)\b", re.I)
_STORE_NUMBER = re.compile(r"\s*(?:#|no\.?|num\.?)\s*\d+\s*$", re.I)


def persist(body):
    digest = hashlib.sha256(body).hexdigest()
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, digest + ".json")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(body)
    return digest


def fetch_rows(where, stats, order="city_account_number"):
    rows, offset, pages = [], 0, []
    while True:
        q = urllib.parse.urlencode([("$where", where), ("$limit", PAGE), ("$offset", offset), ("$order", order)])
        url = ENDPOINT + "?" + q
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        stats["requests"] += 1
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
        got = json.loads(body.decode("utf-8"))
        pages.append(OrderedDict([("url", url), ("rows", len(got)), ("sha256", persist(body)),
                                  ("fetched_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))]))
        rows.extend(got)
        if len(got) < PAGE:
            break
        offset += PAGE
        time.sleep(1.0)
    return rows, pages


def fetch_counts(stats):
    """NAICS counts for the residential-lessor and accommodation codes (counted, never leads)."""
    where = "naics_code like '7211%' OR naics_code like '7213%' OR naics_code in ('531110','531311')"
    q = urllib.parse.urlencode([("$select", "naics_code,count(*)"), ("$where", where), ("$group", "naics_code"),
                                ("$order", "naics_code")])
    url = ENDPOINT + "?" + q
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    stats["requests"] += 1
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read()
    persist(body)
    return OrderedDict((r["naics_code"], int(r["count"])) for r in json.loads(body.decode("utf-8")))


def _s(v):
    return " ".join(str(v or "").split())


def lead(r, snapshot):
    naics = _s(r.get("naics_code"))
    trade = _s(r.get("trade_name"))
    legal = _s(r.get("business_legal_name"))
    name = trade or legal
    z = _s(r.get("zip"))[:5]
    city = _s(r.get("city")).title()
    klass, slug, why = GEO.classify_postal(z, city)
    return OrderedDict([
        ("lane", "REGISTRY_LICENCE"),
        ("business_name", _STORE_NUMBER.sub("", name).strip(" -#") or name),
        ("registered_location_name", name),
        ("licensee_name", legal),
        ("trade_name_present", bool(trade)),
        ("street", _s(r.get("street_address"))),
        ("city", city), ("state", _s(r.get("state")) or GEO.STATE_CODE), ("postal_code", z),
        ("phone", _s(r.get("business_phone"))),
        ("license_number", _s(r.get("city_account_number"))),
        ("ubi", _s(r.get("ubi"))),
        ("ownership_type", _s(r.get("ownership_type"))),
        ("rank_code", naics), ("naics_code", naics), ("naics_label", NAICS_LABEL.get(naics, "")),
        ("responsibility_begin_date", _s(r.get("license_start_date"))[:8]),
        ("out_of_business_date", ""),
        ("geography_class", klass), ("corridor_slug", slug), ("membership_reason", why),
        ("snapshot_sha256", snapshot),
        ("raw_pointer", "https://data.seattle.gov/resource/%s.json?city_account_number=%s"
         % (DATASET, _s(r.get("city_account_number")))),
    ])


def is_lead(r):
    if r["naics_code"] in HOTEL_NAICS:
        return True
    return r["naics_code"] in NAMED_LODGING_NAICS and bool(_LODGING_WORDS.search(r["registered_location_name"]))


def build():
    stats = {"requests": 0}
    where = "naics_code like '7211%' OR naics_code like '7213%'"
    rows, pages = fetch_rows(where, stats)
    counts = fetch_counts(stats)
    snap = pages[0]["sha256"] if pages else ""
    all_rows = [lead(r, snap) for r in rows]
    leads = [r for r in all_rows if is_lead(r)]
    admitted = [r for r in leads if r["corridor_slug"]]
    refused = [r for r in leads if not r["corridor_slug"]]
    not_leads = [r for r in all_rows if not is_lead(r)]
    return OrderedDict([
        ("schema", "ptf-registry-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "7 -- the Seattle lodging register (Active Business License Tax Certificates, data.seattle.gov "
                  "wnbq-64tb)"),
        ("source", OrderedDict([
            ("dataset", "Active Business License Tax Certificate (City of Seattle)"),
            ("endpoint", ENDPOINT),
            ("licence", "City of Seattle Open Data -- public domain / open"),
            ("statewide_alternative_refused",
             "data.wa.gov 9vm5-7kxk 'Transient Accommodations (Lodging)' -- updated 2018-03-12, non-tabular "
             "('no row or column access to non-tabular tables'); not a current register."),
        ])),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats["requests"]),
        ("a_register_row_is_not_a_policy",
         "Tier-3 IDENTITY evidence. A certificate carries no pet policy, admits nothing by itself, is never closure "
         "evidence (active certificates only) and never outranks the property's own page. Its legal (licensee) name "
         "never outranks a proven trade name."),
        ("hotel_naics", sorted(HOTEL_NAICS)),
        ("named_lodging_naics", sorted(NAMED_LODGING_NAICS)),
        ("accommodation_rows", len(all_rows)),
        ("accommodation_rows_by_naics", OrderedDict(Counter(r["naics_code"] for r in all_rows).most_common())),
        ("naics_counts_portal", counts),
        ("lead_rows", len(leads)),
        ("leads_by_naics", OrderedDict(Counter(r["naics_code"] for r in leads).most_common())),
        ("leads_in_admitted_postal_codes", len(admitted)),
        ("leads_by_corridor", OrderedDict(sorted(Counter(r["corridor_slug"] for r in admitted).items()))),
        ("leads_refused_by_their_own_postal_code", len(refused)),
        ("leads_refused_by_future_market", OrderedDict(sorted(Counter(
            GEO.future_market_for(r["postal_code"]) or "other" for r in refused).items()))),
        ("leads_without_trade_name", sum(1 for r in leads if not r["trade_name_present"])),
        ("short_term_rental_and_other_rows_counted_not_leads", len(not_leads)),
        ("pages", pages),
        ("leads", leads),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for k in ("accommodation_rows", "lead_rows", "leads_in_admitted_postal_codes",
              "leads_refused_by_their_own_postal_code", "leads_without_trade_name",
              "short_term_rental_and_other_rows_counted_not_leads", "free_http_requests"):
        print("%-52s %s" % (k, rep[k]))
    print("leads by naics:", dict(rep["leads_by_naics"]))
    print("by corridor:", dict(rep["leads_by_corridor"]))
    print("refused:", dict(rep["leads_refused_by_future_market"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
