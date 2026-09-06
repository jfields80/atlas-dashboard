"""PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003 Phase 5 -- record a spend that already happened.

PTF-CINCINNATI-HARDENED-REVALIDATION-001 ran the Firecrawl rung and spent five
plan credits over seven attempts. It wrote its own market report and, being a
parallel-safe order, was forbidden to touch the SHARED paid-attempt ledger. The
parallel order that followed found the gap and flagged it rather than fixing it,
for the same reason. This order owns the serialized lane, so it pays the debt.

WHAT THIS IS NOT
----------------
Not a purchase. No provider is called, no credit is consumed and no URL is
fetched. Every field written here is read out of the committed run document.
A ledger entry is a RECORD of a past attempt, and inventing one would be as
wrong as omitting one.

WHY THE LEDGER AND NOT THE REPORT
---------------------------------
The market report says what the run found. The ledger answers a different and
narrower question -- "have we already paid this lane to fetch this page?" -- and
it is the instrument the acquisition ladder consults before it spends again.
A run missing from it is a run the factory is free to buy a second time.

CREDITS: THE RUN TOTAL IS EXACT, THE PER-ROW FIGURE IS AN ESTIMATE
-----------------------------------------------------------------
The meter read 520 before and 515 after, so the run cost five credits and that
total is not in doubt. The ledger's own writer apportions a run total evenly
across its attempts, and says in as many words that the total is exact while the
per-row figure is a reconstruction. That is kept.

It is worth recording that the even split is not what actually happened.
Firecrawl's cost is bimodal -- one credit when a page comes back, none when
every engine is refused -- and on that reading the five credits belong to the
five rows that returned a document (three VALID and two IDENTITY_MISMATCH), with
nothing charged to the two the origin refused outright. That allocation
reconciles to the measured delta exactly, and it is reported alongside the even
split rather than substituted for it, because the ledger's arithmetic is the
ledger's to define.

IDEMPOTENT BY CONSTRUCTION
--------------------------
``attempt_id`` hashes (market, run, identity, lane), and ``merge`` skips an id
it already holds. Running this twice records nothing the second time, which is
the property that makes it safe to re-run during validation.

Read-only with respect to every market but Cincinnati. No network.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003"
MARKET = "cincinnati-oh"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = PACKAGE / "ptf_paid_attempt_ledger_001.json"
RUN_PATH = (PACKAGE / "markets" / "reports"
            / "cincinnati_oh_firecrawl_pass_001.json")
REPORT_PATH = (PACKAGE / "markets" / "reports"
               / "cincinnati_oh_firecrawl_ledger_reconciliation_003.json")

#: The lane these attempts were made on. The run document's own ``lane`` field
#: says "firecrawl (rendered scrape; billed in PLAN CREDITS, no USD)"; the
#: ledger stores the bare lane token that the ladder matches on.
LANE = "firecrawl"

#: An origin that refused every engine returned no document, and Firecrawl bills
#: nothing for it. Used only for the reported bimodal reconciliation, never to
#: overrule the ledger writer's own apportionment.
REFUSED_OUTCOME = "ACCESS_DENIED"


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_as_acquisition_document(run: Dict) -> Dict:
    """The Firecrawl run, shaped as the document ``ingest_run`` reads.

    The two schemas describe the same event with different field names. Nothing
    is invented in the translation: every value below is copied out of the run
    document, and the credit total is its measured meter delta rather than a
    per-call price, which the adapter explicitly refuses to assert.
    """
    results: List[Dict] = []
    for row in run["rows"]:
        results.append({
            "identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "brand": row.get("family") or "",
            "property_code": row.get("property_code") or "",
            "url": row.get("final_url") or row.get("requested_url") or "",
            "official_url": row.get("requested_url") or "",
            "postal_code": row.get("expected_postal_code") or "",
            "street": row.get("expected_street") or "",
            "outcome": row["outcome"],
            "provider": LANE,
            "providers_tried": [LANE],
            "artifact_hash": row.get("page_sha256") or "",
            "artifact_path": row.get("artifact_dir") or "",
            "attempted_at": row.get("captured_at") or "",
            "reader": "generic",
        })
    return {
        "schema": "ptf-market-paid-acquisition/1.0",
        "market_id": run["market_id"],
        # The attempts belong to the order that MADE them, not to this one.
        "work_order": run["work_order"],
        "run_id": run["run_id"],
        "dry_run": False,
        "spend": {
            # No USD was spent: this rung is billed in plan credits.
            "binding_usd_minor": 0,
            "estimated_plan_credits": run["credits"]["delta"],
        },
        "results": results,
    }


def reconcile(write: bool = False) -> Dict:
    run = _load(RUN_PATH)
    ledger = PAL.load(LEDGER_PATH)
    before = list(ledger.get("attempts") or ())

    existing_ids = {r.get("attempt_id") for r in before}
    cincinnati_before = [r for r in before if r.get("market_id") == MARKET]
    firecrawl_before = [r for r in cincinnati_before
                        if (r.get("firecrawl_credits") or 0) > 0
                        or r.get("lane") == LANE]

    records = PAL.ingest_run(_run_as_acquisition_document(run), market_id=MARKET)
    duplicates = [r for r in records if r["attempt_id"] in existing_ids]
    fresh = [r for r in records if r["attempt_id"] not in existing_ids]

    merged = PAL.merge(ledger, records)
    after = list(merged.get("attempts") or ())

    # The bimodal reading, reported rather than applied.
    fetched = [r for r in run["rows"] if r["outcome"] != REFUSED_OUTCOME]
    refused = [r for r in run["rows"] if r["outcome"] == REFUSED_OUTCOME]

    report = OrderedDict()
    report["schema"] = "ptf-paid-ledger-reconciliation/1.0"
    report["work_order"] = WORK_ORDER
    report["market_id"] = MARKET
    report["phase"] = "5 -- reconcile the Firecrawl attempts the parallel order could not write"
    report["provider_calls_made_by_this_order"] = 0
    report["usd_spent_by_this_order"] = 0.0
    report["plan_credits_spent_by_this_order"] = 0
    report["what_this_records"] = (
        "attempts that already happened under %s. No provider was called and no "
        "credit was consumed to produce this file." % run["work_order"])
    report["source_run"] = OrderedDict((
        ("run_id", run["run_id"]),
        ("work_order", run["work_order"]),
        ("lane", run["lane"]),
        ("attempted_rows", run["attempted_rows"]),
        ("credits_before", run["credits"]["before"]),
        ("credits_after", run["credits"]["after"]),
        ("credits_delta_measured", run["credits"]["delta"]),
        ("outcome_counts", run["outcome_counts"]),
    ))
    report["ledger_before"] = OrderedDict((
        ("total_attempts", len(before)),
        ("cincinnati_attempts", len(cincinnati_before)),
        ("cincinnati_firecrawl_attempts", len(firecrawl_before)),
        ("cincinnati_usd_minor", sum(r.get("cost_usd_minor") or 0
                                     for r in cincinnati_before)),
    ))
    report["rows_considered"] = len(records)
    report["already_present"] = len(duplicates)
    report["duplicates_rejected"] = [r["attempt_id"] for r in duplicates]
    report["new_ledger_entries"] = len(fresh)
    report["credits_represented"] = run["credits"]["delta"]
    report["usd_represented_minor"] = 0
    report["apportionment"] = OrderedDict((
        ("method", "the ledger writer's own even split across the run's attempts"),
        ("run_total_is_exact", True),
        ("per_row_figure_is_an_estimate", True),
        ("credits_per_attempt", (run["credits"]["delta"] / len(records))
         if records else 0),
    ))
    report["bimodal_reconciliation_reported_not_applied"] = OrderedDict((
        ("rule", "Firecrawl bills one credit when a document comes back and "
                 "nothing when every engine is refused"),
        ("rows_that_returned_a_document", len(fetched)),
        ("rows_the_origin_refused_outright", len(refused)),
        ("credits_implied", len(fetched)),
        ("measured_meter_delta", run["credits"]["delta"]),
        ("reconciles_exactly", len(fetched) == run["credits"]["delta"]),
    ))
    report["new_entries"] = [
        OrderedDict((("attempt_id", r["attempt_id"]),
                     ("identity_key", r["identity_key"]),
                     ("canonical_name", r["canonical_name"]),
                     ("lane", r["lane"]),
                     ("outcome", r["outcome"]),
                     ("terminal", r["terminal"]),
                     ("reusable_evidence", r["reusable_evidence"]),
                     ("firecrawl_credits", r["firecrawl_credits"]),
                     ("cost_usd_minor", r["cost_usd_minor"])))
        for r in fresh
    ]
    report["ledger_after"] = OrderedDict((
        ("total_attempts", len(after)),
        ("cincinnati_attempts",
         len([r for r in after if r.get("market_id") == MARKET])),
        ("cincinnati_outcomes",
         dict(Counter(r.get("outcome") or "(escalation leg)"
                      for r in after if r.get("market_id") == MARKET))),
    ))
    report["historical_entries_changed"] = 0
    report["other_markets_changed"] = 0

    # Prove the claim rather than asserting it: every pre-existing row must come
    # back byte-identical, and no market but Cincinnati may gain a row.
    by_id_before = {r["attempt_id"]: r for r in before}
    changed = [i for i, r in by_id_before.items()
               if json.dumps(r, sort_keys=True)
               != json.dumps(next(x for x in after if x["attempt_id"] == i),
                             sort_keys=True)]
    report["historical_entries_changed"] = len(changed)
    gained = Counter(r.get("market_id") for r in after) - Counter(
        r.get("market_id") for r in before)
    report["other_markets_changed"] = len(
        [m for m in gained if m != MARKET])
    report["markets_that_gained_rows"] = dict(gained)

    if write:
        PAL.save(LEDGER_PATH, merged)
        # LF-exact: launch_packages/**/*.json is pinned to eol=lf.
        REPORT_PATH.write_bytes(
            (json.dumps(report, indent=1) + "\n").encode("utf-8"))
    return report


def main(argv: List[str]) -> int:
    write = "--write" in argv
    report = reconcile(write=write)
    print(json.dumps({k: report[k] for k in (
        "rows_considered", "already_present", "new_ledger_entries",
        "credits_represented", "historical_entries_changed",
        "other_markets_changed")}, indent=1))
    print("bimodal reconciles exactly:",
          report["bimodal_reconciliation_reported_not_applied"]["reconciles_exactly"])
    print("ledger attempts: %d -> %d"
          % (report["ledger_before"]["total_attempts"],
             report["ledger_after"]["total_attempts"]))
    if not write:
        print("(dry run; pass --write to record)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
