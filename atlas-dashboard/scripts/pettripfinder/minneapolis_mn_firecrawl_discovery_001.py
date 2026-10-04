"""PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001 -- Phase 12E: Firecrawl ROUTE DISCOVERY on the two Firecrawl-routed families
whose own inventory refused a plain client (Choice: sitemap timeout; IHG: sitemap 403).

The committed route table sends CHOICE (and the www.choicehotels.com domain) and IHG to Firecrawl on a measured
decision. Before this order can put a Choice or IHG identity on the property-page ladder it needs the property's own
route, and the brand's own CITY page lists every property near that city with its canonical property route. One
rendered fetch of that page (one plan credit on success, zero on refusal) replaces a sitemap walk the plain client
could not make. The page is persisted by sha256 under data/acquisition/minneapolis_mn_firecrawl_discovery/ and only
the property ROUTES are read from it -- never a policy.

Attempt cap: 20 pages. Credit floor: 120 (a reserve kept for other orders on the shared plan).

Output: launch_packages/pettripfinder/markets/reports/minneapolis_mn_firecrawl_discovery_001.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import firecrawl_capture as FC  # noqa: E402

WORK_ORDER = "PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001"
DOCS = os.path.join(_DASH, "data", "acquisition", "minneapolis_mn_firecrawl_discovery")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports", "minneapolis_mn_firecrawl_discovery_001.json")
CAP = 20
FLOOR = 120
PAGES = [
    # CHOICE and IHG are routed to Firecrawl by the committed route table (Choice: the plain client's sitemap read
    # times out; IHG: 403). The brand's own CITY page beats its sitemap (standing rule) and lists every property NEAR
    # that city, so a handful of Twin Cities pages -- both downtowns, the airport / Bloomington cluster and the four
    # suburban quadrants -- covers the admitted corridors; the refused neighbours (Rochester, Duluth, St. Cloud,
    # Mankato, Stillwater) never get a page.
    ("CHOICE", "https://www.choicehotels.com/minnesota/minneapolis/hotels"),
    ("CHOICE", "https://www.choicehotels.com/minnesota/st-paul/hotels"),
    ("CHOICE", "https://www.choicehotels.com/minnesota/bloomington/hotels"),
    ("CHOICE", "https://www.choicehotels.com/minnesota/eagan/hotels"),
    ("CHOICE", "https://www.choicehotels.com/minnesota/burnsville/hotels"),
    ("CHOICE", "https://www.choicehotels.com/minnesota/roseville/hotels"),
    ("CHOICE", "https://www.choicehotels.com/minnesota/maple-grove/hotels"),
    ("CHOICE", "https://www.choicehotels.com/minnesota/woodbury/hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/minneapolis-hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/st-paul-hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/bloomington-hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/eagan-hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/burnsville-hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/roseville-hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/maple-grove-hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/plymouth-hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/woodbury-hotels"),
    ("IHG", "https://www.ihg.com/destinations/us/en/united-states/minnesota/eden-prairie-hotels"),
]
_CHOICE = re.compile(r"(?:https://www\.choicehotels\.com)?/(minnesota)/([a-z-]+)/([a-z-]+)-hotels/(mn[a-z0-9]{3,4})\b")
_IHG = re.compile(r"(?:https://www\.ihg\.com)?/([a-z]+)/hotels/us/en/([a-z-]+)/([a-z0-9]{5})/hoteldetail")


def _route(fam, m):
    """(route, code) for a match on the brand's own page."""
    if fam == "CHOICE":
        return ("https://www.choicehotels.com/%s/%s/%s-hotels/%s" % (m.group(1), m.group(2), m.group(3), m.group(4)),
                m.group(4))
    return ("https://www.ihg.com/%s/hotels/us/en/%s/%s/hoteldetail" % (m.group(1), m.group(2), m.group(3)),
            m.group(3))


