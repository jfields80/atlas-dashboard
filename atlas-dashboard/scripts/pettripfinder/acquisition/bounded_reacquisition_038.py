"""PTF-...-FULL-CLOSURE-038, phase 9 -- the two pages nobody has ever fetched.

Zero-cost replay answered what it could from disk. What remains are properties
whose only persisted capture is a HOMEPAGE, and two of those sites publish a
policy page that discovery already found and no run has ever read: a FAQ and,
on a hotel whose homepage nav says "DOGS", a /dogs/ page.

That is the whole cohort, and it is derived rather than listed. A property
qualifies only when all four hold:

  * it is active-eligible and outside authority,
  * the closure ledger classifies it RECOVERABLE_LOW_COST,
  * source discovery names a first-party policy URL, and
  * no capture journal on disk contains that URL.

Everything else that failed is left alone. Re-fetching the same URL through the
same lane that already returned nothing is not a bounded retry, it is the same
attempt with a new run id, and the work order forbids exactly that.

SOURCE SELECTION IS NOT PROVIDER SELECTION
------------------------------------------
The census URL stays canonical and the LANE stays keyed on it (``route_url``),
so reading a better page cannot move a property to a different provider. No
route, no reader and no schema changes here.

NOTHING ACQUIRED HERE BECOMES AUTHORITY
---------------------------------------
A page that reads cleanly today produces a founder-review CANDIDATE. 036's
approvals were given against rows the founder actually saw, and they do not
reach forward.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import closure_038 as C38            # noqa: E402
from scripts.pettripfinder.acquisition import final_pass_026 as F26         # noqa: E402
from scripts.pettripfinder.acquisition import hilton_decision_023 as H23    # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS        # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2    # noqa: E402

WORK_ORDER = C38.WORK_ORDER
MARKET = C38.MARKET

RUN_ID = "milwaukee-closure-038"
RUN_DIR = REPO / "data" / "acquisition" / RUN_ID / RUN_ID
JOURNAL = REPO / "data" / "acquisition" / RUN_ID / "journal.jsonl"
REPORT = C38.F36.REPORTS / "ptf_milwaukee_bounded_reacquisition_038.json"

#: Ceiling on the cohort. Not a target -- an abort. If the derivation ever
#: proposes more than this many provider calls, something upstream changed and
#: a human decides before money moves.
MAX_PROPERTIES = 4


def cohort() -> List[Dict]:
    """Every property with an unfetched first-party policy page, derived."""
    census = C38.F36.census_rows()
    out = []
    for row in C38.active_rows():
        if row["recovery_class"] != C38.RECOVERABLE_LOW_COST:
            continue
        target = (row["lineage"] or {}).get("unfetched_policy_url", "")
        if not target:
            continue
        identity = census.get(row["identity_key"]) or {}
        out.append({
            "identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "brand": row.get("brand", "") or identity.get("brand", ""),
            "official_url": identity.get("official_url", ""),
            "unfetched_policy_url": target,
            "prior_disposition": row["disposition"],
        })
    return sorted(out, key=lambda item: item["identity_key"])


def preflight() -> Dict:
    rows = cohort()
    problems = []
    if len(rows) > MAX_PROPERTIES:
        problems.append("cohort is %d, above the %d ceiling; a human decides "
                        "before this runs" % (len(rows), MAX_PROPERTIES))
    for row in rows:
        if not row["unfetched_policy_url"].startswith("http"):
            problems.append("%s: no usable policy URL" % row["identity_key"])
    return {"work_order": WORK_ORDER, "run_id": RUN_ID,
            "cohort_size": len(rows), "max_properties": MAX_PROPERTIES,
            "cohort": rows, "problems": problems,
            "provider_calls_authorised": len(rows) if not problems else 0}


async def acquire(row: Mapping) -> Dict:
    record = F26._record_for(row)
    target = SS._retargeted(P2.target_for(record), row["unfetched_policy_url"])
    began = time.monotonic()
    result = await ROUTER.route_property(
        record, target, run_dir=RUN_DIR, run_id=RUN_ID,
        registry=REGISTRY.load(), route_url=row["official_url"])
    document = result.document
    verdict = H23.usable_policy(document, expected_code="")
    return {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "census_url": row["official_url"],
        "source_url": row["unfetched_policy_url"],
        "source_origin": SS.FROM_DISCOVERY,
        "prior_disposition": row["prior_disposition"],
        "providers_tried": list(result.providers_tried),
        "attempts": len(result.attempts),
        "final_state": result.state,
        "acquisition_status": "ACQUIRED" if document is not None
                              else "NOT_ACQUIRED",
        "identity_confirmed": bool((document.identity or {}).get(
            "confirmed", True)) if document is not None else False,
        "policy_block": verdict.get("block_text", ""),
        "policy_block_chars": verdict.get("block_chars", 0),
        "reader_fields": verdict.get("substantive_fields", []),
        "reader_withheld": verdict.get("withheld_fields", []),
        "states_a_refusal": verdict.get("states_a_refusal", False),
        "publication_grade": result.state == "ACQUIRED_PUBLICATION_GRADE",
        "usable_policy": verdict["verdict"],
        "failure": result.failure,
        "failure_class": result.failure_class,
        "elapsed_seconds": round(time.monotonic() - began, 3),
        "estimated_bytes": result.cost.estimated_bytes,
        "authority_effect": "NONE -- a reading here is a founder-review "
                            "candidate, never an approval",
    }


async def run() -> Dict:
    check = preflight()
    if check["problems"]:
        raise SystemExit("ABORT: " + "; ".join(check["problems"]))
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    done = {}
    if JOURNAL.is_file():
        for line in JOURNAL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                done[entry["identity_key"]] = entry
    before = F26.read_spend("038:before")
    out: List[Dict] = []
    for row in check["cohort"]:
        if row["identity_key"] in done:
            out.append(done[row["identity_key"]])
            continue
        try:
            result = await acquire(row)
        except Exception as exc:                                  # noqa: BLE001
            result = {"identity_key": row["identity_key"],
                      "canonical_name": row["canonical_name"],
                      "source_url": row["unfetched_policy_url"],
                      "acquisition_status": "NOT_ACQUIRED",
                      "final_state": "EXCEPTION", "usable_policy": H23.NOT_USABLE,
                      "publication_grade": False, "failure": repr(exc)[:200]}
        # Journalled one property at a time: a kill mid-run must not cost the
        # rows already paid for.
        with JOURNAL.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        out.append(result)
    after = F26.read_spend("038:after")
    return {
        "schema": "ptf-milwaukee-bounded-reacquisition/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "run_id": RUN_ID,
        "cohort_size": len(check["cohort"]),
        "acquired": sum(1 for r in out
                        if r.get("acquisition_status") == "ACQUIRED"),
        "publication_grade": sum(1 for r in out if r.get("publication_grade")),
        "usable": sum(1 for r in out if r.get("usable_policy") == H23.USABLE),
        "spend": F26.spend_delta(before, after),
        "properties": out,
        "authority_effect": "NONE. Nothing acquired here entered authority, "
                            "nothing was published and nothing was deployed.",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.run:
        doc = asyncio.run(run())
        if args.write_report:
            REPORT.write_text(json.dumps(doc, indent=1, ensure_ascii=False)
                              + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in doc.items() if k != "properties"},
                         indent=2))
        for row in doc["properties"]:
            print("%-40s %-28s %s" % (row["canonical_name"][:40],
                                      row.get("final_state", ""),
                                      row.get("usable_policy", "")))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
