"""PTF-IHG-FIRECRAWL-DECISION-009 -- the live Milwaukee IHG run.

Five properties, through the newly applied production route, with the guard the
previous work order earned the hard way.

WHY THIS DOES NOT REUSE THE RESUME RUNNER
-----------------------------------------
PTF-WYNDHAM-FIRECRAWL-DECISION-008 ran its live pass through the generic resume
runner, which selects every Firecrawl-ELIGIBLE property. The moment the Wyndham
route was applied, that set also contained the four Choice rows already
completed in RESUME-007, and they were acquired a second time. Four wasted
credits, no data harm, entirely avoidable.

So the subject set here is constructed by ``brand == IHG`` and the count is
ASSERTED before a single request is made. If it is not exactly five, this run
aborts rather than acquiring whatever it happened to find.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import failures as F                 # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_capture as FC       # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL            # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.acquisition import wyndham_firecrawl_decision_008 as WY  # noqa: E402
from scripts.pettripfinder.milwaukee_acquisition_run_001 import SpendMeter  # noqa: E402

WORK_ORDER = "PTF-IHG-FIRECRAWL-DECISION-009"
MARKET = "milwaukee-wi"
BRAND = "IHG"
EXPECTED_COHORT = 5
HARD_CAP_USD_MINOR = 1500

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "milwaukee-ihg-009"


def cohort() -> List[Dict]:
    """Exactly the IHG rows, by brand, never by routing eligibility."""
    rows = WY.subjects(BRAND)
    if len(rows) != EXPECTED_COHORT:
        raise SystemExit(
            "ABORT: expected %d %s properties, derived %d. This run refuses to "
            "acquire a set it did not expect -- the previous work order "
            "over-ran by selecting on eligibility instead of brand."
            % (EXPECTED_COHORT, BRAND, len(rows)))
    off_brand = [r["identity_key"] for r in rows if r["brand"] != BRAND]
    if off_brand:
        raise SystemExit("ABORT: non-%s rows in the cohort: %s"
                         % (BRAND, off_brand))
    return rows


def _usage(result) -> Dict:
    attempts: Counter = Counter()
    outcomes: Dict[str, List[str]] = {}
    for a in result.attempts:
        attempts[a.provider] += 1
        outcomes.setdefault(a.provider, []).append(a.outcome)
    fc_last = outcomes.get(PROVIDERS.FIRECRAWL, [])
    return {
        "providers_tried": list(result.providers_tried),
        "attempts_by_provider": dict(attempts),
        "outcomes_by_provider": outcomes,
        "acquired_by": (result.document.provider
                        if result.document is not None else None),
        "firecrawl_attempts": attempts.get(PROVIDERS.FIRECRAWL, 0),
        "web_unlocker_attempts": attempts.get(PROVIDERS.BRIGHTDATA_WEB_UNLOCKER, 0),
        "brightdata_browser_calls": attempts.get(PROVIDERS.BRIGHTDATA_BROWSER, 0),
        "fallback_invoked": bool(result.cost.fallback_invoked),
        "fallback_reason": (F.from_capture_outcome(fc_last[-1])
                            if fc_last and fc_last[-1] != "VALID" else ""),
        "credits": result.cost.reported_credits,
    }


async def run(args) -> Dict:
    rows = cohort()
    print("cohort asserted: %d %s properties" % (len(rows), BRAND))

    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal = JOURNAL.Journal(path=run_dir / "journal.jsonl")
    done = journal.completed_keys() if not args.no_resume else set()
    todo = [r for r in rows if r["identity_key"] not in done]

    meter = SpendMeter()
    if meter.anchor_zone_costs() is None:
        raise SystemExit("no market cost anchor; refusing to spend blind")
    credits_before = FC.credits_remaining()
    began = time.monotonic()
    stopped = ""

    for row in todo:
        spent = meter.spent_usd_minor()
        if spent is None:
            stopped = "cost telemetry unavailable; stopping rather than spending blind"
            break
        if spent >= HARD_CAP_USD_MINOR:
            stopped = "hard cap reached: %d of %d" % (spent, HARD_CAP_USD_MINOR)
            break

        record, target = WY._record_for(row, BRAND)
        result = await ROUTER.route_property(record, target, run_dir=run_dir,
                                             run_id=args.run_id)
        doc = result.document
        entry = {
            "identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "brand": row["brand"],
            "official_url": row["official_url"],
            "final_state": result.state,
            "publication_grade": bool(doc is not None and doc.is_publication_grade),
            "identity_confirmed": bool(doc is not None
                                       and (doc.identity or {}).get("confirmed")),
            "extraction": (dict(doc.observation.get("extraction") or {})
                           if doc is not None else {}),
            "failure": result.failure,
            "failure_class": result.failure_class,
            "usage": _usage(result),
            "route": result.route,
        }
        journal.append(entry)
        u = entry["usage"]
        print("  %-46s %-30s via %-22s fc=%d bd=%d"
              % (entry["canonical_name"][:46], entry["final_state"],
                 u["acquired_by"] or "-", u["firecrawl_attempts"],
                 u["web_unlocker_attempts"]), flush=True)
        await asyncio.sleep(args.pace)

    credits_after = FC.credits_remaining()
    cost_path = run_dir / "cost.json"
    measured = (None if credits_before is None or credits_after is None
                else credits_before - credits_after)
    if todo and measured is not None:
        cost_path.write_bytes((json.dumps(
            {"credits_before": credits_before, "credits_after": credits_after,
             "measured_credits": measured}, indent=1) + "\n").encode("utf-8"))
    elif cost_path.is_file():
        measured = json.loads(cost_path.read_text(encoding="utf-8")).get(
            "measured_credits")

    stored = journal.read()
    results = sorted((stored[k] for k in stored), key=lambda r: r["identity_key"])
    return report(results, credits=measured, spent=meter.spent_usd_minor(),
                  stopped=stopped, elapsed=round(time.monotonic() - began, 1))


def report(results: List[Dict], *, credits, spent, stopped: str,
           elapsed: float) -> Dict:
    n = len(results)
    fc_only = [r for r in results
               if r["usage"]["acquired_by"] == PROVIDERS.FIRECRAWL
               and not r["usage"]["fallback_invoked"]]
    escalated = [r for r in results if r["usage"]["fallback_invoked"]]
    recovered = [r for r in escalated
                 if (r["usage"]["acquired_by"] or "").startswith("brightdata")]
    pub = [r for r in results if r["publication_grade"]]
    unresolved = [r for r in results if not r["final_state"].startswith("ACQUIRED")]

    doc = {
        "schema": "ptf-brand-live-run/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": BRAND,
        "cohort_guard": {
            "expected": EXPECTED_COHORT,
            "selected_by": "brand == %s" % BRAND,
            "asserted_before_acquisition": True,
            "why": ("PTF-WYNDHAM-FIRECRAWL-DECISION-008 selected on routing "
                    "eligibility and re-acquired four already-complete Choice "
                    "properties. Selecting by brand and asserting the count "
                    "makes that failure impossible here."),
        },
        "totals": {
            "properties_tested": n,
            "firecrawl_only_successes": len(fc_only),
            "firecrawl_publication_grade_rate": (round(len(pub) / n, 4) if n else None),
            "total_firecrawl_attempts": sum(r["usage"]["firecrawl_attempts"]
                                            for r in results),
            "fallback_invocations": len(escalated),
            "fallback_reasons": dict(Counter(r["usage"]["fallback_reason"]
                                             for r in escalated
                                             if r["usage"]["fallback_reason"])),
            "web_unlocker_attempts": sum(r["usage"]["web_unlocker_attempts"]
                                         for r in results),
            "bright_data_recoveries": len(recovered),
            "brightdata_browser_calls": sum(r["usage"]["brightdata_browser_calls"]
                                            for r in results),
            "publication_grade": len(pub),
            "unresolved_manual_review": len(unresolved),
        },
        "cost": {
            "firecrawl_credits": credits,
            "bright_data_spent_usd_minor_month_to_date": spent,
            "hard_cap_usd_minor": HARD_CAP_USD_MINOR,
            "remaining_market_cap_usd": (None if spent is None
                                         else round((HARD_CAP_USD_MINOR - spent) / 100, 2)),
            "currencies_are_not_combined": (
                "Firecrawl bills plan credits, Bright Data bills dollars; no "
                "total spans them"),
        },
        "no_extrapolation": ("nothing here says anything about Marriott, "
                             "Hilton, Motel 6, Red Roof or the independents"),
        "stopped_because": stopped,
        "routes_changed": False,
        "authority_written": False,
        "policies_published": False,
        "total_elapsed_seconds": elapsed,
        "items": results,
    }
    out = REPORTS / "ptf_ihg_live_run_009.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="milwaukee-ihg-009")
    parser.add_argument("--pace", type=float, default=8.0)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    if not FC.credential_present():
        print("%s is not set" % FC.KEY_ENV)
        return 2

    doc = asyncio.run(run(args))
    t = doc["totals"]
    print()
    print("processed %d | firecrawl-only %d | pub-grade %d | fallbacks %d | "
          "recoveries %d | unresolved %d"
          % (t["properties_tested"], t["firecrawl_only_successes"],
             t["publication_grade"], t["fallback_invocations"],
             t["bright_data_recoveries"], t["unresolved_manual_review"]))
    print("credits %s | unlocker attempts %d | browser calls %d"
          % (doc["cost"]["firecrawl_credits"], t["web_unlocker_attempts"],
             t["brightdata_browser_calls"]))
    if doc["stopped_because"]:
        print("STOPPED: %s" % doc["stopped_because"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
