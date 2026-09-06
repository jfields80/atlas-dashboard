"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phase 4C/7 pass 2, the STALE-REFUSAL lane.

Pass 1 re-probed the eight families that Dayton and Cleveland recorded as
`refused_families`, because a refusal list is a MEASUREMENT with a date on it,
not a standing property of a brand. Six of the eight answered a plain client:

    IHG 200   BEST_WESTERN 200   RED_ROOF 200   CHOICE 200   MOTEL6 200   RADISSON 200
    HYATT 429 (rate limited)     ESA 403        -- still refusing

Every prior market inherited that list as gospel and walked those six brands
into a browser, or paid for them, or simply never censused them. This pass
walks them for free.

The selection is deliberately PERMISSIVE and the verification is strict: a URL
is kept when its path names Kentucky or any central-Kentucky locality this
order recognises, and admission is then decided downstream on the address the
property's own page states. Brand URL slugs are discovery leads, never policy
evidence and never an identity on their own.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.lexington_ky_brand_directory_harvest_001 import (  # noqa: E402
    CORE_LOCALITY_TOKENS, FRINGE_LOCALITY_TOKENS, NEAR_MISS_TOKENS,
    harvest_family, locality_hit, read_page_identity, REPORTS,
)

WORK_ORDER = "PTF-LEXINGTON-KY-NEW-MARKET-001"
MARKET_ID = "lexington-ky"
SCHEMA = "ptf-brand-directory-harvest/1.0"

_KY = r"(?:kentucky|/ky/|\.ky\.|-ky[-/.]|_ky_)"
_LOC = "|".join(CORE_LOCALITY_TOKENS + FRINGE_LOCALITY_TOKENS + NEAR_MISS_TOKENS)

FAMILIES = OrderedDict([
    # ihg.com/<brand>/hotels/us/en/<locality>/<code>/hoteldetail
    ("IHG", {"robots": "https://www.ihg.com/robots.txt",
             "property_re": r"ihg\.com/[a-z0-9]+/hotels/[a-z]{2}/en/[^/]*(?:%s)[^/]*/[a-z0-9]{3,7}/hoteldetail" % _LOC,
             "child_filter": r"."}),
    ("BEST_WESTERN", {"robots": "https://www.bestwestern.com/robots.txt",
                      "property_re": r"bestwestern\.com/[^\s]*(?:%s|%s)[^\s]*" % (_KY, _LOC),
                      "child_filter": r"."}),
    ("RED_ROOF", {"robots": "https://www.redroof.com/robots.txt",
                  "property_re": r"redroof\.com/[^\s]*(?:%s|%s)[^\s]*" % (_KY, _LOC),
                  "child_filter": r"."}),
    ("CHOICE", {"robots": "https://www.choicehotels.com/robots.txt",
                "property_re": r"choicehotels\.com/[^\s]*(?:%s|%s)[^\s]*" % (_KY, _LOC),
                "child_filter": r"."}),
    ("MOTEL6", {"robots": "https://www.motel6.com/robots.txt",
                "property_re": r"motel6\.com/[^\s]*(?:%s|%s)[^\s]*" % (_KY, _LOC),
                "child_filter": r"."}),
    ("RADISSON", {"robots": "https://www.radissonhotels.com/robots.txt",
                  "property_re": r"radissonhotels\.com/[^\s]*(?:%s|%s)[^\s]*" % (_KY, _LOC),
                  "child_filter": r"."}),
])

STILL_REFUSING = OrderedDict([
    ("HYATT", "robots.txt 429 to a plain client (probe 2026-09-06) -- rate limited, not walled; "
              "the ADR still forbids satisfying a Kasada interstitial."),
    ("ESA", "robots.txt 403 to a plain client (probe 2026-09-06)."),
])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--families", nargs="*", default=None)
    ap.add_argument("--max-children", type=int, default=200)
    ap.add_argument("--max-pages", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    stats = {"requests": 0}
    families = OrderedDict()
    for fam, spec in FAMILIES.items():
        if args.families and fam not in args.families:
            continue
        print("harvesting", fam, flush=True)
        families[fam] = harvest_family(fam, spec, stats, max_children=args.max_children)
        h = families[fam]
        print("  ", fam, "robots", h["robots"], "sitemaps", h["sitemaps_fetched"],
              "urls", h["urls_seen"], "property urls", len(h["property_urls"]), flush=True)

    candidates = []
    for fam, h in families.items():
        for u in h["property_urls"]:
            tok, band = locality_hit(u)
            candidates.append(OrderedDict([
                ("family", fam), ("url", u), ("locality_token", tok), ("locality_band", band),
                ("selected_by", "LOCALITY_TOKEN" if tok else "STATE_TOKEN_ONLY"),
            ]))

    to_fetch = [c for c in candidates if c["locality_band"] in ("CORE", "FRINGE")]
    if args.max_pages:
        to_fetch = to_fetch[: args.max_pages]
    print("candidates", len(candidates), "fetching", len(to_fetch), flush=True)
    pages = []
    for i, c in enumerate(to_fetch):
        c["page"] = read_page_identity(c["url"], c["family"], stats)
        pages.append(c["page"])
        if (i + 1) % 20 == 0:
            print("  fetched", i + 1, "requests", stats["requests"], flush=True)

    status_counts: "OrderedDict[str,int]" = OrderedDict()
    for p in pages:
        status_counts[str(p["status"])] = status_counts.get(str(p["status"]), 0) + 1
    by_family: "OrderedDict[str,int]" = OrderedDict()
    by_band: "OrderedDict[str,int]" = OrderedDict()
    for c in candidates:
        by_family[c["family"]] = by_family.get(c["family"], 0) + 1
        by_band[c["locality_band"] or "NONE"] = by_band.get(c["locality_band"] or "NONE", 0) + 1

    report = OrderedDict([
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("phase", "4C/7 pass 2 -- the stale-refusal lane"),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("what_this_is",
         "A first-party sitemap walk of the six families that prior markets recorded as "
         "refusing a plain client and that this order re-probed and found ANSWERING. A "
         "refusal list is a measurement with a date on it, not a property of a brand."),
        ("stale_refusal_finding",
         "Dayton (2026-09-01/02) and Cleveland recorded IHG, BEST_WESTERN, RED_ROOF, CHOICE, "
         "MOTEL6 and RADISSON as refused. Re-probed 2026-09-06 all six returned robots.txt 200. "
         "Only HYATT (429) and ESA (403) still refuse. Inheriting that list unchecked is how a "
         "market walks a free lane into an attended browser or a paid provider."),
        ("still_refusing", STILL_REFUSING),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("families", families),
        ("candidate_counts", OrderedDict([
            ("total", len(candidates)), ("by_family", by_family),
            ("by_locality_band", by_band), ("pages_fetched", len(pages)),
            ("page_status", status_counts),
        ])),
        ("candidates", candidates),
    ])

    os.makedirs(REPORTS, exist_ok=True)
    out = args.out or os.path.join(REPORTS, "lexington_ky_brand_directory_harvest_002.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print("wrote", out, flush=True)
    print("free_http_requests", stats["requests"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
