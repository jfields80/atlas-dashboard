"""PTF-MIAMI-FL-HARDENED-SOURCE-READY-001 -- the independents' OWN sites the Places route-discovery lane found.

For every unrouted census identity that miami_fl_places_route_discovery_001 bound (street number + ZIP) to a place
carrying a website, this lane reads that site with the same reader and the same binding discipline as the
independents' policy-pages lane (miami_fl_policy_pages_lane_001.read_sites): the site's own home or policy page must
state the census house number AND ZIP, or the census phone, or its own JSON-LD street + ZIP. A Places listing never
binds a site; the site binds itself. Brand and OTA hosts are skipped here (their own lanes read them).

Output:
  launch_packages/pettripfinder/markets/staging/miami-fl/raw_captures/closure_static_rows.json
"""
from __future__ import annotations

import json
import os
import sys

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import miami_fl_policy_pages_lane_001 as PP  # noqa: E402

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
PLACES = os.path.join(PKG, "markets", "reports", "miami_fl_places_route_discovery_001.json")
CENSUS = os.path.join(PKG, "identity_census_proposed", "miami-fl.json")
OUT = os.path.join(PKG, "markets", "staging", "miami-fl", "raw_captures", "closure_static_rows.json")


def targets():
    census = {h["identity_key"]: h for h in json.load(open(CENSUS, encoding="utf-8"))["hotels"]}
    out = []
    for r in json.load(open(PLACES, encoding="utf-8"))["rows"]:
        if r.get("cohort") != "ROUTE_DISCOVERY" or not r.get("bound"):
            continue
        url = r["place"].get("website_uri") or ""
        h = census.get(r["identity_key"])
        if not url or h is None or PP.BRAND_HOSTS.search(url):
            continue
        out.append({"identity_key": h["identity_key"], "canonical_name": h["canonical_name"], "url": url,
                    "street": h.get("street", ""), "postal_code": h.get("postal_code", ""),
                    "phone": h.get("phone") or r["place"].get("phone", "")})
    return sorted(out, key=lambda t: t["identity_key"])


def main():
    PP.read_sites(targets(), OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
