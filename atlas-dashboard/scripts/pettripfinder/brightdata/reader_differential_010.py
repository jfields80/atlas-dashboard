"""PTF-POLICY-READER-TIERED-FEE-HARDENING-010 -- before/after, and a dry corpus run.

Two jobs, both read-only.

``--snapshot`` records what the reader does RIGHT NOW to the focused regression
corpus, so the fix is measured against a recorded baseline rather than against
memory. ``--diff`` replays that baseline against the current reader and prints
one row per case with the reason for any change.

``--corpus`` runs the current reader across every persisted policy block this
branch has acquired -- every capture directory under ``data/acquisition`` -- and
reports how many records would change if authority were re-derived. It writes
NOTHING to authority. That is the point: this work order fixes and measures the
reader, and the migration is somebody's explicit decision afterwards.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.brightdata import policy_reading as PR          # noqa: E402
from scripts.pettripfinder.brightdata import tiered_fee_corpus_010 as CORPUS  # noqa: E402

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
BASELINE = (REPO / "data" / "acquisition" / "reader-differential-010"
            / "baseline.json")
ACQUISITION = REPO / "data" / "acquisition"


def read(text: str) -> Dict:
    """One reading, reduced to the fields this work order is about."""
    reading = PR.parse(text, strategy="differential")
    result = PR.to_extraction(reading, location="")
    extraction = dict(result.extraction)
    withheld = dict(result.withheld)
    return {
        "pet_fee": extraction.get("pet_fee"),
        "fee_basis": extraction.get("fee_basis"),
        "fee_scope": extraction.get("fee_scope"),
        "fee_cap": extraction.get("fee_cap"),
        "weight_limit": extraction.get("weight_limit"),
        "pet_count_limit": extraction.get("pet_count_limit"),
        "withheld_pet_fee": withheld.get("pet_fee"),
        "withheld_fee_basis": withheld.get("fee_basis"),
        "flags": sorted({f.get("code") for f in (result.flags or []) if f.get("code")}),
        "charges": len(reading.charges),
    }


def snapshot() -> Dict:
    out = {c["case"]: read(c["text"]) for c in CORPUS.CASES}
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_bytes((json.dumps(out, indent=1) + "\n").encode("utf-8"))
    return out


def _fee_str(row: Dict) -> str:
    if row["pet_fee"] is not None:
        return "%d%s" % (row["pet_fee"],
                         "/%s" % row["fee_basis"] if row["fee_basis"] else "")
    if row["withheld_pet_fee"]:
        return "WITHHELD:%s" % row["withheld_pet_fee"]
    return "-"


def _weight_str(row: Dict) -> str:
    w = row["weight_limit"]
    return "-" if not w else "%s%s" % (w.get("value"), w.get("unit"))


def differential() -> Dict:
    if not BASELINE.is_file():
        raise SystemExit("no baseline; run --snapshot before changing the reader")
    before = json.loads(BASELINE.read_text(encoding="utf-8"))
    rows = []
    for case in CORPUS.CASES:
        old = before.get(case["case"], {})
        new = read(case["text"])
        changed = any(old.get(k) != new.get(k) for k in
                      ("pet_fee", "fee_basis", "weight_limit", "withheld_pet_fee"))
        rows.append({
            "case": case["case"],
            "source": case["source"],
            "family": case["family"],
            "expect": case["expect"],
            "raw_phrase": case["text"][:150],
            "old_fee": _fee_str(old) if old else "(no baseline)",
            "new_fee": _fee_str(new),
            "old_weight": _weight_str(old) if old else "(no baseline)",
            "new_weight": _weight_str(new),
            "changed": changed,
            "reason": case["why"],
            "meets_expectation": _meets(case, new),
        })
    return {"rows": rows,
            "changed": sum(1 for r in rows if r["changed"]),
            "failing_expectation": [r["case"] for r in rows
                                    if not r["meets_expectation"]]}


def _meets(case: Dict, new: Dict) -> bool:
    if case["expect"] == "WITHHOLD":
        return new["pet_fee"] is None and bool(new["withheld_pet_fee"])
    if case["expect"] == "NO_WEIGHT":
        return new["weight_limit"] is None
    if case["expect"] == "STRUCTURE":
        if "expect_weight" in case:
            return bool(new["weight_limit"]) and \
                new["weight_limit"]["value"] == case["expect_weight"]
        return new["pet_fee"] is not None
    return True


# --------------------------------------------------------------------------- #
# Dry run over everything this branch has actually acquired
# --------------------------------------------------------------------------- #

def persisted_blocks() -> List[Dict]:
    """Every bounded policy block on disk, with where it came from."""
    out = []
    for path in sorted(ACQUISITION.rglob("policy-block.txt")):
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        parts = path.parts
        run = parts[parts.index("acquisition") + 1] if "acquisition" in parts else "?"
        out.append({"run": run, "slug": path.parent.parent.name,
                    "path": str(path.relative_to(REPO)), "text": text})
    return out


_BRAND_HINTS = (
    ("CHOICE", ("comfort", "clarion", "econo", "rodeway", "sleep-inn",
                "suburban", "cambria", "country-inn", "royle")),
    ("WYNDHAM", ("la-quinta", "ramada", "super-8", "travelodge", "days-inn",
                 "baymont", "microtel", "howard-johnson")),
    ("IHG", ("holiday-inn", "staybridge", "kimpton", "candlewood",
             "crowne-plaza", "avid")),
    ("MARRIOTT", ("marriott", "courtyard", "fairfield", "residence-inn",
                  "springhill", "towneplace", "aloft", "four-points", "sheraton")),
    ("HILTON", ("hilton", "hampton", "embassy", "doubletree", "tru-by",
                "home2", "homewood")),
)


def _brand_of(slug: str) -> str:
    low = slug.lower()
    for brand, hints in _BRAND_HINTS:
        if any(h in low for h in hints):
            return brand
    return "OTHER"


def corpus_dry_run() -> Dict:
    if not BASELINE.is_file():
        raise SystemExit("no baseline")
    blocks = persisted_blocks()
    # Dedupe identical text: the same property re-acquired across runs is one
    # record for migration purposes, not four.
    seen: Dict[str, Dict] = {}
    for b in blocks:
        seen.setdefault(b["text"], b)
    unique = list(seen.values())

    changed_fee, changed_weight, newly_withheld, newly_structured = [], [], [], []
    for b in unique:
        new = read(b["text"])
        old = _read_with_frozen_reader(b["text"])
        row = {"slug": b["slug"], "run": b["run"], "brand": _brand_of(b["slug"]),
               "old_fee": _fee_str(old), "new_fee": _fee_str(new),
               "old_weight": _weight_str(old), "new_weight": _weight_str(new),
               "path": b["path"]}
        if old.get("pet_fee") != new.get("pet_fee"):
            changed_fee.append(row)
            if old.get("pet_fee") is not None and new.get("pet_fee") is None:
                newly_withheld.append(row)
            elif old.get("pet_fee") is None and new.get("pet_fee") is not None:
                newly_structured.append(row)
        if old.get("weight_limit") != new.get("weight_limit"):
            changed_weight.append(row)

    changed_slugs = {r["slug"] for r in changed_fee} | {r["slug"] for r in changed_weight}
    return {
        "total_blocks_on_disk": len(blocks),
        "unique_policy_texts_scanned": len(unique),
        "fee_output_changed": len(changed_fee),
        "weight_output_changed": len(changed_weight),
        "newly_withheld": len(newly_withheld),
        "newly_structured": len(newly_structured),
        "unchanged": len(unique) - len(changed_slugs),
        "changes_by_brand": dict(Counter(
            r["brand"] for r in changed_fee + changed_weight)),
        "changes_by_reason": {
            "tiered_fee_now_withheld": len(newly_withheld),
            "weight_now_recognised": len(newly_structured) + len([
                r for r in changed_weight if r["old_weight"] == "-"]),
        },
        "fee_changes": changed_fee,
        "weight_changes": changed_weight,
        "authority_written": False,
        "note": ("read-only. Nothing here touches authority. Records listed "
                 "are MIGRATION CANDIDATES for an explicit re-certification "
                 "decision, not a rewrite this work order performs."),
    }


_FROZEN: Optional[Dict] = None


def _read_with_frozen_reader(text: str) -> Dict:
    """The pre-fix reading, from the committed parser at HEAD.

    Loaded once, from git, so the comparison is against what production
    actually does rather than against a remembered behaviour.
    """
    global _FROZEN
    if _FROZEN is None:
        import subprocess, types
        src = subprocess.run(
            ["git", "show",
             "HEAD:atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py"],
            capture_output=True, text=True, check=True, cwd=str(REPO)).stdout
        name = "policy_reading_frozen_010"
        module = types.ModuleType(name)
        module.__file__ = str(REPO / "scripts" / "pettripfinder" / "brightdata"
                              / "policy_reading.py")
        # Registered BEFORE exec: the frozen module defines dataclasses, and
        # dataclasses resolve their own __module__ through sys.modules while
        # the class body is still executing.
        sys.modules[name] = module
        exec(compile(src, module.__file__, "exec"), module.__dict__)
        _FROZEN = module
    reading = _FROZEN.parse(text, strategy="frozen")
    result = _FROZEN.to_extraction(reading, location="")
    extraction, withheld = dict(result.extraction), dict(result.withheld)
    return {"pet_fee": extraction.get("pet_fee"),
            "fee_basis": extraction.get("fee_basis"),
            "weight_limit": extraction.get("weight_limit"),
            "withheld_pet_fee": withheld.get("pet_fee")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--corpus", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    if args.snapshot:
        out = snapshot()
        print("baseline recorded for %d cases -> %s"
              % (len(out), BASELINE.relative_to(REPO)))
        return 0

    doc: Dict = {"schema": "ptf-reader-differential/1.0",
                 "work_order": "PTF-POLICY-READER-TIERED-FEE-HARDENING-010"}

    if args.diff:
        d = differential()
        doc["focused_regression"] = d
        print("%-36s %-11s %-16s %-16s %-9s %-9s %s"
              % ("case", "expect", "old fee", "new fee", "old wt", "new wt", "ok"))
        print("-" * 118)
        for r in d["rows"]:
            print("%-36s %-11s %-16s %-16s %-9s %-9s %s"
                  % (r["case"][:36], r["expect"], r["old_fee"][:16],
                     r["new_fee"][:16], r["old_weight"], r["new_weight"],
                     "OK" if r["meets_expectation"] else "FAIL"))
        print()
        print("changed: %d | failing expectation: %s"
              % (d["changed"], d["failing_expectation"] or "none"))

    if args.corpus:
        c = corpus_dry_run()
        doc["corpus_dry_run"] = c
        print()
        print("CORPUS DRY RUN (read-only)")
        for k in ("total_blocks_on_disk", "unique_policy_texts_scanned",
                  "fee_output_changed", "weight_output_changed",
                  "newly_withheld", "newly_structured", "unchanged"):
            print("  %-30s %s" % (k, c[k]))
        print("  changes_by_brand              %s" % c["changes_by_brand"])

    if args.write and len(doc) > 2:
        out = REPORTS / "ptf_reader_differential_010.json"
        out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                        .encode("utf-8"))
        print("\nwrote %s" % out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
