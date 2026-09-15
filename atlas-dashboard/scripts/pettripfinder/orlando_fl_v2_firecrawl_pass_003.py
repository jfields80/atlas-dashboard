"""PTF-ORLANDO-FL-V2-TARGETED-COVERAGE-CLOSURE-002 -- the Firecrawl rung for the targeted closure cohort.

Only targets of this order (BringFido-matched, V1 regression, corridor-critical) whose family the committed route table
sends to Firecrawl and that no earlier pass attempted are planned here. CHOICE is Firecrawl-routed on a measured
decision; its plain-client sitemap timed out in the source-ready order, so the property route below was found by a
discovery web search (a route, never a policy) and is read here once. Rows carry no census expectation (the property
code selects; the page's own address admits): the adapter declines identity and persists the page, and
orlando_fl_v2_choice_reread_001 reads it offline.

Same harness, same attempt cap / credit floor discipline as pass 001 (only the cohort function is replaced).

Output: launch_packages/pettripfinder/markets/reports/orlando_fl_v2_firecrawl_pass_003.json
"""
from __future__ import annotations

import os
import sys

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import orlando_fl_v2_firecrawl_pass_001 as P1  # noqa: E402

# (identity-fill key, family, route, why) -- corridor-critical: four-corners-davenport
CLOSURE_ROUTES = [
    ("choice-route::fla64", "CHOICE", "https://www.choicehotels.com/florida/davenport/comfort-inn-hotels/fla64",
     "CLOSURE_002_CORRIDOR_CRITICAL_FOUR_CORNERS_ROUTE_FROM_DISCOVERY_SEARCH"),
]


def cohort(static_report):
    attempted = set()
    for name in ("orlando_fl_v2_firecrawl_pass_001.json", "orlando_fl_v2_firecrawl_pass_002.json"):
        doc = P1.read_json(os.path.join(P1.REPORTS, name))
        attempted |= {r["requested_url"].split("?")[0].rstrip("/").lower() for r in doc["rows"]}
    out = []
    for key, family, url, why in CLOSURE_ROUTES:
        if url.rstrip("/").lower() in attempted:
            continue
        out.append(P1._D(key, family, url, why, "CLOSURE_ROUTED", "PTF-CHOICE-FIRECRAWL-ROUTE-TABLE"))
    return out, []


def main(argv=None):
    P1.cohort = cohort
    argv = list(argv if argv is not None else sys.argv[1:])
    if not any(a.startswith("--out") for a in argv):
        argv += ["--out", os.path.join(P1.REPORTS, "orlando_fl_v2_firecrawl_pass_003.json")]
    if not any(a.startswith("--run-id") for a in argv):
        argv += ["--run-id", "orlando_fl_v2_firecrawl_003"]
    return P1.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
