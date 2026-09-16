"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 24 quality pass: the
Wyndham first-party property-SERVICE lane (cloned from the Savannah GA
helper; Augusta tokens), replacing the unreliable ``/overview`` page this
order already proved redirects to a non-deterministic shared search hub.

The technique (already measured working on a prior market, not invented
here): a plain HTTPS GET of the property's own overview URL still returns,
for most routes, the page's Hotel JSON-LD before any client-side redirect --
its ``identifier`` is the brand's own numeric property id. That id feeds
Wyndham's own property-service endpoint
(``/BWSServices/services/search/property/search?propertyId=<id>``), the
exact JSON the real page renders from, whose ``hotelPolicies.petpolicy`` is
the property's own text and whose address fields are the property's own --
a stable, reliable, per-property document distinct from the volatile hub
page. A route whose overview page itself 200s into the brand search hub
(``/hotels/...``) is a RETIRED ROUTE, recorded as such, not a refusal.

Output:
  launch_packages/pettripfinder/markets/reports/augusta_ga_wyndham_lane_009.json
  data/acquisition/augusta_ga_wyndham_009/<sha256>.bin
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

from scripts.pettripfinder import augusta_ga_brand_inventory_001 as B  # noqa: E402

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
CENSUS = os.path.join(PKG, "identity_census_proposed", "augusta-ga.json")
PLAN = os.path.join(PKG, "markets", "reports", "augusta_ga_acquisition_cost_plan_003.json")
OUT = os.path.join(PKG, "markets", "reports", "augusta_ga_wyndham_lane_009.json")
B.DOCS = os.path.join(_DASH, "data", "acquisition", "augusta_ga_wyndham_009")
API = ("https://www.wyndhamhotels.com/BWSServices/services/search/property/search?isOverviewNeeded=true"
       "&propertyId=%s&isAmenitiesNeeded=false&channelId=tab&language=en-us&isRoomAmenitiesNeeded=false")


def wyndham_targets():
    plan = json.load(open(PLAN, encoding="utf-8"))
    census = json.load(open(CENSUS, encoding="utf-8"))
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    out = OrderedDict()
    for d in plan["decisions"]:
        if d["family"] != "WYNDHAM":
            continue
        h = by_key.get(d["identity_key"])
        url = (h.get("official_url") if h else None) or d.get("url")
        if url and url.rstrip("/").endswith("overview"):
            out[d["identity_key"]] = url
    return out


def read(identity_key, url):
    st = B.Stats()
    row, body = B.fetch(url, st, timeout=40)
    rec = OrderedDict([("identity_key", identity_key), ("overview_url", url), ("overview_status", row["status"]),
                       ("overview_final_url", row["final_url"])])
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
    rec.update(OrderedDict([("property_id", pid), ("api_url", API % pid), ("api_status", arow["status"])]))
    try:
        p = json.loads(abody)["properties"][0]
    except Exception as exc:  # noqa: BLE001
        rec["error"] = "property service unreadable: %s" % exc
        return rec
    hp = p.get("hotelPolicies") or {}
    rec.update(OrderedDict([
        ("name", p.get("hotelName") or p.get("name")), ("street", p.get("address1")), ("city", p.get("city")),
        ("state", p.get("stateCode")), ("postal_code", p.get("postalCode")), ("phone", p.get("phone1")),
        ("latitude", p.get("latitude")), ("longitude", p.get("longitude")),
        ("unique_url", p.get("uniqueUrl")),
        ("pet_indicator", hp.get("petPolicyindicator")),
        ("pet_policy_text", re.sub(r"[ \t ]+", " ", hp.get("petpolicy") or "").strip()),
        ("api_content_bytes", arow["bytes"]), ("api_content_sha256", arow["sha256"]),
    ]))
    return rec


def main():
    t0 = time.time()
    targets = wyndham_targets()
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(lambda kv: read(kv[0], kv[1]), targets.items()))
    retired = [r["identity_key"] for r in rows if r.get("retired")]
    good = [r for r in rows if r.get("property_id") and not r.get("error")]
    errors = [r for r in rows if r.get("error")]
    doc = OrderedDict([
        ("schema", "ptf-wyndham-property-service-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("lane", "DIRECT_STATIC_FETCH (overview page's JSON-LD identifier + the brand's own property service)"),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("targets", len(targets)), ("resolved_via_property_service", len(good)),
        ("retired_routes_redirected_to_brand_search", len(retired)), ("errors", len(errors)),
        ("by_pet_indicator", dict(Counter(r.get("pet_indicator") for r in good))),
        ("documents_persisted_at", os.path.relpath(B.DOCS, _DASH).replace("\\", "/")),
        ("seconds", round(time.time() - t0, 1)),
        ("rows", good), ("retired_identity_keys", retired), ("error_rows", errors),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("targets", len(targets), "resolved", len(good), "retired", len(retired), "errors", len(errors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
