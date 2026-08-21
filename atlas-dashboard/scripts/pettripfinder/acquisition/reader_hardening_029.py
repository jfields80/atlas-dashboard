"""PTF-GENERIC-READER-BEST-WESTERN-HARDENING-029 -- reading what was captured.

028 reached two Best Western property pages that state a pet policy in plain
English -- up to two dogs, an eighty pound size limit, and a daily rate -- and
the generic reader represented the allowed flag and nothing else. The pages
were not the problem: the identity bound on the property code, the canonical
locator recorded the boundary, and the block on disk carries every one of those
facts.

THREE SEPARATE CAUSES, NOT ONE
------------------------------
Measured against the patterns rather than guessed at:

* COUNT. "allow up to two dogs" hit none of eleven count patterns. Every "up
  to" form needs the number in FIGURES and the literal word "pet"; every
  spelled-out form needs either the word "max" after the number or a "per room"
  scope. This wording has none of the four.

* WEIGHT. "The size limit for any one dog shall be 80 pounds" hit none of seven.
  The patterns want the noun "weight", or a maximum word immediately before the
  figure, or "or less" immediately after it. "size limit ... shall be" is a
  different noun with a copula and several words in between.

* FEE. The pattern matched perfectly and the GUARD threw it away.
  ``_SCOPED_CHARGE_USD_RE`` reads "35.00 USD per day"; ``_pet_context`` then
  asks what stands between the nearest pet word and the figure, finds "rate",
  and rejects the amount as a room rate. That guard exists because a Choice
  guest-room card carries "No Pets Allowed" and "$160 USD /night" in one
  container. Best Western calls its pet charge "the Pet Friendly rate", so the
  guard fired on a real pet fee.

The guard is not relaxed. A charge is now read when the pet word appears INSIDE
the charge's own name, bound to the charge noun with at most one adjective
between and no clause-closing word -- which is the same argument the
basis-first pattern already makes for requiring the pet word in its label. In
"No Pets Allowed Discounted rate" the word after "Pets" is "Allowed", the pet
statement ends there, and the pattern does not match.

A FOURTH THING, FOUND BY THE CORPUS
-----------------------------------
Building the controls turned up a defect no capture had reported: "combined
weight not to exceed 100 pounds" was being read as an individual weight limit.
Publishing it would invite a guest to arrive with a hundred-pound dog the
property never agreed to. A combined figure is now recorded as a note and never
as a limit.

WHAT THIS WORK ORDER DID NOT DO
--------------------------------
It did not re-acquire anything -- every block is read from the artifact 028
persisted, and provider usage is zero. It did not touch routing, providers,
source selection, or the species parsing that "We welcome dogs and cats" also
escapes. And it did not decide that a daily rate is a nightly one: ``per_day``
is already a published member of ``FEE_BASES`` and is deliberately distinct
from ``per_night``, so the surface's own word is recorded.
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

from scripts.pettripfinder.acquisition import premium_resolution_028 as P28    # noqa: E402
from scripts.pettripfinder.acquisition import reader_corpus_029 as CORPUS      # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S       # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR              # noqa: E402
from scripts.pettripfinder.contracts import enums                              # noqa: E402

WORK_ORDER = "PTF-GENERIC-READER-BEST-WESTERN-HARDENING-029"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
RUN_REPORT = REPORTS / "ptf_generic_reader_hardening_029.json"
DATA = REPO / "data" / "acquisition"

#: The commit whose reader is "the old reader". Pinned rather than read from
#: HEAD, because HEAD becomes the NEW reader the moment this work order is
#: committed and the comparison would then measure the change against itself --
#: the mistake 028 found in 027's blast radius.
BASELINE_COMMIT = "ccd041f324fb3e01e13901ae01529c3012ecc3d1"
_READER_PATH = "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py"

_BASELINE_CACHE: Dict[str, object] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# --------------------------------------------------------------------------- #
# The reader as it was.
# --------------------------------------------------------------------------- #

def baseline_reader():
    """``policy_reading`` exactly as committed at the baseline, importable.

    Materialised as its own module rather than re-implemented: a hand-copied
    "old reader" is a second implementation that can disagree with the one that
    actually ran, and then the before/after numbers measure the copy.
    """
    if "module" in _BASELINE_CACHE:
        return _BASELINE_CACHE["module"]
    import importlib.util
    import tempfile
    source = subprocess.run(
        ["git", "show", "%s:%s" % (BASELINE_COMMIT, _READER_PATH)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        check=True).stdout
    holder = Path(tempfile.mkdtemp(prefix="ptf029-")) / "policy_reading_baseline.py"
    holder.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "policy_reading_baseline_029", holder)
    module = importlib.util.module_from_spec(spec)
    # Registered BEFORE execution: ``dataclasses`` resolves a field's owning
    # module through ``sys.modules`` while the class body runs, and a module
    # that is not there yet makes every dataclass in the file fail to build.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _BASELINE_CACHE["module"] = module
    return module


def read_with(module, block: str, *, strategy: str = "") -> Dict:
    reading = module.parse(block, strategy=strategy)
    result = module.to_extraction(reading, location=MARKET)
    return {
        "extraction": dict(result.extraction),
        "withheld": dict(result.withheld),
        "non_inferences": list(result.non_inferences),
        "flags": [dict(f) for f in (result.flags or ())],
        "found": bool(reading.found),
    }


# --------------------------------------------------------------------------- #
# Phase 1 / 2 -- the targets and their reproduction.
# --------------------------------------------------------------------------- #

def targets() -> List[str]:
    return CORPUS.targets()


def store_rows() -> Dict[str, Dict]:
    doc = json.loads(STORE.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["items"]}


def preflight() -> Dict:
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    found = targets()
    blocks = {}
    for key in found:
        row = next(r for r in P28.journal_rows() if r["identity_key"] == key)
        attempt = REPO / row["canonical_artifacts"]["attempt_dir"]
        blocks[key] = {
            "attempt_dir": _rel(attempt),
            "policy_block_present": (attempt / "policy-block.txt").is_file(),
            "locator_json_present": (attempt / "locator.json").is_file(),
            "replay_status": row["canonical_artifacts"]["replay_status"],
            "block_sha256": row["canonical_artifacts"]["block_sha256"],
        }
    return {
        "checked_at": _now(),
        "targets": found,
        "target_artifacts": blocks,
        "store_rows": len(store["items"]),
        "published": sum(1 for row in store["items"] if row.get("published")),
        "authority_written": bool(store.get("authority_written")),
        "authority_files": len(list(
            (REPO / "launch_packages" / "pettripfinder")
            .rglob("*hotel_policy_facts*milwaukee*"))),
        "assertions": {
            "two_targets": len(found) == 2,
            "store_before_this_run_was_114": len(store["items"]) == 114
            or _store_rows_before() == 114,
            "every_target_has_a_persisted_block":
                all(b["policy_block_present"] for b in blocks.values()),
            "every_target_replays_canonically":
                all(b["replay_status"] == "REPLAYED_FROM_CANONICAL_ARTIFACT"
                    for b in blocks.values()),
            "nothing_published": all(not row.get("published")
                                     for row in store["items"]),
            "authority_absent": not bool(store.get("authority_written")),
        },
    }


def _store_rows_before() -> Optional[int]:
    path = REPORTS / "ptf_milwaukee_store_integration_025.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig")).get("rows_before")


def reproduce() -> List[Dict]:
    """The under-reading, re-derived from the persisted block before any edit.

    Reads with the BASELINE reader, so this reproduces what 028 recorded rather
    than describing it.
    """
    rows = store_rows()
    old = baseline_reader()
    out = []
    for key in targets():
        journal = next(r for r in P28.journal_rows()
                       if r["identity_key"] == key)
        block = CORPUS.persisted_block(key)
        before = read_with(old, block, strategy=journal["policy_locator"])
        row = rows.get(key, {})
        out.append({
            "identity_key": key,
            "canonical_name": journal["canonical_name"],
            "policy_block": block,
            "policy_block_chars": len(block),
            "block_sha256": journal["canonical_artifacts"]["block_sha256"],
            "baseline_extraction": before["extraction"],
            "baseline_withheld": before["withheld"],
            "stored_facts": dict(row.get("proposed_facts") or {}),
            "stored_withheld": dict(row.get("withheld_fields") or {}),
            "stored_review_status": row.get("review_status", ""),
            "reproduces_the_store": (before["extraction"]
                                     == dict(row.get("proposed_facts") or {})),
        })
    return out


# --------------------------------------------------------------------------- #
# Phase 3 -- the cause, measured against the patterns.
# --------------------------------------------------------------------------- #

CAUSE_COUNT = "COUNT_WORDING_UNSUPPORTED"
CAUSE_WEIGHT = "WEIGHT_PHRASE_UNSUPPORTED"
CAUSE_FEE_GUARD = "PET_FEE_VETOED_BY_RATE_MARKER_GUARD"


def root_cause(block: str) -> Dict:
    """Which layer lost each concept, established by running the patterns."""
    old = baseline_reader()
    count_hits = [i for i, p in enumerate(old._COUNT_RES) if p.search(block)]
    weight_hits = [i for i, p in enumerate(old._WEIGHT_RES) if p.search(block)]
    charge_hits = {}
    for name in ("_SCOPED_CHARGE_RE", "_LOOSE_CHARGE_RE",
                 "_SCOPED_CHARGE_USD_RE", "_BASIS_FIRST_CHARGE_RE",
                 "_BARE_CHARGE_RE"):
        match = getattr(old, name).search(block)
        charge_hits[name] = match.group(0) if match else ""
    matched = old._SCOPED_CHARGE_USD_RE.search(block)
    guard = None
    if matched:
        guard = old._pet_context(block, matched.start(), matched.end())
    causes = []
    if not count_hits:
        causes.append(CAUSE_COUNT)
    if not weight_hits:
        causes.append(CAUSE_WEIGHT)
    if matched and guard is False:
        causes.append(CAUSE_FEE_GUARD)
    return {
        "count_patterns_matched": count_hits,
        "weight_patterns_matched": weight_hits,
        "charge_patterns_matched": charge_hits,
        "charge_survived_the_pet_context_guard": guard,
        "causes": causes,
        "explanation": {
            CAUSE_COUNT: ("every 'up to' count form requires the number in "
                          "figures AND the literal word 'pet'; every "
                          "spelled-out form requires 'max' after the number or "
                          "a per-room scope"),
            CAUSE_WEIGHT: ("every weight form requires the noun 'weight', a "
                           "maximum word immediately before the figure, or a "
                           "trailing 'or less'"),
            CAUSE_FEE_GUARD: ("the amount matched and the guard rejected it: "
                              "the word 'rate' stands between the nearest pet "
                              "word and the figure, and that marker exists to "
                              "stop a nightly ROOM rate being published as a "
                              "pet fee"),
        },
    }


# --------------------------------------------------------------------------- #
# Phase 8 -- per day.
# --------------------------------------------------------------------------- #

EXISTING_EQUIVALENCE = "EXISTING_EQUIVALENCE"
SAFE_AMOUNT_BASIS_WITHHELD = "SAFE_AMOUNT_BASIS_WITHHELD"
SCHEMA_CANNOT_REPRESENT = "SCHEMA_CANNOT_REPRESENT"


def per_day_decision() -> Dict:
    """What the published contract already says about a daily pet fee.

    Read from the contract rather than decided here. ``per_day`` is a member of
    ``FEE_BASES``; the reader's own basis map already routes "day" and "daily"
    to it; the store builder accepts it; and other markets have published it.
    Nothing new is invented, and nothing is normalised: the contract keeps
    ``per_day`` distinct from ``per_night`` on purpose, so the surface's own
    word is the one recorded.
    """
    from scripts.pettripfinder.milwaukee_policy_proposals_001 import (
        VALID_FEE_BASES)
    return {
        "decision": EXISTING_EQUIVALENCE,
        "basis_recorded": enums.BASIS_PER_DAY,
        "per_day_in_published_fee_bases": enums.BASIS_PER_DAY in enums.FEE_BASES,
        "per_day_accepted_by_the_store_builder": (enums.BASIS_PER_DAY
                                                  in VALID_FEE_BASES),
        "reader_already_maps_day_and_daily": (
            PR._BASIS_BY_WORD.get("day") == enums.BASIS_PER_DAY
            and PR._BASIS_BY_WORD.get("daily") == enums.BASIS_PER_DAY),
        "per_day_is_not_per_night": (enums.BASIS_PER_DAY
                                     != enums.BASIS_PER_NIGHT),
        "new_vocabulary_created": False,
        "note": ("the contract keeps per_day and per_night distinct and this "
                 "layer does not normalise one into the other; a surface that "
                 "says 'per day' is recorded as per_day"),
    }


# --------------------------------------------------------------------------- #
# Phase 9 -- the fixed corpus differential.
# --------------------------------------------------------------------------- #

def corpus_differential() -> Dict:
    old = baseline_reader()
    rows: List[Dict] = []
    for case in CORPUS.available():
        block = case.block()
        before = read_with(old, block)
        after = read_with(PR, block)
        added = sorted(set(after["extraction"]) - set(before["extraction"]))
        removed = sorted(set(before["extraction"]) - set(after["extraction"]))
        changed = sorted(field for field in
                         set(after["extraction"]) & set(before["extraction"])
                         if after["extraction"][field]
                         != before["extraction"][field])
        satisfied = (all(f in after["extraction"] for f in case.must_extract)
                     and all(f not in after["extraction"]
                             for f in case.must_not_extract)
                     and all(f in after["withheld"]
                             for f in case.must_withhold))
        rows.append({
            "case_id": case.case_id,
            "kind": case.kind,
            "scenario": case.scenario,
            "policy_text": block,
            "old_extraction": before["extraction"],
            "new_extraction": after["extraction"],
            "added_fields": added,
            "removed_fields": removed,
            "changed_fields": changed,
            "old_withheld": before["withheld"],
            "new_withheld": after["withheld"],
            "differs": bool(added or removed or changed
                            or before["withheld"] != after["withheld"]),
            "expectation_met": satisfied,
            "why": case.why,
        })
    return {
        "cases": len(rows),
        "changed": sum(1 for row in rows if row["differs"]),
        "unchanged": sum(1 for row in rows if not row["differs"]),
        "expectations_met": sum(1 for row in rows if row["expectation_met"]),
        "expectations_failed": [row["case_id"] for row in rows
                                if not row["expectation_met"]],
        "changed_cases": [row["case_id"] for row in rows if row["differs"]],
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Phase 10 -- every persisted Milwaukee policy block.
# --------------------------------------------------------------------------- #

def persisted_blocks() -> List[Dict]:
    """Every policy block a Milwaukee production run persisted, with its run."""
    out: List[Dict] = []
    for run_id, _journal, capture_root in S.SOURCES:
        root = DATA / capture_root
        if not root.is_dir():
            continue
        for block_path in sorted(root.rglob("policy-block.txt")):
            out.append({"run_id": run_id, "path": _rel(block_path),
                        "slug": block_path.parent.parent.name})
    return out


_SLUG_TO_IDENTITY: Dict[str, str] = {}


def brand_for_slug(slug: str) -> Tuple[str, str]:
    """(identity_key, brand) for a capture directory's slug.

    The capture named its own directory from the canonical name, so the queue
    is joined on that rather than on the slug directly -- ``brand_for`` is
    keyed on the identity, and passing it a slug returns the fallback for
    everything, which is how the first dry run attributed every change to
    "UNKNOWN".
    """
    global _SLUG_TO_IDENTITY
    if not _SLUG_TO_IDENTITY:
        doc = json.loads(
            (REPORTS / ("%s_policy_acquisition_queue_001.json" % MARKET))
            .read_text(encoding="utf-8-sig"))
        for row in doc["items"]:
            _SLUG_TO_IDENTITY[S._slug(row["canonical_name"])[:80]] =                 row["identity_key"]
    identity = _SLUG_TO_IDENTITY.get(slug, "")
    return identity, (S.brand_for(identity, "") if identity else "") or "UNKNOWN"


def corpus_wide_dry_run() -> Dict:
    """The changed reader over every persisted block. Nothing is written."""
    old = baseline_reader()
    scanned = 0
    changed: List[Dict] = []
    by_brand = Counter()
    added_fields = Counter()
    removed_fields = Counter()
    withheld_added = Counter()
    for item in persisted_blocks():
        block = (REPO / item["path"]).read_text(encoding="utf-8",
                                                errors="replace")
        scanned += 1
        before = read_with(old, block)
        after = read_with(PR, block)
        if before["extraction"] == after["extraction"] \
                and before["withheld"] == after["withheld"]:
            continue
        added = sorted(set(after["extraction"]) - set(before["extraction"]))
        removed = sorted(set(before["extraction"]) - set(after["extraction"]))
        gained_withheld = sorted(set(after["withheld"])
                                 - set(before["withheld"]))
        for field in added:
            added_fields[field] += 1
        for field in removed:
            removed_fields[field] += 1
        for field in gained_withheld:
            withheld_added[field] += 1
        identity, brand = brand_for_slug(item["slug"])
        by_brand[brand] += 1
        changed.append({
            "run_id": item["run_id"],
            "slug": item["slug"],
            "identity_key": identity,
            "brand": brand,
            "path": item["path"],
            "old_extraction": before["extraction"],
            "new_extraction": after["extraction"],
            "added_fields": added,
            "removed_fields": removed,
            "withheld_added": gained_withheld,
            "withheld_removed": sorted(set(before["withheld"])
                                       - set(after["withheld"])),
        })
    return {
        "blocks_scanned": scanned,
        "observations_changed": len(changed),
        "observations_unchanged": scanned - len(changed),
        "newly_structured_fields": dict(added_fields),
        "fields_removed": dict(removed_fields),
        "newly_withheld_fields": dict(withheld_added),
        "changes_by_brand": dict(by_brand),
        "affected": changed,
    }


# --------------------------------------------------------------------------- #
# Phase 11 / 13 -- what the corrected reading makes of the targets.
# --------------------------------------------------------------------------- #

def rederivation() -> List[Dict]:
    """The two targets re-read from their own canonical evidence.

    Zero provider calls by construction: the only input is the block the 028
    capture persisted, and its hash is carried forward so the lineage is
    checkable rather than asserted.
    """
    rows = store_rows()
    old = baseline_reader()
    out = []
    for key in targets():
        journal = next(r for r in P28.journal_rows()
                       if r["identity_key"] == key)
        block = CORPUS.persisted_block(key)
        before = read_with(old, block, strategy=journal["policy_locator"])
        after = read_with(PR, block, strategy=journal["policy_locator"])
        row = rows.get(key, {})
        out.append({
            "identity_key": key,
            "canonical_name": journal["canonical_name"],
            "source_url": journal["source_url"],
            "source_run": P28.RUN_ID,
            "policy_locator": journal["policy_locator"],
            "block_sha256": journal["canonical_artifacts"]["block_sha256"],
            "attempt_dir": journal["canonical_artifacts"]["attempt_dir"],
            "replay_status": journal["canonical_artifacts"]["replay_status"],
            "provider_calls": 0,
            "historical_028_reading": before["extraction"],
            "historical_028_withheld": before["withheld"],
            "rederived_extraction": after["extraction"],
            "rederived_withheld": after["withheld"],
            "rederived_non_inferences": after["non_inferences"],
            "review_status_before": row.get("review_status", ""),
        })
    return out


def overlay() -> Dict[str, Dict]:
    """The re-derived readings, keyed for 025's ``rederived`` seam."""
    out: Dict[str, Dict] = {}
    for row in rederivation():
        out[row["identity_key"]] = {
            "extraction": row["rederived_extraction"],
            "withheld": row["rederived_withheld"],
            "non_inferences": row["rederived_non_inferences"],
            "rederivation": {
                "work_order": WORK_ORDER,
                "reason": ("the generic reader was hardened against this "
                           "surface's count, weight and pet-named-charge "
                           "wording; the evidence is unchanged"),
                "evidence_sha256": row["block_sha256"],
                "supersedes_run": row["source_run"],
                "provider_calls": 0,
            },
        }
    return out


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def store_tracking() -> Dict:
    """Which improved readings the store can actually take, and which it cannot.

    A finding this work order surfaced rather than created. The store rebuilds
    non-router runs by RE-READING each record's persisted block, so a reader
    change reaches them automatically. The router-001 rows are built from that
    run's own journal instead, and only an explicit overlay -- currently scoped
    to fifteen queued identities -- can move them.

    So a repair that improves eight identities updates four. The other four are
    correct on disk and stale in the store, and widening that scope moves
    fifty-eight rows at once, which is a store decision and not a reader one.
    """
    rows = store_rows()
    improved: Dict[str, List[str]] = {}
    for change in corpus_wide_dry_run()["affected"]:
        key = change.get("identity_key") or change["slug"]
        improved.setdefault(key, []).append(change["run_id"])
    tracked, untracked = [], []
    for key, runs in sorted(improved.items()):
        row = rows.get(key)
        entry = {"identity_key": key,
                 "runs_with_a_changed_block": sorted(set(runs)),
                 "store_source_run": (row or {}).get("source_run", "")}
        if row and row.get("source_run") == "milwaukee-router-001":
            untracked.append(entry)
        else:
            tracked.append(entry)
    return {
        "identities_with_an_improved_reading": len(improved),
        "tracked_by_the_store": len(tracked),
        "not_tracked_by_the_store": len(untracked),
        "tracked": tracked,
        "untracked": untracked,
        "why": ("the store re-reads persisted evidence for runs it carries as "
                "extra entries and rebuilds router-001 from that run's own "
                "journal; only a named overlay moves a router-001 row"),
        "recommendation": ("re-derive the router-001 rows from their persisted "
                           "blocks in a store work order, where fifty-eight "
                           "rows moving at once is the subject rather than a "
                           "side effect"),
    }


