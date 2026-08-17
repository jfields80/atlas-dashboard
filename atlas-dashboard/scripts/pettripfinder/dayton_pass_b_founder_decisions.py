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
DECISION_ORDER = "DAYTON PASS B -- FOUNDER DECISIONS BATCH A"
DECIDED_AT = "2026-08-16"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
PACKET_PATH = LP / "dayton_passB_founder_review_packet.json"
LEDGER_PATH = LP / "dayton_passB_founder_decisions.json"

APPROVE = "APPROVE_CORRECTED_RECORD"
HOLD = "HOLD"

#: The founder's decisions, exactly as given. Nothing here is derived.
BATCH_A: Tuple[Tuple[str, str], ...] = (
    ("DAY-B01", APPROVE),
    ("DAY-B02", APPROVE),
    ("DAY-B03", APPROVE),
    ("DAY-B04", APPROVE),
    ("DAY-B05", APPROVE),
    ("DAY-B06", APPROVE),
)

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
}


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> Dict:
    packet = load_json(PACKET_PATH)
    facts = load_json(FACTS_PATH)
    by_key = {hotel["identity_key"]: hotel for hotel in facts["hotels"]}
    presented = {d["decision_id"]: d for d in packet["policy_decisions"]}

    decided = {decision_id for decision_id, _ in BATCH_A}
    expected = set(packet["batches"]["A_monetary"])
    if decided != expected:
        raise AssertionError(
            "Batch A is %s but decisions were given for %s; this module records "
            "the decisions it was given and never invents the rest"
            % (sorted(expected), sorted(decided)))

    rows: List[Dict] = []
    for decision_id, ruling in BATCH_A:
        if ruling not in (APPROVE, HOLD):
            raise AssertionError("%s: %r is not a decision" % (decision_id, ruling))
        row = presented[decision_id]
        hotel = by_key[row["identity_key"]]
        approval = hotel["approval"]

        # The decision binds the record it was given for, or it binds nothing.
        live_record = record_hash(hotel)
        live_evidence = evidence_hash(hotel["evidence"])
        for label, presented_value, live_value, stored_value in (
                ("record_hash", row["final_record_hash"], live_record,
                 approval["record_hash"]),
                ("evidence_hash", row["final_evidence_hash"], live_evidence,
                 approval["evidence_hash"])):
            if not presented_value == live_value == stored_value:
                raise AssertionError(
                    "%s: %s moved since the founder was shown it "
                    "(presented %s, live %s, on record %s). A decision given "
                    "for one record must not be recorded against another."
                    % (decision_id, label, presented_value[:23],
                       live_value[:23], stored_value[:23]))

        rows.append(OrderedDict([
            ("decision_id", decision_id),
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
        ]))

    approved = [r for r in rows if r["founder_decision"] == APPROVE]
    held = [r for r in rows if r["founder_decision"] == HOLD]

    return OrderedDict([
        ("schema", "ptf-dayton-passB-founder-decisions/1.0"),
        ("work_order", WORK_ORDER),
        ("decision_order", DECISION_ORDER),
        ("batch", "A"),
        ("market_id", MARKET),
        ("decided_by", FOUNDER),
        ("decided_at", DECIDED_AT),
        ("recorded_by",
         "claude-opus-5 (%s, agent) -- transcription only; the decisions are "
         "the founder's and no ruling was inferred, defaulted or completed by "
         "the agent" % WORK_ORDER),
        ("status", "RECORDED_NOT_APPLIED"),
        ("what_recorded_means",
         "The founder's ruling is on file and bound to the exact hashes they "
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
            ("presented", len(BATCH_A)),
            ("approved", len(approved)),
            ("held", len(held)),
            ("applied", 0),
        ])),
        ("remaining_batches", OrderedDict([
            ("B_service_animal_and_esa", packet["batches"]["B_service_animal_and_esa"]),
            ("C_pointer_repair", packet["batches"]["C_pointer_repair"]),
            ("artifact_binding_only_cohort",
             packet["artifact_binding_only_reattestation"]["cohort_size"]),
        ])),
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
    print("batch                : %s" % ledger["batch"])
    print("presented            : %d" % counts["presented"])
    print("approved             : %d" % counts["approved"])
    print("held                 : %d" % counts["held"])
    print("applied to authority : %d" % counts["applied"])
    for row in ledger["decisions"]:
        print("  %-8s %-44s %s" % (row["decision_id"], row["hotel"][:44],
                                   row["founder_decision"]))
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
