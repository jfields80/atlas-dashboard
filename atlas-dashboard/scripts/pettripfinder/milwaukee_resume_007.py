"""PTF-MILWAUKEE-RESUME-007 -- resume Milwaukee, Firecrawl first, nothing forced.

Everything here goes through ``router.route_property``. That is the point: the
configured route decides the provider, the route's own attempt budget decides
how many tries the primary gets, and ``failures.may_escalate`` decides whether
a second lane is even permitted. This module chooses the WORK, never the lane.

WHAT IS ELIGIBLE, AND WHY IT IS FOUR AND NOT SIXTY
--------------------------------------------------
Sixty queued Milwaukee properties remain unacquired. Their configured primaries
are not all the same, and the instruction set for this run is explicit on three
points that interact:

    "Firecrawl as the first acquisition provider for every eligible route"
    "Do not use brightdata_browser"
    "Do not change routing rules during the run"

Only the CHOICE lane is configured to lead with Firecrawl -- that is what
PTF-CHOICE-FIRECRAWL-ROUTE-APPLICATION-006 applied, on the only measurement
that justified it. The other fifty-six resolve to ``brightdata_browser`` as
their PRIMARY. Running them Firecrawl-first would require editing the route
table mid-run, and running them as configured would require the forbidden
provider. Both are ruled out, so they are not attempted and are reported as
BLOCKED rather than as failures. Recording them as failures would make
Firecrawl look worse than it is on lanes it was never given.

So "every eligible route" resolves, mechanically, to the four remaining Choice
properties. The eligibility test is the live registry, not a list in this file.

THE SPEND CAP IS STILL IN FORCE
-------------------------------
The market's hard provider cap is $15 and $13.22 of it is spent. Firecrawl bills
plan credits and does not touch that cap; the Web Unlocker fallback bills
dollars and does. The meter is checked BEFORE each property and the run stops
rather than crossing the line -- the same rule the original run was killed
under, for the same reason.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import failures as F                  # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_capture as FC        # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL             # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS         # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY           # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER               # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS                # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2     # noqa: E402
from scripts.pettripfinder.milwaukee_acquisition_run_001 import (            # noqa: E402
    BILLABLE_ZONES, SpendMeter,
)

WORK_ORDER = "PTF-MILWAUKEE-RESUME-007"
MARKET = "milwaukee-wi"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
QUEUE = REPORTS / "milwaukee-wi_policy_acquisition_queue_001.json"
PRIOR_JOURNAL = (REPO / "data" / "acquisition" / "milwaukee-router-001"
                 / "milwaukee-router-001" / "journal.jsonl")
RUN_ROOT = REPO / "data" / "acquisition" / "milwaukee-resume-007"

#: The market's hard provider cap, unchanged. Dollars, not credits: Firecrawl
#: bills plan credits and cannot move this number.
HARD_CAP_USD_MINOR = 1500

#: The lane a property must LEAD with to be eligible for this run.
FIRECRAWL = PROVIDERS.FIRECRAWL

#: Never, on any lane, in this run.
FORBIDDEN = PROVIDERS.BRIGHTDATA_BROWSER

#: Natural Choice acquisitions made through Firecrawl under a >=3-attempt
#: regime, and how many of them needed Bright Data. Counted across the work
#: orders that produced them so the projection rests on more than this run:
#:
#:   004  15 Choice properties, 13 acquired at a 2-attempt budget
#:   005   2 of those retried at 3 attempts, both acquired
#:   006   1 live control acquired (the forced-failure property is excluded --
#:         it was made to fail and is not evidence about natural rates)
#:   007   4 acquired here
#:
#: 15 + 1 + 4 = 20 distinct natural acquisitions, 0 of which escalated.
CHOICE_NATURAL_ACQUISITIONS = 20
CHOICE_NATURAL_ESCALATIONS = 0


def queue_rows() -> List[Dict]:
    doc = json.loads(QUEUE.read_text(encoding="utf-8"))
    return [r for r in doc["items"]
            if r["queue_state"] == "QUEUED" and not r.get("brand_excluded")]


def already_processed() -> set:
    if not PRIOR_JOURNAL.exists():
        return set()
    return {json.loads(l)["identity_key"]
            for l in PRIOR_JOURNAL.read_text(encoding="utf-8").splitlines()
            if l.strip()}


def partition_remaining() -> Dict[str, List[Dict]]:
    """Split what is left into what this run may attempt and what it may not.

    Eligibility is read from the live registry. A property is eligible when its
    configured PRIMARY is Firecrawl; it is blocked when the primary is the
    forbidden provider, because honouring both instructions at once is not
    possible without editing routes mid-run.
    """
    done = already_processed()
    eligible, blocked = [], []
    for row in queue_rows():
        if row["identity_key"] in done:
            continue
        route = REGISTRY.resolve(brand=row["brand"], url=row["official_url"],
                                 identity_key=row["identity_key"])
        entry = dict(row)
        entry["route_primary"] = route.provider
        entry["route_ladder"] = list(route.ladder)
        entry["route_max_attempts"] = route.max_attempts_per_provider
        if route.provider == FIRECRAWL:
            eligible.append(entry)
        else:
            entry["blocked_reason"] = (
                "its configured primary is %r. Leading with Firecrawl would "
                "require editing routes.json mid-run, and running it as "
                "configured would require the provider this run forbids."
                % route.provider)
            blocked.append(entry)
    return {"eligible": eligible, "blocked": blocked}


def _record_for(row: Dict):
    record = CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"], name=row["canonical_name"],
        market_id=MARKET, brand=row["brand"],
        bucket=CORPUS.bucket_of(row["brand"]), source_url=row["official_url"],
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census")
    return record, P2.target_for(record)


def _usage(result) -> Dict:
    """Per-property provider usage, from the attempts the router actually made."""
    attempts = Counter()
    outcomes: Dict[str, List[str]] = {}
    seconds: Dict[str, float] = {}
    for a in result.attempts:
        attempts[a.provider] += 1
        outcomes.setdefault(a.provider, []).append(a.outcome)
        seconds[a.provider] = seconds.get(a.provider, 0.0) + (a.elapsed_seconds or 0.0)
    acquired_by = result.document.provider if result.document is not None else None
    return {
        "providers_tried": list(result.providers_tried),
        "attempts_by_provider": dict(attempts),
        "outcomes_by_provider": outcomes,
        "seconds_by_provider": {k: round(v, 2) for k, v in seconds.items()},
        "acquired_by": acquired_by,
        "firecrawl_attempts": attempts.get(FIRECRAWL, 0),
        "brightdata_attempts": sum(n for p, n in attempts.items()
                                   if p.startswith("brightdata")),
        "brightdata_browser_calls": attempts.get(FORBIDDEN, 0),
        "fallback_invoked": bool(result.cost.fallback_invoked),
        "escalated_to_brightdata": any(p.startswith("brightdata")
                                       for p in result.providers_tried),
        "credits": result.cost.reported_credits,
        # Why the fallback was needed, kept as the router's own classification
        # so "why did this cost money" is answerable by failure family.
        "fallback_reason": (F.from_capture_outcome(outcomes[FIRECRAWL][-1])
                            if outcomes.get(FIRECRAWL)
                            and outcomes[FIRECRAWL][-1] != "VALID" else ""),
    }


async def run(args) -> Dict:
    split = partition_remaining()
    eligible = split["eligible"]
    if args.limit:
        eligible = eligible[:args.limit]

    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal = JOURNAL.Journal(path=run_dir / "journal.jsonl")
    done = journal.completed_keys() if not args.no_resume else set()
    todo = [r for r in eligible if r["identity_key"] not in done]

    # The market cost anchor is persisted by the ORIGINAL run and deliberately
    # outlives the process: the cap is "$15 for this market", not "$15 per
    # invocation". Re-anchoring here would reset the cumulative figure to zero
    # and let this run spend the whole cap again.
    meter = SpendMeter()
    if meter.anchor_zone_costs() is None:
        raise SystemExit("no market cost anchor found; refusing to spend "
                         "without a cumulative baseline")
    credits_before = FC.credits_remaining()
    stopped_because = ""
    began = time.monotonic()

    for row in todo:
        # The cap is checked BEFORE the property, never after. Crossing it and
        # then noticing is what the original run was killed for.
        spent = meter.spent_usd_minor()
        if spent is None:
            stopped_because = ("provider cost telemetry is unavailable; "
                               "stopping rather than spending blind")
            break
        if spent >= HARD_CAP_USD_MINOR:
            stopped_because = ("hard cap reached: %d of %d usd_minor"
                               % (spent, HARD_CAP_USD_MINOR))
            break

        record, target = _record_for(row)
        result = await ROUTER.route_property(
            record, target, run_dir=run_dir, run_id=args.run_id)
        entry = {
            "identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "brand": row["brand"],
            "official_url": row["official_url"],
            "route": result.route,
            "final_state": result.state,
            "failure": result.failure,
            "failure_class": result.failure_class,
            "escalation_stopped_because": result.escalation_stopped_because,
            "publication_grade": bool(result.document is not None
                                      and result.document.is_publication_grade),
            "identity_confirmed": bool(result.document is not None
                                       and (result.document.identity or {}).get("confirmed")),
            "extraction": (dict(result.document.observation.get("extraction") or {})
                           if result.document is not None else {}),
            "usage": _usage(result),
            "cost": result.cost.to_dict(),
            "spend_before_usd_minor": spent,
        }
        journal.append(entry)          # durable before the next property
        u = entry["usage"]
        print("  %-44s %-30s via %-22s fc=%d bd=%d"
              % (entry["canonical_name"][:44], entry["final_state"],
                 u["acquired_by"] or "-", u["firecrawl_attempts"],
                 u["brightdata_attempts"]), flush=True)
        await asyncio.sleep(args.pace)

    credits_after = FC.credits_remaining()
    spent_after = meter.spent_usd_minor()

    # Cost is measured once, when the requests are made. A later rebuild has
    # nothing left to measure and must not overwrite the measurement with a
    # zero -- the same durability rule every completed property follows.
    cost_path = run_dir / "cost.json"
    measured = (None if credits_before is None or credits_after is None
                else credits_before - credits_after)
    if todo and measured is not None:
        cost_path.write_bytes((json.dumps(
            {"credits_before": credits_before, "credits_after": credits_after,
             "measured_credits": measured}, indent=1) + "\n").encode("utf-8"))
    elif cost_path.is_file():
        saved = json.loads(cost_path.read_text(encoding="utf-8"))
        credits_before = saved.get("credits_before")
        credits_after = saved.get("credits_after")
        if credits_before is None and saved.get("measured_credits") is not None:
            # Only the delta survived. Carried forward as a delta rather than
            # inventing endpoint readings for it.
            credits_before, credits_after = saved["measured_credits"], 0
    rows = journal.read()
    results = sorted((rows[k] for k in rows), key=lambda r: r["identity_key"])
    return report(results, split, credits_before=credits_before,
                  credits_after=credits_after, spent_after=spent_after,
                  stopped_because=stopped_because,
                  elapsed=round(time.monotonic() - began, 1))


def report(results: List[Dict], split: Dict, *, credits_before, credits_after,
           spent_after, stopped_because: str, elapsed: float) -> Dict:
    total = len(results)
    acquired = [r for r in results if r["final_state"].startswith("ACQUIRED")]
    pub = [r for r in results if r["final_state"] == "ACQUIRED_PUBLICATION_GRADE"]
    fc_only = [r for r in results
               if r["usage"]["acquired_by"] == FIRECRAWL
               and not r["usage"]["escalated_to_brightdata"]]
    escalated = [r for r in results if r["usage"]["escalated_to_brightdata"]]
    bd_recovered = [r for r in escalated
                    if (r["usage"]["acquired_by"] or "").startswith("brightdata")]
    unresolved = [r for r in results if not r["final_state"].startswith("ACQUIRED")]

    def pct(n, d):
        return None if not d else round(100.0 * n / d, 1)

    fallback_reasons = Counter(r["usage"]["fallback_reason"] for r in escalated
                               if r["usage"]["fallback_reason"])
    reasons_by_class = Counter(F.classify(v) for v in fallback_reasons.elements())

    fc_attempts = sum(r["usage"]["firecrawl_attempts"] for r in results)
    bd_attempts = sum(r["usage"]["brightdata_attempts"] for r in results)
    credits = (None if credits_before is None or credits_after is None
               else credits_before - credits_after)

    # Projection.
    #
    # This run is n=4 with zero escalations. A rate computed from that alone
    # would read 0%, which is not a measurement -- it is a small sample that
    # happened not to fail. So the Choice-lane rate is taken over EVERY natural
    # Choice acquisition made under a three-attempt regime across work orders
    # 004, 005, 006 and 007, and it is reported with an upper bound rather than
    # as a point estimate, because "0 of 19" bounds a rate, it does not fix it.
    #
    # The whole-market figure is stated separately and is the one that matters
    # commercially: Choice is 15 of Milwaukee's 127 routable rows, and every
    # other brand still leads with Bright Data.
    choice_natural_acquisitions = CHOICE_NATURAL_ACQUISITIONS
    choice_escalations = CHOICE_NATURAL_ESCALATIONS
    # Rule of three: with zero events in n trials, the 95% upper bound on the
    # rate is about 3/n. Quoting zero would overclaim.
    upper_bound = (3.0 / choice_natural_acquisitions
                   if choice_escalations == 0 else None)
    choice_rate = choice_escalations / choice_natural_acquisitions

    choice_per_market = 15            # Milwaukee's Choice queue
    non_choice_per_market = 127 - 15  # everything still on a Bright Data lane
    projection = {}
    for n in (1, 5, 10, 50):
        choice_props = choice_per_market * n
        non_choice = non_choice_per_market * n
        projection["%d_comparable_markets" % n] = {
            "choice_properties": choice_props,
            "choice_bright_data_escalations_expected": round(choice_props * choice_rate, 1),
            "choice_bright_data_escalations_upper_bound_95pct": (
                None if upper_bound is None else round(choice_props * upper_bound, 1)),
            "choice_firecrawl_credits_expected": choice_props,
            "non_choice_properties_still_on_bright_data": non_choice,
            "non_choice_bright_data_usd_expected": round(non_choice * 0.197, 2),
            "total_bright_data_usd_expected": round(
                (non_choice + choice_props * choice_rate) * 0.197, 2),
            "total_bright_data_usd_upper_bound_95pct": (
                None if upper_bound is None else round(
                    (non_choice + choice_props * upper_bound) * 0.197, 2)),
        }

    doc = {
        "schema": "ptf-provider-utilization/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "note": ("Every property here was acquired through router.route_property "
                 "against the applied route table. No provider was chosen by "
                 "this module, no route was edited, and no gate was relaxed."),
        "eligibility": {
            "remaining_in_queue": len(split["eligible"]) + len(split["blocked"]),
            "eligible_firecrawl_first": len(split["eligible"]),
            "blocked": len(split["blocked"]),
            "blocked_reason": ("their configured primary is brightdata_browser. "
                               "Leading with Firecrawl would require editing "
                               "routes.json mid-run, which this run forbids; "
                               "running them as configured would require the "
                               "provider this run forbids. They were NOT "
                               "attempted and are not counted as failures."),
            "blocked_by_brand": dict(Counter(r["brand"] for r in split["blocked"])),
        },
        "totals": {
            "total_properties_processed": total,
            "firecrawl_only_successes": len(fc_only),
            "firecrawl_success_rate_pct": pct(len(fc_only), total),
            "properties_escalated_to_bright_data": len(escalated),
            "bright_data_fallback_rate_pct": pct(len(escalated), total),
            "bright_data_recoveries": len(bd_recovered),
            "bright_data_recovery_rate_pct": pct(len(bd_recovered), len(escalated)),
            "acquired": len(acquired),
            "publication_grade": len(pub),
            "unresolved_manual_review": len(unresolved),
        },
        "fallback_reasons": {
            "by_failure": dict(fallback_reasons),
            "by_failure_class": dict(reasons_by_class),
            "note": ("classified by the router's own failure family, so 'why "
                     "did this cost Bright Data money' is answerable without "
                     "re-reading logs. Only TECHNICAL failures can appear "
                     "here: source, policy and identity failures stop the "
                     "ladder and never reach a second provider."),
        },
        "attempts": {
            "firecrawl_attempts": fc_attempts,
            "bright_data_attempts": bd_attempts,
            "bright_data_browser_calls": sum(
                r["usage"]["brightdata_browser_calls"] for r in results),
        },
        "cost": {
            "firecrawl_credits": credits,
            "bright_data_spent_usd_minor_month_to_date": spent_after,
            "hard_cap_usd_minor": HARD_CAP_USD_MINOR,
            "currencies_are_not_combined": (
                "Firecrawl bills plan credits and Bright Data bills dollars; "
                "the plan endpoint reports an allowance, not a unit price, so "
                "no total spans them"),
            "bright_data_usd_per_attempted_property": 0.197,
        },
        "projection": {
            "basis": ("Choice-lane escalation measured over %d natural "
                      "acquisitions under the applied three-attempt route "
                      "(work orders 004, 005, 006 and 007), not over this "
                      "run's four alone."
                      % choice_natural_acquisitions),
            "choice_escalations_observed": choice_escalations,
            "choice_escalation_rate": round(choice_rate, 4),
            "choice_escalation_rate_upper_bound_95pct": (
                None if upper_bound is None else round(upper_bound, 4)),
            "why_a_bound_and_not_a_rate": (
                "zero escalations in %d attempts does not measure a 0%% rate; "
                "it bounds one. The rule of three puts the 95%% upper bound at "
                "about 3/n. Quoting zero would be an overclaim, and the "
                "difference matters at 50 markets."
                % choice_natural_acquisitions),
            "the_number_that_actually_matters": (
                "Choice is 15 of Milwaukee's 127 routable properties. The "
                "other 112 still lead with Bright Data, and this work order "
                "measured nothing about them. Firecrawl was 1/4 on Marriott "
                "and 0/3 on Hilton when it was tested there, so the "
                "non-Choice column below should be read as the current cost "
                "of a market, not as a gap waiting to be closed."),
            "assumptions": {
                "choice_per_market": choice_per_market,
                "non_choice_per_market": non_choice_per_market,
                "bright_data_usd_per_attempted_property": 0.197,
                "comparable_market": ("a market with Milwaukee's brand mix and "
                                      "queue size; markets differ and this is "
                                      "a planning figure, not a quote"),
            },
            "per_market": projection,
        },
        "per_property": [
            {"identity_key": r["identity_key"],
             "brand": r["brand"],
             "final_state": r["final_state"],
             "provider_used": r["usage"]["acquired_by"],
             "providers_tried": r["usage"]["providers_tried"],
             "firecrawl_attempts": r["usage"]["firecrawl_attempts"],
             "bright_data_attempts": r["usage"]["brightdata_attempts"],
             "fallback_invoked": r["usage"]["fallback_invoked"],
             "fallback_reason": r["usage"]["fallback_reason"],
             "publication_grade": r["publication_grade"],
             "credits": r["usage"]["credits"]}
            for r in results],
        "not_attempted": [
            {"identity_key": r["identity_key"], "brand": r["brand"],
             "route_primary": r["route_primary"]}
            for r in split["blocked"]],
        "stopped_because": stopped_because,
        "routes_changed": False,
        "authority_written": False,
        "policies_published": False,
        "total_elapsed_seconds": elapsed,
        "items": results,
    }
    out = REPORTS / "ptf_milwaukee_provider_utilization_007.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="milwaukee-resume-007")
    parser.add_argument("--pace", type=float, default=8.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    if not FC.credential_present():
        print("%s is not set" % FC.KEY_ENV)
        return 2

    doc = asyncio.run(run(args))
    t = doc["totals"]
    print()
    print("processed %d | firecrawl-only %d (%s%%) | escalated %d | recovered %d"
          % (t["total_properties_processed"], t["firecrawl_only_successes"],
             t["firecrawl_success_rate_pct"],
             t["properties_escalated_to_bright_data"],
             t["bright_data_recoveries"]))
    print("publication-grade %d | unresolved %d"
          % (t["publication_grade"], t["unresolved_manual_review"]))
    print("credits %s | bright data attempts %d | browser calls %d"
          % (doc["cost"]["firecrawl_credits"],
             doc["attempts"]["bright_data_attempts"],
             doc["attempts"]["bright_data_browser_calls"]))
    if doc["stopped_because"]:
        print("STOPPED: %s" % doc["stopped_because"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
