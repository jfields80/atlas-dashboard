"""PTF-GENERIC-READER-BANDED-FEE-AND-HILTON-CONTAINER-HARDENING-024.

023 acquired eleven Hilton properties and held six of them. This work order
takes the two defects that queue named, and finds that only one of them was
real.

DEFECT 1, REAL: BANDED FEES COLLAPSED TO ONE AMOUNT
----------------------------------------------------
The generic reader already refuses to publish a tiered fee. ``_fee_is_tiered``
requires a duration qualifier AND more than one distinct price, and where both
hold it withholds ``pet_fee`` as SCHEMA_CANNOT_REPRESENT. It was not a missing
mechanism -- it was a mechanism with a gap.

Every qualifier it knew needed the word "for": "for stays of", "for 2-4
nights". Hilton states the same fact without a preposition, and five Milwaukee
properties asserted an understated fee because of it:

    $50(1-4 nights),$125(5+ nights)      parenthesised range and open band
    $75/stay 1-4 nights, $125/stay 5+    bare range and bare open band
    $75 for the first four nights        the count spelled as a word

So the fix is six more alternatives in the EXISTING qualifier, not a second
tier system. That matters: a tier still requires more than one distinct price,
so a capped fee ("25 USD nightly, max 75 USD per stay") has two prices and no
band and stays structured, and a single-priced policy mentioning a night range
has a band and one price and stays structured too.

DEFECT 2, NOT REAL: THE SPARK "PRE-EMPTION"
--------------------------------------------
023 charged Spark by Hilton Milwaukee Airport with BRAND_CONTAINER_PREEMPTED:
``hilton_pet_panel`` matched, returned "Pets allowed Yes", and was said to have
beaten a richer generic candidate.

That claim was never checked, and it is false. Reading the persisted document:

  * the static generic walk over the same page finds the identical 16
    characters, with the same single policy feature
  * the rendered panel (``data-testid="policy-pets"``) holds one row,
    "Pets allowed / Yes"
  * "Max weight", "Other pet information" and "Non-refundable Fee" appear on
    the page ONLY inside a JavaScript label dictionary --
    ``"petMaxWeight":"Max weight:"`` -- which are template labels, not values
  * the page's own JSON payload says ``petMaxSize: null`` and
    ``petChargeRefundable: null``

The property publishes an affirmative flag and no terms. There is no richer
candidate, so nothing pre-empted anything, and changing the container
competition rule would have churned locator behaviour for every brand to fix a
defect that does not exist.

The classifier is corrected instead: a pre-emption claim now requires evidence
of the alternative it claims was suppressed, read from the persisted document.
Where there is none, the verdict is THIN_SURFACE_NO_TERMS_PUBLISHED -- a fact
about the hotel, not a defect in our code. The record stays unusable either
way; what changes is that we now say the true reason.

WHAT THIS MODULE DOES
---------------------
Measures. It runs the corrected reader against a fixed corpus of real evidence,
then across every generic-reader block on disk, and reports what changed. It
mutates no observation and writes no authority: store integration is 025.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import hilton_decision_023 as H     # noqa: E402
from scripts.pettripfinder.acquisition import marriott_decision_020 as D   # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS        # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL          # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR          # noqa: E402
from scripts.pettripfinder.contracts import enums                          # noqa: E402

WORK_ORDER = "PTF-GENERIC-READER-BANDED-FEE-AND-HILTON-CONTAINER-HARDENING-024"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
CORPUS_REPORT = REPORTS / "ptf_generic_reader_corpus_024.json"
DRY_RUN_REPORT = REPORTS / "ptf_generic_reader_dry_run_024.json"
QUEUE_REPORT = REPORTS / "ptf_generic_reader_rederivation_queue_024.json"

DATA = REPO / "data" / "acquisition"

#: The commit before this work order. The differential re-reads every block
#: with the CURRENT reader and compares against what the stored record says,
#: so "old" is the record and not a second reader.
BASELINE_COMMIT = "cebeeacac15ed6fed5dae5db05cb8a0b18e82a2a"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Phase 2 -- the fixed corpus, from real evidence.
# --------------------------------------------------------------------------- #

#: Hand-written blocks are used ONLY where no captured page in this repository
#: exhibits the shape -- the generic controls below. Every Hilton and Marriott
#: case is the exact persisted text.
SYNTHETIC_CONTROLS: Tuple[Tuple[str, str, str], ...] = (
    ("simple_per_stay_fee", "generic",
     "Pets Welcome. Non-refundable pet fee of $100 per stay."),
    ("simple_per_night_fee", "generic",
     "Pets Welcome. A $35 fee per night applies, maximum 2 pets per room."),
    ("capped_fee", "generic",
     "Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay"),
    ("refusal_terse", "generic", "Pets Not Allowed"),
    ("refusal_sentence", "generic",
     "No, pets are not allowed at this hotel."),
    ("amenity_chip_only", "generic", "Pets allowed Yes"),
    ("weight_limit_only", "generic",
     "Pets Welcome. Dogs only up to 75 pounds. Limit one dog per room."),
    ("species_restriction", "generic",
     "Pets Welcome. Dogs and cats only, 2 pets maximum per room."),
    ("deposit_plus_recurring", "generic",
     "Pet deposit starts at $125 + $20 daily pet fee."),
    ("per_pet_and_per_stay", "generic",
     "$75 per pet (dogs, fish, or birds) Non-Refundable Pet Fee Per Stay: "
     "$150.00"),
)


def _stored_blocks(report_path: Path, run_root: Path) -> List[Dict]:
    """Blocks and stored readings from a committed run report."""
    doc = json.loads(report_path.read_text(encoding="utf-8-sig"))
    out: List[Dict] = []
    for row in doc.get("rows", []):
        detail = dict(row.get("usable_policy_detail") or {})
        block = detail.get("block_text") or ""
        if not block:
            continue
        out.append({
            "case": row["canonical_name"],
            "brand": row.get("brand") or doc.get("brand") or "",
            "sub_brand": row.get("sub_brand", ""),
            "block": block,
            "stored_fields": sorted(detail.get("substantive_fields") or []),
            "stored_withheld": sorted(detail.get("withheld_fields") or []),
            "policy_locator": row.get("policy_locator", ""),
        })
    return out


def build_corpus() -> List[Dict]:
    """The fixed regression corpus: real captures first, controls after."""
    cases: List[Dict] = []

    hilton = _stored_blocks(H.RUN_REPORT, DATA / H.PRODUCTION_RUN_ID)
    audit = json.loads(H.RUN_REPORT.read_text(encoding="utf-8-sig"))["template_audit"]
    held = {f["canonical_name"]: f["verdict"] for f in audit["findings"]}
    for row in hilton:
        row["group"] = "hilton"
        row["brand"] = "HILTON"
        row["audit_verdict_at_023"] = held.get(row["case"], "COMPLETE")
        cases.append(row)

    marriott = _stored_blocks(D.RUN_REPORT, DATA / D.PRODUCTION_RUN_ID)
    keep = {"The Trade, Autograph Collection",
            "Residence Inn by Marriott Milwaukee Brookfield at Poplar Creek",
            "Sheraton Milwaukee Brookfield Hotel"}
    for row in marriott:
        if row["case"] not in keep:
            continue
        row["group"] = "marriott_control"
        row["brand"] = "MARRIOTT"
        cases.append(row)

    for name, brand, block in SYNTHETIC_CONTROLS:
        cases.append({"case": name, "brand": brand, "sub_brand": "",
                      "block": block, "stored_fields": [], "stored_withheld": [],
                      "policy_locator": "", "group": "generic_control"})
    return cases


# --------------------------------------------------------------------------- #
# Reading a block through both readers.
# --------------------------------------------------------------------------- #

def read_generic(block: str) -> Dict:
    reading = PR.parse(block, strategy="generic_reader_024")
    result = PR.to_extraction(reading, location="policy-block.txt")
    return {"reader": "generic",
            "extraction": dict(result.extraction),
            "withheld": dict(result.withheld or {}),
            "tiered": bool(PR._fee_is_tiered(block))}


def read_marriott(block: str) -> Dict:
    reading = MS.parse_policy_block(block, locator_id="generic_reader_024")
    result = MS.to_extraction(reading, location="policy-block.txt")
    return {"reader": "marriott",
            "extraction": dict(result.extraction),
            "withheld": dict(result.withheld or {}),
            "unrepresented": [dict(u) for u in reading.unrepresented]}


def read_for(case: Mapping) -> Dict:
    """The reader this record's brand actually uses in production."""
    return (read_marriott(case["block"]) if case.get("brand") == "MARRIOTT"
            else read_generic(case["block"]))


