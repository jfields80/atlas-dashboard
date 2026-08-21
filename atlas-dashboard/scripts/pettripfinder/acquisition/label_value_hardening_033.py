"""PTF-LABEL-VALUE-POLICY-READER-HARDENING-033 -- reading a table, not a sentence.

032 recovered the right block for both Milwaukee Hyatts and the generic reader
made nothing of either. The pages are not obscure: Hyatt Regency prints

    Pet Fees Price : $40 / NIGHT
    Weight Limits Individual pet weight limit : 150 Pounds
                  Combined pets weight limit  : 150 Pounds
    Maximum number of pets is 2.

and the reader returned an empty extraction. Every pattern in the file expects
a SENTENCE -- a subject, a verb, an amount -- and this surface states a LABEL
and a VALUE with a colon between them. The facts are there; the grammar is not.

FIVE CAUSES, MEASURED
---------------------
* WEIGHT, the copula. "weight limit : 150 Pounds" was refused by a rule that
  accepts "weight limit is 150 pounds", because the boundary after the noun
  guarded the word copulas and not the punctuation that replaces them.

* WEIGHT, the winner. Both Hyatts state the individual limit and then the
  combined one. Pattern PRECEDENCE picks the match, not position, so a loose
  bare-number pattern read "150 Pounds Maximum" out of the COMBINED row and
  029's combined-weight guard correctly threw it away -- along with the
  individual limit sitting two clauses earlier, which nothing then looked for.

* COUNT. "Maximum number of pets is 2" matched none of twelve count patterns:
  every one of them wants the number before or immediately after the maximum
  word, and this puts a five-word label in between.

* CHARGE NAME. 029 taught the reader to read a charge whose own name carries
  the pet word -- "the Pet Friendly rate" -- but only for four charge nouns.
  "Pet Fees Price :" uses a fifth.

* CLEANING. Hyatt Place Airport bands its fee by stay length and the reader
  labelled the FIRST band a cleaning fee, because the cleaning wording that
  belongs to the SECOND band sits within reach of a backward-looking rule.

WHAT IS NOT DONE HERE
---------------------
No routing, no source selection, no locator behaviour, and no Hyatt-specific
logic: every change is a general statement about labelled layouts, and the
corpus holds nine negative controls that pin what must NOT be read that way --
a room-price card, a member rate, parking, a resort fee, a smoking fee, a
generic cleaning deposit, an amenity grid, a service-animal-only page, and an
occupancy count that is not a pet count.

Provider calls: zero. Both properties are re-derived from the document their
own 028 capture persisted, whose sha256 is carried forward and checked.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import label_value_corpus_033 as CORPUS  # noqa: E402
from scripts.pettripfinder.acquisition import locator_recovery_032 as R32       # noqa: E402
from scripts.pettripfinder.acquisition import premium_resolution_028 as P28     # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S        # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL               # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR               # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS               # noqa: E402

WORK_ORDER = "PTF-LABEL-VALUE-POLICY-READER-HARDENING-033"
MARKET = "milwaukee-wi"
RUN_ID = "milwaukee-label-value-033"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
RUN_REPORT = REPORTS / "ptf_label_value_reader_hardening_033.json"
DATA = REPO / "data" / "acquisition"
RUN_DIR = DATA / RUN_ID / RUN_ID
JOURNAL = RUN_DIR / "journal.jsonl"

#: The reader as it stood when this work order opened. Pinned to the commit,
#: never read from HEAD: the moment this is committed HEAD becomes the NEW
#: reader and every before/after number would compare the change with itself.
#: 028 found that mistake in 027 and 029 fixed it the same way.
BASELINE_COMMIT = "b21a04a034eec2be802a2892008c93489f54d188"
_READER_PATH = "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py"

#: A reading is an OBSERVATION only when it states a pet fact. Borrowed from
#: 032 unchanged so the two work orders answer the question the same way.
SUBSTANTIVE_FIELDS = R32.SUBSTANTIVE_FIELDS
PUBLICATION_GRADE = R32.PUBLICATION_GRADE

_BASELINE_CACHE: Dict[str, object] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# --------------------------------------------------------------------------- #
# The reader as it was.
# --------------------------------------------------------------------------- #

def baseline_reader():
    """``policy_reading`` exactly as committed at ``BASELINE_COMMIT``."""
    if "module" in _BASELINE_CACHE:
        return _BASELINE_CACHE["module"]
    import importlib.util
    import tempfile
    source = subprocess.run(
        ["git", "show", "%s:%s" % (BASELINE_COMMIT, _READER_PATH)],
        cwd=str(REPO.parent), capture_output=True, text=True, encoding="utf-8",
        check=True).stdout
    if not source.strip():
        raise RuntimeError("the baseline reader came back empty; git show "
                           "echoes an unresolvable argument rather than "
                           "failing, so this is checked")
    holder = Path(tempfile.mkdtemp(prefix="ptf033-")) / "policy_reading_baseline.py"
    holder.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "policy_reading_baseline_033", holder)
    module = importlib.util.module_from_spec(spec)
    # Registered BEFORE execution: a dataclass resolves its owning module
    # through ``sys.modules`` while the class body runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _BASELINE_CACHE["module"] = module
    return module


def read_with(module, block: str, *, strategy: str = "") -> Dict:
    reading = module.parse(block, strategy=strategy)
    result = module.to_extraction(reading, location=MARKET)
    return {
        "extraction": dict(result.extraction),
        "withheld": dict(result.withheld or {}),
        "non_inferences": list(result.non_inferences),
        "flags": [dict(flag) for flag in (result.flags or ())],
        "found": bool(reading.found),
    }


# --------------------------------------------------------------------------- #
# Phase 1 -- the targets and the state they start from.
# --------------------------------------------------------------------------- #

def targets() -> List[str]:
    return CORPUS.targets()


def store_rows() -> Dict[str, Dict]:
    doc = json.loads(STORE.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["items"]}


def _recovery_rows() -> Dict[str, Dict]:
    return {row["identity_key"]: row for row in R32.recoveries()}


def preflight() -> Dict:
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    found = targets()
    rows = _recovery_rows()
    old_reader = baseline_reader()
    evidence = {}
    for key in found:
        row = rows[key]
        directory = REPO / row["source_attempt_dir"]
        # Read with the PINNED reader, not with 032's live row: ``recoveries()``
        # runs whatever reader is on disk, so the "before" it reports becomes
        # the "after" as soon as this work order changes one line.
        before = read_with(old_reader, row["new_block"],
                           strategy="richer_block_recovery")
        evidence[key] = {
            "source_run": row["source_run"],
            "source_attempt_dir": row["source_attempt_dir"],
            "document_sha256": row["document_sha256"],
            "document_present": (directory / "rendered.html").is_file(),
            "recovered_block_chars": row["new_block_chars"],
            "baseline_extraction": before["extraction"],
            "baseline_withheld": before["withheld"],
        }
    return {
        "checked_at": _now(),
        "targets": found,
        "target_evidence": evidence,
        "store_rows": len(store["items"]),
        "published": sum(1 for row in store["items"] if row.get("published")),
        "authority_written": bool(store.get("authority_written")),
        "assertions": {
            "two_targets": len(found) == 2,
            "store_before_this_run_was_115": len(store["items"]) == 115,
            "every_target_has_its_document":
                all(item["document_present"] for item in evidence.values()),
            "no_target_reads_a_pet_fact_yet":
                all(not (set(item["baseline_extraction"]) & SUBSTANTIVE_FIELDS)
                    and "pets_allowed" not in item["baseline_extraction"]
                    for item in evidence.values()),
            "nothing_published": all(not row.get("published")
                                     for row in store["items"]),
            "authority_absent": not bool(store.get("authority_written")),
        },
    }


# --------------------------------------------------------------------------- #
# Phase 10 -- the corpus, old reader against new.
# --------------------------------------------------------------------------- #

def corpus_differential() -> Dict:
    old = baseline_reader()
    rows: List[Dict] = []
    for case in CORPUS.available():
        block = case.block()
        before = read_with(old, block)
        after = read_with(PR, block)
        met = (all(field in after["extraction"] for field in case.must_extract)
               and all(field not in after["extraction"]
                       for field in case.must_not_extract)
               and all(field in after["withheld"]
                       for field in case.must_withhold))
        met_before = (
            all(field in before["extraction"] for field in case.must_extract)
            and all(field not in before["extraction"]
                    for field in case.must_not_extract)
            and all(field in before["withheld"]
                    for field in case.must_withhold))
        rows.append({
            "case_id": case.case_id,
            "kind": case.kind,
            "scenario": case.scenario,
            "block": block,
            "old_extraction": before["extraction"],
            "old_withheld": before["withheld"],
            "new_extraction": after["extraction"],
            "new_withheld": after["withheld"],
            "differs": (before["extraction"] != after["extraction"]
                        or before["withheld"] != after["withheld"]),
            "expectation_met": met,
            "expectation_met_before": met_before,
        })
    return {
        "cases": len(rows),
        "cases_changed": sum(1 for row in rows if row["differs"]),
        "expectations_met": sum(1 for row in rows if row["expectation_met"]),
        "expectations_failed": [row["case_id"] for row in rows
                                if not row["expectation_met"]],
        "expectations_met_before": sum(1 for row in rows
                                       if row["expectation_met_before"]),
        "negative_controls": [row["case_id"] for row in rows
                              if row["kind"] == CORPUS.NEGATIVE],
        "negative_controls_that_changed_answer": [
            row["case_id"] for row in rows
            if row["kind"] == CORPUS.NEGATIVE and not row["expectation_met"]],
        "regression_controls_that_changed": [
            row["case_id"] for row in rows
            if row["kind"] == CORPUS.REGRESSION and row["differs"]],
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Phase 11 -- every persisted Milwaukee block, read both ways. Nothing written.
# --------------------------------------------------------------------------- #

def persisted_blocks() -> List[Dict]:
    out: List[Dict] = []
    for run_id, _journal, capture_root in S.SOURCES:
        root = DATA / capture_root
        if not root.is_dir():
            continue
        for block_path in sorted(root.rglob("policy-block.txt")):
            out.append({"run_id": run_id, "path": _rel(block_path),
                        "slug": block_path.parent.parent.name})
    return out


def production_readers() -> Dict[str, str]:
    """Which reader the store actually used, keyed by attempt directory.

    A block on disk is not necessarily read by the GENERIC reader: Marriott's
    surface has its own, and this dry run reads everything generically. Without
    this the report claims a change to a row that the store reads with a
    different reader entirely -- true about the block, false about the record.
    """
    out: Dict[str, str] = {}
    doc = json.loads(STORE.read_text(encoding="utf-8-sig"))
    for row in doc["items"]:
        pointer = (row.get("provenance") or {}).get("raw_pointer", "")
        pointer = str(pointer).replace("\\", "/").rstrip("/")
        if not pointer:
            continue
        marker = "data/acquisition/"
        if marker in pointer:
            pointer = pointer[pointer.index(marker):]
        out[pointer] = (row.get("provenance") or {}).get("reader", "")
    return out


def corpus_wide_dry_run() -> Dict:
    old = baseline_reader()
    readers = production_readers()
    scanned = 0
    changed: List[Dict] = []
    added_fields = Counter()
    removed_fields = Counter()
    withheld_added = Counter()
    by_run = Counter()
    for item in persisted_blocks():
        block = (REPO / item["path"]).read_text(encoding="utf-8",
                                                errors="replace")
        scanned += 1
        before = read_with(old, block)
        after = read_with(PR, block)
        if (before["extraction"] == after["extraction"]
                and before["withheld"] == after["withheld"]):
            continue
        added = sorted(set(after["extraction"]) - set(before["extraction"]))
        removed = sorted(set(before["extraction"]) - set(after["extraction"]))
        gained = sorted(set(after["withheld"]) - set(before["withheld"]))
        for field in added:
            added_fields[field] += 1
        for field in removed:
            removed_fields[field] += 1
        for field in gained:
            withheld_added[field] += 1
        by_run[item["run_id"]] += 1
        attempt = item["path"].rsplit("/", 1)[0]
        changed.append({
            "production_reader": readers.get(attempt, ""),
            "run_id": item["run_id"],
            "slug": item["slug"],
            "path": item["path"],
            "old_extraction": before["extraction"],
            "new_extraction": after["extraction"],
            "old_withheld": before["withheld"],
            "new_withheld": after["withheld"],
            "added_fields": added,
            "removed_fields": removed,
            "withheld_added": gained,
            "withheld_removed": sorted(set(before["withheld"])
                                       - set(after["withheld"])),
        })
    return {
        "blocks_scanned": scanned,
        "blocks_changed": len(changed),
        "blocks_unchanged": scanned - len(changed),
        "newly_structured_fields": dict(added_fields),
        "fields_removed": dict(removed_fields),
        "newly_withheld_fields": dict(withheld_added),
        "changes_by_run": dict(by_run),
        "blocks_changed_that_the_store_reads_generically":
            sum(1 for row in changed if row["production_reader"] == "generic"),
        "blocks_changed_read_by_another_reader":
            sorted({row["production_reader"] for row in changed
                    if row["production_reader"] != "generic"}),
        "affected": changed,
    }


# --------------------------------------------------------------------------- #
# Phase 12 -- the two targets, re-derived offline.
# --------------------------------------------------------------------------- #

def rederivation() -> List[Dict]:
    """Both Hyatts read from the block 032 recovered. Zero provider calls."""
    old = baseline_reader()
    rows = store_rows()
    recovery = _recovery_rows()
    out: List[Dict] = []
    for key in targets():
        source = recovery[key]
        block = CORPUS.recovered_block(key)
        before = read_with(old, block, strategy="richer_block_recovery")
        after = read_with(PR, block, strategy="richer_block_recovery")
        fields = ((set(after["extraction"]) & SUBSTANTIVE_FIELDS)
                  | ({"pets_allowed"} if "pets_allowed" in after["extraction"]
                     else set()))
        out.append({
            "identity_key": key,
            "canonical_name": source["canonical_name"],
            "brand": source["brand"],
            "source_url": source["source_url"],
            "source_run": source["source_run"],
            "source_attempt_dir": source["source_attempt_dir"],
            "document_sha256": source["document_sha256"],
            "policy_locator": "richer_block_recovery",
            "policy_block": block,
            "policy_block_chars": len(block),
            "provider_calls": 0,
            "reading_before": before["extraction"],
            "withheld_before": before["withheld"],
            "reading_after": after["extraction"],
            "withheld_after": after["withheld"],
            "non_inferences": after["non_inferences"],
            "substantive_pet_fields": sorted(fields),
            "yields_an_observation": bool(fields),
            "review_status_before": rows.get(key, {}).get("review_status", ""),
            "in_store_before": key in rows,
        })
    return out


# --------------------------------------------------------------------------- #
# Phase 13 -- persisting the derived evidence the store reads.
# --------------------------------------------------------------------------- #

def write_evidence(row: Mapping) -> Dict:
    """A new attempt directory carrying 032's document and its block.

    The same shape 032 wrote for Wildwood Lodge, for the same reason: the store
    finds an observation by finding a ``policy-block.txt``, and the block has to
    sit beside the document it came out of so a reader can check one against the
    other. The document is copied verbatim, so its sha256 still matches the 028
    capture that served it.
    """
    source = _recovery_rows()[row["identity_key"]]
    directory = RUN_DIR / R32._slug(source) / "attempt-01"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "rendered.html").write_text(source["_html"], encoding="utf-8")
    (directory / "page-text.txt").write_text(source["_page_text"],
                                             encoding="utf-8")
    (directory / PL.BLOCK_ARTIFACT).write_text(row["policy_block"],
                                               encoding="utf-8")

    class _Hit:
        found = True
        strategy = "richer_block_recovery"
        selector = ""
        matched_phrase = ""
        policy_features = PS.policy_features(row["policy_block"])
        container_chars = len(row["policy_block"])
        candidates_considered = source["recovery"]["candidates_considered"]
        brand_generic = False
        rendered = False

    record = PL.build_record(
        hit=_Hit(), block_text=row["policy_block"],
        document_sha256=row["document_sha256"],
        walk=PL.STATIC_TEXT_WALK,
        recovery=dict(source["recovery"],
                      work_order=WORK_ORDER,
                      recovered_from_run=row["source_run"],
                      recovered_from_attempt_dir=row["source_attempt_dir"],
                      provider_calls=0))
    PL.persist(directory, record)
    return {"attempt_dir": _rel(directory),
            "block_sha256": record["block_sha256"],
            "document_sha256": record["document_sha256"]}


def journal_entry(row: Mapping, evidence: Mapping) -> Dict:
    return {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "source_url": row["source_url"],
        "official_url": row["source_url"],
        "provider": "",
        "provider_used": "",
        "providers_tried": [],
        "reader": "generic",
        "final_state": PUBLICATION_GRADE,
        "acquisition_status": "ACQUIRED",
        "publication_grade": True,
        "policy_locator": row["policy_locator"],
        "policy_block": row["policy_block"],
        "policy_block_chars": row["policy_block_chars"],
        "reader_fields": sorted(row["reading_after"]),
        "reader_withheld": sorted(row["withheld_after"]),
        "attempt_records": [],
        "recovered_from": {
            "work_order": WORK_ORDER,
            "run": row["source_run"],
            "attempt_dir": row["source_attempt_dir"],
            "document_sha256": row["document_sha256"],
            "provider_calls": 0,
            "why": ("032 recovered this block and declined to journal it "
                    "because the reader made nothing of it; the block is "
                    "byte-identical and the reader now reads the layout"),
        },
        "attempt_dir": evidence["attempt_dir"],
        "completed_at": _now(),
    }


def run(*, write: bool = True) -> List[Dict]:
    rows = rederivation()
    out: List[Dict] = []
    if write:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        if JOURNAL.is_file():
            JOURNAL.unlink()
    for row in rows:
        entry = None
        if row["yields_an_observation"] and write:
            evidence = write_evidence(row)
            entry = journal_entry(row, evidence)
            with JOURNAL.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        out.append(dict(row, journalled=entry is not None))
    return out


def journal_rows() -> List[Dict]:
    if not JOURNAL.is_file():
        return []
    return [json.loads(line) for line in
            JOURNAL.read_text(encoding="utf-8").splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
# Phases 14 and 16 -- the counters, and what this cost.
# --------------------------------------------------------------------------- #

def counters() -> Dict:
    census = P28.full_census()
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    return {
        "census_total": census["census_total"],
        "active_eligible": census["active_eligible_total"],
        "observed": census["phase11_final_states"]["OBSERVED"],
        "active_unresolved": census["phase11_final_states"]["TOUCHED_UNRESOLVED"],
        "published": sum(1 for row in store["items"] if row.get("published")),
        "store_rows": len(store["items"]),
        "sum_of_final_states": census["phase11_sum"],
    }


def cost() -> Dict:
    return {
        "provider_calls": 0,
        "pages_fetched": 0,
        "incremental_spend_usd": 0.0,
        "why": ("every block read here was persisted by an earlier run and "
                "every document hash is carried forward from it"),
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def build_report() -> Dict:
    rows = rederivation()
    journalled = {entry["identity_key"] for entry in journal_rows()}
    for row in rows:
        row["journalled"] = row["identity_key"] in journalled
    return {
        "schema": "ptf-label-value-reader-hardening/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "run_id": RUN_ID,
        "generated_at": _now(),
        "baseline_commit": BASELINE_COMMIT,
        "preflight": preflight(),
        "targets": targets(),
        "corpus_differential": corpus_differential(),
        "corpus_wide_dry_run": corpus_wide_dry_run(),
        "rederivation": rows,
        "journalled": len(journalled),
        "counters": counters(),
        "cost": cost(),
        "provider_calls": 0,
        "authority_written": False,
        "published": 0,
    }


def write_report() -> Dict:
    doc = build_report()
    RUN_REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--corpus", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rederive", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.corpus:
        report = corpus_differential()
        for row in report["rows"]:
            print("%-34s %-8s %s -> %s"
                  % (row["case_id"],
                     "CHANGED" if row["differs"] else "same",
                     json.dumps(row["old_extraction"], default=str)[:48],
                     json.dumps(row["new_extraction"], default=str)[:64]))
        print("met %d/%d (was %d); failed %s"
              % (report["expectations_met"], report["cases"],
                 report["expectations_met_before"],
                 report["expectations_failed"]))
    if args.dry_run:
        report = corpus_wide_dry_run()
        print(json.dumps({k: v for k, v in report.items() if k != "affected"},
                         indent=2))
    if args.rederive:
        for row in rederivation():
            print("== %s" % row["identity_key"])
            print("   before %s" % json.dumps(row["reading_before"],
                                              default=str))
            print("   after  %s" % json.dumps(row["reading_after"],
                                              default=str))
            print("   withheld %s" % json.dumps(row["withheld_after"]))
            print("   observation: %s" % row["yields_an_observation"])
    if args.apply:
        for row in run(write=True):
            print("%-34s journalled=%s" % (row["identity_key"],
                                           row["journalled"]))
    if args.report:
        doc = write_report()
        print(json.dumps(doc["counters"], indent=2))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