def main():
    os.makedirs(DOCS, exist_ok=True)
    before = FC.credits_remaining()
    pages, routes, seen = [], [], set()
    prior = {}
    if os.path.exists(OUT):
        for p in json.load(open(OUT, encoding="utf-8")).get("pages", []):
            if p.get("sha256") or p.get("error"):
                prior[p["url"]] = p
    for fam, url in PAGES[:CAP]:
        if url in prior:
            # PAY ONCE PER PAGE: a page this order already fetched (or was refused) is re-read from its persisted
            # document, never bought again.
            row = OrderedDict(prior[url])
            html = ""
            if row.get("sha256") and os.path.exists(os.path.join(DOCS, row["sha256"] + ".html")):
                html = open(os.path.join(DOCS, row["sha256"] + ".html"), encoding="utf-8").read()
            rx = _CHOICE if fam == "CHOICE" else _IHG
            n = 0
            for m in rx.finditer(html):
                route, code = _route(fam, m)
                if (fam, code) in seen:
                    continue
                seen.add((fam, code))
                n += 1
                routes.append(OrderedDict([("family", fam), ("route", route), ("property_code", code),
                                           ("lane", "BRAND_SITEMAP"), ("found_in", url), ("found_in_sha256", row.get("sha256")),
                                           ("discovery_lane", "FIRECRAWL_BRAND_CITY_PAGE")]))
            row["new_routes"] = n
            row["reused_persisted_document"] = True
            pages.append(row)
            continue
        live = FC.credits_remaining()
        if live is not None and live <= FLOOR:
            pages.append(OrderedDict([("url", url), ("stopped", "CREDIT_FLOOR")]))
            break
        row = OrderedDict([("family", fam), ("url", url)])
        try:
            r = FC.fetch(url, profile=FC.ROUTED_PROFILE)
            html = r.get("html") or ""
            sha = hashlib.sha256(html.encode("utf-8")).hexdigest() if html else ""
            if html:
                open(os.path.join(DOCS, sha + ".html"), "w", encoding="utf-8", newline="").write(html)
            row.update(status=r.get("status"), ok=r.get("ok"), bytes=len(html.encode("utf-8")), sha256=sha,
                       credits_used=r.get("credits_used"), final_url=r.get("final_url"),
                       captured_at=(r.get("provenance") or {}).get("captured_at"))
            rx = _CHOICE if fam == "CHOICE" else _IHG
            n = 0
            for m in rx.finditer(html):
                route, code = _route(fam, m)
                if (fam, code) in seen:
                    continue
                seen.add((fam, code))
                n += 1
                routes.append(OrderedDict([("family", fam), ("route", route), ("property_code", code),
                                           ("lane", "BRAND_SITEMAP"), ("found_in", url), ("found_in_sha256", sha),
                                           ("discovery_lane", "FIRECRAWL_BRAND_CITY_PAGE")]))
            row["new_routes"] = n
        except Exception as exc:  # noqa: BLE001
            row.update(error="%s: %s" % (type(exc).__name__, FC.redact(str(exc))[:200]))
        pages.append(row)
        print(row, flush=True)
        time.sleep(2)
    after = FC.credits_remaining()
    doc = OrderedDict([
        ("schema", "ptf-firecrawl-discovery/1.0"), ("work_order", WORK_ORDER), ("market_id", "minneapolis-mn"),
        ("lane", "FIRECRAWL (route discovery on Firecrawl-routed family domains; billed in plan credits, no USD)"),
        ("authorization", OrderedDict([("granted_by", "existing plan credits under the standing bounded-cohort doctrine; "
                                                      "no new spend"), ("cap_attempts", CAP), ("credit_floor", FLOOR)])),
        ("credits", OrderedDict([("before", before), ("after", after),
                                 ("delta", (before - after) if before is not None and after is not None else None)])),
        ("a_route_is_not_a_policy", "Only property routes are read from these pages; nothing here carries a policy."),
        ("pages", pages), ("route_count", len(routes)), ("routes", routes),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("routes", len(routes), "credits", before, "->", after)


if __name__ == "__main__":
    main()