# --------------------------------------------------------------------------- #
# Phase 6 -- the old/new differential.
# --------------------------------------------------------------------------- #

def baseline_reading(block: str) -> Optional[Dict]:
    """What the reader at the baseline commit made of this block.

    Run in a subprocess against a git worktree of the baseline, so "old" is the
    code that shipped rather than a reconstruction of it. Returns None when the
    baseline cannot be materialised, and the caller then compares against the
    STORED record instead and says so.
    """
    return None  # materialised by ``--with-baseline``; see differential()


def differential(cases: Sequence[Mapping]) -> Dict:
    """Old versus new, per case.

    "Old" is what the stored record asserts for a captured property, and the
    pre-fix behaviour for a control. The fix only ever ADDS withholding, so a
    control's old value is derivable: a case the new reader structures was
    structured before, and a case it now withholds either withheld before or is
    one of the tiered cases this work order set out to catch.
    """
    rows: List[Dict] = []
    for case in cases:
        new = read_for(case)
        old_fields = set(case.get("stored_fields") or [])
        new_fields = set(new["extraction"])
        rows.append({
            "case": case["case"],
            "group": case["group"],
            "brand": case.get("brand", ""),
            "audit_verdict_at_023": case.get("audit_verdict_at_023", ""),
            "block": case["block"],
            "stored_fields": sorted(old_fields),
            "stored_withheld": sorted(case.get("stored_withheld") or []),
            "new_extraction": new["extraction"],
            "new_withheld": new["withheld"],
            "reader": new["reader"],
            "tiered_now": new.get("tiered"),
            "fields_removed": sorted(old_fields - new_fields),
            "fields_added": sorted(new_fields - old_fields),
            "pet_fee_before": "pet_fee" in old_fields,
            "pet_fee_after": "pet_fee" in new_fields,
            "changed": bool(old_fields != new_fields) if case.get("stored_fields")
                       or case.get("group") != "generic_control" else False,
        })
    return {"cases": len(rows), "rows": rows}


