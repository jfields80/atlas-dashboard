"""PTF-DAYTON-RECERTIFICATION-001 Pass B -- record the founder's decisions.

RECORDS decisions. Applies nothing. After this runs, every Dayton record is
still ``MACHINE_REVIEWED_PENDING_OPERATOR`` and the policy package is byte-for-
byte what Pass B committed; the ledger is the founder's answer sitting beside
the packet's question, waiting for a separate application order.

Why the ledger is its own file
------------------------------
Cleveland recorded its rulings inside the review packet. Dayton's packet is
emitted by an idempotent generator, so a re-run of
``dayton_pass_b_policy_corrections`` would overwrite whatever was written into
it -- and the thing it would overwrite is a human decision. The generated
question and the human answer therefore live in separate files: nothing that
regenerates can destroy an attestation.

What "recording" binds
----------------------
A decision is only meaningful against the exact record it was given for, so
each row carries the ``record_hash`` and ``evidence_hash`` the founder was
shown, and this module REFUSES to write unless those still equal the live
record's hashes AND the record's own approval block. A decision recorded
against a record that has since moved is not a decision about that record.

Attribution
-----------
``decided_by`` is the founder, because the founder gave these six decisions
explicitly and in writing. That is the only circumstance in which their name
may appear on a decision: this module never infers a ruling, never fills a
default, and fails closed if asked to record a decision it was not given.

Run:
  python -m scripts.pettripfinder.dayton_pass_b_founder_decisions [--apply]
"""

from __future__ import annotations

import argparse
import json
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
DECISION_ORDERS = OrderedDict([
    ("A", "DAYTON PASS B -- FOUNDER DECISIONS BATCH A"),
    ("B", "DAYTON PASS B -- FOUNDER DECISIONS BATCH B"),
    ("C", "DAYTON PASS B -- FOUNDER DECISIONS BATCH C"),
])
DECIDED_AT = "2026-08-16"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
COHORT_REPORT_PATH = LP / "dayton_artifact_cohort_verification.json"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
PACKET_PATH = LP / "dayton_passB_founder_review_packet.json"
LEDGER_PATH = LP / "dayton_passB_founder_decisions.json"

APPROVE = "APPROVE_CORRECTED_RECORD"
HOLD = "HOLD"
APPROVE_COHORT = "APPROVE_ARTIFACT_BINDING_ONLY_REATTESTATION"

#: The founder's block decision on the 34-record artifact-only cohort, and the
#: exact grounds they gave for it. The grounds are recorded because the block
#: form is conditional on them: this is an approval of a PROVEN homogeneous
#: cohort, not a general licence to batch.
COHORT_DECISION: Dict = OrderedDict([
    ("decision", APPROVE_COHORT),
    ("decided_by", FOUNDER),
    ("decided_at", DECIDED_AT),
    ("decision_order", "DAYTON -- ARTIFACT-ONLY COHORT FOUNDER ATTESTATION"),
    ("approved_on_the_basis_that_the_verifier_proves", (
        "facts unchanged",
        "quotes unchanged",
        "source_url / field / value wording unchanged",
        "evidence_hash unchanged",
        "withheld_fields unchanged",
        "service_animal_statement unchanged",
        "evidence set unchanged",
        "no policy correction hidden inside the cohort",
        "only publication-grade artifact metadata / artifact binding moved "
        "record_hash",
        "every final target record_hash is explicitly enumerated and "
        "re-verified live",
    )),
    ("governance", (
        "GOV-01 applies: these records DO require founder re-attestation "
        "because their final record_hash / evidentiary binding changed.",
        "One founder cohort decision is sufficient ONLY because the verifier "
        "proves this is a homogeneous artifact-binding-only cohort with zero "
        "policy movement.",
        "This is NOT permission to use block approval for mixed or partially "
        "verified cohorts.",
        "If any record fails the artifact-only verifier at application time, "
        "STOP for that record. Do not silently include it in this cohort.",
    )),
    ("scope", (
        "Approve exactly the 34 records classified ARTIFACT_BINDING_ONLY.",
        "Do NOT include any of the 13 separately reviewed policy-correction "
        "records in this cohort.",
        "34 cohort + 13 policy = 47 total, with 0 overlap and 0 omission.",
    )),
    ("applied_to_authority", False),
])

