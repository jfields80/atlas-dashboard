"""PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001 -- the attended-browser ROUTE recorder.

Choice's own sitemap timed out to the plain client and every Firecrawl engine was refused on Choice's city pages
(0 credits), so Choice's routes are read in the SUPPORTED ATTENDED BROWSER off the brand's OWN directory page:
navigate, then the accessibility tree's link hrefs -- no JS exfiltration, no relay, nothing bypassed.

Each call appends one directory surface (a JSON file: surface, family, host, stated_total, routes [[name, href]])
to ``markets/staging/minneapolis-mn/raw_captures/browser_route_discovery_001.json``. The recording clock stamps the
batch (never typed). A route is a LEAD: the property's own page decides identity and membership.

Usage:
  python -m scripts.pettripfinder.minneapolis_mn_browser_route_recorder_001 <batch.json>
"""
import json
import os
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "minneapolis-mn", "raw_captures",
                   "browser_route_discovery_001.json")


def main(path):
    batch = json.load(open(path, encoding="utf-8"))
    doc = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else OrderedDict([
        ("schema", "ptf-browser-route-discovery/1.0"),
        ("work_order", "PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001"),
        ("capture_method", "claude-in-chrome navigate + accessibility-tree read of the brand's OWN directory page "
                           "(hrefs only; no JS exfiltration, no relay, no bypass)"),
        ("a_route_is_not_a_policy", "Only property routes are read; the property's own page decides identity."),
        ("surfaces", []), ("routes", [])])
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    doc["surfaces"].append(OrderedDict([("surface", batch["surface"]), ("family", batch["family"]),
                                        ("stated_total", batch.get("stated_total")),
                                        ("routes_read", len(batch["routes"])), ("recorded_at", stamp),
                                        ("note", batch.get("note", ""))]))
    seen = {r["route"] for r in doc["routes"]}
    for name, href in batch["routes"]:
        route = href if href.startswith("http") else batch["host"] + href
        if route in seen:
            continue
        seen.add(route)
        doc["routes"].append(OrderedDict([("family", batch["family"]), ("route", route), ("listed_name", name),
                                          ("lane", "BRAND_SITEMAP"), ("found_in", batch["surface"]),
                                          ("discovery_lane", "ATTENDED_BROWSER_BRAND_DIRECTORY"),
                                          ("recorded_at", stamp)]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("routes now", len(doc["routes"]), "recorded_at", stamp)


if __name__ == "__main__":
    main(sys.argv[1])
