"""PTF-SPIDER-BENCHMARK-001 -- Spider against a known-good Bright Data baseline.

What makes this benchmark worth trusting
----------------------------------------
Milwaukee already has 58 publication-grade captures from the Bright Data lanes,
each with its schema-1.2 extraction and its exact quotes. That is a REAL
baseline: not a hand-built fixture and not a vendor's own claim. This module
re-fetches the same properties through Spider, runs them through the SAME
readers and the SAME gates, and compares field by field.

Because only the fetch differs, any difference in the result is the fetch.

The comparison vocabulary is deliberately asymmetric
---------------------------------------------------
    MATCH     both lanes produced the same value for a field
    MISSING   Bright Data had it, Spider did not          -> a recall loss
    EXTRA     Spider had it, Bright Data did not          -> possibly a gain
    MISMATCH  both had it and they DISAGREE               -> the dangerous one

MISMATCH is reported first and loudest. A cheaper provider that misses a field
costs coverage; one that returns a DIFFERENT fee or weight limit would publish
a wrong fact to a guest, and no price makes that acceptable.

Cost
----
Spider reports its own per-request cost, so unlike the Bright Data lanes there
is no zone delta to infer and no billing lag to correct for. The figure here is
the vendor's, summed per property.
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

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import readers as READERS       # noqa: E402
from scripts.pettripfinder.acquisition import spider_capture as SPIDER  # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS          # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O             # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG   # noqa: E402

MARKET = "milwaukee-wi"
WORK_ORDER = "PTF-SPIDER-BENCHMARK-001"
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
JOURNAL = (REPO / "data" / "acquisition" / "milwaukee-router-001"
           / "milwaukee-router-001" / "journal.jsonl")
RUN_ROOT = REPO / "data" / "acquisition" / "spider-benchmark-001"

#: Lanes a live probe showed Spider can actually reach. Marriott returned 403,
#: Hilton and Choice timed out at the edge. Recorded as measured, not assumed,
#: and re-measured by --all.
REACHABLE_READERS = ("ihg", "wyndham", "generic")


def baseline_rows(readers: Optional[List[str]] = None) -> List[Dict]:
    """Publication-grade Bright Data captures, which are the comparison set."""
    if not JOURNAL.exists():
        return []
    rows = [json.loads(l) for l in JOURNAL.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    keep = [r for r in rows if r["final_state"] == "ACQUIRED_PUBLICATION_GRADE"]
    if readers is not None:
        keep = [r for r in keep if r.get("reader") in readers]
    return sorted(keep, key=lambda r: r["identity_key"])


def _extraction(entry: Dict) -> Dict:
    doc = (entry.get("result") or {}).get("document") or {}
    return dict((doc.get("observation") or {}).get("extraction") or {})


def compare(base: Dict, spider: Dict) -> Dict:
    """Field-by-field, with MISMATCH separated from MISSING."""
    fields = sorted(set(base) | set(spider))
    verdicts: Dict[str, str] = {}
    for field in fields:
        if field in base and field not in spider:
            verdicts[field] = "MISSING"
        elif field in spider and field not in base:
            verdicts[field] = "EXTRA"
        elif base[field] == spider[field]:
            verdicts[field] = "MATCH"
        else:
            verdicts[field] = "MISMATCH"
    counts = Counter(verdicts.values())
    return {"per_field": verdicts, "counts": dict(counts),
            "mismatches": {f: {"bright_data": base[f], "spider": spider[f]}
                           for f, v in verdicts.items() if v == "MISMATCH"}}


def _diagnose(attempt, entry: Dict) -> Dict:
    """Why a fetch that "worked" produced nothing usable."""
    outcome = attempt.outcome
    body = attempt.body_chars or 0
    if outcome == O.ACCESS_DENIED:
        label = "BLOCKED_AT_EDGE"
        detail = "the site or the provider's edge refused the request"
    elif outcome == O.NAVIGATION_FAILED:
        label = "PROVIDER_ERROR"
        detail = "the provider did not return a page (timeout or upstream error)"
    elif outcome == O.POLICY_NOT_FOUND and body < 6000:
        label = "JAVASCRIPT_SHELL"
        detail = ("HTTP 200 with only %d characters of extractable text and no "
                  "policy signal phrase: the document arrived and its content "
                  "did not. The Bright Data lane reaches this content by "
                  "RUNNING the page and opening its disclosures, which a fetch "
                  "cannot do." % body)
    elif outcome == O.POLICY_NOT_FOUND:
        label = "RENDERED_BUT_NO_POLICY_BLOCK"
        detail = ("%d characters of text arrived but no bounded policy block "
                  "was located in it" % body)
    elif outcome == O.IDENTITY_MISMATCH:
        label = "IDENTITY_MISMATCH"
        detail = "the page served was not this property"
    else:
        label = outcome
        detail = attempt.detail or ""
    return {"label": label, "detail": detail, "extractable_text_chars": body,
            "bright_data_reached_it": True,
            "bright_data_reader": entry.get("reader")}


async def run_one(entry: Dict, *, run_dir: Path, max_attempts: int) -> Dict:
    record = CORPUS.BenchmarkRecord(
        identity_key=entry["identity_key"], name=entry["canonical_name"],
        market_id=MARKET, brand=entry["brand"],
        bucket=CORPUS.bucket_of(entry["brand"]), source_url=entry["official_url"],
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census")
    target = P2.target_for(record)
    reader_id = entry.get("reader") or "generic"
    brand_locator = READERS.locator_brand_for(reader_id)

    began = time.monotonic()
    attempts, payload = await SPIDER.capture_property(
        target, run_dir=run_dir, brand=brand_locator, max_attempts=max_attempts)
    elapsed = time.monotonic() - began

    # Spider reports cost per request; the payload carries the successful
    # one. A failed attempt still bills, so its cost is read off the attempt
    # record's own note rather than being quietly dropped.
    reported = float(payload.get("reported_usd", 0.0)) if payload else 0.0
    for record_attempt in attempts:
        note = (record_attempt.network or {}).get("note", "")
        if "$" in note and record_attempt.outcome != "VALID":
            try:
                reported += float(note.rsplit("$", 1)[-1])
            except ValueError:
                pass

    out = {
        "identity_key": entry["identity_key"],
        "canonical_name": entry["canonical_name"],
        "brand": entry["brand"],
        "reader": reader_id,
        "url": entry["official_url"],
        "spider_attempts": len(attempts),
        "spider_outcome": attempts[-1].outcome if attempts else "NO_ATTEMPT",
        "spider_elapsed_seconds": round(elapsed, 1),
        "spider_reported_usd": reported,
        "bright_data_elapsed_seconds": entry.get("elapsed_seconds"),
        "bright_data_attempts": entry.get("attempts"),
        "bright_data_provider": entry.get("provider"),
    }

    if not payload:
        out["spider_state"] = "NOT_ACQUIRED"
        out["spider_failure"] = attempts[-1].detail if attempts else ""
        # A bare POLICY_NOT_FOUND count is not a finding, it is a shrug. Record
        # WHY: an HTTP 200 that yields a large raw body but almost no extracted
        # text and no signal phrase is a JavaScript SHELL -- the page arrived
        # and its content did not. That is a different failure from being
        # blocked, and the two must not be reported as one number.
        out["diagnosis"] = _diagnose(attempts[-1], entry)
        return out

    observation, result = P2.build_observation(
        record, target, attempts[-1], payload, run_id="spider-benchmark-001")
    grade = PG.assess(
        evidence_items=observation["evidence"], extraction=observation["extraction"],
        source_url=observation["source_url"], captured_at=attempts[-1].started_at,
        ref_prefix="spider::%s" % record.identity_key,
        artifact_path=P2._artifact_path(payload["artifacts"], PG.PRIMARY_ARTIFACT),
        recorded_sha256=str(((payload["artifacts"].get("files") or {})
                             .get(PG.PRIMARY_ARTIFACT) or {}).get("sha256") or ""),
        page_text_path=P2._artifact_path(payload["artifacts"], "page-text.txt"),
        identity_confirmed=bool((attempts[-1].identity or {}).get("confirmed")))

    spider_extraction = dict(observation["extraction"])
    out.update({
        "spider_state": ("ACQUIRED_PUBLICATION_GRADE" if grade.confirmed
                         else "ACQUIRED_NONPUBLICATION_GRADE"),
        "spider_publication_grade": grade.to_dict().get("verdict", ""),
        "spider_extraction": spider_extraction,
        "bright_data_extraction": _extraction(entry),
        "comparison": compare(_extraction(entry), spider_extraction),
    })
    return out


async def main_async(args) -> Dict:
    readers = None if args.all else list(REACHABLE_READERS)
    rows = baseline_rows(readers)
    # Disjoint batches: a benchmark that cannot be run in slices has to be run
    # in one sitting, and one long sitting is exactly what keeps getting killed.
    rows = rows[args.offset:]
    # Skip already-done rows BEFORE slicing. Slicing first takes N rows that
    # may all be complete and then processes none of them, which looks
    # identical to "the batch finished" and silently stalls the benchmark.
    carried: List[Dict] = []
    if args.merge:
        prior = Path(args.merge)
        if prior.is_file():
            existing = json.loads(prior.read_text(encoding="utf-8-sig"))
            carried = existing.get("items", existing) if isinstance(existing, dict) else existing
            done = {r["identity_key"] for r in carried}
            rows = [r for r in rows if r["identity_key"] not in done]
    if args.limit:
        rows = rows[:args.limit]

    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    credits_before = SPIDER.credits_remaining()

    results: List[Dict] = list(carried)
    started = time.monotonic()
    for entry in rows:
        results.append(await run_one(entry, run_dir=run_dir,
                                     max_attempts=args.max_attempts))
        (run_dir / "partial.json").write_text(
            json.dumps(results, indent=1), encoding="utf-8")
        print("  %-46s %-26s %s" % (results[-1]["canonical_name"][:46],
                                    results[-1].get("spider_state", "?"),
                                    results[-1]["spider_outcome"]), flush=True)

    credits_after = SPIDER.credits_remaining()
    acquired = [r for r in results if r.get("spider_state", "").startswith("ACQUIRED")]
    pub = [r for r in results if r.get("spider_state") == "ACQUIRED_PUBLICATION_GRADE"]
    compared = [r for r in results if "comparison" in r]

    field_counts: Counter = Counter()
    for r in compared:
        field_counts.update(r["comparison"]["counts"])
    mismatched = [r for r in compared if r["comparison"]["counts"].get("MISMATCH")]

    spider_cost = sum(r.get("spider_reported_usd") or 0.0 for r in results)
    spider_times = [r["spider_elapsed_seconds"] for r in results]
    bd_times = [r["bright_data_elapsed_seconds"] for r in results
                if r.get("bright_data_elapsed_seconds")]

    doc = {
        "schema": "ptf-spider-benchmark/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "note": (
            "Spider re-fetching properties Bright Data already captured at "
            "publication grade, through the same readers and the same gates. "
            "Only the fetch differs, so any difference is the fetch. Nothing "
            "here writes authority and nothing is published; the route table "
            "is untouched and Spider is not registered as a routable provider."),
        "baseline": "the 58 publication-grade Milwaukee captures from "
                    "PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001",
        "sample_selection": ("readers Spider was measured able to reach"
                            if not args.all else "every publication-grade row"),
        "sample_size": len(results),
        "fetch": {
            "acquired": len(acquired),
            "publication_grade": len(pub),
            "not_acquired": len(results) - len(acquired),
            "outcome_counts": dict(Counter(r["spider_outcome"] for r in results)),
        },
        "why_not_acquired": dict(Counter(
            r["diagnosis"]["label"] for r in results if "diagnosis" in r)),
        "field_comparison": {
            "properties_compared": len(compared),
            "field_verdicts": dict(field_counts),
            "properties_with_a_mismatch": len(mismatched),
            "mismatch_detail": [
                {"identity_key": r["identity_key"],
                 "mismatches": r["comparison"]["mismatches"]}
                for r in mismatched],
        },
        "cost": {
            "spider_reported_usd": round(spider_cost, 6),
            "spider_usd_per_property": (round(spider_cost / len(results), 6)
                                        if results else None),
            "credits_before": credits_before,
            "credits_after": credits_after,
            "credits_used": (round(credits_before - credits_after, 3)
                             if credits_before and credits_after else None),
            "bright_data_usd_per_property_measured": 0.197,
            "basis": ("Spider reports its own per-request cost, so this is the "
                      "vendor's figure and not an inference. The Bright Data "
                      "figure is the measured Milwaukee run: $13.22 over 67 "
                      "properties."),
        },
        "time": {
            "spider_avg_seconds": (round(statistics.mean(spider_times), 1)
                                   if spider_times else None),
            "spider_median_seconds": (round(statistics.median(spider_times), 1)
                                      if spider_times else None),
            "bright_data_avg_seconds": (round(statistics.mean(bd_times), 1)
                                        if bd_times else None),
        },
        "total_elapsed_seconds": round(time.monotonic() - started, 1),
        "authority_written": False,
        "routes_changed": False,
        "items": results,
    }
    out = REPORTS / "ptf_spider_benchmark_001.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="spider-benchmark-001")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--merge", default=None,
                        help="carry forward results from a previous batch")
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--all", action="store_true",
                        help="include lanes the probe showed Spider cannot reach")
    args = parser.parse_args(argv)

    if not SPIDER.credential_present():
        print("%s is not set" % SPIDER.KEY_ENV)
        return 2

    doc = asyncio.run(main_async(args))
    f, c, t = doc["fetch"], doc["cost"], doc["time"]
    print()
    print("sample                %d" % doc["sample_size"])
    print("acquired              %d (publication-grade %d)"
          % (f["acquired"], f["publication_grade"]))
    print("outcomes              %s" % f["outcome_counts"])
    print("field verdicts        %s" % doc["field_comparison"]["field_verdicts"])
    print("properties w/ MISMATCH %d" % doc["field_comparison"]["properties_with_a_mismatch"])
    print("spider cost           $%.6f total, $%.6f/property"
          % (c["spider_reported_usd"], c["spider_usd_per_property"] or 0))
    print("bright data           $%.4f/property (measured)"
          % c["bright_data_usd_per_property_measured"])
    print("spider time           %ss avg | bright data %ss avg"
          % (t["spider_avg_seconds"], t["bright_data_avg_seconds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