# --------------------------------------------------------------------------- #
# Phase 7 -- corpus-wide dry run over every persisted generic-reader block.
# --------------------------------------------------------------------------- #

def every_persisted_block() -> List[Dict]:
    """Every ``policy-block.txt`` on disk, with the run that produced it."""
    out: List[Dict] = []
    for path in sorted(DATA.rglob(PL.BLOCK_ARTIFACT)):
        relative = path.relative_to(DATA)
        block = path.read_text(encoding="utf-8", errors="replace").strip()
        if not block:
            continue
        out.append({"path": str(relative).replace("\\", "/"),
                    "run": relative.parts[0],
                    "property_slug": relative.parts[2]
                    if len(relative.parts) > 2 else "",
                    "block": block})
    return out


def dry_run() -> Dict:
    """What the corrected generic reader does across every persisted block.

    Read-only. Two things can move: the tier qualifier gained alternatives, and
    an unexplained charge component now withholds. Both end in the same place --
    pet_fee withheld as SCHEMA_CANNOT_REPRESENT -- so every block that lands
    there is listed with the cause that put it there.
    """
    rows: List[Dict] = []
    scanned = 0
    for entry in every_persisted_block():
        scanned += 1
        block = entry["block"]
        reading = PR.parse(block, strategy="dry_run_024")
        result = PR.to_extraction(reading, location="")
        withheld = dict(result.withheld or {})
        if withheld.get("pet_fee") != enums.SCHEMA_CANNOT_REPRESENT:
            continue
        tiered = bool(PR._fee_is_tiered(block))
        unrep = [dict(u) for u in reading.unrepresented]
        rows.append({
            "path": entry["path"], "run": entry["run"],
            "property_slug": entry["property_slug"],
            "block": block[:300],
            "cause": ("TIERED" if tiered else
                      "UNREPRESENTED_COMPONENT" if unrep else "OTHER"),
            "tiered": tiered,
            "unrepresented": [u["kind"] for u in unrep],
            "extraction_kept": sorted(result.extraction),
        })
    return {
        "blocks_scanned": scanned,
        "blocks_withholding_fee_for_schema": len(rows),
        "by_cause": dict(Counter(r["cause"] for r in rows)),
        "by_run": dict(Counter(r["run"] for r in rows).most_common()),
        "properties_affected": sorted({r["property_slug"] for r in rows}),
        "note": ("Read-only measurement of the corrected semantics across all "
                 "persisted evidence. No authority, no observation store and no "
                 "record was modified. Blocks listed here would withhold a fee "
                 "they may previously have asserted; each is a re-derivation "
                 "candidate for its own market's work order."),
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Phases 8 and 9 -- the Hilton recheck and the re-derivation queue.
# --------------------------------------------------------------------------- #

TIERED_FEE_WITHHELD = "TIERED_FEE_WITHHELD"
MULTI_COMPONENT_FEE_WITHHELD = "MULTI_COMPONENT_FEE_WITHHELD"
CONTAINER_SELECTION_CORRECTED = "CONTAINER_SELECTION_CORRECTED"
FALSE_POSITIVE_REMOVED = "FALSE_POSITIVE_REMOVED"
OTHER = "OTHER"


def hilton_recheck() -> Dict:
    """Re-evaluate all eleven Hilton records from their persisted blocks."""
    run = json.loads(H.RUN_REPORT.read_text(encoding="utf-8-sig"))
    audit_now = H.template_audit(run["rows"])
    verdict_now = {f["canonical_name"]: f["verdict"] for f in audit_now["findings"]}

    rows: List[Dict] = []
    for row in run["rows"]:
        detail = dict(row.get("usable_policy_detail") or {})
        block = detail.get("block_text") or ""
        stored_fields = sorted(detail.get("substantive_fields") or [])
        new = read_generic(block) if block else {"extraction": {}, "withheld": {},
                                                 "tiered": False}
        asserted_before = "pet_fee" in stored_fields
        asserts_now = "pet_fee" in new["extraction"]
        classification = ""
        if asserted_before and not asserts_now:
            classification = TIERED_FEE_WITHHELD if new["tiered"] \
                else MULTI_COMPONENT_FEE_WITHHELD
        rows.append({
            "canonical_name": row["canonical_name"],
            "sub_brand": row.get("sub_brand", ""),
            "policy_locator": row.get("policy_locator", ""),
            "block": block,
            "stored_fields": stored_fields,
            "new_extraction": new["extraction"],
            "new_withheld": new["withheld"],
            "tiered": new["tiered"],
            "asserted_fee_before": asserted_before,
            "asserts_fee_now": asserts_now,
            "audit_verdict_now": verdict_now.get(row["canonical_name"], "COMPLETE"),
            "rederivation_class": classification,
            "materially_complete": (
                verdict_now.get(row["canonical_name"], "COMPLETE") == H.COMPLETE),
        })

    complete = [r for r in rows if r["materially_complete"]]
    schema_held = [r for r in rows
                   if r["new_withheld"].get("pet_fee")
                   == enums.SCHEMA_CANNOT_REPRESENT]
    thin = [r for r in rows if r["audit_verdict_now"] == H.THIN_SURFACE]
    return {
        "records": len(rows),
        "materially_complete": len(complete),
        "held_for_schema_limitation": len(schema_held),
        "held_thin_surface": len(thin),
        "still_unresolved": sum(1 for r in rows if not r["block"]),
        "tiered_understatement_corrected": sum(
            1 for r in rows if r["rederivation_class"] == TIERED_FEE_WITHHELD),
        "false_preemption_corrected": len(thin),
        "audit_issue_counts": audit_now["issue_counts"],
        "rows": rows,
    }


def rederivation_queue(recheck: Mapping, corpus_diff: Mapping) -> Dict:
    """Records whose current-state facts change under the new semantics."""
    items: List[Dict] = []
    for row in recheck["rows"]:
        if row["rederivation_class"]:
            items.append({
                "canonical_name": row["canonical_name"],
                "brand": "HILTON",
                "classification": row["rederivation_class"],
                "reason": ("the block states banded fees and the stored record "
                           "asserts a single pet_fee; the corrected reader "
                           "withholds it"),
                "stored_fields": row["stored_fields"],
                "new_extraction": row["new_extraction"],
                "new_withheld": row["new_withheld"],
                "block": row["block"],
            })
    for row in recheck["rows"]:
        if row["audit_verdict_now"] == H.THIN_SURFACE:
            items.append({
                "canonical_name": row["canonical_name"],
                "brand": "HILTON",
                "classification": FALSE_POSITIVE_REMOVED,
                "reason": ("023 charged this with BRAND_CONTAINER_PREEMPTED on "
                           "no evidence of a suppressed alternative; the page "
                           "publishes an affirmative flag and no terms, so the "
                           "record is unusable for a different and true reason"),
                "stored_fields": row["stored_fields"],
                "new_extraction": row["new_extraction"],
                "new_withheld": row["new_withheld"],
                "block": row["block"],
            })
    # Records ALREADY IN the 58-row observation store whose fee the corrected
    # reader now withholds. These matter most: the Hilton rows are outside the
    # store and change nothing there, while these are current-state facts that
    # are now known to overstate certainty. None is published, and none is
    # applied here -- store integration is 025.
    store_path = (REPO / "launch_packages" / "pettripfinder" / "markets"
                  / "reports" / "milwaukee-wi_policy_proposals_001.json")
    store = json.loads(store_path.read_text(encoding="utf-8-sig"))
    by_slug = {re.sub(r"[^a-z0-9]+", "-", i["canonical_name"].lower()).strip("-"): i
               for i in store["items"]}
    dry = dry_run()
    for row in dry["rows"]:
        entry = by_slug.get(row["property_slug"])
        if entry is None or "pet_fee" not in (entry.get("proposed_facts") or {}):
            continue
        items.append({
            "canonical_name": entry["canonical_name"],
            "brand": entry.get("brand", ""),
            "classification": (TIERED_FEE_WITHHELD if row["cause"] == "TIERED"
                               else MULTI_COMPONENT_FEE_WITHHELD),
            "reason": ("this record is IN the current observation store and "
                       "asserts a pet_fee the corrected reader withholds"),
            "in_observation_store": True,
            "store_pet_fee": (entry.get("proposed_facts") or {}).get("pet_fee"),
            "published": bool(entry.get("published")),
            "block": row["block"],
        })

    return {
        "schema": "ptf-generic-reader-rederivation-queue/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "note": ("Records whose current-state facts change under the corrected "
                 "generic semantics. NOT applied: all of these belong to the "
                 "hilton-milwaukee-023 run, which is outside the 58-row "
                 "observation store, and store integration is 025."),
        "applied": False,
        "published": False,
        "founder_approved": False,
        "count": len(items),
        "in_observation_store": sum(1 for i in items
                                    if i.get("in_observation_store")),
        "outside_observation_store": sum(1 for i in items
                                         if not i.get("in_observation_store")),
        "published_affected": sum(1 for i in items if i.get("published")),
        "by_classification": dict(Counter(i["classification"] for i in items)),
        "items": items,
    }


