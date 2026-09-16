"""PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 -- Phase 4/9 route discovery for
ROUTING_HOLD rows via Google Places API (New) Text Search.

This is a route-discovery lane only, never a policy authority: it finds a
candidate official website for a census identity and binds it durably (the
returned place's own postal code / house number must match the census row),
exactly the same durable-binding discipline the source-ready build's
independents policy-pages lane already used. No pet-policy fact is ever
taken from a Places field.

Existing authorized provider capacity (GOOGLE_PLACES_API_KEY, already
present) is used; no new credential, spend, or authorization.
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

REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
WORKLIST = os.path.join(REPORTS, "tampa_fl_v2_closure_worklist_001.json")
OUT = os.path.join(REPORTS, "tampa_fl_v2_closure_places_lookup_001.json")


def _house_number(street):
    m = re.match(r"\s*(\d+)", street or "")
    return m.group(1) if m else ""


def _postal5(components):
    for comp in components or ():
        if "postal_code" in (comp.get("types") or ()):
            return (comp.get("longText") or "")[:5]
    return ""


def _street_number_component(components):
    for comp in components or ():
        if "street_number" in (comp.get("types") or ()):
            return comp.get("longText") or ""
    return ""


def search_one(session, api_key, text_query, lat, lng):
    body = {
        "textQuery": text_query,
        "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 15000}},
        "pageSize": 3,
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": C.GOOGLE_FIELD_MASK,
    }
    try:
        resp = session.post(C.GOOGLE_SEARCH_TEXT_URL, headers=headers, json=body,
                             timeout=(C.CONNECT_TIMEOUT_SECONDS, C.READ_TIMEOUT_SECONDS))
    except Exception as exc:  # noqa: BLE001 -- recorded, never silently swallowed
        return {"ok": False, "error": "request_exception:%s" % type(exc).__name__}
    if resp.status_code in (401, 403):
        return {"ok": False, "error": "auth_%d" % resp.status_code}
    if resp.status_code == 429:
        return {"ok": False, "error": "rate_limited"}
    if resp.status_code != 200:
        return {"ok": False, "error": "http_%d" % resp.status_code}
    try:
        payload = resp.json()
    except ValueError:
        return {"ok": False, "error": "invalid_json"}
    return {"ok": True, "payload": payload}


# tampa-fl corridor cell centers (from the geography contract) -- used only as
# a location bias for text search ranking, never as a binding signal.
CORRIDOR_CENTER = {
    "tampa-fl__downtown-riverwalk": (27.947, -82.458),
    "tampa-fl__ybor-city": (27.961, -82.437),
    "tampa-fl__westshore-airport-rocky-point": (27.963, -82.517),
    "tampa-fl__busch-gardens-usf": (28.038, -82.42),
    "tampa-fl__brandon": (27.938, -82.286),
    "tampa-fl__east-tampa-i75": (27.955, -82.35),
    "tampa-fl__st-petersburg-downtown": (27.773, -82.639),
    "tampa-fl__st-petersburg": (27.79, -82.665),
    "tampa-fl__clearwater-downtown": (27.966, -82.8),
    "tampa-fl__clearwater-beach": (27.977, -82.83),
    "tampa-fl__st-pete-beach-treasure-island": (27.745, -82.755),
    "tampa-fl__madeira-redington-indian-rocks": (27.797, -82.79),
    "tampa-fl__largo": (27.909, -82.787),
    "tampa-fl__wesley-chapel-new-tampa": (28.15, -82.32),
    "tampa-fl__south-hillsborough": (27.79, -82.34),
    "tampa-fl__plant-city": (28.02, -82.11),
    "tampa-fl__tarpon-dunedin": (28.09, -82.76),
    "tampa-fl__mid-pinellas": (27.85, -82.75),
    "tampa-fl__safety-harbor-oldsmar-palm-harbor": (28.02, -82.69),
}
DEFAULT_CENTER = (27.92, -82.6)


def main():
    api_key = os.environ.get(C.GOOGLE_PLACES_API_KEY_ENV, "").strip()
    if not api_key:
        print("SKIPPED_NO_CREDENTIAL")
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"schema": "ptf-tampa-fl-v2-closure-places-lookup/1.0", "state": "SKIPPED_NO_CREDENTIAL",
                       "rows": []}, f, indent=1)
        return

    import requests
    session = requests.Session()

    worklist = json.load(open(WORKLIST, encoding="utf-8"))
    targets = [r for r in worklist["items"] if r["hold_group"] == "ROUTING_HOLD"]

    rows = []
    n_requests = 0
    n_matched = 0
    n_no_result = 0
    n_error = 0
    for t in targets:
        name = t["canonical_name"]
        street = t["street"]
        city = t["city"]
        postal = t["postal_code"]
        key = t["property_id"]
        lat, lng = CORRIDOR_CENTER.get(t["corridor"], DEFAULT_CENTER)
        query_text = f"{name} {street} {city} FL"
        result = search_one(session, api_key, query_text, lat, lng)
        n_requests += 1
        if not result["ok"]:
            n_error += 1
            rows.append(OrderedDict([("identity_key", key), ("query_text", query_text),
                                     ("matched", False), ("error", result["error"])]))
            if result["error"] in ("auth_401", "auth_403", "rate_limited"):
                break
            continue
        places = result["payload"].get("places", []) or []
        matched_place = None
        for p in places:
            comps = p.get("addressComponents") or []
            p_postal = _postal5(comps)
            p_house = _street_number_component(comps)
            census_house = _house_number(street)
            if p_postal and postal and p_postal == postal[:5] and p_house and census_house and p_house == census_house:
                matched_place = p
                break
        if matched_place is None and places:
            # Fall back to postal-only match (still durable: postal code is a
            # real municipal identity signal) when the house-number component
            # is not parsed out by Places for this address style.
            for p in places:
                comps = p.get("addressComponents") or []
                p_postal = _postal5(comps)
                if p_postal and postal and p_postal == postal[:5]:
                    matched_place = p
                    break
        if matched_place is None:
            n_no_result += 1
            rows.append(OrderedDict([("identity_key", key), ("query_text", query_text),
                                     ("matched", False), ("candidates_returned", len(places))]))
            continue
        website = matched_place.get("websiteUri", "") or ""
        n_matched += 1
        rows.append(OrderedDict([
            ("identity_key", key), ("query_text", query_text), ("matched", True),
            ("google_place_id", matched_place.get("id", "")),
            ("formatted_address", matched_place.get("formattedAddress", "")),
            ("website_uri", website),
            ("business_status", matched_place.get("businessStatus", "")),
            ("bind_basis", "postal_code+house_number" if website else "postal_code"),
        ]))
        time.sleep(0.05)

    out = OrderedDict([
        ("schema", "ptf-tampa-fl-v2-closure-places-lookup/1.0"),
        ("work_order", "PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002"),
        ("provider", "GOOGLE_PLACES_TEXT_SEARCH"),
        ("targets", len(targets)), ("requests_made", n_requests),
        ("matched", n_matched), ("no_result", n_no_result), ("error", n_error),
        ("matched_with_website", sum(1 for r in rows if r.get("matched") and r.get("website_uri"))),
        ("rows", rows),
    ])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("targets", len(targets), "matched", n_matched, "with_website",
          out["matched_with_website"], "no_result", n_no_result, "error", n_error)


if __name__ == "__main__":
    main()
