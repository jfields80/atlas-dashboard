"""PTF-FORT-WAYNE-IN-NEW-MARKET-001 -- Phase 11/17 (the ladder planner).

Ask the committed acquisition ladder -- not this order's own arithmetic -- which
rung each unresolved Fort Wayne row belongs on, and what a rendered lane would
actually cost.

WHY THIS EXISTS. The shadow package first reported "16 Firecrawl candidate rows"
by counting the rows the static lane failed to answer. That number is wrong, and
wrong in the direction that spends money: ``ladder.firecrawl_candidacy`` is
EVIDENCE-AWARE, and ten of those sixteen are Marriott and Hilton, which
PTF-FIRECRAWL-HARD-LANES-003 MEASURED as a capability wall
(``FIRECRAWL_KNOWN_CAPABILITY_WALL``). Buying credits for them would reproduce a
failure the factory has already paid to learn once. A row that the static lane
merely failed on is not thereby a Firecrawl row.

The planner also separates the two reasons a row is unresolved, which look
identical in a count and are not the same problem:

  a CHANNEL failure  -- the page refused us or never hydrated. A rendered lane
                        can answer it.
  a SOURCE silence   -- the page loaded and said nothing about pets. No lane
                        changes that, and no amount of money will.

``attended_pressure`` is reported for the same reason it exists: to say, before
anyone opens a browser, how much of the queue a cheaper rung would have taken.

This module SPENDS NOTHING and requests nothing. It reads committed reports.

Output:
  launch_packages/pettripfinder/markets/reports/fort_wayne_in_ladder_plan_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import ladder as L  # noqa: E402

WORK_ORDER = "PTF-FORT-WAYNE-IN-NEW-MARKET-001"
MARKET_ID = "fort-wayne-in"
SCHEMA = "ptf-acquisition-ladder-plan/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CAPTURE = os.path.join(REPORTS, "fort_wayne_in_routing_and_static_capture_001.json")


def read_json(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def build(args):
    capture = read_json(CAPTURE)
    rows = []
    for r in capture["rows"]:
        if not r.get("url") or not r.get("outcome"):
            continue
        rows.append(L.RowEvidence(
            identity_key=r["identity_key"],
            family=r.get("brand") or "INDEPENDENT",
            url=r["url"],
            static_outcome=r.get("outcome") or ""))

    decisions = L.plan_cohort(rows)
    plain = [d.as_dict() for d in decisions]
    pressure = L.attended_pressure(decisions)

    firecrawl_rows = [d for d in plain if d["firecrawl_candidate"]]
    probe_rows = [d for d in plain if d["firecrawl_probe_eligible"]]
    walled = [d for d in plain
              if d["firecrawl_reason"] == L.NOT_CANDIDATE_KNOWN_WALL]

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "11/17 -- acquisition ladder plan and paid readiness"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("what_this_is",
         "The committed ladder's own decision for every routed Fort Wayne row, from "
         "the static lane's outcomes. Firecrawl candidacy is evidence-aware: a row "
         "the static lane failed is NOT thereby a Firecrawl row, and the families "
         "measured as a capability wall are never candidates. Nothing was requested "
         "and nothing was spent."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("credits_consumed", 0),
        ("known_capability_walls", dict(L.KNOWN_CAPABILITY_WALLS)),
        ("firecrawl_routed_families", list(L.firecrawl_routed_families())),
        ("counts", OrderedDict([
            ("rows_planned", len(plain)),
            ("by_next_lane", OrderedDict(sorted(Counter(d["next_lane"] for d in plain).items()))),
            ("by_firecrawl_reason",
             OrderedDict(sorted(Counter(d["firecrawl_reason"] for d in plain).items()))),
            ("firecrawl_candidates", len(firecrawl_rows)),
            ("firecrawl_credits_worst_case", len(firecrawl_rows)),
            ("firecrawl_probe_eligible_not_candidates", len(probe_rows)),
            ("blocked_by_a_measured_capability_wall", len(walled)),
        ])),
        ("attended_pressure", pressure if isinstance(pressure, dict)
         else getattr(pressure, "__dict__", str(pressure))),
        ("firecrawl_candidate_rows", firecrawl_rows),
        ("decisions", plain),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "fort_wayne_in_ladder_plan_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
