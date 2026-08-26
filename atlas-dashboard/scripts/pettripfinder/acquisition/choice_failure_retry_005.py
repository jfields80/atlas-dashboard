"""PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005 -- retry the two Choice failures.

PTF-FIRECRAWL-CHOICE-VALIDATION-004 ran fifteen Milwaukee Choice properties on
a two-attempt budget and two came back SCRAPE_ALL_ENGINES_FAILED: Clarion
Pointe Milwaukee Airport and Sleep Inn & Suites Milwaukee Airport.

That run also established, against my own earlier published claim, that the
error is INTERMITTENT on the Choice origin -- Country Inn Brown Deer failed its
first call and succeeded on its second, and two siblings succeeded on a first
call after failing a single-call probe in the 003 addendum. Two attempts is
therefore not enough to call a Choice property unreachable, and this module
tests exactly that on the only two rows still open.

The order is deliberate and is the order the proposed route would use
---------------------------------------------------------------------
Firecrawl up to three attempts first. Only if all three fail is the Web
Unlocker tried, and then exactly once, through its existing registered route --
because the question is whether the CURRENT fallback still adds value, not
whether some new configuration would. Nothing about the router is modified: the
route is read, not written.

If Firecrawl succeeds the record goes through the ordinary ``choice_static``
reader and the ordinary publication-grade validator, the same ones every other
Choice record in this corpus went through. A property acquired by a retry is
not held to a lower standard than one acquired first time.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FIRECRAWL  # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL             # noqa: E402
from scripts.pettripfinder.acquisition import readers as READERS             # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY           # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_choice_validation_004 as CV  # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_hard_lanes_003 as HL  # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS                # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2     # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG         # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC          # noqa: E402

WORK_ORDER = "PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005"
MARKET = "milwaukee-wi"
BRAND = "CHOICE"
RUN_ID = "choice-failure-retry-005"
REF_TAG = "fc5"

PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
VALIDATION_REPORT = REPORTS / "ptf_firecrawl_choice_validation_004.json"
RUN_ROOT = REPO / "data" / "acquisition" / "choice-failure-retry-005"

#: Three, because two is where both of these landed and the failure is known to
#: be intermittent. Not more: a budget large enough to eventually succeed at
#: anything measures patience rather than capability.
FIRECRAWL_ATTEMPTS = 3

#: One. The Web Unlocker is a proven lane and this is a fallback probe, not a
#: benchmark of it.
UNLOCKER_ATTEMPTS = 1


def open_failures() -> List[str]:
    """The Choice rows 004 left unacquired. Read from its report, not listed."""
    doc = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8-sig"))
    return sorted(row["identity_key"] for row in doc["items"]
                  if not str(row.get("firecrawl_state", "")).startswith("ACQUIRED"))


def entries_for(keys: List[str]) -> List[Dict]:
    """Queue rows plus baselines, built by the same derivation 004 used."""
    all_entries, tested = CV.remaining_sample()
    known = {e["identity_key"]: e for e in all_entries}
    missing = [k for k in keys if k not in known]
    if missing:
        raise SystemExit("not in the derived Choice sample: %s" % missing)
    return [known[k] for k in keys]


async def unlocker_once(entry: Dict, *, run_dir: Path) -> Dict:
    """One fetch through the route the router would actually use today.

    The route is RESOLVED, not assumed: if the registered Choice lane is not
    the Web Unlocker any more, this says so rather than quietly probing a
    provider nobody chose.
    """
    route = REGISTRY.resolve(brand=BRAND, url=entry["official_url"])
    out: Dict = {"route_provider": route.provider, "route_reader": route.reader,
                 "attempts": UNLOCKER_ATTEMPTS}
    if route.provider != "brightdata_web_unlocker":
        out.update({"state": "SKIPPED_ROUTE_IS_NOT_THE_UNLOCKER",
                    "detail": "the registered Choice provider is %r" % route.provider})
        return out

    record = CORPUS.BenchmarkRecord(
        identity_key=entry["identity_key"], name=entry["canonical_name"],
        market_id=MARKET, brand=BRAND, bucket=CORPUS.bucket_of(BRAND),
        source_url=entry["official_url"], pets_allowed=None, facts={},
        quotes=(), withheld_fields={}, service_animal_statement="",
        categories=frozenset(), origin="census")
    target = P2.target_for(record)
    brand_locator = READERS.locator_brand_for(route.reader or "choice_static")

    began = time.monotonic()
    try:
        attempts, payload = await UC.capture_property(
            target, run_dir=run_dir / "unlocker", brand=brand_locator,
            max_attempts=UNLOCKER_ATTEMPTS)
    except Exception as exc:                                     # noqa: BLE001
        out.update({"state": "PROVIDER_ERROR",
                    "detail": "%s: %s" % (type(exc).__name__, exc),
                    "elapsed_seconds": round(time.monotonic() - began, 1)})
        return out
    out["elapsed_seconds"] = round(time.monotonic() - began, 1)
    last = attempts[-1] if attempts else None
    out["outcome"] = getattr(last, "outcome", "NO_ATTEMPT")
    out["detail"] = getattr(last, "detail", "")
    if payload is None:
        out["state"] = "NOT_ACQUIRED"
        return out

    observation, _res = P2.build_observation(record, target, last, payload,
                                             run_id=RUN_ID)
    grade = PG.assess(
        evidence_items=observation["evidence"], extraction=observation["extraction"],
        source_url=observation["source_url"], captured_at=last.started_at,
        ref_prefix="%s::%s" % (REF_TAG, record.identity_key),
        artifact_path=P2._artifact_path(payload["artifacts"], PG.PRIMARY_ARTIFACT),
        recorded_sha256=str(((payload["artifacts"].get("files") or {})
                             .get(PG.PRIMARY_ARTIFACT) or {}).get("sha256") or ""),
        page_text_path=P2._artifact_path(payload["artifacts"], "page-text.txt"),
        identity_confirmed=bool((last.identity or {}).get("confirmed")))
    out.update({
        "state": ("ACQUIRED_PUBLICATION_GRADE" if grade.confirmed
                  else "ACQUIRED_NONPUBLICATION_GRADE"),
        "extraction": dict(observation["extraction"]),
        "field_count": len(observation["extraction"]),
    })
    return out


async def main_async(args) -> Dict:
    keys = args.only or open_failures()
    entries = entries_for(keys)
    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal = JOURNAL.Journal(path=run_dir / "journal.jsonl")
    done = journal.completed_keys() if not args.no_resume else set()
    todo = [e for e in entries if e["identity_key"] not in done]

    credits_before = FIRECRAWL.credits_remaining()
    started = time.monotonic()

    for entry in todo:
        # Firecrawl first, three attempts, the profile 004 proved.
        result = await HL.acquire(entry, run_dir=run_dir, pace=args.pace,
                                  run_id=RUN_ID, ref_tag=REF_TAG,
                                  max_attempts=FIRECRAWL_ATTEMPTS)
        result["brand"] = BRAND
        result["baseline_state"] = entry["baseline_state"]
        result["comparable"] = entry["comparable"]
        result["firecrawl_attempts_budget"] = FIRECRAWL_ATTEMPTS
        result["work_order_state"] = CV.work_order_state(result)
        result["policy_completeness"] = CV.measure_completeness(result, entry)

        acquired = str(result.get("firecrawl_state", "")).startswith("ACQUIRED")
        if not acquired:
            # Only now, and only once, through the route as it stands today.
            result["unlocker_fallback"] = await unlocker_once(entry, run_dir=run_dir)
        journal.append(result)
        fb = result.get("unlocker_fallback") or {}
        print("  %-44s firecrawl=%-28s %s"
              % (result["canonical_name"][:44], result["work_order_state"],
                 ("| unlocker=%s" % fb.get("state")) if fb else ""), flush=True)
        await asyncio.sleep(args.pace)

    credits_after = FIRECRAWL.credits_remaining()
    rows = journal.read()
    results = sorted((rows[k] for k in rows), key=lambda r: r["identity_key"])

    cost_path = run_dir / "cost.json"
    if not args.report_only:
        cost_path.write_bytes((json.dumps(
            {"credits_before": credits_before, "credits_after": credits_after,
             "measured_credits": (None if credits_before is None or credits_after is None
                                  else credits_before - credits_after)},
            indent=1) + "\n").encode("utf-8"))
    elif cost_path.is_file():
        saved = json.loads(cost_path.read_text(encoding="utf-8"))
        credits_before, credits_after = (saved.get("credits_before"),
                                         saved.get("credits_after"))

    return build_report(results, credits_before=credits_before,
                        credits_after=credits_after,
                        elapsed=round(time.monotonic() - started, 1))


def build_report(results: List[Dict], *, credits_before, credits_after,
                 elapsed: float) -> Dict:
    firecrawl_ok = [r for r in results
                    if str(r.get("firecrawl_state", "")).startswith("ACQUIRED")]
    unlocker_ok = [r for r in results
                   if str((r.get("unlocker_fallback") or {}).get("state", ""))
                   .startswith("ACQUIRED")]
    times = [r["firecrawl_elapsed_seconds"] for r in results
             if r.get("firecrawl_elapsed_seconds")]
    total_credits = (None if credits_before is None or credits_after is None
                     else credits_before - credits_after)

    doc = {
        "schema": "ptf-choice-failure-retry/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": BRAND,
        "note": ("Retries the two Choice rows PTF-FIRECRAWL-CHOICE-VALIDATION-004 "
                 "left unacquired, on a three-attempt Firecrawl budget, with the "
                 "Web Unlocker probed once through its existing route only after "
                 "all three fail. routes.json is read, never written."),
        "question": ("Is SCRAPE_ALL_ENGINES_FAILED intermittent for these two "
                     "properties, as it proved to be for Country Inn Brown Deer, "
                     "or is it settled?"),
        "firecrawl_attempts_budget": FIRECRAWL_ATTEMPTS,
        "unlocker_attempts_budget": UNLOCKER_ATTEMPTS,
        "total": len(results),
        "firecrawl_acquired": len(firecrawl_ok),
        "unlocker_unique_recoveries": len(unlocker_ok),
        "still_unacquired": len(results) - len(firecrawl_ok) - len(unlocker_ok),
        "avg_firecrawl_seconds": round(statistics.mean(times), 1) if times else None,
        "cost": {
            "credits_before": credits_before if credits_after else None,
            "credits_after": credits_after or None,
            "measured_credits": total_credits,
            "scrape_calls": sum(r.get("scrape_calls", 0) for r in results),
            "interact_calls": sum(r.get("interact_calls", 0) for r in results),
            "dollar_conversion": ("not derivable: the plan endpoint reports "
                                  "credits and a monthly allowance, not a unit "
                                  "price, so no dollar figure is asserted"),
        },
        "routes_changed": False,
        "authority_written": False,
        "total_elapsed_seconds": elapsed,
        "items": results,
    }
    out = REPORTS / "ptf_choice_failure_retry_005.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--pace", type=float, default=8.0)
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    if not args.report_only and not FIRECRAWL.credential_present():
        print("%s is not set" % FIRECRAWL.KEY_ENV)
        return 2

    doc = asyncio.run(main_async(args))
    print()
    print("firecrawl acquired %d/%d | unlocker unique recoveries %d | still open %d"
          % (doc["firecrawl_acquired"], doc["total"],
             doc["unlocker_unique_recoveries"], doc["still_unacquired"]))
    print("credits %s" % doc["cost"]["measured_credits"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