#: The founder's decisions, exactly as given, batch by batch. Nothing here is
#: derived. The ledger is rebuilt from this table on every run, so a batch
#: already recorded must reproduce byte-identically -- which it does only while
#: its records have not moved, and the hash guard below is what proves it.
DECISIONS: "OrderedDict[str, Tuple[Tuple[str, str], ...]]" = OrderedDict([
    ("A", (
        ("DAY-B01", APPROVE),
        ("DAY-B02", APPROVE),
        ("DAY-B03", APPROVE),
        ("DAY-B04", APPROVE),
        ("DAY-B05", APPROVE),
        ("DAY-B06", APPROVE),
    )),
    ("B", (
        ("DAY-B07", APPROVE),
        ("DAY-B08", APPROVE),
        ("DAY-B09", APPROVE),
        ("DAY-B10", APPROVE),
        ("DAY-B11", APPROVE),
    )),
    ("C", (
        ("DAY-B12", APPROVE),
        ("DAY-B13", APPROVE),
    )),
])

#: Which packet batch each ledger batch answers, so the coverage check compares
#: the decisions given against the decisions asked for.
PACKET_BATCH_KEYS = {"A": "A_monetary", "B": "B_service_animal_and_esa",
                     "C": "C_pointer_repair"}

BATCH_A: Tuple[Tuple[str, str], ...] = DECISIONS["A"]

#: Rulings the founder attached to a specific decision, recorded verbatim so
#: the application order has no room to interpret them.
DECISION_NOTES: Dict[str, Tuple[str, ...]] = {
    "DAY-B06": (
        "Approve pet_fee.refundable = false.",
        "Approve pet_fee.tax_relationship = plus_tax.",
        "Do NOT create $87.94 as a second fee amount.",
        "$87.94 is the source's arithmetic result from the already-published "
        "$75 fee plus 17.25% tax.",
        "REND-01 remains a separate renderer issue and does not block approval "
        "of the canonical fact.",
    ),
    "DAY-B07": (
        "Approve service_animal_statement = {stated: true, charges_stated: "
        "no_charge}, based on the explicit first-party wording \"Service "
        "Animals - ADA-defined service animals are welcome free of charge.\"",
        "Approve the associated service_animal_exception evidence.",
        "Do not broaden this beyond the explicit source language.",
        "All existing pet-policy facts remain unchanged.",
    ),
    "DAY-B08": (
        "Approve service_animal_statement = {stated: true, charges_stated: "
        "no_charge}, based on \"Service animals will be exempt from this "
        "charge.\"",
        "Approve the ceiling-handling correction: withheld.pet_fee "
        "SOURCE_AMBIGUOUS -> SCHEMA_CANNOT_REPRESENT.",
        "Add withheld.cleaning_fee = SCHEMA_CANNOT_REPRESENT.",
        "Retain both ceiling sentences verbatim in evidence.",
        "Do NOT publish $25 or $15 as exact pet-fee prices. CEILING != PRICE.",
    ),
    "DAY-B09": (
        "Apply the exact same approved treatment as DAY-B08: service-animal "
        "statement; no-charge mapping limited to the referenced pet charge; "
        "pet_fee withholding reason -> SCHEMA_CANNOT_REPRESENT; cleaning_fee "
        "withheld as SCHEMA_CANNOT_REPRESENT; both ceiling sentences "
        "preserved; no $25/$15 exact price published.",
    ),
    "DAY-B10": (
        "Apply the exact same approved treatment as DAY-B08. CEILING != PRICE.",
        "Do not invent or publish an exact charge from \"Not to exceed a "
        "$25.00 per day cleaning fee...\" or \"not to exceed a $15.00 per "
        "day...\"",
    ),
    "DAY-B11": (
        "Apply the exact same approved treatment as DAY-B08.",
        "Approve the explicit service-animal statement and the "
        "schema-cannot-represent handling of the two cleaning-fee ceilings.",
        "Do not manufacture an exact pet fee.",
    ),
    "DAY-B12": (
        "Approve the fee_scope evidence-pointer repair.",
        "Approve the existing canonical interpretation: pet_fee amount $25, "
        "basis per_night, scope per_room, scope_pet_allowance 2; fee_cap "
        "amount $75, basis per_stay, qualifier_stated true.",
        "The source wording \"Fees - Non-refundable 25 USD nightly for up to "
        "2 pets. Max 75 USD per stay.\" supports the existing per-room charge "
        "covering up to two pets.",
        "No policy fact changes are authorized beyond what is already in the "
        "corrected record.",
    ),
    "DAY-B13": (
        "Approve the same evidence-pointer repair and existing canonical "
        "interpretation as DAY-B12, based on this property's own captured "
        "first-party artifact.",
        "Approve the added fee_scope evidence pointer.",
        "No fact change. No public-rendering change. No new source text.",
    ),
}

