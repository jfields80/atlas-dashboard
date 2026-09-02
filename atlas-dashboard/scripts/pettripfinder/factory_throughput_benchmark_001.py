"""PTF-FACTORY-THROUGHPUT-HARDENING-001 Part C -- the benchmark.

    python scripts/pettripfinder/factory_throughput_benchmark_001.py \
        --regression-runs data/regression/targeted data/regression/full \
        --out launch_packages/pettripfinder/reports/factory_throughput_001_benchmark.json

Two measurements, no spend, no authority change:

1. THE LADDER REPLAY. Dayton's committed evidence inventory -- the free-static
   capture report, the attended capture report and the owned-evidence replay
   from PTF-DAYTON-OH-HARDENED-REVALIDATION-001 -- is replayed through the
   acquisition ladder planner exactly as it stood, read-only. The replay
   counts how many rows the planner would have routed to each lane, and what
   the attended lane would have been left with had Firecrawl been evaluated
   first for the families the route table already sends there.

   The attended-page reduction is an ESTIMATE bounded two ways: the upper
   bound assumes every Firecrawl candidate answers (100%); the expected case
   applies the publication-grade rate the route decisions measured for those
   families. Neither is a promise; the plan is what a future market runs.

2. THE REGRESSION FLOW. Timings from regression_lanes runs (targeted lanes,
   assembly, the single broad regression) against the numbers Dayton
   APPLICATION-002 recorded: 337 minutes total, ~45 of actual application,
   ~37 minutes per full regression, several of them.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import ladder as L  # noqa: E402

SCHEMA = "ptf-factory-throughput-benchmark/1.0"
WORK_ORDER = "PTF-FACTORY-THROUGHPUT-HARDENING-001"
REPORTS = _REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"

#: What Dayton APPLICATION-002 cost, from its own closeout.
DAYTON_APPLICATION_002 = OrderedDict((
    ("work_order", "PTF-DAYTON-OH-HARDENED-APPLICATION-002"),
    ("total_minutes", 337),
    ("actual_application_minutes", 45),
    ("full_regression_minutes_each", 37),
    ("epoch_pin_failures", 85),
    ("modules_with_epoch_pin_failures", 19),
))

#: Publication-grade rates the route decisions measured for the families the
#: table sends to Firecrawl. Used only to state an EXPECTED case beside the
#: upper bound; each is quoted with the order that measured it.
MEASURED_FIRECRAWL_RATES: Dict[str, Dict] = OrderedDict((
    ("IHG", {"rate": 5 / 5, "sample": 5, "measured_by": "PTF-IHG-FIRECRAWL-DECISION-009"}),
    ("WYNDHAM", {"rate": 7 / 7, "sample": 7, "measured_by": "PTF-WYNDHAM-FIRECRAWL-DECISION-008"}),
    ("CHOICE", {"rate": 28 / 30, "sample": 30,
                "measured_by": "PTF-FIRECRAWL-CHOICE-VALIDATION-004 (28 publication-grade "
                               "of 30 effective attempts, identity failures excluded)"}),
))


def _read(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ladder_replay(market_id: str = "dayton-oh") -> Dict:
    prefix = market_id.replace("-", "_")
    static = _read(REPORTS / ("%s_free_static_capture_001.json" % prefix))
    attended = _read(REPORTS / ("%s_attended_capture_001.json" % prefix))
    owned = _read(REPORTS / ("%s_owned_evidence_replay_001.json" % prefix))

    # As it happened: owned -> static -> attended, Firecrawl never evaluated.
    as_run = L.plan_document(
        L.rows_from_reports(static_report=static, attended_report=attended,
                            owned_report=owned),
        market_id=market_id, work_order=WORK_ORDER)
    # The decision point the ladder inserts: after the static lane, before
    # anyone opens a browser. Owned evidence counts only where the repository
    # holds a corroborating capture (rows_from_reports applies that rule).
    at_decision_point = L.plan_document(
        L.rows_from_reports(static_report=static, owned_report=owned),
        market_id=market_id, work_order=WORK_ORDER)

    attended_rows = attended.get("results") or []
    attended_by_family = Counter(r.get("brand") for r in attended_rows)
    attended_bound = sum(1 for r in attended_rows
                         if (r.get("identity_binding") or {}).get("bound"))
    candidates = [d for d in at_decision_point["decisions"]
                  if d["next_lane"] == L.FIRECRAWL]
    candidate_keys = {d["identity_key"] for d in candidates}
    attended_that_were_candidates = [r for r in attended_rows
                                     if r["identity_key"] in candidate_keys]
    by_family = Counter(d["family"] for d in candidates)
    expected_answered = sum(n * MEASURED_FIRECRAWL_RATES.get(f, {"rate": 0.0})["rate"]
                            for f, n in by_family.items())
    unresolved_at_decision = at_decision_point["attended_pressure"]["unresolved_routed"]
    to_browser_without_ladder = [d for d in at_decision_point["decisions"]
                                 if not d["settled"] and d["next_lane"] in
                                 (L.FIRECRAWL, L.ATTENDED_BROWSER)]
    to_browser_with_ladder = [d for d in at_decision_point["decisions"]
                              if not d["settled"] and d["next_lane"] == L.ATTENDED_BROWSER]

    return OrderedDict((
        ("market_id", market_id),
        ("inputs", OrderedDict((
            ("static_report", static.get("work_order")),
            ("static_rows", len(static.get("rows") or [])),
            ("static_outcomes", OrderedDict(sorted(Counter(
                r["outcome"] for r in static.get("rows") or []).items()))),
            ("attended_rows", len(attended_rows)),
            ("attended_by_family", OrderedDict(sorted(attended_by_family.items()))),
            ("attended_identity_bound", attended_bound),
            ("owned_rows", len(owned.get("rows") or [])),
        ))),
        ("as_run", OrderedDict((
            ("by_next_lane", as_run["by_next_lane"]),
            ("settled", as_run["settled"]),
            ("note", "owned -> static -> attended; Firecrawl never evaluated"),
        ))),
        ("at_the_decision_point", OrderedDict((
            ("unresolved_routed", unresolved_at_decision),
            ("by_next_lane_unsettled", at_decision_point["by_next_lane_unsettled"]),
            ("firecrawl_candidates_by_family", OrderedDict(sorted(by_family.items()))),
            ("attended_pressure", at_decision_point["attended_pressure"]),
            ("firecrawl_not_candidate_reasons", OrderedDict(sorted(Counter(
                d["firecrawl_reason"] for d in at_decision_point["decisions"]
                if not d["settled"] and d["next_lane"] != L.FIRECRAWL).items()))),
        ))),
        ("attended_page_reduction", OrderedDict((
            ("attended_pages_dayton_actually_opened", len(attended_rows)),
            ("of_which_firecrawl_candidates", len(attended_that_were_candidates)),
            ("rows_headed_to_a_browser_without_the_ladder", len(to_browser_without_ladder)),
            ("rows_headed_to_a_browser_with_the_ladder_upper_bound", len(to_browser_with_ladder)),
            ("firecrawl_candidates", len(candidates)),
            ("expected_firecrawl_answers", round(expected_answered, 1)),
            ("rows_headed_to_a_browser_with_the_ladder_expected",
             round(len(to_browser_with_ladder) + (len(candidates) - expected_answered), 1)),
            ("reduction_upper_bound_share",
             round(len(candidates) / len(to_browser_without_ladder), 4)
             if to_browser_without_ladder else 0.0),
            ("reduction_expected_share",
             round(expected_answered / len(to_browser_without_ladder), 4)
             if to_browser_without_ladder else 0.0),
            ("measured_rates_used", MEASURED_FIRECRAWL_RATES),
            ("credits_upper_bound", len(candidates)),
            ("credits_note", "one credit per scrape is the benchmark-002 figure; "
                             "Detroit PASS-008 measured 0.95 per ATTEMPT including "
                             "engine fallthrough, so budget the candidate count "
                             "as the floor and read the credit delta as the truth"),
            ("caveat", "the attended lane batched a whole brand per session in "
                       "Dayton, so pages are not sessions; the saving is in "
                       "rows that never need a person, not in minutes per page"),
        ))),
        ("safety", OrderedDict((
            ("paid_provider_calls", 0),
            ("usd_spent", 0.0),
            ("credits_spent", 0),
            ("authority_changed", False),
        ))),
    ))


def regression_flow(run_dirs: Sequence[Path], *, assembly_seconds: Optional[float] = None,
                    assembly_bundle_sha256: str = "",
                    full_regression_seconds: Optional[float] = None) -> Dict:
    from scripts.pettripfinder import regression_lanes as RL
    runs = []
    for run_dir in run_dirs:
        run_dir = Path(run_dir)
        doc = None
        for name in ("run.json", "summary.json"):
            if (run_dir / name).is_file():
                doc = _read(run_dir / name)
                break
        if doc is None:
            doc = RL.read_run(run_dir)
        timing = doc.get("timing") or doc.get("chunks") or []
        seconds = sum(float(t.get("seconds", 0)) for t in timing) or float(
            doc.get("total_seconds", 0))
        runs.append(OrderedDict((
            ("run_dir", str(run_dir)),
            ("label", doc.get("label") or ",".join(doc.get("lanes") or [])),
            ("market", doc.get("market")),
            ("collected", doc.get("collected")),
            ("failed", doc.get("failed")),
            ("seconds", round(seconds, 1)),
            ("minutes", round(seconds / 60.0, 1)),
            ("timing", timing),
        )))
    lane_seconds = sum(r["seconds"] for r in runs)
    projected = OrderedDict((
        ("targeted_lanes_minutes", round(lane_seconds / 60.0, 1)),
        ("assembly_minutes", round((assembly_seconds or 0) / 60.0, 1)),
        ("full_regression_minutes", round((full_regression_seconds or 0) / 60.0, 1)),
        ("pin_edits", "three JSON files plus the order's own suite; no module hunt"),
        ("expected_engineering_overhead_minutes",
         round((lane_seconds + (assembly_seconds or 0) + (full_regression_seconds or 0))
               / 60.0, 1)),
        ("note", "targeted lanes are run once per pin-fix cycle (each a few "
                 "minutes); the full regression runs ONCE, after the commit"),
    ))
    return OrderedDict((
        ("old", DAYTON_APPLICATION_002),
        ("old_regression_overhead_minutes",
         DAYTON_APPLICATION_002["total_minutes"]
         - DAYTON_APPLICATION_002["actual_application_minutes"]),
        ("new_runs", runs),
        ("assembly", OrderedDict((("seconds", assembly_seconds),
                                  ("bundle_sha256", assembly_bundle_sha256)))),
        ("projected_new_market_overhead", projected),
    ))


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--market", default="dayton-oh")
    p.add_argument("--regression-runs", nargs="*", default=[])
    p.add_argument("--assembly-seconds", type=float, default=None)
    p.add_argument("--assembly-bundle-sha256", default="")
    p.add_argument("--full-regression-seconds", type=float, default=None)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    doc = OrderedDict((
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("ladder_replay", ladder_replay(args.market)),
        ("regression_flow", regression_flow(
            [Path(r) for r in args.regression_runs],
            assembly_seconds=args.assembly_seconds,
            assembly_bundle_sha256=args.assembly_bundle_sha256,
            full_regression_seconds=args.full_regression_seconds)),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(doc["ladder_replay"]["attended_page_reduction"], indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
