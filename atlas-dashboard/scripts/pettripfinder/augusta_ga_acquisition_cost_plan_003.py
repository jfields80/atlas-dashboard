"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 11/12/13: classify the
105-row admitted census through the REAL acquisition ladder
(scripts/pettripfinder/acquisition/ladder.py) and stop. No Firecrawl call, no
Bright Data call, no attended browser session -- this produces a plan only.

Family is derived from the brand/name/URL the census already carries (never
guessed beyond the acquisition ladder's own known families); a hotel with no
recognizable brand token is INDEPENDENT and is never a Firecrawl candidate
(the route table only lists IHG, Wyndham and Choice; an independent goes
straight to DIRECT_STATIC_FETCH-if-untried, else ATTENDED_BROWSER).

Output:
  launch_packages/pettripfinder/markets/reports/augusta_ga_acquisition_cost_plan_003.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import ladder  # noqa: E402

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
CENSUS = os.path.join(PKG, "identity_census_proposed", "augusta-ga.json")
STATIC_REPORT = os.path.join(PKG, "markets", "reports", "augusta_ga_static_lane_001.json")
OUT = os.path.join(PKG, "markets", "reports", "augusta_ga_acquisition_cost_plan_003.json")

FAMILY_TOKENS = OrderedDict([
    ("MARRIOTT", ("marriott", "fairfield inn", "courtyard", "residence inn", "springhill",
                   "towneplace", "ritz-carlton", "sheraton", "westin", "aloft", "element",
                   "four points", "delta hotels", "gaylord")),
    ("HILTON", ("hilton", "hampton inn", "homewood suites", "home2 suites", "doubletree",
                 "embassy suites", "tru by", "spark by", "livsmart", "candlewood suites")),
    ("IHG", ("holiday inn", "crowne plaza", "staybridge", "avid hotel", "candlewood suites ihg",
              "indigo")),
    ("WYNDHAM", ("wyndham", "days inn", "super 8", "baymont", "microtel", "wingate",
                  "ramada", "hawthorn suites", "travelodge", "howard johnson", "americinn",
                  "la quinta")),
    ("CHOICE", ("choice", "comfort inn", "comfort suites", "quality inn", "econo lodge",
                 "rodeway inn", "sleep inn", "clarion", "mainstay")),
    ("HYATT", ("hyatt",)),
    ("BEST_WESTERN", ("best western",)),
    ("SONESTA", ("sonesta", "woodspring")),
    ("EXTENDED_STAY_AMERICA", ("extended stay america",)),
    ("REDROOF", ("red roof",)),
    ("MOTEL6", ("motel 6", "studio 6")),
])

CANDLEWOOD_IHG_HINT = "ihg"


def family_of(hotel):
    name = (hotel.get("canonical_name") or "").lower()
    urls = " ".join(e.get("source_url", "") for e in hotel.get("evidence", [])).lower()
    if hotel.get("official_url"):
        urls += " " + hotel["official_url"].lower()
    blob = name + " " + urls
    if "candlewood" in blob:
        return "IHG"  # Candlewood Suites is always an IHG brand, never Hilton
    for family, tokens in FAMILY_TOKENS.items():
        if any(t in blob for t in tokens):
            return family
    return "INDEPENDENT"


def url_of(hotel):
    """The hotel's own first-party page only -- never an OSM node/way URL,
    which is identity evidence (a map pin), not a page the ladder can fetch
    or parse a brand property code from. No URL at all is a real, honest
    LOCAL_FREE_DISCOVERY state, not something to paper over with a map link."""
    if hotel.get("official_url") and "openstreetmap.org" not in hotel["official_url"]:
        return hotel["official_url"]
    for e in hotel.get("evidence", []):
        u = e.get("source_url", "")
        if u and "openstreetmap.org" not in u:
            return u
    return ""


def main():
    census = json.load(open(CENSUS, encoding="utf-8"))
    hotels = census["hotels"]
    static = {}
    if os.path.exists(STATIC_REPORT):
        sdoc = json.load(open(STATIC_REPORT, encoding="utf-8"))
        for row in sdoc.get("rows", []):
            for key in row.get("census_identity_keys", []):
                static[key] = row

    rows = []
    for h in hotels:
        fam = family_of(h)
        url = url_of(h)
        static_outcome = ""
        srow = static.get(h["identity_key"])
        if srow is not None:
            static_outcome = srow.get("outcome") or ""
        rows.append(ladder.RowEvidence(identity_key=h["identity_key"], family=fam, url=url,
                                        owned_state="", static_outcome=static_outcome,
                                        firecrawl_class="", attended_state=""))

    decisions = ladder.plan_cohort(rows, attended_available=True)
    pressure = ladder.attended_pressure(decisions)

    by_lane = Counter(d.next_lane for d in decisions)
    by_family = OrderedDict()
    for h, d in zip(hotels, decisions):
        fam = d.family
        by_family.setdefault(fam, Counter())[d.next_lane] += 1

    firecrawl_rows = [d for d in decisions if d.next_lane == ladder.FIRECRAWL]
    attended_rows = [d for d in decisions if d.next_lane == ladder.ATTENDED_BROWSER]
    routing_repair_rows = [d for d in decisions if "ROUTING_REPAIR" in (d.reason or "")]
    settled_rows = [d for d in decisions if d.settled]

    doc = OrderedDict([
        ("schema", "ptf-acquisition-cost-plan/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("cohort_size", len(hotels)),
        ("already_settled_no_further_lane_needed", len(settled_rows)),
        ("by_next_lane", dict(by_lane)),
        ("by_family_by_lane", {k: dict(v) for k, v in by_family.items()}),
        ("firecrawl_candidate_count", len(firecrawl_rows)),
        ("firecrawl_candidate_families", sorted(set(d.family for d in firecrawl_rows))),
        ("attended_browser_count", len(attended_rows)),
        ("attended_browser_families", dict(Counter(d.family for d in attended_rows))),
        ("routing_repair_required", [d.identity_key for d in routing_repair_rows]),
        ("attended_pressure", pressure),
        ("expected_firecrawl_credits", len(firecrawl_rows)),
        ("expected_usd", 0.0),
        ("note", "1 credit is the documented Firecrawl unit cost per prior market plans; USD not computed here "
                 "pending the vendor balance read (this script does not call the Firecrawl account API). "
                 "authorised_cap_usd=10 matches the documented factory-runbook example and prior market precedent; "
                 "NOT yet spent -- --authorise-spend has not been passed anywhere in this build."),
        ("paid_provider_calls_this_script", 0), ("usd_spent_this_script", 0.0),
        ("decisions", [d.as_dict() for d in decisions]),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("cohort", len(hotels), "by_lane", dict(by_lane), "firecrawl", len(firecrawl_rows), "attended", len(attended_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