#: Standing rules the founder set while deciding. Recorded here because a
#: principle given in passing during a batch review is exactly the kind of
#: thing that evaporates when the conversation ends, and this one governs
#: every market that follows.
GOVERNANCE_RULINGS: Tuple[Dict, ...] = (
    OrderedDict([
        ("id", "GOV-01"),
        ("ruled_during", "Dayton Pass B Batch C"),
        ("ruled_by", FOUNDER),
        ("ruled_at", DECIDED_AT),
        ("rule",
         "A citation-only / evidence-pointer repair DOES require founder "
         "re-attestation when it changes the final record_hash or evidence "
         "binding."),
        ("reason",
         "The public facts may be unchanged, but the record's evidentiary "
         "basis has changed. Founder attestation must bind the final supported "
         "record, not merely the visible facts."),
        ("scope",
         "Apply consistently in future markets unless the evidence contract is "
         "later changed explicitly."),
        ("first_applied_to", ["DAY-B12", "DAY-B13"]),
    ]),
)

#: Work the founder directed OUT of this order rather than into it. Recorded
#: here so a recommendation given during a decision does not evaporate when the
#: conversation ends.
FOLLOW_UPS: Tuple[Dict, ...] = (
    OrderedDict([
        ("id", "FU-01"),
        ("raised_during", "Dayton Pass B Batch B"),
        ("finding",
         "Cleveland's two Extended Stay America records carry no "
         "service_animal_statement and no service-animal quote anywhere in "
         "their evidence, while the Dayton ESA pages state \"Service animals "
         "will be exempt from this charge.\" explicitly. Approving Dayton "
         "Batch B therefore leaves Dayton's four ESA records more complete "
         "than Cleveland's two on this field."),
        ("founder_ruling",
         "Acknowledged. Does NOT block Dayton Batch B approval. Do not alter "
         "Cleveland in this Dayton work order."),
        ("recommended_owner",
         "a separate Cleveland evidence-completeness work order, opened after "
         "Dayton is closed"),
        ("records", [
            "cleveland-akron-canton-oh / extended stay america select suites akron south",
            "cleveland-akron-canton-oh / extended stay america hotel akron copley east",
        ]),
        ("cleveland_touched_by_this_order", False),
    ]),
)


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _bind(decision_id: str, ruling: str, batch: str, row: Dict,
          hotel: Dict) -> Dict:
    """One decision row, bound to the record it was given for -- or refused.

    The binding is checked against three sources that must all agree: the hash
    the founder was shown in the packet, the hash recomputed from the live
    record, and the hash the record's own approval block carries. A decision
    recorded against a record that has since moved is not a decision about that
    record.
    """
    if ruling not in (APPROVE, HOLD):
        raise AssertionError("%s: %r is not a decision" % (decision_id, ruling))

    approval = hotel["approval"]
    for label, presented_value, live_value, stored_value in (
            ("record_hash", row["final_record_hash"], record_hash(hotel),
             approval["record_hash"]),
            ("evidence_hash", row["final_evidence_hash"],
             evidence_hash(hotel["evidence"]), approval["evidence_hash"])):
        if not presented_value == live_value == stored_value:
            raise AssertionError(
                "%s: %s moved since the founder was shown it (presented %s, "
                "live %s, on record %s). A decision given for one record must "
                "not be recorded against another."
                % (decision_id, label, presented_value[:23], live_value[:23],
                   stored_value[:23]))

    return OrderedDict([
        ("decision_id", decision_id),
        ("batch", batch),
        ("hotel", row["hotel"]),
        ("identity_key", row["identity_key"]),
        ("group", row["group"]),
        ("founder_decision", ruling),
        ("decided_by", FOUNDER),
        ("decided_at", DECIDED_AT),
        ("decision_notes", list(DECISION_NOTES.get(decision_id, ()))),
        ("bound_record_hash", row["final_record_hash"]),
        ("bound_evidence_hash", row["final_evidence_hash"]),
        ("hashes_reverified_at_recording", True),
        ("changes_approved", row["changes"]),
        ("public_rendering_note", row["public_rendering_note"]),
        ("applied_to_authority", False),
        ("authority_state_now", approval["decision"]),
    ])


