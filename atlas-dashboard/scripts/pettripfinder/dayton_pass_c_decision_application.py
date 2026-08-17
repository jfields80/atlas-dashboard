"""PTF-DAYTON-RECERTIFICATION-001 Pass C -- apply the founder's decisions.

PREPARED, NOT RUN. This module turns the recorded decisions into live founder
approvals, and the work order that prepared it did not authorise running it with
``--apply``. Its dry run is the deliverable: it shows exactly what it would
write, and writes nothing.

What it applies
---------------
* the 13 recorded policy decisions (DAY-B01..B13), each APPROVE_CORRECTED_RECORD
* the 34-record ARTIFACT_BINDING_ONLY block re-attestation

...to a single end state: 47 live ``APPROVED_AFTER_CURRENT_REVIEW`` approvals in
the founder's name, and zero records left ``MACHINE_REVIEWED_PENDING_OPERATOR``.

Every approval it writes binds the FINAL hashes
-----------------------------------------------
An approval is a statement about a specific record, so each one is written
against the ``record_hash`` and ``evidence_hash`` recomputed from the record at
application time -- and only after those are confirmed equal to the hashes the
founder was actually shown. A decision given for one record can never become an
approval of another.

Fail closed, per record
-----------------------
The founder's cohort ruling is explicit: *if any record fails the artifact-only
verifier at application time, STOP for that record; do not silently include it
in this cohort.* So the cohort is re-verified here against the same
pre-work-order baseline rather than trusted from the committed report, and a
record that no longer qualifies is REFUSED individually -- reported, left
pending, and never folded into a block approval it no longer belongs to.

The supersedes chain
--------------------
Applying replaces the agent's machine block, never the founder's own approval.
The prior preserved under ``supersedes`` stays the founder's earlier attestation
-- so the chain reads founder -> founder, and no agent name is ever left in the
provenance a reader checks first.

Run:
  python -m scripts.pettripfinder.dayton_pass_c_decision_application \\
      [--baseline d14cdc4] [--apply]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                    # noqa: E402
from scripts.pettripfinder.dayton_artifact_cohort_verification import (      # noqa: E402
    baseline_package, verify_record,
)
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, record_hash,
)

MARKET = "dayton-oh"
WORK_ORDER = "PTF-DAYTON-RECERTIFICATION-001"
PASS_NAME = "Pass C"
APPLIED_AT = "2026-08-16"
FOUNDER = "jfields80"
DEFAULT_BASELINE = "d14cdc4"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
LEDGER_PATH = LP / "dayton_passB_founder_decisions.json"
REPORT_PATH = LP / "dayton_passC_application_report.json"
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))

POLICY = "POLICY_DECISION"
COHORT = "ARTIFACT_BINDING_ONLY_REATTESTATION"
APPROVE_COHORT = "APPROVE_ARTIFACT_BINDING_ONLY_REATTESTATION"


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _founder_prior(approval: Dict) -> Dict:
    """The last HUMAN approval in this record's chain.

    Applying must not bury it under the agent's machine block, and must not
    leave an agent name where a reader looks for the previous human decision.
    """
    node = approval
    # Skip the agent's machine block, and skip THIS pass's own output too: on a
    # re-run the live approval is already the founder's, and treating it as the
    # prior would make the record supersede itself -- the same self-nesting
    # defect Pass A hit. A block this pass wrote is identifiable by the
    # decision_source it stamps; the founder's own earlier attestations carry
    # none.
    while node.get("supersedes") and (
            node.get("operator") != FOUNDER or "decision_source" in node):
        node = node["supersedes"]
    if node.get("operator") != FOUNDER:
        raise AssertionError("no founder approval anywhere in the chain")
    if "decision_source" in node:
        raise AssertionError(
            "the only founder approval in the chain is this pass's own output")
    return node


def approve(record: Dict, kind: str, decision_row: Dict,
            decided_at: str = "", ledger_file: str = "") -> Dict:
    """Write the founder's live approval onto one record.

    The approval names WHICH decision authorised it, not merely that one did.
    An approval that binds only hashes says a record was approved; one that also
    names its decision says which ruling, given when, in which ledger -- so a
    later reader can go back to what the founder actually decided rather than
    inferring it from a date.
    """
    approval = record["approval"]
    prior = _founder_prior(approval)

    signed = {k: v for k, v in record.items() if k != "approval"}
    final_record = record_hash(signed)
    final_evidence = evidence_hash(record.get("evidence", []))

    bound_record = decision_row.get("bound_record_hash") or \
        decision_row.get("final_record_hash_to_attest")
    bound_evidence = decision_row.get("bound_evidence_hash") or \
        decision_row.get("final_evidence_hash")
    if final_record != bound_record or final_evidence != bound_evidence:
        raise AssertionError(
            "%s: the record moved between decision and application "
            "(decided %s, now %s). An approval must bind the record it was "
            "given for." % (record["identity_key"], str(bound_record)[7:23],
                            final_record[7:23]))

    caveat = (
        "%s %s. Founder decision applied. " % (WORK_ORDER, PASS_NAME)
    ) + (
        "Approved as a corrected record: the policy correction prepared in "
        "Pass B was reviewed and approved individually against these hashes."
        if kind == POLICY else
        "Approved as part of the 34-record ARTIFACT_BINDING_ONLY cohort. The "
        "committed verifier proved against the pre-work-order baseline that "
        "this record's facts, quotes, source URLs, withholding decisions, "
        "service-animal statement and evidence set are all unchanged, and that "
        "record_hash moved solely because its evidence entries gained "
        "publication-grade artifact bindings; evidence_hash is identical to "
        "the value the superseded approval recorded."
    ) + (
        " The approval under 'supersedes' is the founder's own earlier "
        "attestation, preserved verbatim; it described this record before the "
        "recertification and no longer binds it."
    )

    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", APPLIED_AT),
        ("decision_source", OrderedDict([
            ("kind", kind),
            ("decision_id", decision_row.get("decision_id", APPROVE_COHORT)),
            ("decided_by", FOUNDER),
            ("decided_at", decided_at or APPLIED_AT),
            ("ledger", ledger_file or LEDGER_PATH.name),
        ])),
        ("supersedes", copy.deepcopy(dict(prior))),
        ("caveats", [caveat]),
        ("record_hash", final_record),
        ("evidence_hash", final_evidence),
    ])
    return record["approval"]


def run(baseline: str, apply: bool) -> Dict:
    facts = load_json(FACTS_PATH)
    ledger = load_json(LEDGER_PATH)
    by_key = {h["identity_key"]: h for h in facts["hotels"]}
    before = {h["identity_key"]: h
              for h in baseline_package(baseline)["hotels"]}

    cohort_decision = ledger["artifact_only_cohort_decision"]
    policy_rows = {r["identity_key"]: r for r in ledger["decisions"]}
    cohort_rows = {r["identity_key"]: r for r in cohort_decision["records"]}

    if set(policy_rows) & set(cohort_rows):
        raise AssertionError("a record is in both lanes: %s"
                             % sorted(set(policy_rows) & set(cohort_rows)))
    if set(policy_rows) | set(cohort_rows) != set(by_key):
        raise AssertionError("the two lanes do not cover the market exactly")

    applied: List[Dict] = []
    refused: List[Dict] = []

    for key, row in policy_rows.items():
        if row["founder_decision"] != "APPROVE_CORRECTED_RECORD":
            refused.append(OrderedDict([
                ("identity_key", key), ("lane", POLICY),
                ("reason", "founder decision is %r" % row["founder_decision"])]))
            continue
        approval = approve(by_key[key], POLICY, row,
                           decided_at=row["decided_at"],
                           ledger_file=LEDGER_PATH.name)
        applied.append(OrderedDict([
            ("identity_key", key), ("lane", POLICY),
            ("decision_id", row["decision_id"]),
            ("record_hash", approval["record_hash"]),
            ("evidence_hash", approval["evidence_hash"])]))

    for key, row in cohort_rows.items():
        # The founder's condition, enforced per record: re-verify rather than
        # trust the committed report, and refuse individually on failure.
        verdict = verify_record(before[key], by_key[key])
        if verdict["verdict"] != "ARTIFACT_BINDING_ONLY":
            refused.append(OrderedDict([
                ("identity_key", key), ("lane", COHORT),
                ("reason", "failed the artifact-only verifier at application "
                           "time"),
                ("failures", verdict["failures"])]))
            continue
        approval = approve(by_key[key], COHORT, row,
                           decided_at=cohort_decision["decided_at"],
                           ledger_file=LEDGER_PATH.name)
        applied.append(OrderedDict([
            ("identity_key", key), ("lane", COHORT),
            ("record_hash", approval["record_hash"]),
            ("evidence_hash", approval["evidence_hash"])]))

    # Post-conditions the work order names explicitly.
    pending = [h["identity_key"] for h in facts["hotels"]
               if h["approval"]["decision"] ==
               enums.MACHINE_REVIEWED_PENDING_OPERATOR]
    founder_bound = [h for h in facts["hotels"]
                     if h["approval"]["decision"] ==
                     enums.APPROVED_AFTER_CURRENT_REVIEW
                     and h["approval"]["operator"] == FOUNDER]
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        if approval["decision"] != enums.APPROVED_AFTER_CURRENT_REVIEW:
            continue
        if approval["record_hash"] != record_hash(hotel) or \
                approval["evidence_hash"] != evidence_hash(hotel["evidence"]):
            raise AssertionError("%s: applied approval does not bind its record"
                                 % hotel["identity_key"])
        if approval["supersedes"].get("operator") != FOUNDER:
            raise AssertionError("%s: supersedes is not the founder's"
                                 % hotel["identity_key"])
        if evidence_contract.validate(hotel) or \
                evidence_contract.publication_blockers(hotel) or \
                policy_schema.validate_record(hotel):
            raise AssertionError("%s: record invalid after application"
                                 % hotel["identity_key"])

    payload = (json.dumps(facts, indent=2, ensure_ascii=False) + "\n") \
        .encode("utf-8")
    projected_sha = hashlib.sha256(payload).hexdigest()

    report = OrderedDict([
        ("schema", "ptf-dayton-passC-application/1.0"),
        ("work_order", WORK_ORDER),
        ("pass", PASS_NAME),
        ("as_of", APPLIED_AT),
        ("market_id", MARKET),
        ("status", "APPLIED" if apply else "PREPARED_NOT_APPLIED"),
        ("baseline_ref", baseline),
        ("applied_by",
         "claude-opus-5 (%s, agent) -- mechanical application of decisions the "
         "founder gave; every live approval is attributed to the founder "
         "because the founder made it" % WORK_ORDER),
        ("counts", OrderedDict([
            ("policy_decisions_applied",
             sum(1 for r in applied if r["lane"] == POLICY)),
            ("cohort_reattestations_applied",
             sum(1 for r in applied if r["lane"] == COHORT)),
            ("total_applied", len(applied)),
            ("refused", len(refused)),
            ("still_pending_operator", len(pending)),
            ("founder_bound_after_application", len(founder_bound)),
        ])),
        ("post_conditions", OrderedDict([
            ("all_47_founder_approved", len(founder_bound) == 47),
            ("zero_machine_reviewed_pending", not pending),
            ("every_approval_binds_its_record", True),
            ("supersedes_is_always_the_founders", True),
        ])),
        ("release_contract", OrderedDict([
            ("current_sha256",
             load_json(CONTRACT_PATH)["policy_package"]["expected_sha256"]),
            ("projected_sha256", projected_sha),
            ("repinned", bool(apply)),
        ])),
        ("refused_records", refused),
        ("applied_records", applied),
    ])

    if apply:
        FACTS_PATH.write_bytes(payload)
        contract = load_json(CONTRACT_PATH)
        contract["policy_package"]["expected_sha256"] = projected_sha
        CONTRACT_PATH.write_bytes(
            (json.dumps(contract, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        REPORT_PATH.write_bytes(
            (json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--apply", action="store_true",
                        help="write the founder approvals, re-pin the release "
                             "contract and emit the application report")
    args = parser.parse_args()

    report = run(args.baseline, args.apply)
    counts = report["counts"]
    print("status                          : %s" % report["status"])
    print("policy decisions applied        : %d" % counts["policy_decisions_applied"])
    print("cohort re-attestations applied  : %d" % counts["cohort_reattestations_applied"])
    print("refused                         : %d" % counts["refused"])
    print("founder-approved after apply    : %d" % counts["founder_bound_after_application"])
    print("still MACHINE_REVIEWED_PENDING  : %d" % counts["still_pending_operator"])
    for name, value in report["post_conditions"].items():
        print("  %-34s %s" % (name, value))
    print("release contract sha            : %s -> %s"
          % (report["release_contract"]["current_sha256"][:16],
             report["release_contract"]["projected_sha256"][:16]))
    for row in report["refused_records"]:
        print("  REFUSED %-44s %s" % (row["identity_key"][:44], row["reason"]))
    if not args.apply:
        print("dry run: nothing written. This module is PREPARED; applying it "
              "is a separate authorisation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
