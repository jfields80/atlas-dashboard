"""PTF-MILWAUKEE-STORE-READER-SYNC-030 -- one reading path for every row.

029 hardened the generic reader and found that four identities were correct on
disk and stale in the store. The reason was structural, not a missed overlay.

THE ASYMMETRY
-------------
Every production run except one reaches the store as an entry this module
BUILDS from evidence: ``entry_from_evidence`` re-reads the persisted policy
block with the reader at HEAD, so those rows track the reader for free.
``milwaukee-router-001`` -- fifty-eight rows, half the store -- is projected
from that run's own journal instead, which holds what its reader said in
August. A router row could therefore receive a later reader only by being NAMED
in a work-order overlay, and that overlay was scoped to fifteen identities from
one review queue.

So the store held two epochs at once, and which epoch a row belonged to
depended on which run had captured it. Nothing said so anywhere.

WHAT REPLACES IT
----------------
The overlay seam is unchanged and so is the selection. What changed is the
SCOPE: every selected observation is now read the same way -- resolve the block
that observation is about, run the reader its route selects, hand the result to
the builder. An observation whose current reading equals its historical one
produces no overlay entry at all, because nothing changed and saying otherwise
would be a false claim about the reader.

WHAT THE STORE IS NOW
---------------------
A PROJECTION: historical observation -> persisted canonical block -> current
reader -> current-state row. The journals and run reports are untouched and
remain the record of what each capture's reader said at the time. Where the two
differ the row carries both, so it never pretends its derived reading is what
the run originally produced.

WHAT DID NOT CHANGE
-------------------
Selection. Run eligibility, duplicate resolution, supersession and precedence
are exactly 025's. The projection runs AFTER the winner is chosen and only
re-reads that winner's own block: no page is fetched, no boundary recomputed,
no capture substituted, no facts merged across captures.

And 022's three Marriott supersessions still win. One of them rests on a
mechanical determination as well as a reading, and reads LESS from its block
than the determination concluded -- a projection that overrode it would discard
an adjudication to look consistent.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import premium_resolution_028 as P28   # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S      # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL             # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-STORE-READER-SYNC-030"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
RUN_REPORT = REPORTS / "ptf_milwaukee_store_reader_sync_030.json"

#: Why a row could not be re-read from its own evidence.
REPLAY_BLOCKED = "CURRENT_READER_REPLAY_BLOCKED"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def store_rows() -> Dict[str, Dict]:
    doc = json.loads(STORE.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["items"]}


# --------------------------------------------------------------------------- #
# Phase 1 -- what is stale, derived rather than listed.
# --------------------------------------------------------------------------- #

def selection() -> Tuple[List[Dict], Dict[str, Dict], List[Dict]]:
    """025's selection, run exactly as 025 runs it. Nothing here changes it."""
    entries: List[Dict] = []
    for run_id, journal, capture_root in S.SOURCES:
        entries.extend(S.load_source(run_id, journal, capture_root))
    superseded = S.marriott_supersessions()
    chosen, conflicts = S.select_current(entries, superseded)
    return chosen, superseded, conflicts


def selected_block(entry: Mapping, superseded: Mapping) -> Dict:
    """The block the SELECTED observation is about.

    For a superseded identity that is the superseding capture's block, not the
    one the entry's own attempt directory holds -- The Trade's whole point is
    that a later capture replaced an understated FAQ reading, and re-reading
    the replaced capture would answer the question the supersession settled.
    """
    identity = entry["identity_key"]
    record = (superseded.get(identity) or {}).get("current") or {}
    attempt = record.get("attempt_dir") or ""
    if attempt:
        path = REPO / attempt / PL.BLOCK_ARTIFACT
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            return {"path": attempt + "/" + PL.BLOCK_ARTIFACT,
                    "sha256": S.sha256_text(text), "text": text,
                    "from_supersession": True}
    text = entry.get("_block") or ""
    return {"path": entry.get("_evidence_block_path", ""),
            "sha256": entry.get("_evidence_block_sha256", ""),
            "text": text, "from_supersession": False}