def _cohort_decision(decided_rows: List[Dict], by_key: Dict) -> Dict:
    """The founder's block decision, bound to the verified cohort.

    Recorded only against records the committed verifier classified
    ARTIFACT_BINDING_ONLY, and only while their enumerated hashes still equal
    the live record. The founder made the block form conditional on that proof,
    so a cohort that no longer verifies is not the cohort they approved.
    """
    report = load_json(COHORT_REPORT_PATH)
    decided = {row["identity_key"] for row in decided_rows}

    rows: List[Dict] = []
    for row in report["records"]:
        key = row["identity_key"]
        if row["verdict"] != "ARTIFACT_BINDING_ONLY":
            raise AssertionError(
                "%s is in the cohort report as %s; the founder approved only "
                "ARTIFACT_BINDING_ONLY records" % (key, row["verdict"]))
        if key in decided:
            raise AssertionError(
                "%s is in BOTH the cohort and a policy decision; the founder "
                "required zero overlap" % key)
        record = by_key[key]
        approval = record["approval"]
        live_record = record_hash(record)
        live_evidence = evidence_hash(record["evidence"])
        if not row["final_record_hash_to_attest"] == live_record == \
                approval["record_hash"]:
            raise AssertionError(
                "%s: record_hash moved since the cohort was verified and "
                "approved (enumerated %s, live %s)"
                % (key, row["final_record_hash_to_attest"][:23],
                   live_record[:23]))
        if not row["evidence_hash"] == live_evidence == \
                approval["evidence_hash"]:
            raise AssertionError(
                "%s: evidence_hash moved since the cohort was approved" % key)
        rows.append(OrderedDict([
            ("identity_key", key),
            ("hotel", row["hotel"]),
            ("record_hash_before_work_order",
             row["record_hash_before_work_order"]),
            ("final_record_hash_to_attest", live_record),
            ("final_evidence_hash", live_evidence),
            ("evidence_hash_unchanged_since_founder_approval",
             row["evidence_hash_unchanged"]),
            ("applied_to_authority", False),
            ("authority_state_now", approval["decision"]),
        ]))

    if len(rows) + len(decided) != len(by_key):
        raise AssertionError(
            "cohort %d + decisions %d != %d published records; the founder "
            "required zero omission"
            % (len(rows), len(decided), len(by_key)))

    decision = OrderedDict(COHORT_DECISION)
    decision["verifier_report"] = COHORT_REPORT_PATH.name
    decision["verifier_baseline_ref"] = report["baseline_ref"]
    decision["cohort_size"] = len(rows)
    decision["policy_corrections_hidden_in_the_cohort"] = \
        report["policy_corrections_hidden_in_the_cohort"]
    decision["records"] = rows
    return decision


