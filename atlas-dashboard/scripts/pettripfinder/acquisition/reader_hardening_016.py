"""PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016 -- the reader differential.

WHAT THIS IS FOR
----------------
A reader change is a claim about many documents, and the only honest way to
make one is to run the old reader and the new reader over the same fixed set
and print both answers. This module is that harness. It does not fetch, it does
not write authority, and it holds no property-specific rule: every case is a
row in a committed corpus, and the corpus is text the previous work orders
already paid for.

WHY THE CORPUS IS COMMITTED AS TEXT
-----------------------------------
``data/`` is gitignored, so a corpus that read the cached HTML would evaluate
to nothing in a fresh worktree and the tests guarding this change would pass by
vacuum. The corpus therefore carries the extracted document TEXT, which is also
the smallest thing that can still exercise the locator -- a case whose defect is
"the locator found no block at all" cannot be represented by the block.

WHAT A "BETTER" RESULT MEANS
----------------------------
Three directions, counted apart, because they are not the same event:

  STRUCTURED   a field the reader now states and did not before
  WITHHELD     a field the reader now refuses to state, with a reason
  REMOVED      a value the reader used to state and no longer does

More structured output is not automatically an improvement and fewer fields is
not automatically a regression: a false positive removed is a win, and a fee
withheld because the surface prices it two ways is a win. So the direction is
recorded per field and the judgement is left visible rather than folded into a
single percentage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402

REPO = _REPO_ROOT
WORK_ORDER = "PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016"
CORPUS = (REPO / "tests" / "pettripfinder" / "fixtures"
          / "reader_hardening_016" / "corpus.json")
#: The reader as it stood at 8a58409, recorded before a line of it was edited.
#: Committed so the differential is reproducible by anyone, rather than by
#: whoever still has the scratch file.
BASELINE = (REPO / "tests" / "pettripfinder" / "fixtures"
            / "reader_hardening_016" / "baseline_8a58409.json")
REPORT = (REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
          / "ptf_reader_hardening_differential_016.json")

#: Groups whose measured outcome this work order is answerable for.
KNOWN_MISSES = "URL_FOUND_READER_STILL_MISSES"
CONTROLS = "URL_FIX_SUFFICIENT"
RED_ROOF = "RED_ROOF"
AMENITY_CHIPS = "MOTEL6_AMENITY_CHIP"


def load_corpus() -> Dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def block_for(case: Mapping) -> str:
    """The policy block this case presents to the parser.

    A case built from a document is re-located every time, because the locator
    is part of what this work order changes: Wildwood's policy was on the page
    and the locator returned nothing, and a corpus that stored only the block
    would have recorded that defect as an empty string forever.
    """
    if case.get("document_text") is None:
        return case["block_before"]
    hit = UC.locate_policy_in_text(case["document_text"])
    return hit.text if hit.found else ""


def read(case: Mapping) -> Dict:
    """One case, all the way through the reader that is installed right now."""
    block = block_for(case)
    if not block:
        return {"block": "", "block_chars": 0, "block_found": False,
                "extraction": {}, "withheld": {}, "flags": [], "notes": []}
    reading = PR.parse(block, strategy="reader_hardening_016")
    result = PR.to_extraction(reading, location="")
    return {
        "block": block,
        "block_chars": len(block),
        "block_found": True,
        "extraction": dict(result.extraction),
        "withheld": dict(result.withheld or {}),
        "flags": [dict(f) for f in (result.flags or [])],
        "notes": list(reading.parser_notes),
    }


def snapshot() -> Dict[str, Dict]:
    """Every case read by the reader as it stands. The baseline, or the after."""
    return {c["case_id"]: read(c) for c in load_corpus()["cases"]}


# --------------------------------------------------------------------------- #
# The differential.
# --------------------------------------------------------------------------- #

STRUCTURED = "NEWLY_STRUCTURED"
WITHHELD = "NEWLY_WITHHELD"
REMOVED = "VALUE_REMOVED"
CHANGED = "VALUE_CHANGED"


def field_changes(before: Mapping, after: Mapping) -> List[Dict]:
    """Field-by-field, in both directions, with the direction named."""
    changes: List[Dict] = []
    fields = sorted(set(before.get("extraction", {}))
                    | set(after.get("extraction", {}))
                    | set(before.get("withheld", {}))
                    | set(after.get("withheld", {})))
    for name in fields:
        old = before.get("extraction", {}).get(name)
        new = after.get("extraction", {}).get(name)
        old_withheld = before.get("withheld", {}).get(name)
        new_withheld = after.get("withheld", {}).get(name)
        if old == new and old_withheld == new_withheld:
            continue
        if old is None and new is not None:
            direction = STRUCTURED
        elif old is not None and new is None:
            direction = WITHHELD if new_withheld else REMOVED
        elif old != new:
            direction = CHANGED
        else:
            direction = WITHHELD if new_withheld else REMOVED
        changes.append({
            "field": name, "old": old, "new": new,
            "old_withholding_reason": old_withheld,
            "new_withholding_reason": new_withheld,
            "direction": direction,
        })
    return changes


def differential(before: Mapping[str, Dict],
                 after: Mapping[str, Dict]) -> Dict:
    cases = load_corpus()["cases"]
    rows = []
    for case in cases:
        key = case["case_id"]
        old, new = before.get(key, {}), after.get(key, {})
        changes = field_changes(old, new)
        rows.append({
            "case_id": key,
            "group": case["group"],
            "property_name": case["property_name"],
            "source_url": case["source_url"],
            "note": case["note"],
            "policy_text": new.get("block") or old.get("block") or "",
            "block_found_before": bool(old.get("block_found")),
            "block_found_after": bool(new.get("block_found")),
            "old_output": old.get("extraction", {}),
            "new_output": new.get("extraction", {}),
            "old_withheld": old.get("withheld", {}),
            "new_withheld": new.get("withheld", {}),
            "new_flags": [f.get("code") for f in new.get("flags", [])],
            "changes": changes,
            "changed": bool(changes) or
                       bool(old.get("block_found")) != bool(new.get("block_found")),
        })
    return {"rows": rows, "totals": _totals(rows)}


def _totals(rows: List[Dict]) -> Dict:
    counts = {"cases": len(rows), "changed": 0, "unchanged": 0,
              STRUCTURED: 0, WITHHELD: 0, REMOVED: 0, CHANGED: 0,
              "blocks_newly_located": 0}
    for row in rows:
        counts["changed" if row["changed"] else "unchanged"] += 1
        if row["block_found_after"] and not row["block_found_before"]:
            counts["blocks_newly_located"] += 1
        for change in row["changes"]:
            counts[change["direction"]] += 1
    return counts


def _fields(row: Mapping) -> set:
    return set(row.get("new_output") or {})


def outcomes(diff: Mapping) -> Dict:
    """The required outcomes, evaluated mechanically rather than asserted."""
    rows = diff["rows"]
    by_group: Dict[str, List[Dict]] = {}
    for row in rows:
        by_group.setdefault(row["group"], []).append(row)

    improved = [r for r in by_group.get(KNOWN_MISSES, [])
                if _fields(r) - set(r.get("old_output") or {})]
    regressed = [r for r in by_group.get(CONTROLS, [])
                 if set(r.get("old_output") or {}) - _fields(r)
                 and not r["new_withheld"]]
    chips = [r for r in by_group.get(AMENITY_CHIPS, [])
             if _fields(r)]
    red_roof = by_group.get(RED_ROOF, [])
    red_roof_gain = sum(len(_fields(r) - set(r.get("old_output") or {}))
                        for r in red_roof)

    return {
        "known_misses_total": len(by_group.get(KNOWN_MISSES, [])),
        "known_misses_improved": len(improved),
        "known_misses_improved_cases": [r["property_name"] for r in improved],
        "controls_total": len(by_group.get(CONTROLS, [])),
        "controls_regressed": len(regressed),
        "controls_regressed_cases": [r["property_name"] for r in regressed],
        "amenity_chips_total": len(by_group.get(AMENITY_CHIPS, [])),
        "amenity_chips_still_producing_policy": len(chips),
        "red_roof_fields_gained": red_roof_gain,
        "tiered_fee_control_still_withheld": all(
            "pet_fee" not in _fields(r)
            for r in by_group.get("PARSER_CONTROL_TIERED_FEE", [])),
    }


def report(before: Mapping, after: Mapping) -> Dict:
    diff = differential(before, after)
    return {
        "schema": "ptf-reader-differential/1.0",
        "work_order": WORK_ORDER,
        "corpus": str(CORPUS.relative_to(REPO)).replace("\\", "/"),
        "note": ("Old and new reader over one fixed corpus. Directions are "
                 "counted apart: a withheld field and a removed false positive "
                 "are not losses, and are not reported as gains either."),
        "totals": diff["totals"],
        "outcomes": outcomes(diff),
        "rows": diff["rows"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE,
                        help="a baseline snapshot written by --write-baseline")
    parser.add_argument("--write-baseline", type=Path,
                        help="record the CURRENT reader as the baseline")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    if args.write_baseline:
        args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.write_baseline.write_text(
            json.dumps(snapshot(), indent=1, ensure_ascii=False),
            encoding="utf-8")
        print("baseline written: %s" % args.write_baseline)
        return 0

    if not args.baseline:
        parser.error("--baseline is required unless writing one")
    before = json.loads(args.baseline.read_text(encoding="utf-8"))
    doc = report(before, snapshot())

    print(json.dumps(doc["totals"], indent=1))
    print(json.dumps(doc["outcomes"], indent=1))
    for row in doc["rows"]:
        if not row["changed"]:
            continue
        print("-" * 78)
        print("%s  [%s]" % (row["property_name"] or row["case_id"], row["group"]))
        for change in row["changes"]:
            print("   %-18s %-14s %r -> %r %s"
                  % (change["field"], change["direction"], change["old"],
                     change["new"], change["new_withholding_reason"] or ""))
    if args.write_report:
        REPORT.write_text(json.dumps(doc, indent=1, ensure_ascii=False),
                          encoding="utf-8")
        print("report written: %s" % REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
