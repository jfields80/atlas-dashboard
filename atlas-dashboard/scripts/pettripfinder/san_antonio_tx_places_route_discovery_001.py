"""PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001 -- Google Places Text Search (the existing
GOOGLE_PLACES_API_KEY capacity): competitor GAP VERIFICATION and, this month, ROUTE DISCOVERY.

WHY ROUTE DISCOVERY RUNS IN THIS ORDER, AND HOW IT IS BOUNDED
------------------------------------------------------------
The Austin order (2026-09-30) did not run route discovery: it needs ``websiteUri``, a Text Search ENTERPRISE-SKU
field whose free monthly allowance (about 1,000 requests) the factory's committed reports showed as consumed for
SEPTEMBER (998 requests). The allowance renewed on 2026-10-01. Measured before this run: no worktree on this
machine holds a Places report or ledger written since 2026-10-01, so this month's committed Places use is ZERO.
Route discovery therefore runs inside the existing free allowance, capped at ROUTE_DISCOVERY_CAP Enterprise
requests (well under the allowance), and stops on the first 401 / 403 / 429. No new provider, no new purchase.

  ROUTE_DISCOVERY   the property's own website for an admitted, UNROUTED identity -- the Enterprise mask
                    (adds websiteUri and nationalPhoneNumber). A place binds ONLY on street number + postal code;
                    the website it names is a ROUTE, which the policy-pages lane must still bind to the census row
                    on the site's own address or phone.
  GAP_VERIFICATION  every BringFido TRUE_MISSING lead (san_antonio_tx_competitor_reconciliation_001), with a
                    market-local PRO-tier mask (no website, no phone): does a real, operating lodging
                    establishment exist at an ADMITTED postal code that no census node already carries?

A Places card is identity evidence (tier 3), never policy.

Output:
  launch_packages/pettripfinder/markets/reports/san_antonio_tx_places_route_discovery_001.json
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
from scripts.pettripfinder import san_antonio_tx_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "san-antonio-tx.json")
ROUTING = os.path.join(REPORTS, "san_antonio_tx_routing_001.json")
RECON = os.path.join(REPORTS, "san_antonio_tx_competitor_reconciliation_001.json")
OUT = os.path.join(REPORTS, "san_antonio_tx_places_route_discovery_001.json")
REQUEST_CAP = 400
#: Enterprise-SKU requests (websiteUri) this order may make -- inside the renewed free monthly allowance.
ROUTE_DISCOVERY_CAP = 300
LODGING_TYPES = {"lodging", "hotel", "motel", "resort_hotel", "bed_and_breakfast", "inn", "extended_stay_hotel",
                 "hostel", "guest_house", "cottage", "private_guest_room", "budget_japanese_inn", "farmstay"}
CENTERS = {c[0]: (c[3], c[4]) for c in GEO.CELLS}
DEFAULT_CENTER = (29.4241, -98.4936)
#: PRO-tier mask: no websiteUri, no nationalPhoneNumber (both Enterprise). Market-local; the shared mask is untouched.
PRO_FIELD_MASK = ",".join(["places.id", "places.displayName", "places.formattedAddress", "places.addressComponents",
                           "places.location", "places.primaryType", "places.types", "places.businessStatus"])
ROUTE_DISCOVERY_RUN = True
#: ENTERPRISE mask for the route-discovery cohort only: the PRO mask plus the property's own website and phone.
ENTERPRISE_FIELD_MASK = PRO_FIELD_MASK + ",places.websiteUri,places.nationalPhoneNumber"


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


def search(session, key, text, lat, lng, mask=PRO_FIELD_MASK):
    body = {"textQuery": text, "pageSize": 3,
            "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 15000}}}
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": mask}
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
    # A DEAD ROUTE IS NO ROUTE: a row whose census route the clean authority found retired, expired or answering an
    # error page is a ROUTING_HOLD with a URL still on it; it is asked exactly like an unrouted row.
    _clean = os.path.join(REPORTS, "san_antonio_tx_clean_authority_001.json")
    _held = {c["identity_key"] for c in (json.load(open(_clean, encoding="utf-8")).get("rows", [])
                                         if os.path.exists(_clean) else []) if c.get("disposition") == "ROUTING_HOLD"}
    _seen = {r["identity_key"] for r in unrouted}
    unrouted += sorted((r for r in routing["routes"] if r["identity_key"] in _held and r["identity_key"] not in _seen),
                       key=lambda r: r["identity_key"])
    recon = json.load(open(RECON, encoding="utf-8")) if os.path.exists(RECON) else {"rows": []}
    gap = sorted((r for r in recon["rows"] if r["classification"] == "TRUE_MISSING"), key=lambda r: r["bringfido_name"])
    census_house_zip = {(_house(h["street"]), h["postal_code"][:5]) for h in census["hotels"]}
    census_phone = {_digits(h.get("phone")) for h in census["hotels"]} - {""}
    rows, requests_made, errors = [], 0, Counter()
    if not key:
        return OrderedDict([("schema", "ptf-places-route-discovery/1.0"), ("state", "SKIPPED_NO_CREDENTIAL"), ("rows", [])])
    import requests
    session = requests.Session()
    enterprise_made = 0
    # PAY ONCE PER QUERY: an identity (or BringFido lead) this lane already queried keeps its recorded answer; only
    # identities that became unrouted AFTER the previous run (their census route proved dead or retired) are asked.
    prior = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"rows": []}
    prior_route = {p["identity_key"]: p for p in prior.get("rows", []) if p.get("cohort") == "ROUTE_DISCOVERY"}
    prior_gap = {p["bringfido_name"]: p for p in prior.get("rows", []) if p.get("cohort") == "GAP_VERIFICATION"}
    reused = 0
    for r in (unrouted if ROUTE_DISCOVERY_RUN else []):
        if r["identity_key"] in prior_route:
            rows.append(prior_route[r["identity_key"]])
            reused += 1
            continue
        if requests_made >= limit or enterprise_made >= ROUTE_DISCOVERY_CAP:
            break
        h = by_key.get(r["identity_key"], {})
        lat, lng = CENTERS.get((h.get("corridor") or "").split("__")[-1], DEFAULT_CENTER)
        text = "%s %s %s TX %s" % (h.get("canonical_name"), h.get("street", ""), h.get("city", ""), h.get("postal_code", ""))
        places, err = search(session, key, text, lat, lng, mask=ENTERPRISE_FIELD_MASK)
        requests_made += 1
        enterprise_made += 1
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
        if g["bringfido_name"] in prior_gap:
            rows.append(prior_gap[g["bringfido_name"]])
            reused += 1
            continue
        if requests_made >= limit:
            break
        text = "%s San Antonio TX" % g["bringfido_name"]
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
    # A VERIFICATION IS NEVER DROPPED. A lead Places verified as a missing hotel becomes a census identity, and so
    # stops being a TRUE_MISSING lead -- dropping its row on the next run would remove the identity it admitted. Every
    # prior verification (and every prior route answer) not asked again this run is carried forward unchanged.
    _have_gap = {r.get("bringfido_name") for r in rows if r.get("cohort") == "GAP_VERIFICATION"}
    _have_route = {r.get("identity_key") for r in rows if r.get("cohort") == "ROUTE_DISCOVERY"}
    for name, p in sorted(prior_gap.items()):
        if name not in _have_gap:
            rows.append(p)
    for key, p in sorted(prior_route.items()):
        if key not in _have_route:
            rows.append(p)
    return OrderedDict([
        ("schema", "ptf-places-route-discovery/1.0"), ("work_order", WORK_ORDER), ("market_id", "san-antonio-tx"),
        ("provider", "GOOGLE_PLACES_TEXT_SEARCH (existing GOOGLE_PLACES_API_KEY capacity)"),
        ("field_mask_gap_verification", PRO_FIELD_MASK),
        ("field_mask_route_discovery", ENTERPRISE_FIELD_MASK),
        ("route_discovery_run", ROUTE_DISCOVERY_RUN),
        ("route_discovery_capacity_basis",
         "websiteUri is an Enterprise-SKU field; its free monthly allowance (about 1,000 requests) renewed on "
         "2026-10-01 and no worktree on this machine holds a Places report or ledger written since then. This run "
         "stays inside that allowance (cap %d Enterprise requests) -- existing capacity, no new paid spend." %
         ROUTE_DISCOVERY_CAP),
        ("request_cap", limit), ("route_discovery_cap", ROUTE_DISCOVERY_CAP),
        ("requests_made", requests_made + int(prior.get("requests_made") or 0)),
        ("enterprise_requests_made", enterprise_made + int(prior.get("enterprise_requests_made") or 0)),
        ("pro_requests_made", (requests_made - enterprise_made) + int(prior.get("pro_requests_made") or 0)),
        ("requests_this_run", requests_made), ("answers_reused_from_prior_runs", reused),
        ("errors", dict(errors)),
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