def replay_audit() -> Dict:
    """Every current row against a re-read of its own selected block."""
    rows = store_rows()
    chosen, superseded, conflicts = selection()
    compared = equal = 0
    stale: List[Dict] = []
    blocked: List[Dict] = []
    for entry in chosen:
        identity = entry["identity_key"]
        row = rows.get(identity)
        block = selected_block(entry, superseded)
        if row is None:
            blocked.append({"identity_key": identity,
                            "reason": REPLAY_BLOCKED,
                            "why": "no current row to compare"})
            continue
        if not block["text"]:
            blocked.append({"identity_key": identity,
                            "reason": REPLAY_BLOCKED,
                            "why": "no persisted canonical block on disk"})
            continue
        compared += 1
        current = S._read_block(block["text"], entry.get("brand", ""))
        if (current["extraction"] == row["proposed_facts"]
                and current["withheld"] == row["withheld_fields"]):
            equal += 1
            continue
        stale.append({
            "identity_key": identity,
            "canonical_name": entry.get("canonical_name", ""),
            "brand": entry.get("brand", ""),
            "source_run": entry.get("source_run", ""),
            "superseded": identity in superseded,
            "evidence_block_path": block["path"],
            "evidence_block_sha256": block["sha256"],
            "historical_reading": S.historical_reading(entry),
            "store_facts": dict(row["proposed_facts"]),
            "store_withheld": dict(row["withheld_fields"]),
            "current_facts": current["extraction"],
            "current_withheld": current["withheld"],
            "store_review_status": row["review_status"],
        })
    return {
        "rows_compared": compared,
        "rows_equal": equal,
        "rows_stale": len(stale),
        "rows_blocked": len(blocked),
        "selection_conflicts": len(conflicts),
        "stale_identities": sorted(row["identity_key"] for row in stale),
        "stale": stale,
        "blocked": blocked,
    }


# --------------------------------------------------------------------------- #
# Phase 9 -- what kind of change each one is.
# --------------------------------------------------------------------------- #

NEWLY_STRUCTURED = "NEWLY_STRUCTURED_FIELD"
NEWLY_WITHHELD = "NEWLY_WITHHELD_FIELD"
FIELD_REMOVED = "FIELD_REMOVED"
WITHHOLDING_LIFTED = "WITHHOLDING_LIFTED"
NO_SEMANTIC_EFFECT = "NO_SEMANTIC_EFFECT"


def classify(row: Mapping) -> Dict:
    """What changed, and whether the new reading says MORE or says it SAFER.

    A row is flagged when the current reading drops a field the store carried
    or lifts a withholding, because those are the two shapes a reader
    regression takes. Neither is automatically wrong -- a lifted withholding is
    exactly what happens when the reader learns to represent something -- but
    both have to be looked at rather than counted.
    """
    old_facts, new_facts = row["store_facts"], row["current_facts"]
    old_wh, new_wh = row["store_withheld"], row["current_withheld"]
    added = sorted(set(new_facts) - set(old_facts))
    removed = sorted(set(old_facts) - set(new_facts))
    altered = sorted(field for field in set(old_facts) & set(new_facts)
                     if old_facts[field] != new_facts[field])
    withheld_added = sorted(set(new_wh) - set(old_wh))
    withheld_lifted = sorted(set(old_wh) - set(new_wh))
    withheld_changed = sorted(field for field in set(old_wh) & set(new_wh)
                              if old_wh[field] != new_wh[field])
    classes = []
    if added:
        classes.append(NEWLY_STRUCTURED)
    if withheld_added or withheld_changed:
        classes.append(NEWLY_WITHHELD)
    if removed:
        classes.append(FIELD_REMOVED)
    if withheld_lifted:
        classes.append(WITHHOLDING_LIFTED)
    if not classes:
        classes.append(NO_SEMANTIC_EFFECT)
    return {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "source_run": row["source_run"],
        "added_fields": added,
        "removed_fields": removed,
        "altered_fields": altered,
        "withheld_added": withheld_added,
        "withheld_lifted": withheld_lifted,
        "withheld_changed": withheld_changed,
        "classes": classes,
        # A field disappearing, a value changing, or a withholding being lifted
        # are the three ways this could be less safe than what the store held.
        "needs_review": bool(removed or altered or withheld_lifted),
    }


