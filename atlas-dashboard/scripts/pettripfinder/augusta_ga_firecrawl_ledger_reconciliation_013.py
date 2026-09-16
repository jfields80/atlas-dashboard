"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 Phase 26 -- record a spend that already happened.

The real Firecrawl acquisition pass (augusta_ga_firecrawl_acquisition_005.py,
plus the corrective retry embedded in augusta_ga_wyndham_lane_009.py) already
spent real plan credits and wrote its own market reports. Neither ever
recorded its attempts in the SHARED cross-run paid-attempt ledger
(launch_packages/pettripfinder/ptf_paid_attempt_ledger_001.json), which the
FAST lane's rule O and the acquisition ladder consult before spending again.
This script closes that gap, following the exact precedent of
cincinnati_oh_firecrawl_ledger_reconciliation_003.py.

WHAT THIS IS NOT
----------------
Not a purchase. No provider is called, no credit is consumed, no URL is
fetched. Every field written here is read out of the two committed run
reports. A ledger entry is a RECORD of a past attempt.

Read-only with respect to every market but Augusta. No network.
"""
from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET = "augusta-ga"
LANE = "firecrawl"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = PACKAGE / "ptf_paid_attempt_ledger_001.json"
RUN_005 = PACKAGE / "markets" / "reports" / "augusta_ga_firecrawl_acquisition_005.json"
RUN_009 = PACKAGE / "markets" / "reports" / "augusta_ga_wyndham_lane_009.json"
REPORT_PATH = (PACKAGE / "markets" / "reports"
               / "augusta_ga_firecrawl_ledger_reconciliation_013.json")


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rows_as_acquisition_document(rows: List[Dict], *, run_id: str,
                                  credits_delta: int) -> Dict:
    results = []
    for row in rows:
        if not row.get("ok"):
            continue
        results.append({
            "identity_key": row["identity_key"],
            "canonical_name": row.get("canonical_name") or row["identity_key"],
            "brand": row.get("family") or "",
            "property_code": "",
            "url": row.get("final_url") or row.get("requested_url") or "",
            "official_url": row.get("requested_url") or "",
            "postal_code": "",
            "street": "",
            "outcome": "ACQUIRED_PUBLICATION_GRADE",
            "final_state": "ACQUIRED_PUBLICATION_GRADE",
            "provider": LANE,
            "providers_tried": [LANE],
            "artifact_hash": row.get("content_sha256") or "",
            "artifact_path": "",
            "attempted_at": row.get("captured_at") or "",
            "reader": "generic",
        })
    return {
        "schema": "ptf-market-paid-acquisition/1.0",
        "market_id": MARKET,
        "work_order": WORK_ORDER,
        "run_id": run_id,
        "dry_run": False,
        "spend": {
            "binding_usd_minor": 0,
            "estimated_plan_credits": credits_delta,
        },
        "results": results,
    }


def reconcile(write: bool = False) -> Dict:
    run_005 = _load(RUN_005)
    run_009 = _load(RUN_009)
    ledger = PAL.load(LEDGER_PATH)
    before = list(ledger.get("attempts") or ())
    existing_ids = {r.get("attempt_id") for r in before}

    doc_005 = _rows_as_acquisition_document(
        run_005.get("rows") or [], run_id="augusta_ga_firecrawl_acquisition_005",
        credits_delta=int(run_005.get("credits_used") or 0))
    doc_009 = _rows_as_acquisition_document(
        run_009.get("rows") or [], run_id="augusta_ga_wyndham_lane_009",
        credits_delta=len([r for r in (run_009.get("rows") or []) if r.get("ok")]))

    records = PAL.ingest_run(doc_005, market_id=MARKET) + PAL.ingest_run(doc_009, market_id=MARKET)
    duplicates = [r for r in records if r["attempt_id"] in existing_ids]
    fresh = [r for r in records if r["attempt_id"] not in existing_ids]

    merged = PAL.merge(ledger, records)
    after = list(merged.get("attempts") or ())

    report = OrderedDict()
    report["schema"] = "ptf-paid-ledger-reconciliation/1.0"
    report["work_order"] = WORK_ORDER
    report["market_id"] = MARKET
    report["what_this_records"] = ("attempts that already happened under "
                                   "augusta_ga_firecrawl_acquisition_005 and "
                                   "augusta_ga_wyndham_lane_009. No provider "
                                   "was called and no credit was consumed to "
                                   "produce this file.")
    report["provider_calls_made_by_this_order"] = 0
    report["usd_spent_by_this_order"] = 0.0
    report["rows_considered"] = len(records)
    report["already_present"] = len(duplicates)
    report["new_ledger_entries"] = len(fresh)
    report["new_entries"] = [
        OrderedDict((("attempt_id", r["attempt_id"]), ("identity_key", r["identity_key"]),
                     ("canonical_name", r["canonical_name"]), ("lane", r["lane"]),
                     ("run_id", r["run_id"])))
        for r in fresh
    ]
    report["ledger_before_total_attempts"] = len(before)
    report["ledger_after_total_attempts"] = len(after)

    by_id_before = {r["attempt_id"]: r for r in before}
    changed = [i for i, r in by_id_before.items()
              if json.dumps(r, sort_keys=True)
              != json.dumps(next(x for x in after if x["attempt_id"] == i), sort_keys=True)]
    report["historical_entries_changed"] = len(changed)
    from collections import Counter
    gained = Counter(r.get("market_id") for r in after) - Counter(r.get("market_id") for r in before)
    report["other_markets_changed"] = len([m for m in gained if m != MARKET])

    if write:
        PAL.save(LEDGER_PATH, merged)
        REPORT_PATH.write_bytes((json.dumps(report, indent=1) + "\n").encode("utf-8"))
    return report, records


def main(argv: List[str]) -> int:
    write = "--write" in argv
    report, records = reconcile(write=write)
    print(json.dumps({k: report[k] for k in (
        "rows_considered", "already_present", "new_ledger_entries",
        "historical_entries_changed", "other_markets_changed")}, indent=1))
    if not write:
        print("(dry run; pass --write to record)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