def build_report() -> Dict:
    reproduction = reproduce()
    return {
        "schema": "ptf-generic-reader-hardening/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "preflight": preflight(),
        "targets": targets(),
        "reproduction": reproduction,
        "root_cause": {row["identity_key"]: root_cause(row["policy_block"])
                       for row in reproduction},
        "per_day_decision": per_day_decision(),
        "corpus_differential": corpus_differential(),
        "corpus_wide_dry_run": corpus_wide_dry_run(),
        "store_tracking": store_tracking(),
        "rederivation": rederivation(),
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
    parser.add_argument("--reproduce", action="store_true")
    parser.add_argument("--cause", action="store_true")
    parser.add_argument("--differential", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rederive", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.reproduce:
        for row in reproduce():
            print("%-56s reproduces_store=%s %s"
                  % (row["canonical_name"], row["reproduces_the_store"],
                     json.dumps(row["baseline_extraction"])))
    if args.cause:
        for row in reproduce():
            print(row["canonical_name"], json.dumps(
                root_cause(row["policy_block"])["causes"]))
    if args.differential:
        doc = corpus_differential()
        for row in doc["rows"]:
            print("%-30s %-8s +%s -%s"
                  % (row["case_id"], "CHANGED" if row["differs"] else "same",
                     row["added_fields"] or "-", row["removed_fields"] or "-"))
        print(json.dumps({k: v for k, v in doc.items() if k != "rows"},
                         indent=2))
    if args.dry_run:
        doc = corpus_wide_dry_run()
        print(json.dumps({k: v for k, v in doc.items() if k != "affected"},
                         indent=2))
        for row in doc["affected"]:
            print("  %-40s %-16s +%s -%s"
                  % (row["slug"][:40], row["brand"], row["added_fields"],
                     row["removed_fields"]))
    if args.rederive:
        for row in rederivation():
            print("%-56s %s -> %s" % (row["canonical_name"],
                                      json.dumps(row["historical_028_reading"]),
                                      json.dumps(row["rederived_extraction"])))
    if args.report:
        doc = write_report()
        print(json.dumps({k: v for k, v in doc.items()
                          if k not in ("reproduction", "corpus_differential",
                                       "corpus_wide_dry_run", "rederivation",
                                       "preflight", "root_cause")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