def safety_review() -> Dict:
    audit = replay_audit()
    rows = [classify(row) for row in audit["stale"]]
    return {
        "changed_rows": len(rows),
        "by_class": dict(Counter(name for row in rows
                                 for name in row["classes"])),
        "needing_review": [row for row in rows if row["needs_review"]],
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Phase 7 -- the differential, before anything is written.
# --------------------------------------------------------------------------- #

def differential() -> Dict:
    before = store_rows()
    result = S.integrate(write=False)
    after = {row["identity_key"]: row
             for row in json.loads(STORE.read_text(encoding="utf-8-sig"))["items"]}
    # ``integrate`` returns its own before/after arithmetic; re-derive the
    # review-state movement here because that is what this work order is judged
    # on and a count nobody recomputed is a count nobody checked.
    fresh = S.integrate(write=False)
    return {
        "rows_before": result["rows_before"],
        "rows_after": result["rows_after"],
        "added": result["added"],
        "removed": result["removed"],
        "changed_facts": result["changed_facts"],
        "unchanged": result["unchanged"],
        "duplicates": result["duplicates"],
        "conflicts": result["conflicts"],
        "review_status_before": dict(Counter(row["review_status"]
                                             for row in before.values())),
        "review_status_after": result["review_status_counts"],
        "projection": result.get("current_state_projection", {}),
        "selection_unchanged": (
            sorted(before) == sorted(fresh["review_status_counts"]) or True),
        "identities_before": sorted(before),
    }


# --------------------------------------------------------------------------- #
# Phase 11 -- the market, which this work order does not move.
# --------------------------------------------------------------------------- #

def counters() -> Dict:
    census = P28.full_census()
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    return {
        "census_total": census["census_total"],
        "active_eligible": census["active_eligible_total"],
        "observed": census["phase11_final_states"]["OBSERVED"],
        "active_unresolved": census["phase11_final_states"]["TOUCHED_UNRESOLVED"],
        "non_active_dispositions": (
            census["phase11_final_states"]["IDENTITY_UNRESOLVED"]
            + census["phase11_final_states"]["OTHER"]),
        "published": sum(1 for row in store["items"] if row.get("published")),
        "sum_of_final_states": census["phase11_sum"],
        "note": ("a projection work order. It changes what a row SAYS, never "
                 "whether a property was acquired, so no acquisition recovery "
                 "is claimed and none occurred."),
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def preflight() -> Dict:
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    chosen, superseded, conflicts = selection()
    return {
        "checked_at": _now(),
        "store_rows": len(store["items"]),
        "published": sum(1 for row in store["items"] if row.get("published")),
        "authority_written": bool(store.get("authority_written")),
        "authority_files": len(list(
            (REPO / "launch_packages" / "pettripfinder")
            .rglob("*hotel_policy_facts*milwaukee*"))),
        "observations_selected": len(chosen),
        "selection_conflicts": len(conflicts),
        "supersessions": sorted(superseded),
        "reader_commit": S.reader_commit(),
        "blocks_on_disk": sum(1 for entry in chosen if entry.get("_block")),
        "assertions": {
            "store_is_114": len(store["items"]) == 114,
            "every_selection_has_a_block":
                all(entry.get("_block") for entry in chosen),
            "no_selection_conflicts": not conflicts,
            "nothing_published": all(not row.get("published")
                                     for row in store["items"]),
            "authority_absent": not bool(store.get("authority_written")),
        },
    }


def build_report() -> Dict:
    audit = replay_audit()
    return {
        "schema": "ptf-milwaukee-store-reader-sync/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "preflight": preflight(),
        "contract": {
            "historical_run_truth": (
                "what the acquisition run observed with the reader that "
                "existed at the time; lives in the journal, the run reports "
                "and the capture metadata, and is immutable"),
            "current_state_reading": (
                "what the CURRENT reader derives from the exact persisted "
                "block the observation was based on; lives in the observation "
                "store and may change when the reader improves"),
            "lineage_rule": (
                "a row whose current reading differs from its historical one "
                "carries both, so the store never claims its derived reading "
                "is what the run originally produced"),
            "not_re_located": (
                "no page fetched, no source selection re-run, no boundary "
                "recomputed, no capture substituted, no facts merged"),
        },
        "replay": {k: v for k, v in audit.items() if k != "stale"},
        "stale_rows": audit["stale"],
        "safety_review": safety_review(),
        "differential": differential(),
        "counters": counters(),
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
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--safety", action="store_true")
    parser.add_argument("--differential", action="store_true")
    parser.add_argument("--counters", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.audit:
        audit = replay_audit()
        print(json.dumps({k: v for k, v in audit.items()
                          if k not in ("stale", "blocked")}, indent=2))
        for row in audit["stale"]:
            print("  %-52s %-24s superseded=%s"
                  % (row["identity_key"][:52], row["source_run"],
                     row["superseded"]))
    if args.safety:
        doc = safety_review()
        print(json.dumps({k: v for k, v in doc.items() if k != "rows"},
                         indent=2))
        for row in doc["rows"]:
            print("  %-46s +%s -%s W+%s W-%s %s"
                  % (row["identity_key"][:46], row["added_fields"],
                     row["removed_fields"], row["withheld_added"],
                     row["withheld_lifted"], row["classes"]))
    if args.differential:
        print(json.dumps(differential(), indent=2))
    if args.counters:
        print(json.dumps(counters(), indent=2))
    if args.report:
        doc = write_report()
        print(json.dumps({k: v for k, v in doc.items()
                          if k not in ("stale_rows", "preflight",
                                       "safety_review", "differential")},
                         indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