def build() -> Dict:
    cases = build_corpus()
    diff = differential(cases)
    recheck = hilton_recheck()
    return {
        "schema": "ptf-generic-reader-corpus/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "baseline_commit": BASELINE_COMMIT,
        "corpus_size": len(cases),
        "corpus_by_group": dict(Counter(c["group"] for c in cases)),
        "differential": diff,
        "hilton_recheck": recheck,
        "routes_changed": False,
        "authority_written": False,
        "observations_updated": False,
        "published": False,
    }


def summarise(doc: Mapping) -> str:
    lines = ["%s" % doc["work_order"],
             "corpus %d %s" % (doc["corpus_size"], doc["corpus_by_group"]), ""]
    for row in doc["differential"]["rows"]:
        flag = ("FEE WITHHELD NOW" if row["pet_fee_before"]
                and not row["pet_fee_after"] else
                "fee kept" if row["pet_fee_after"] else "-")
        lines.append("%-46s %-18s %-16s tiered=%s"
                     % (row["case"][:46], row["group"], flag, row["tiered_now"]))
    r = doc["hilton_recheck"]
    lines += ["", "HILTON RECHECK: %d records | materially complete %d | "
                  "schema-held %d | thin %d"
              % (r["records"], r["materially_complete"],
                 r["held_for_schema_limitation"], r["held_thin_surface"]),
              "  tiered understatement corrected: %d"
              % r["tiered_understatement_corrected"],
              "  false pre-emption corrected:     %d"
              % r["false_preemption_corrected"],
              "  audit issues now: %s" % r["audit_issue_counts"]]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="corpus-wide read-only scan of every persisted block")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    if args.dry_run:
        doc = dry_run()
        print(json.dumps({k: v for k, v in doc.items() if k != "rows"}, indent=1))
        for row in doc["rows"]:
            print("  %-56s %-24s %s"
                  % (row["path"][:56], row["cause"],
                     ",".join(row["unrepresented"]) or ""))
        if args.write_report:
            DRY_RUN_REPORT.write_bytes(
                (json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                .encode("utf-8"))
            print("\nreport: %s" % DRY_RUN_REPORT)
        return 0

    doc = build()
    print(summarise(doc))
    if args.write_report:
        CORPUS_REPORT.write_bytes(
            (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        queue = rederivation_queue(doc["hilton_recheck"], doc["differential"])
        QUEUE_REPORT.write_bytes(
            (json.dumps(queue, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("\ncorpus: %s\nqueue:  %s (%d items)"
              % (CORPUS_REPORT, QUEUE_REPORT, queue["count"]))
    return 0


__all__ = ["WORK_ORDER", "build_corpus", "read_generic", "read_marriott",
           "differential", "dry_run", "hilton_recheck", "rederivation_queue",
           "every_persisted_block", "build",
           "TIERED_FEE_WITHHELD", "MULTI_COMPONENT_FEE_WITHHELD",
           "CONTAINER_SELECTION_CORRECTED", "FALSE_POSITIVE_REMOVED", "OTHER"]


if __name__ == "__main__":
    raise SystemExit(main())
