"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 13C: the Firecrawl rung, second cohort (IHG identity fill).

IHG is Firecrawl-routed on a measured decision (PTF-IHG-FIRECRAWL-DECISION-009) and refuses a plain client on its
sitemap and property pages. This order's first Firecrawl pass could only reach the IHG properties the bureau or the map
linked. IHG's own destination pages (read through Firecrawl in orlando_fl_v2_firecrawl_discovery_001) list the rest.
This pass fetches each in-market IHG property route those pages list that pass 001 did not already attempt (PAY ONCE
PER PAGE). Rows carry no census expectation -- a property code selects, the page's own address admits -- so the
adapter declines identity and persists the page; orlando_fl_v2_ihg_reread_001 reads it offline.

Same harness, same attempt cap / credit floor discipline as pass 001 (the cohort function is replaced, nothing else).

Output: launch_packages/pettripfinder/markets/reports/orlando_fl_v2_firecrawl_pass_002.json
"""
from __future__ import annotations

import os
import sys

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import orlando_fl_v2_firecrawl_pass_001 as P1  # noqa: E402

IN_MARKET_TOWNS = ("orlando", "kissimmee", "lake-buena-vista", "celebration", "davenport", "clermont", "apopka",
                   "altamonte-springs", "sanford", "lake-mary", "ocoee", "winter-garden", "winter-park", "maitland",
                   "st-cloud", "longwood", "casselberry", "oviedo", "windermere", "champions-gate", "championsgate")


def cohort(static_report):
    disc = P1.read_json(P1.DISCOVERY)
    done = P1.read_json(os.path.join(P1.REPORTS, "orlando_fl_v2_firecrawl_pass_001.json"))
    attempted = {r["requested_url"].split("?")[0].rstrip("/").lower() for r in done["rows"]}
    attempted_codes = {(r["requested_url"].split("/hoteldetail")[0].rsplit("/", 1)[-1]).lower()
                       for r in done["rows"] if "ihg.com" in r["requested_url"]}
    out = []
    for r in sorted(disc.get("routes", []), key=lambda x: x["route"]):
        if r["family"] != "IHG":
            continue
        town = r["route"].split("/us/en/", 1)[-1].split("/", 1)[0]
        if town not in IN_MARKET_TOWNS:
            continue
        if r["route"].rstrip("/").lower() in attempted or r["property_code"].lower() in attempted_codes:
            continue
        out.append(P1._D("ihg-route::" + r["property_code"], "IHG", r["route"], "IHG_DISCOVERED_ROUTE_IDENTITY_FILL",
                         "DISCOVERED", "PTF-IHG-FIRECRAWL-DECISION-009"))
    return out, []


def main(argv=None):
    P1.cohort = cohort
    argv = list(argv if argv is not None else sys.argv[1:])
    if not any(a.startswith("--out") for a in argv):
        argv += ["--out", os.path.join(P1.REPORTS, "orlando_fl_v2_firecrawl_pass_002.json")]
    if not any(a.startswith("--run-id") for a in argv):
        argv += ["--run-id", "orlando_fl_v2_firecrawl_002"]
    return P1.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