def build() -> Dict:
    packet = load_json(PACKET_PATH)
    facts = load_json(FACTS_PATH)
    by_key = {hotel["identity_key"]: hotel for hotel in facts["hotels"]}
    presented = {d["decision_id"]: d for d in packet["policy_decisions"]}

    # A batch is recorded whole or not at all: a partial batch would leave
    # records looking undecided when they had simply been dropped here.
    for batch, given in DECISIONS.items():
        decided = {decision_id for decision_id, _ in given}
        expected = set(packet["batches"][PACKET_BATCH_KEYS[batch]])
        if decided != expected:
            raise AssertionError(
                "Batch %s is %s but decisions were given for %s; this module "
                "records the decisions it was given and never invents the rest"
                % (batch, sorted(expected), sorted(decided)))

    rows: List[Dict] = [
        _bind(decision_id, ruling, batch, presented[decision_id],
              by_key[presented[decision_id]["identity_key"]])
        for batch, given in DECISIONS.items()
        for decision_id, ruling in given
    ]

    approved = [r for r in rows if r["founder_decision"] == APPROVE]
    held = [r for r in rows if r["founder_decision"] == HOLD]

    per_batch = OrderedDict(
        (batch, OrderedDict([
            ("decision_order", DECISION_ORDERS[batch]),
            ("presented", len(given)),
            ("approved", sum(1 for _, r in given if r == APPROVE)),
            ("held", sum(1 for _, r in given if r == HOLD)),
            ("decision_ids", [decision_id for decision_id, _ in given]),
        ]))
        for batch, given in DECISIONS.items())

    outstanding = OrderedDict(
        (PACKET_BATCH_KEYS[batch], packet["batches"][PACKET_BATCH_KEYS[batch]])
        for batch in PACKET_BATCH_KEYS if batch not in DECISIONS)

    # The cohort is a decision now, not an outstanding item; it stays listed as
    # outstanding only while the founder has not ruled on it.
    cohort = _cohort_decision(rows, by_key)
    if not cohort["records"]:
        outstanding["artifact_binding_only_cohort"] = \
            packet["artifact_binding_only_reattestation"]["cohort_size"]

    return OrderedDict([
        ("schema", "ptf-dayton-passB-founder-decisions/1.1"),
        ("work_order", WORK_ORDER),
        ("batches_recorded", list(DECISIONS)),
        ("market_id", MARKET),
        ("decided_by", FOUNDER),
        ("decided_at", DECIDED_AT),
        ("recorded_by",
         "claude-opus-5 (%s, agent) -- transcription only; the decisions are "
         "the founder's and no ruling was inferred, defaulted or completed by "
         "the agent" % WORK_ORDER),
        ("status", "RECORDED_NOT_APPLIED"),
        ("what_recorded_means",
         "The founder's rulings are on file and bound to the exact hashes they "
         "were shown. NOTHING has been applied: every Dayton record is still "
         "MACHINE_REVIEWED_PENDING_OPERATOR, no approval block was rewritten, "
         "and the policy package is byte-for-byte what Pass B committed. "
         "Applying these decisions -- turning each into an "
         "APPROVED_AFTER_CURRENT_REVIEW approval in the founder's name -- is a "
         "separate order that this pass was not given."),
        ("why_a_separate_file_from_the_packet",
         "The review packet is emitted by an idempotent generator, so "
         "re-running it would overwrite anything written into it. A human "
         "attestation must not live somewhere a regeneration can erase."),
        ("counts", OrderedDict([
            ("presented", len(rows)),
            ("approved", len(approved)),
            ("held", len(held)),
            ("applied", 0),
        ])),
        ("counts_by_batch", per_batch),
        ("still_outstanding", outstanding),
        ("artifact_only_cohort_decision", cohort),
        ("governance_rulings", [OrderedDict(g) for g in GOVERNANCE_RULINGS]),
        ("follow_ups", [OrderedDict(f) for f in FOLLOW_UPS]),
        ("decisions", rows),
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="write the decision ledger (still applies nothing "
                             "to the policy authority)")
    args = parser.parse_args()

    ledger = build()
    counts = ledger["counts"]
    print("batches recorded     : %s" % ", ".join(ledger["batches_recorded"]))
    print("presented            : %d" % counts["presented"])
    print("approved             : %d" % counts["approved"])
    print("held                 : %d" % counts["held"])
    print("applied to authority : %d" % counts["applied"])
    for batch, summary in ledger["counts_by_batch"].items():
        print("  batch %s: %d presented, %d approved, %d held"
              % (batch, summary["presented"], summary["approved"],
                 summary["held"]))
    for row in ledger["decisions"]:
        print("  %-8s %-1s %-42s %s" % (row["decision_id"], row["batch"],
                                        row["hotel"][:42],
                                        row["founder_decision"]))
    cohort = ledger["artifact_only_cohort_decision"]
    print("artifact-only cohort : %s (%d records, %d applied)"
          % (cohort["decision"], cohort["cohort_size"],
             sum(1 for r in cohort["records"] if r["applied_to_authority"])))
    print("total founder actions: %d policy + %d cohort = %d"
          % (len(ledger["decisions"]), cohort["cohort_size"],
             len(ledger["decisions"]) + cohort["cohort_size"]))
    for key, value in ledger["still_outstanding"].items():
        print("  outstanding %-32s %s" % (key, value))
    if not ledger["still_outstanding"]:
        print("  nothing outstanding: every published record has a decision")
    if args.apply:
        LEDGER_PATH.write_bytes(
            (json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        print("ledger written: %s" % LEDGER_PATH.name)
    else:
        print("dry run: nothing written (pass --apply to record the ledger)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
