"""PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016 -- Phase 8, read-only.

Every document the generic reader has ever been pointed at in this repository,
re-read by the reader as it stands, and nothing written anywhere.

WHY IT IS A SEPARATE MODULE FROM THE DIFFERENTIAL
-------------------------------------------------
The differential in ``reader_hardening_016`` runs a FIXED corpus: eleven
surfaces chosen because a previous work order measured a defect on them, plus
the parser controls. It answers "did the thing I set out to fix get fixed".

That is not the same question as "what else did I change". A pattern edit
reaches every document the reader will ever see, and the only way to know its
blast radius is to run it over everything already on disk and count. This
module answers that one, and it deliberately answers it with COUNTS AND NAMES
rather than a verdict: a record whose reading changed is a record a human has
to look at, not a record this module may quietly re-derive.

NOTHING IS WRITTEN
------------------
No authority, no observation, no journal. Records whose reading changed are
emitted as a QUEUE -- a list of what would need re-deriving, for a work order
that is authorised to re-derive it. This one is not.

THE DOCUMENTS LIVE IN ``data/``, WHICH IS GITIGNORED
----------------------------------------------------
So ``--data-root`` is a parameter rather than a constant: the same scan can be
run from a worktree checked out at another commit, pointed at the one copy of
the cached documents, which is how the before/after comparison is made without
either reader having to know the other exists.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402

REPO = _REPO_ROOT
WORK_ORDER = "PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016"
DEFAULT_DATA_ROOT = REPO / "data" / "acquisition"
REPORT = (REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
          / "ptf_reader_corpus_dry_run_016.json")


def documents(data_root: Path) -> List[Path]:
    """Every persisted document under the acquisition data root, sorted.

    Sorted so two runs enumerate in the same order and the comparison is by
    identity rather than by position.
    """
    return sorted(data_root.rglob("rendered.html"))


def read_document(path: Path, data_root: Path) -> Dict:
    html = path.read_text(encoding="utf-8", errors="replace")
    hit = UC.locate_policy_in_html(html)
    key = str(path.relative_to(data_root)).replace("\\", "/")
    if not hit.found:
        return {"key": key, "block_found": False, "block_chars": 0,
                "extraction": {}, "withheld": {}, "flags": []}
    reading = PR.parse(hit.text, strategy="corpus_dry_run_016")
    result = PR.to_extraction(reading, location="")
    return {
        "key": key,
        "block_found": True,
        "block_chars": len(hit.text),
        "extraction": dict(result.extraction),
        "withheld": dict(result.withheld or {}),
        "flags": [f.get("code") for f in (result.flags or [])],
    }


def scan(data_root: Path) -> Dict[str, Dict]:
    return {r["key"]: r for r in
            (read_document(p, data_root) for p in documents(data_root))}


# --------------------------------------------------------------------------- #
# Comparison.
# --------------------------------------------------------------------------- #

def _run_of(key: str) -> str:
    """The evidence run a document belongs to: its top directory."""
    return key.split("/", 1)[0]


def compare(before: Dict[str, Dict], after: Dict[str, Dict]) -> Dict:
    keys = sorted(set(before) | set(after))
    rows, by_run = [], {}
    counts = Counter()
    for key in keys:
        old, new = before.get(key, {}), after.get(key, {})
        old_ex, new_ex = old.get("extraction", {}), new.get("extraction", {})
        old_wh, new_wh = old.get("withheld", {}), new.get("withheld", {})
        if old_ex == new_ex and old_wh == new_wh \
                and old.get("block_found") == new.get("block_found"):
            counts["unchanged"] += 1
            continue
        counts["changed"] += 1
        gained = sorted(set(new_ex) - set(old_ex))
        lost = sorted(set(old_ex) - set(new_ex))
        altered = sorted(f for f in set(old_ex) & set(new_ex)
                         if old_ex[f] != new_ex[f])
        newly_withheld = sorted(f for f in lost if f in new_wh)
        removed = sorted(f for f in lost if f not in new_wh)
        counts["newly_structured"] += len(gained)
        counts["newly_withheld"] += len(newly_withheld)
        counts["values_removed"] += len(removed)
        counts["values_altered"] += len(altered)
        if new.get("block_found") and not old.get("block_found"):
            counts["blocks_newly_located"] += 1
        if old.get("block_found") and not new.get("block_found"):
            counts["blocks_no_longer_located"] += 1
        run = _run_of(key)
        by_run[run] = by_run.get(run, 0) + 1
        rows.append({
            "document": key,
            "run": run,
            "block_found_before": bool(old.get("block_found")),
            "block_found_after": bool(new.get("block_found")),
            "fields_gained": gained,
            "fields_newly_withheld": newly_withheld,
            "fields_removed": removed,
            "fields_altered": altered,
            "old_extraction": old_ex,
            "new_extraction": new_ex,
            "new_withheld": new_wh,
            "new_flags": new.get("flags", []),
        })
    return {
        "documents_scanned": len(keys),
        "counts": dict(counts),
        "changed_by_run": dict(sorted(by_run.items())),
        "rows": rows,
    }


def queue(comparison: Dict) -> Dict:
    """What a LATER work order would have to re-derive. Not re-derived here."""
    return {
        "note": ("Documents whose reading changed. These are candidates for "
                 "re-derivation by a work order authorised to write "
                 "observations; this one writes nothing and re-derives "
                 "nothing."),
        "documents": [r["document"] for r in comparison["rows"]],
        "count": len(comparison["rows"]),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--write-scan", type=Path,
                        help="write this tree's scan and stop")
    parser.add_argument("--before", type=Path,
                        help="a scan written by another tree, to compare against")
    parser.add_argument("--write-report", action="store_true")
    # A later work order re-runs this scanner against its own baseline, and
    # its report is not this one. Writing to the fixed path would overwrite a
    # committed measurement with a different run's numbers -- the mistake that
    # cost 008 its predecessor's report.
    parser.add_argument("--report-path", type=Path, default=REPORT)
    args = parser.parse_args(argv)

    data_root = args.data_root.resolve()
    if not data_root.is_dir():
        raise SystemExit("no such data root: %s" % data_root)

    result = scan(data_root)
    if args.write_scan:
        args.write_scan.parent.mkdir(parents=True, exist_ok=True)
        args.write_scan.write_text(json.dumps(result, indent=1,
                                              ensure_ascii=False),
                                   encoding="utf-8")
        print("scan written: %d documents -> %s" % (len(result), args.write_scan))
        return 0

    if not args.before:
        parser.error("--before is required unless writing a scan")
    before = json.loads(args.before.read_text(encoding="utf-8"))
    comparison = compare(before, result)
    doc = {
        "schema": "ptf-reader-corpus-dry-run/1.0",
        "work_order": WORK_ORDER,
        "data_root": str(data_root),
        "authority_written": False,
        "observations_updated": False,
        "documents_scanned": comparison["documents_scanned"],
        "counts": comparison["counts"],
        "changed_by_run": comparison["changed_by_run"],
        "re_derivation_queue": queue(comparison),
        "rows": comparison["rows"],
    }
    print(json.dumps({k: doc[k] for k in
                      ("documents_scanned", "counts", "changed_by_run")},
                     indent=1))
    if args.write_report:
        args.report_path.write_text(json.dumps(doc, indent=1,
                                               ensure_ascii=False),
                                    encoding="utf-8")
        print("report written: %s" % args.report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
