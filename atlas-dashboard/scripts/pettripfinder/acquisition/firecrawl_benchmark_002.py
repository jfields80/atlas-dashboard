"""PTF-FIRECRAWL-BENCHMARK-002 -- Firecrawl against the Bright Data baseline.

Same sample and same comparison vocabulary as the Spider benchmark, so all
three vendors are measured on identical ground. ``compare`` and
``baseline_rows`` are IMPORTED from that module rather than reimplemented: two
benchmarks with two definitions of MISMATCH would not be comparable, and the
whole point of running a second vendor is comparability.

What this benchmark measures that the Spider one did not
--------------------------------------------------------
Spider failed on acquisition, so completeness never came up. Firecrawl reaches
the pages, which exposes a second question the baseline quietly hides:
PUBLICATION-GRADE IS A STATEMENT ABOUT EVIDENCE, NOT ABOUT COVERAGE. A capture
qualifies when its artifact hashes, its quotes are contiguous and its identity
is confirmed -- it can qualify while extracting a single field, and 16 of the
58 committed Milwaukee baselines do exactly that.

So this run reports FIELD COUNT DELTA alongside agreement:

    fields_gained   Firecrawl extracted a field the baseline did not
    fields_lost     the baseline had a field Firecrawl did not
    MISMATCH        both had it and they DISAGREE

Gained fields are not automatically good -- a field is only worth having if the
quote behind it is real, which the publication-grade gate still decides. But a
lane that consistently returns nine fields where the incumbent returned one is
telling you something about the incumbent, not only about itself.
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

from scripts.pettripfinder.acquisition import firecrawl_capture as FIRECRAWL  # noqa: E402
from scripts.pettripfinder.acquisition import readers as READERS             # noqa: E402
from scripts.pettripfinder.acquisition.spider_benchmark_001 import (          # noqa: E402
    baseline_rows, compare, _extraction, REACHABLE_READERS as SPIDER_LANES,
)
from scripts.pettripfinder.brightdata import corpus as CORPUS                # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2     # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG         # noqa: E402

MARKET = "milwaukee-wi"
WORK_ORDER = "PTF-FIRECRAWL-BENCHMARK-002"
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "firecrawl-benchmark-002"


#: Fields whose value is a verbatim excerpt of page prose rather than a
#: structured fact. Two lanes quoting different sentences from the same
#: paragraph disagree textually and agree factually.
FREE_TEXT_FIELDS = ("service_animal_exception", "service_animal_statement",
                    "policy_text", "notes")


def classify_mismatches(mismatches: Dict) -> Dict:
    """Separate the disqualifying kind of disagreement from the cosmetic kind.

    A STRUCTURED_DISAGREEMENT means two lanes read the same page and returned
    different FACTS -- a different fee, a different weight limit. One of them is
    wrong and there is no price at which that is acceptable.

    A TEXT_EXCERPT_VARIANT means both quoted the page correctly and quoted
    different sentences. That is a difference in what was excerpted, not in
    what is true, and reporting it in the same number as the first kind would
    make a safe lane look unsafe.
    """
    structured, textual = {}, {}
    for field, sides in mismatches.items():
        values = list(sides.values())
        is_text = (field in FREE_TEXT_FIELDS
                   or all(isinstance(v, str) for v in values))
        (textual if is_text else structured)[field] = sides
    return {"structured_disagreements": structured,
            "text_excerpt_variants": textual}


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
    attempts, payload = await FIRECRAWL.capture_property(
        target, run_dir=run_dir, brand=brand_locator, max_attempts=max_attempts)
    elapsed = time.monotonic() - began

    base = _extraction(entry)
    out = {
        "identity_key": entry["identity_key"],
        "canonical_name": entry["canonical_name"],
        "brand": entry["brand"],
        "reader": reader_id,
        "url": entry["official_url"],
        "firecrawl_attempts": len(attempts),
        "firecrawl_outcome": attempts[-1].outcome if attempts else "NO_ATTEMPT",
        "firecrawl_elapsed_seconds": round(elapsed, 1),
        "bright_data_elapsed_seconds": entry.get("elapsed_seconds"),
        "bright_data_provider": entry.get("provider"),
        "bright_data_field_count": len(base),
    }

    if not payload:
        out["firecrawl_state"] = "NOT_ACQUIRED"
        out["firecrawl_failure"] = attempts[-1].detail if attempts else ""
        out["firecrawl_field_count"] = 0
        return out

    observation, _result = P2.build_observation(
        record, target, attempts[-1], payload, run_id="firecrawl-benchmark-002")
    grade = PG.assess(
        evidence_items=observation["evidence"], extraction=observation["extraction"],
        source_url=observation["source_url"], captured_at=attempts[-1].started_at,
        ref_prefix="firecrawl::%s" % record.identity_key,
        artifact_path=P2._artifact_path(payload["artifacts"], PG.PRIMARY_ARTIFACT),
        recorded_sha256=str(((payload["artifacts"].get("files") or {})
                             .get(PG.PRIMARY_ARTIFACT) or {}).get("sha256") or ""),
        page_text_path=P2._artifact_path(payload["artifacts"], "page-text.txt"),
        identity_confirmed=bool((attempts[-1].identity or {}).get("confirmed")))

    extraction = dict(observation["extraction"])
    comparison = compare(base, extraction)
    comparison.update(classify_mismatches(comparison["mismatches"]))
    out.update({
        "firecrawl_state": ("ACQUIRED_PUBLICATION_GRADE" if grade.confirmed
                            else "ACQUIRED_NONPUBLICATION_GRADE"),
        "firecrawl_publication_grade": grade.to_dict().get("verdict", ""),
        "firecrawl_field_count": len(extraction),
        "field_count_delta": len(extraction) - len(base),
        "firecrawl_extraction": extraction,
        "bright_data_extraction": base,
        "comparison": comparison,
        "evidence": [{"quote": e.get("quote", ""),
                      "field_refs": list(e.get("field_refs") or ())}
                     for e in (observation.get("evidence") or ())],
    })
    return out


async def main_async(args) -> Dict:
    rows = baseline_rows(None if args.all else list(SPIDER_LANES))
    carried: List[Dict] = []
    if args.merge and Path(args.merge).is_file():
        prior = json.loads(Path(args.merge).read_text(encoding="utf-8-sig"))
        carried = prior.get("items", prior) if isinstance(prior, dict) else prior
        done = {r["identity_key"] for r in carried}
        rows = [r for r in rows if r["identity_key"] not in done]
    if args.limit:
        rows = rows[:args.limit]

    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    credits_before = FIRECRAWL.credits_remaining()

    results: List[Dict] = list(carried)
    started = time.monotonic()
    for index, entry in enumerate(rows):
        if index and args.pace:
            # Pacing is not politeness, it is measurement hygiene: without it
            # the plan's rate limit masquerades as a capability failure.
            await asyncio.sleep(args.pace)
        results.append(await run_one(entry, run_dir=run_dir,
                                     max_attempts=args.max_attempts))
        (run_dir / "partial.json").write_text(json.dumps(results, indent=1),
                                              encoding="utf-8")
        row = results[-1]
        print("  %-44s %-28s %s%s"
              % (row["canonical_name"][:44], row.get("firecrawl_state", "?"),
                 row["firecrawl_outcome"],
                 ("  fields %d->%d" % (row["bright_data_field_count"],
                                       row["firecrawl_field_count"]))
                 if "field_count_delta" in row else ""), flush=True)

    credits_after = FIRECRAWL.credits_remaining()
    acquired = [r for r in results if str(r.get("firecrawl_state", "")).startswith("ACQUIRED")]
    pub = [r for r in results if r.get("firecrawl_state") == "ACQUIRED_PUBLICATION_GRADE"]
    compared = [r for r in results if "comparison" in r]

    verdicts: Counter = Counter()
    for r in compared:
        verdicts.update(r["comparison"]["counts"])
    mismatched = [r for r in compared if r["comparison"]["counts"].get("MISMATCH")]
    structural = [r for r in compared
                  if r["comparison"].get("structured_disagreements")]

    fc_times = [r["firecrawl_elapsed_seconds"] for r in results]
    bd_times = [r["bright_data_elapsed_seconds"] for r in results
                if r.get("bright_data_elapsed_seconds")]

    gained = sum(max(0, r.get("field_count_delta", 0)) for r in compared)
    lost = sum(max(0, -r.get("field_count_delta", 0)) for r in compared)

    doc = {
        "schema": "ptf-firecrawl-benchmark/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "note": (
            "Firecrawl re-fetching properties Bright Data already captured at "
            "publication grade, through the same readers and the same gates, "
            "on the same sample as the Spider benchmark. Nothing here writes "
            "authority, nothing is published, the route table is untouched and "
            "Firecrawl is not registered as a routable provider."),
        "comparison_vocabulary_shared_with": "PTF-SPIDER-BENCHMARK-001",
        "sample_size": len(results),
        "fetch": {
            "acquired": len(acquired),
            "publication_grade": len(pub),
            "not_acquired": len(results) - len(acquired),
            "outcome_counts": dict(Counter(r["firecrawl_outcome"] for r in results)),
            "rate_limited": sum(1 for r in results
                                if "RATE_LIMITED" in str(r.get("firecrawl_failure", ""))),
            "attempted_without_rate_limit": sum(
                1 for r in results
                if "RATE_LIMITED" not in str(r.get("firecrawl_failure", ""))),
        },
        "agreement": {
            "properties_compared": len(compared),
            "field_verdicts": dict(verdicts),
            "properties_with_a_mismatch": len(mismatched),
            "properties_with_a_STRUCTURED_disagreement": len(structural),
            "structured_disagreement_detail": [
                {"identity_key": r["identity_key"],
                 "fields": r["comparison"]["structured_disagreements"]}
                for r in structural],
            "mismatch_note": (
                "A structured disagreement means the two lanes read the same "
                "page and returned different FACTS; one is wrong. A text "
                "excerpt variant means both quoted correctly and quoted "
                "different sentences. Only the first kind disqualifies."),
            "mismatch_detail": [
                {"identity_key": r["identity_key"],
                 "mismatches": r["comparison"]["mismatches"]}
                for r in mismatched],
        },
        "completeness": {
            "fields_gained_over_baseline": gained,
            "fields_lost_versus_baseline": lost,
            "properties_where_firecrawl_extracted_more": sum(
                1 for r in compared if r.get("field_count_delta", 0) > 0),
            "properties_where_baseline_extracted_more": sum(
                1 for r in compared if r.get("field_count_delta", 0) < 0),
            "baseline_single_field_captures": sum(
                1 for r in compared if r["bright_data_field_count"] == 1),
            "note": ("Publication grade is a statement about EVIDENCE, not "
                     "about coverage: a capture qualifies on hashes, contiguous "
                     "quotes and confirmed identity while extracting one field."),
        },
        "cost": {
            "credits_before": credits_before,
            "credits_after": credits_after,
            "credits_used": ((credits_before - credits_after)
                             if credits_before is not None and credits_after is not None
                             else None),
            "basis": ("Firecrawl bills in plan credits and reports no "
                      "per-request cost. This is a measured credit delta, not "
                      "a dollar figure: converting it depends on the account's "
                      "plan, which this benchmark does not assume."),
            "bright_data_usd_per_property_measured": 0.197,
        },
        "time": {
            "firecrawl_avg_seconds": (round(statistics.mean(fc_times), 1)
                                      if fc_times else None),
            "firecrawl_median_seconds": (round(statistics.median(fc_times), 1)
                                         if fc_times else None),
            "bright_data_avg_seconds": (round(statistics.mean(bd_times), 1)
                                        if bd_times else None),
        },
        "total_elapsed_seconds": round(time.monotonic() - started, 1),
        "authority_written": False,
        "routes_changed": False,
        "items": results,
    }
    out = REPORTS / "ptf_firecrawl_benchmark_002.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="firecrawl-benchmark-002")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--merge", default=None)
    parser.add_argument("--pace", type=float, default=6.0,
                        help="seconds between properties, so a plan rate limit "
                             "is not misread as a capability failure")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)

    if not FIRECRAWL.credential_present():
        print("%s is not set" % FIRECRAWL.KEY_ENV)
        return 2

    doc = asyncio.run(main_async(args))
    f, a, c, t, comp = (doc["fetch"], doc["agreement"], doc["cost"],
                        doc["time"], doc["completeness"])
    print()
    print("sample                 %d" % doc["sample_size"])
    print("acquired               %d (publication-grade %d)"
          % (f["acquired"], f["publication_grade"]))
    print("outcomes               %s" % f["outcome_counts"])
    print("field verdicts         %s" % a["field_verdicts"])
    print("properties w/ MISMATCH %d" % a["properties_with_a_mismatch"])
    print("fields gained / lost   %d / %d"
          % (comp["fields_gained_over_baseline"], comp["fields_lost_versus_baseline"]))
    print("richer / poorer        %d / %d"
          % (comp["properties_where_firecrawl_extracted_more"],
             comp["properties_where_baseline_extracted_more"]))
    print("credits used           %s" % c["credits_used"])
    print("time                   %ss firecrawl vs %ss bright data"
          % (t["firecrawl_avg_seconds"], t["bright_data_avg_seconds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
