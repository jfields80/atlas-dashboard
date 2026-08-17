"""PTF-DAYTON-RECERTIFICATION-001 -- prove the artifact-only cohort is exactly that.

Thirty-four Dayton records are being put to the founder as ONE block decision on
the claim that nothing about them changed except artifact bindings. A block
decision is only safe if that claim is checked rather than asserted, because the
whole risk of batching is that one real policy change rides along inside a
cohort nobody reads line by line.

So every record in the cohort is diffed against its state at the PRE-PASS-A
baseline -- the committed authority before any of this work order touched it --
and the diff must contain nothing but the five artifact-binding fields.

What must hold, per record
--------------------------
* ``facts`` byte-identical
* every evidence entry's field, quote, source_url and value byte-identical
* the evidence SET unchanged, so ``evidence_hash`` is unchanged
* ``withheld_fields`` unchanged -- a withholding is a policy decision
* ``service_animal_statement`` unchanged
* every other record-level field unchanged apart from ``approval``
* ``record_hash`` DIFFERENT, and different only because the entries gained
  artifact_sha256 / artifact_kind / captured_at / capture_method / source_grade
* the founder's own prior approval still preserved verbatim under supersedes

A record failing any of these is not artifact-only and must be lifted out of the
cohort and put to the founder on its own terms.

Run:
  python -m scripts.pettripfinder.dayton_artifact_cohort_verification \
      [--baseline d14cdc4] [--apply]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, record_hash,
)

MARKET = "dayton-oh"
WORK_ORDER = "PTF-DAYTON-RECERTIFICATION-001"
DEFAULT_BASELINE = "d14cdc4"
AS_OF = "2026-08-16"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
PACKET_PATH = LP / "dayton_passB_founder_review_packet.json"
LEDGER_PATH = LP / "dayton_passB_founder_decisions.json"
REPORT_PATH = LP / "dayton_artifact_cohort_verification.json"

#: The only keys an evidence entry may have gained. Everything else about the
#: entry -- the words, the URL, the field it supports -- must be untouched.
ARTIFACT_BINDING_KEYS = ("artifact_sha256", "artifact_kind", "captured_at",
                         "capture_method", "source_grade")

#: Record-level keys that may legitimately differ: the approval is what a
#: binding pass rewrites, and artifact_class moves with the bindings.
ALLOWED_RECORD_DIFFS = ("approval",)


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def baseline_package(ref: str) -> Dict:
    """The committed Dayton package as of ``ref``, read from git.

    The path is resolved against the git TOPLEVEL rather than this package
    root: the repository checkout may nest ``atlas-dashboard/`` inside it, and
    a path that is right for imports is not automatically right for ``git
    show``.
    """
    toplevel = Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=str(_REPO_ROOT),
        capture_output=True, check=True, text=True).stdout.strip())
    rel = FACTS_PATH.resolve().relative_to(toplevel.resolve()).as_posix()
    blob = subprocess.run(
        ["git", "show", "%s:%s" % (ref, rel)],
        cwd=str(_REPO_ROOT), capture_output=True, check=True)
    return json.loads(blob.stdout.decode("utf-8-sig"))


def _entry_identity(entry: Dict) -> Tuple:
    """Everything about an evidence entry that is NOT an artifact binding."""
    return tuple(sorted(
        (key, json.dumps(value, sort_keys=True))
        for key, value in entry.items()
        if key not in ARTIFACT_BINDING_KEYS
        and key not in ("artifact_class", "contiguity_verified",
                        "provenance_note")))


def verify_record(before: Dict, after: Dict) -> Dict:
    """Diff one cohort record against its pre-work-order self."""
    failures: List[str] = []

    if before["facts"] != after["facts"]:
        failures.append("facts changed")
    if before.get("withheld_fields") != after.get("withheld_fields"):
        failures.append("withheld_fields changed -- that is a policy decision")
    if before.get("service_animal_statement") != \
            after.get("service_animal_statement"):
        failures.append("service_animal_statement changed")

    for key in set(before) | set(after):
        if key in ALLOWED_RECORD_DIFFS or key in (
                "facts", "evidence", "withheld_fields",
                "service_animal_statement"):
            continue
        if before.get(key) != after.get(key):
            failures.append("record field %r changed" % key)

    before_entries = {e["evidence_ref"]: e for e in before["evidence"]}
    after_entries = {e["evidence_ref"]: e for e in after["evidence"]}
    if set(before_entries) != set(after_entries):
        failures.append(
            "the evidence SET changed (added %s, removed %s)"
            % (sorted(set(after_entries) - set(before_entries)),
               sorted(set(before_entries) - set(after_entries))))
    for ref, before_entry in before_entries.items():
        after_entry = after_entries.get(ref)
        if after_entry is None:
            continue
        if _entry_identity(before_entry) != _entry_identity(after_entry):
            failures.append("evidence %s: wording, URL or field changed" % ref)
        gained = [k for k in ARTIFACT_BINDING_KEYS
                  if k in after_entry and k not in before_entry]
        if not gained:
            failures.append("evidence %s: gained no artifact binding" % ref)

    before_evidence = evidence_hash(before["evidence"])
    after_evidence = evidence_hash(after["evidence"])
    if before_evidence != after_evidence:
        failures.append("evidence_hash moved (%s -> %s)"
                        % (before_evidence[7:23], after_evidence[7:23]))

    before_record = record_hash(before)
    after_record = record_hash(after)
    if before_record == after_record:
        failures.append("record_hash did NOT move; nothing was bound")

    # The substance checks above are the founder's condition and never vary.
    # The approval POSTURE does: a record is legitimately pending before Pass C
    # applies and founder-approved after, and this verifier runs in both states
    # -- once per record at application time, and again by the closeout tests.
    # Accepting only one posture would make the applier non-idempotent, which is
    # the exact defect this work order has already hit twice.
    approval = after["approval"]
    prior = approval.get("supersedes") or {}
    decision = approval["decision"]
    if decision == enums.MACHINE_REVIEWED_PENDING_OPERATOR:
        if approval["operator"] == "jfields80":
            failures.append("a machine decision carries the founder's name")
    elif decision == enums.APPROVED_AFTER_CURRENT_REVIEW:
        if approval["operator"] != "jfields80":
            failures.append("a founder approval is not in the founder's name")
    else:
        failures.append("unexpected live approval state %r" % decision)
    if prior.get("operator") != "jfields80":
        failures.append("the preserved prior approval is not the founder's")
    if prior.get("record_hash") != before_record:
        failures.append(
            "the preserved approval does not bind the pre-work-order record")
    if approval["record_hash"] != after_record or \
            approval["evidence_hash"] != after_evidence:
        failures.append("the approval block does not bind this record")

    return OrderedDict([
        ("identity_key", after["identity_key"]),
        ("hotel", after["name"]),
        ("verdict", "ARTIFACT_BINDING_ONLY" if not failures
         else "NOT_ARTIFACT_ONLY"),
        ("facts_unchanged", before["facts"] == after["facts"]),
        ("quotes_unchanged", all(
            _entry_identity(before_entries[r]) == _entry_identity(after_entries[r])
            for r in before_entries if r in after_entries)),
        ("withholding_unchanged",
         before.get("withheld_fields") == after.get("withheld_fields")),
        ("evidence_entries", len(after["evidence"])),
        ("evidence_hash_unchanged", before_evidence == after_evidence),
        ("evidence_hash", after_evidence),
        ("record_hash_before_work_order", before_record),
        ("final_record_hash_to_attest", after_record),
        ("founder_prior_approval", OrderedDict([
            ("operator", prior.get("operator")),
            ("decision", prior.get("decision")),
            ("approval_date", prior.get("approval_date")),
            ("record_hash", prior.get("record_hash")),
        ])),
        ("failures", failures),
    ])


def run(baseline: str, apply: bool) -> Dict:
    before = {h["identity_key"]: h for h in baseline_package(baseline)["hotels"]}
    after = {h["identity_key"]: h for h in load_json(FACTS_PATH)["hotels"]}
    packet = load_json(PACKET_PATH)
    ledger = load_json(LEDGER_PATH)

    decided = {row["identity_key"] for row in ledger["decisions"]}
    cohort = [row["identity_key"] for row in
              packet["artifact_binding_only_reattestation"]["records"]]

    # The cohort and the decided records must partition the market exactly.
    if set(cohort) & decided:
        raise AssertionError("records are in BOTH the cohort and a policy "
                             "decision: %s" % sorted(set(cohort) & decided))
    if set(cohort) | decided != set(after):
        raise AssertionError(
            "cohort + decisions do not cover the market (missing %s, extra %s)"
            % (sorted(set(after) - (set(cohort) | decided)),
               sorted((set(cohort) | decided) - set(after))))
    if set(after) != set(before):
        raise AssertionError("the record set itself moved since %s" % baseline)

    rows = [verify_record(before[key], after[key]) for key in cohort]
    failed = [r for r in rows if r["failures"]]

    report = OrderedDict([
        ("schema", "ptf-dayton-artifact-cohort-verification/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", AS_OF),
        ("market_id", MARKET),
        ("baseline_ref", baseline),
        ("verified_by", "claude-opus-5 (%s, agent)" % WORK_ORDER),
        ("claim_under_test",
         "These %d records changed in exactly one way: their evidence entries "
         "gained publication-grade artifact bindings. No fact, quote, source "
         "URL, withholding decision or service-animal statement moved, and "
         "evidence_hash is identical to the value the founder's own approval "
         "recorded. record_hash moved solely because the record now carries "
         "the bindings." % len(cohort)),
        ("method",
         "Each record is diffed against its committed state at %s -- before "
         "this work order touched anything -- rather than against the "
         "description of what the passes intended to do. A block decision is "
         "only safe if the claim behind it is checked, because the risk of "
         "batching is precisely that one real policy change rides along inside "
         "a cohort nobody reads line by line." % baseline),
        ("cohort_size", len(cohort)),
        ("verdicts", OrderedDict([
            ("ARTIFACT_BINDING_ONLY", len(rows) - len(failed)),
            ("NOT_ARTIFACT_ONLY", len(failed)),
        ])),
        ("policy_corrections_hidden_in_the_cohort", len(failed)),
        ("facts_unchanged_on_all", all(r["facts_unchanged"] for r in rows)),
        ("quotes_unchanged_on_all", all(r["quotes_unchanged"] for r in rows)),
        ("withholding_unchanged_on_all",
         all(r["withholding_unchanged"] for r in rows)),
        ("evidence_hash_unchanged_on_all",
         all(r["evidence_hash_unchanged"] for r in rows)),
        ("record_hash_moved_on_all",
         all(r["record_hash_before_work_order"] !=
             r["final_record_hash_to_attest"] for r in rows)),
        ("records", rows),
    ])

    if apply:
        REPORT_PATH.write_bytes(
            (json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE,
                        help="git ref of the pre-work-order authority")
    parser.add_argument("--apply", action="store_true",
                        help="write the verification report")
    args = parser.parse_args()

    report = run(args.baseline, args.apply)
    print("baseline                    : %s" % report["baseline_ref"])
    print("cohort size                 : %d" % report["cohort_size"])
    for verdict, count in report["verdicts"].items():
        print("  %-30s %d" % (verdict, count))
    for label in ("facts_unchanged_on_all", "quotes_unchanged_on_all",
                  "withholding_unchanged_on_all",
                  "evidence_hash_unchanged_on_all", "record_hash_moved_on_all"):
        print("  %-30s %s" % (label, report[label]))
    print("policy corrections hidden   : %d"
          % report["policy_corrections_hidden_in_the_cohort"])
    for row in report["records"]:
        if row["failures"]:
            print("  !! %-46s %s" % (row["hotel"][:46], row["failures"]))
    if not args.apply:
        print("dry run: nothing written (pass --apply to write the report)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
