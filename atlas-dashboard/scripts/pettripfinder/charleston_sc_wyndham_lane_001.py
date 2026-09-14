"""PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 -- Phase 10/11: the Wyndham first-party lane (plain client).

Wyndham's property pages render the pet policy client-side, but both documents
the page is built from answer a plain HTTPS client:

  1. the property's own OVERVIEW page (its Hotel JSON-LD carries the brand
     property ``identifier``); a route that now redirects to the brand's city
     search (``/hotels/...``) is a RETIRED ROUTE, recorded as such, never a refusal;
  2. the brand's own property service
     ``/BWSServices/services/search/property/search?propertyId=<id>`` -- the
     same JSON the page renders -- whose ``hotelPolicies.petpolicy`` is the
     exact text of the page's ``.pet-policy-desc`` element (verified in the
     attended browser against La Quinta Atlanta Midtown - Buckhead, 53076) and
     whose address fields are the property's own.

Both documents are persisted as returned, addressed by sha256, under
``data/acquisition/charleston_sc_wyndham_001/``. The pet quote is read from the
property-service document, so ``h``/``b`` on each row are that document's.

Routes selected: every en-us South Carolina property route the brand's own sitemap
lists whose city segment is a Charleston-area or observed-neighbour place. A
route admits nothing -- the postal code the property service states decides.

Output:
  data/acquisition/charleston_sc_attended/wyndham_rows.json   (the capture helper's input shape)
  launch_packages/pettripfinder/markets/reports/charleston_sc_wyndham_lane_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import charleston_sc_brand_inventory_001 as B  # noqa: E402

WORK_ORDER = "PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "charleston-sc"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
BRAND = os.path.join(REPORTS, "charleston_sc_brand_inventory_001.json")
RAW_OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "charleston-sc", "raw_captures", "wyndham_rows.json")
REPORT_OUT = os.path.join(REPORTS, "charleston_sc_wyndham_lane_001.json")
B.DOCS = os.path.join(_DASH, "data", "acquisition", "charleston_sc_wyndham_001")
API = ("https://www.wyndhamhotels.com/BWSServices/services/search/property/search?isOverviewNeeded=true"
       "&propertyId=%s&isAmenitiesNeeded=false&channelId=tab&language=en-us&isRoomAmenitiesNeeded=false")

_ROUTE = re.compile(r"^https://www\.wyndhamhotels\.com/(?![a-z]{2}-[a-z]{2}/)[a-z0-9-]+/([a-z-]+)-south-carolina/[a-z0-9-]+/overview$")
PLACES = set(B.LEAD_TOKENS)  # hyphenated city segments, e.g. kill-devil-hills


def routes():
    doc = json.load(open(BRAND, encoding="utf-8"))
    out = []
    for r in doc["families"]["WYNDHAM"]["routes"]:
        m = _ROUTE.match(r["route"])
        if m and m.group(1) in PLACES:
            out.append(r["route"])
    return sorted(set(out))


def read(url):
    st = B.Stats()
    row, body = B.fetch(url, st, timeout=40)
    rec = OrderedDict([("u", url), ("overview_status", row["status"]), ("overview_final_url", row["final_url"]),
                       ("overview_sha256", row["sha256"]), ("overview_bytes", row["bytes"])])
    final = row["final_url"] or ""
    if row["status"] == 200 and "/hotels/" in final.split("wyndhamhotels.com", 1)[-1][:8]:
        rec["retired"] = True
        return rec
    text = body.decode("utf-8", "replace")
    m = re.search(r'"@type":"Hotel"[^<]*?"identifier":"(\d+)"', text)
    if not m:
        rec["error"] = "no Hotel JSON-LD identifier on the overview page (status %s)" % row["status"]
        return rec
    pid = m.group(1)
    arow, abody = B.fetch(API % pid, st, timeout=40)
    rec.update(OrderedDict([("id", pid), ("api_url", API % pid), ("api_status", arow["status"])]))
    try:
        p = json.loads(abody)["properties"][0]
    except Exception as exc:  # noqa: BLE001
        rec["error"] = "property service unreadable: %s" % exc
        return rec
    hp = p.get("hotelPolicies") or {}
    rec.update(OrderedDict([
        ("n", p.get("hotelName") or p.get("name")), ("st", p.get("address1")), ("ci", p.get("city")),
        ("rg", p.get("stateCode")), ("z", p.get("postalCode")), ("ph", p.get("phone1")),
        ("lat", p.get("latitude")), ("lng", p.get("longitude")),
        ("unique_url", p.get("uniqueUrl")),
        ("pet_indicator", hp.get("petPolicyindicator")),
        ("p", re.sub(r"[ \t ]+", " ", hp.get("petpolicy") or "").strip()),
        ("b", arow["bytes"]), ("h", arow["sha256"]),
    ]))
    return rec


def main():
    t0 = time.time()
    urls = routes()
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(read, urls))
    retired = [r["u"] for r in rows if r.get("retired")]
    good = [r for r in rows if r.get("id") and not r.get("error")]
    raw = OrderedDict([("rows", good), ("retired_routes_redirected_to_brand_search", retired),
                       ("errors", [r for r in rows if r.get("error")])])
    os.makedirs(os.path.dirname(RAW_OUT), exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(raw, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    rep = OrderedDict([
        ("schema", "ptf-brand-first-party-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("lane", "DIRECT_STATIC_FETCH (overview page + the brand's own property service)"),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("routes_selected", len(urls)), ("read", len(good)), ("retired", len(retired)),
        ("errors", len(raw["errors"])),
        ("by_pet_indicator", dict(Counter(r.get("pet_indicator") for r in good))),
        ("documents_persisted_at", os.path.relpath(B.DOCS, _DASH).replace("\\", "/")),
        ("seconds", round(time.time() - t0, 1)),
        ("rows", [OrderedDict((k, r.get(k)) for k in ("u", "id", "n", "st", "ci", "z", "overview_sha256", "h", "b", "pet_indicator"))
                  for r in good]),
        ("retired_routes", retired), ("error_rows", raw["errors"]),
    ])
    with open(REPORT_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("selected", len(urls), "read", len(good), "retired", len(retired), "errors", len(raw["errors"]),
          "seconds", rep["seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
