"""PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001 -- competitor GAP VERIFICATION through Google Places Text Search (the
existing GOOGLE_PLACES_API_KEY capacity), with the ROUTE-DISCOVERY cohort deliberately NOT run.

WHY ONLY ONE COHORT, AND WHY A NARROWER FIELD MASK
-------------------------------------------------
Every earlier market ran two cohorts with the shared discovery field mask, which includes ``websiteUri`` and
``nationalPhoneNumber``. Those two fields bill the request on the Text Search ENTERPRISE SKU, whose free monthly
allowance is about 1,000 requests -- and the factory's committed reports already record 998 Places requests this
month (Tampa V2 330, Miami 286, Fort Lauderdale 174, West Palm Beach 126, Jacksonville 82), every one with that
mask. Another Enterprise request this month would therefore very likely be NEW PAID SPEND, which this order may
not incur. So:

  ROUTE_DISCOVERY   (the property's own website for an unrouted identity) -- NOT RUN. It needs ``websiteUri``.
                    Every unrouted identity stays a ROUTING_HOLD whose actionability class is REQUIRES_NEW_SPEND.
  GAP_VERIFICATION  every BringFido TRUE_MISSING lead (san_diego_ca_competitor_reconciliation_001) -- RUN, with a
                    market-local PRO-tier mask (id, displayName, formattedAddress, addressComponents, location,
                    types, primaryType, businessStatus): no website, no phone. The question is only whether a real,
                    operating lodging establishment exists at an ADMITTED postal code that no census node already
                    carries (by house number + ZIP). The shared constants module is NOT edited; the narrower mask is
                    this module's own.

A Places card is identity evidence (tier 3), never policy.

Output:
  launch_packages/pettripfinder/markets/reports/san_diego_ca_places_route_discovery_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.discovery import constants as C  # noqa: E402
from scripts.pettripfinder import san_diego_ca_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census", "san-diego-ca.json")
ROUTING = os.path.join(REPORTS, "san_diego_ca_routing_001.json")
RECON = os.path.join(REPORTS, "san_diego_ca_competitor_reconciliation_001.json")
OUT = os.path.join(REPORTS, "san_diego_ca_places_route_discovery_001.json")
REQUEST_CAP = 400
LODGING_TYPES = {"lodging", "hotel", "motel", "resort_hotel", "bed_and_breakfast", "inn", "extended_stay_hotel",
                 "hostel", "guest_house", "cottage", "private_guest_room", "budget_japanese_inn", "farmstay"}
CENTERS = {c[0]: (c[3], c[4]) for c in GEO.CELLS}
DEFAULT_CENTER = (32.72, -117.16)
#: PRO-tier mask: no websiteUri, no nationalPhoneNumber (both Enterprise). Market-local; the shared mask is untouched.
PRO_FIELD_MASK = ",".join(["places.id", "places.displayName", "places.formattedAddress", "places.addressComponents",
                           "places.location", "places.primaryType", "places.types", "places.businessStatus"])
ROUTE_DISCOVERY_RUN = False


def _house(street):
    m = re.match(r"\s*(\d+)", street or "")
    return m.group(1) if m else ""


def _comp(components, kind):
    for comp in components or ():
        if kind in (comp.get("types") or ()):
            return comp.get("longText") or ""
    return ""


def _digits(v):
    d = re.sub(r"\D", "", v or "")
    return d[-10:] if len(d) >= 10 else ""


def search(session, key, text, lat, lng):
    body = {"textQuery": text, "pageSize": 3,
            "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 15000}}}
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": PRO_FIELD_MASK}
    try:
        resp = session.post(C.GOOGLE_SEARCH_TEXT_URL, headers=headers, json=body,
                            timeout=(C.CONNECT_TIMEOUT_SECONDS, C.READ_TIMEOUT_SECONDS))
    except Exception as exc:  # noqa: BLE001 -- recorded
        return None, "request_exception:%s" % type(exc).__name__
    if resp.status_code != 200:
        return None, "http_%d" % resp.status_code
    try:
        return (resp.json().get("places") or []), None
    except ValueError:
        return None, "invalid_json"


def place_row(p):
    comps = p.get("addressComponents") or []
    return OrderedDict([
        ("google_place_id", p.get("id", "")), ("display_name", (p.get("displayName") or {}).get("text", "")),
        ("formatted_address", p.get("formattedAddress", "")), ("street_number", _comp(comps, "street_number")),
        ("route", _comp(comps, "route")), ("locality", _comp(comps, "locality")),
        ("postal_code", _comp(comps, "postal_code")[:5]), ("phone", p.get("nationalPhoneNumber", "")),
        ("website_uri", p.get("websiteUri", "") or ""), ("business_status", p.get("businessStatus", "")),
        ("types", sorted(p.get("types") or [])),
        ("lat", (p.get("location") or {}).get("latitude")), ("lng", (p.get("location") or {}).get("longitude")),
    ])


def build(limit=REQUEST_CAP):
    key = os.environ.get(C.GOOGLE_PLACES_API_KEY_ENV, "").strip()
    census = json.load(open(CENSUS, encoding="utf-8"))
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    routing = json.load(open(ROUTING, encoding="utf-8"))
    unrouted = sorted((r for r in routing["routes"] if not r.get("url")), key=lambda r: r["identity_key"])
    recon = json.load(open(RECON, encoding="utf-8")) if os.path.exists(RECON) else {"rows": []}
    gap = sorted((r for r in recon["rows"] if r["classification"] == "TRUE_MISSING"), key=lambda r: r["bringfido_name"])
    census_house_zip = {(_house(h["street"]), h["postal_code"][:5]) for h in census["hotels"]}
    census_phone = {_digits(h.get("phone")) for h in census["hotels"]} - {""}
    rows, requests_made, errors = [], 0, Counter()
    if not key:
        return OrderedDict([("schema", "ptf-places-route-discovery/1.0"), ("state", "SKIPPED_NO_CREDENTIAL"), ("rows", [])])
    import requests
    session = requests.Session()
    for r in (unrouted if ROUTE_DISCOVERY_RUN else []):
        if requests_made >= limit:
            break
        h = by_key.get(r["identity_key"], {})
        lat, lng = CENTERS.get((h.get("corridor") or "").split("__")[-1], DEFAULT_CENTER)
        text = "%s %s %s CA %s" % (h.get("canonical_name"), h.get("street", ""), h.get("city", ""), h.get("postal_code", ""))
        places, err = search(session, key, text, lat, lng)
        requests_made += 1
        rec = OrderedDict([("cohort", "ROUTE_DISCOVERY"), ("identity_key", r["identity_key"]), ("query", text)])
        if err:
            errors[err] += 1
            rec["error"] = err
            rows.append(rec)
            if err in ("http_401", "http_403", "http_429"):
                break
            continue
        match = None
        for p in places:
            pr = place_row(p)
            if pr["postal_code"] == (h.get("postal_code") or "")[:5] and pr["street_number"] and \
                    pr["street_number"] == _house(h.get("street")):
                match = pr
                break
        rec["candidates_returned"] = len(places)
        rec["bound"] = match is not None
        if match:
            rec["place"] = match
            rec["bind_basis"] = "street_number+postal_code"
        rows.append(rec)
        time.sleep(0.05)
    for g in gap:
        if requests_made >= limit:
            break
        text = "%s San Diego County CA" % g["bringfido_name"]
        places, err = search(session, key, text, *DEFAULT_CENTER)
        requests_made += 1
        rec = OrderedDict([("cohort", "GAP_VERIFICATION"), ("bringfido_name", g["bringfido_name"]), ("query", text)])
        if err:
            errors[err] += 1
            rec["error"] = err
            rows.append(rec)
            continue
        verdict, best = "NO_LODGING_RESULT", None
        for p in places:
            pr = place_row(p)
            if not (set(pr["types"]) & LODGING_TYPES):
                continue
            best = pr
            klass, slug, _why = GEO.classify_postal(pr["postal_code"], pr["locality"])
            if klass == "OUTSIDE":
                verdict = "OUTSIDE_MARKET"
            elif pr["business_status"] and pr["business_status"] != "OPERATIONAL":
                verdict = "CLOSED_" + pr["business_status"]
            elif (pr["street_number"], pr["postal_code"]) in census_house_zip or _digits(pr["phone"]) in census_phone:
                verdict = "ALREADY_IN_CENSUS_BY_ADDRESS_OR_PHONE"
            else:
                verdict = "VERIFIED_MISSING_AT_ADMITTED_POSTAL_CODE"
                rec["corridor"] = slug
            break
        rec["verdict"] = verdict
        if best:
            rec["place"] = best
        rows.append(rec)
    return OrderedDict([
        ("schema", "ptf-places-route-discovery/1.0"), ("work_order", WORK_ORDER), ("market_id", "san-diego-ca"),
        ("provider", "GOOGLE_PLACES_TEXT_SEARCH (existing GOOGLE_PLACES_API_KEY capacity), PRO-tier field mask"),
        ("field_mask", PRO_FIELD_MASK),
        ("route_discovery_run", ROUTE_DISCOVERY_RUN),
        ("route_discovery_not_run_because",
         "it needs websiteUri, an Enterprise-SKU field whose free monthly allowance the factory's committed reports "
         "show already consumed this month (998 requests); running it would very likely be NEW PAID SPEND, which this "
         "order may not incur. Unrouted identities are ROUTING_HOLD with actionability REQUIRES_NEW_SPEND."),
        ("request_cap", limit), ("requests_made", requests_made), ("errors", dict(errors)),
        ("never_policy", "A Places field is never a pet policy; a website it names is only a route."),
        ("route_discovery_targets", len(unrouted)),
        ("route_discovery_bound", sum(1 for r in rows if r.get("cohort") == "ROUTE_DISCOVERY" and r.get("bound"))),
        ("route_discovery_bound_with_website", sum(1 for r in rows if r.get("cohort") == "ROUTE_DISCOVERY" and r.get("bound")
                                                   and r["place"]["website_uri"])),
        ("gap_verification_targets", len(gap)),
        ("gap_verdicts", dict(Counter(r["verdict"] for r in rows if r.get("cohort") == "GAP_VERIFICATION" and r.get("verdict")))),
        ("rows", rows),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=REQUEST_CAP)
    args = ap.parse_args(argv)
    rep = build(args.limit)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print({k: v for k, v in rep.items() if k != "rows"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
