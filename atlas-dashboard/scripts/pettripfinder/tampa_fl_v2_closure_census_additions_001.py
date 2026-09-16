"""PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 -- Phase 2/10: a bounded number of
BringFido TRUE_MISSING_QUALIFYING_CANDIDATE leads are real national-chain or
named-inn identities the source-ready census missed (the Wyndham lane's own
seed list did not include La Quinta / Days Inn / Microtel; ESA and Sonesta
Simply Suites were never brand-tagged at all). This is a genuine census
defect discovered during closure (PHASE 2 permits correcting it), not a
rebuild: it ADDS rows, it never touches an already-resolved identity.

Each candidate is independently verified via Google Places (existing
authorized capacity) before admission -- a BringFido name alone never
qualifies a row; the place's own formatted address, and its own in-market
postal code against the tampa_fl.json corridor registry, do.

Output:
  launch_packages/pettripfinder/markets/reports/tampa_fl_v2_closure_census_additions_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.discovery import constants as C  # noqa: E402
from scripts.pettripfinder.tampa_fl_v2_closure_places_lookup_001 import (  # noqa: E402
    search_one, DEFAULT_CENTER,
)
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "tampa-fl.json")
BRINGFIDO_RECON = os.path.join(REPORTS, "tampa_fl_v2_closure_bringfido_reconciliation_001.json")
GEOGRAPHY_REPORT = os.path.join(REPORTS, "tampa_fl_v2_geography_001.json")
OUT = os.path.join(REPORTS, "tampa_fl_v2_closure_census_additions_001.json")

# Excluded before lookup: this BringFido lead is a real hotel, but in
# Bradenton (an OBSERVATION-ONLY, refused cell in tampa_fl.json), surfaced
# only because BringFido's own radius-widening bug (documented in
# tampa_fl_v2_competitor_challenge_001.json's method_note) attached it to
# the "St. Pete Beach" city page.
EXCLUDED_OUTSIDE = {"Days Inn by Wyndham Bradenton - Near the Gulf"}

_BRAND_TAG = [
    (re.compile(r"la quinta", re.I), "WYNDHAM"),
    (re.compile(r"days inn", re.I), "WYNDHAM"),
    (re.compile(r"microtel", re.I), "WYNDHAM"),
    (re.compile(r"extended stay america", re.I), "EXTENDED_STAY_AMERICA"),
    (re.compile(r"sonesta", re.I), "SONESTA"),
]


def brand_for(name):
    for pat, brand in _BRAND_TAG:
        if pat.search(name):
            return brand
    return ""


def in_admitted_geography(postal5, admitted_postal_codes):
    # Authoritative check against the corridor registry's own 66-ZIP admitted
    # set (tampa_fl_v2_geography_001.json), not a census-derived proxy -- a
    # ZIP with no *existing* census row is still admitted if the registry
    # itself admits it (DBPR coverage gaps are exactly what this pass exists
    # to catch).
    return postal5 in admitted_postal_codes


def main():
    recon = json.load(open(BRINGFIDO_RECON, encoding="utf-8"))
    candidates = [r for r in recon["rows"] if r["classification"] == "TRUE_MISSING_QUALIFYING_CANDIDATE"
                  and r["bringfido_name"] not in EXCLUDED_OUTSIDE]

    census = json.load(open(CENSUS, encoding="utf-8"))
    existing_postal_house = set()
    existing_phone = set()
    for h in census["hotels"]:
        num_m = re.match(r"\s*(\d+)", h.get("street") or "")
        if num_m and h.get("postal_code"):
            existing_postal_house.add((num_m.group(1), h["postal_code"][:5]))
        if h.get("phone_key"):
            existing_phone.add(h["phone_key"])

    geography_report = json.load(open(GEOGRAPHY_REPORT, encoding="utf-8"))
    admitted_postal_codes = set(geography_report["admitted_postal_codes"])
    postal_to_corridor = {}
    for cor in geography_report["corridors"]:
        for pc in cor.get("included_postal_codes", []):
            postal_to_corridor.setdefault(pc, cor["corridor_id"])

    api_key = os.environ.get(C.GOOGLE_PLACES_API_KEY_ENV, "").strip()
    import requests
    session = requests.Session() if api_key else None

    additions = []
    rejected = []
    for cand in candidates:
        name = cand["bringfido_name"]
        query_text = f"{name} FL"
        if not api_key:
            rejected.append({"name": name, "reason": "NO_GOOGLE_PLACES_CREDENTIAL"})
            continue
        result = search_one(session, api_key, query_text, *DEFAULT_CENTER)
        time.sleep(0.05)
        if not result["ok"]:
            rejected.append({"name": name, "reason": "PLACES_ERROR:%s" % result["error"]})
            continue
        places = result["payload"].get("places", []) or []
        if not places:
            rejected.append({"name": name, "reason": "NO_PLACES_RESULT"})
            continue
        p = places[0]
        comps = p.get("addressComponents") or []
        postal = ""
        house = ""
        for c in comps:
            types = c.get("types") or ()
            if "postal_code" in types:
                postal = (c.get("longText") or "")[:5]
            if "street_number" in types:
                house = c.get("longText") or ""
        if not in_admitted_geography(postal, admitted_postal_codes):
            rejected.append({"name": name, "reason": "POSTAL_NOT_IN_ADMITTED_SET", "postal": postal,
                             "formatted_address": p.get("formattedAddress", "")})
            continue
        if p.get("businessStatus") == "CLOSED_PERMANENTLY":
            rejected.append({"name": name, "reason": "CLOSED_PERMANENTLY"})
            continue
        website = p.get("websiteUri", "") or ""
        if re.search(r"guestybookings\.com|airbnb\.|vrbo\.|homeaway\.|guesty\.com", website, re.I):
            rejected.append({"name": name, "reason": "VACATION_RENTAL_MANAGEMENT_PLATFORM_URL",
                             "website": website})
            continue
        if (house, postal) in existing_postal_house:
            rejected.append({"name": name, "reason": "ALREADY_IN_CENSUS_SAME_ADDRESS",
                             "house": house, "postal": postal})
            continue
        phone = p.get("nationalPhoneNumber", "") or ""
        phone_key = re.sub(r"\D", "", phone)[-10:]
        if phone_key and phone_key in existing_phone:
            rejected.append({"name": name, "reason": "ALREADY_IN_CENSUS_SAME_PHONE", "phone": phone})
            continue
        display_name = (p.get("displayName") or {}).get("text") or name
        addr_parts = [x.strip() for x in p.get("formattedAddress", "").split(",")]
        street = addr_parts[0] if addr_parts else ""
        city = ""
        for c in comps:
            if "locality" in (c.get("types") or ()) or "postal_town" in (c.get("types") or ()):
                city = c.get("longText") or ""
                break
        identity_key = ptf_identity_key(display_name)
        alias_key = ptf_identity_key(name)
        addition = OrderedDict([
            ("identity_key", identity_key),
            ("slug", re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-")),
            ("market_id", "tampa-fl"),
            ("identity_state", "IDENTITY_CONFIRMED"),
            ("lodging_state", "LODGING_CONFIRMED"),
            ("collision_state", "NONE"),
            ("identity_key_aliases", sorted({identity_key, alias_key})),
            ("canonical_name", display_name.strip()),
            ("classification", "TRUE_HOTEL_IDENTITY"),
            ("classification_reason", ""),
            ("street", street.strip()),
            ("city", city.strip()),
            ("state", "FL"),
            ("postal_code", postal),
            ("phone", phone),
            ("phone_key", phone_key),
            ("street_identity", f"{house}||{postal}"),
            ("brand", brand_for(name)),
            ("property_code", ""),
            ("official_url", p.get("websiteUri", "") or ""),
            ("latitude", (p.get("location") or {}).get("latitude")),
            ("longitude", (p.get("location") or {}).get("longitude")),
            ("corridor", postal_to_corridor.get(postal, "")),
            ("assignment_basis", "postal_code"),
            ("assignment_value", postal),
            ("lanes", ["COMPETITOR_LEAD_BRINGFIDO", "GOOGLE_PLACES_VERIFICATION"]),
            ("best_tier", 3),
            ("policy_state", "POLICY_NOT_VERIFIED"),
            ("policy_note", "Identity evidence never establishes a pet policy."),
            ("evidence", [OrderedDict([
                ("lane", "COMPETITOR_LEAD_BRINGFIDO"),
                ("source_url", cand["bringfido_url"]),
                ("name", name),
                ("note", "identity proposed by a BringFido lead; confirmed by an independent Google Places "
                         "record at an admitted postal code before admission -- name alone never qualified it"),
            ]), OrderedDict([
                ("lane", "GOOGLE_PLACES_VERIFICATION"),
                ("source_url", "https://places.googleapis.com/v1/places:searchText"),
                ("place_id", p.get("id", "")),
                ("formatted_address", p.get("formattedAddress", "")),
                ("business_status", p.get("businessStatus", "")),
            ])]),
        ])
        additions.append(addition)

    out = OrderedDict([
        ("schema", "ptf-tampa-fl-v2-closure-census-additions/1.0"),
        ("work_order", "PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002"),
        ("candidates_considered", len(candidates)),
        ("excluded_outside_before_lookup", len(EXCLUDED_OUTSIDE)),
        ("admitted", len(additions)),
        ("rejected", len(rejected)),
        ("rejected_rows", rejected),
        ("additions", additions),
    ])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("candidates", len(candidates), "admitted", len(additions), "rejected", len(rejected))
    for r in rejected:
        print(" REJECT", r["name"], r["reason"])
    for a in additions:
        print(" ADD", a["canonical_name"], a["brand"], a["postal_code"])


if __name__ == "__main__":
    main()
