"""PTF-LOUISVILLE-PASS1-FOUNDER-DECISIONS-001.

Applies only founder decisions that have been explicitly authorized.

Authorized so far:

- D001 21c Museum Hotel Louisville — HOLD_PARTIAL_AFFIRMATIVE

No other Pass 1 row is decided here. Do not infer packet recommendations.

    python -m scripts.pettripfinder.apply_louisville_pass1_founder_decisions
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, enums, partition

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
CENSUS_PATH = PKG / "identity_census" / "louisville-ky.json"
PARTITION_PATH = PKG / "louisville_final_partition_001.json"
RESULTS_PATH = PKG / "markets" / "reports" / "louisville_pass1_capture_results.json"
DECISIONS_PATH = PKG / "markets" / "reports" / "louisville_pass1_founder_decisions.json"
PACKET_PATH = PKG / "markets" / "reports" / "louisville_pass1_founder_review_packet.json"
WORK = "PTF-LOUISVILLE-PASS1-FOUNDER-DECISIONS-001"
AS_OF = "2026-08-16"


def main() -> None:
    census_doc = json.loads(CENSUS_PATH.read_text(encoding="utf-8-sig"))
    part_doc = json.loads(PARTITION_PATH.read_text(encoding="utf-8-sig"))
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8-sig"))
    items = {i["identity_key"]: i for i in part_doc["items"]}
    row21 = next(r for r in results["rows"]
                 if r["identity_key"] == "21c museum hotel louisville")

    item = items["21c museum hotel louisville"]
    item["final_state"] = enums.AWAITING_POLICY_OBSERVATION
    item["resolved"] = False
    item["next_action"] = (
        "Hold the captured partial facts. Do not publish until fee basis "
        "and scope are stated on the property page."
    )
    item["next_action_source"] = (
        "markets/reports/louisville_pass1_founder_decisions.json"
    )
    item["determined_by"] = WORK
    item["updated_at"] = AS_OF
    item["state_override_reason"] = (
        "D001 HOLD_PARTIAL_AFFIRMATIVE. Artifact, quotes, identity binding, "
        "and partial facts preserved. Not published."
    )

    rec = partition.reconcile(
        census.identity_keys(census_doc), part_doc, market_id="louisville-ky")
    if rec.published or rec.verified_no_pets:
        raise SystemExit("D001 must not publish or exclude")
    write_json(PARTITION_PATH, part_doc)

    decisions = OrderedDict((
        ("schema", "ptf-louisville-pass1-founder-decisions/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("operator", "jfields80"),
        ("note",
         "Only D001 has been authorized. No other Pass 1 row has a founder "
         "decision."),
        ("decisions", [OrderedDict((
            ("decision_id", "D001"),
            ("packet_id", "LVL-P1-001"),
            ("identity_key", "21c museum hotel louisville"),
            ("hotel", "21c Museum Hotel Louisville"),
            ("decision", "HOLD_PARTIAL_AFFIRMATIVE"),
            ("publish", False),
            ("preserved", OrderedDict((
                ("artifact_sha256", row21["artifact_sha256"]),
                ("artifact_relpath", row21["artifact_relpath"]),
                ("final_url", row21["final_url"]),
                ("identity_binding", row21["identity_binding"]),
                ("identity_signals", row21["identity_signals"]),
                ("exact_quotes", row21["quotes"]),
                ("captured_partial_facts", row21["proposed_facts"]),
                ("withheld_fields", row21["withheld_fields"]),
            ))),
            ("applied", True),
        ))]),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("unresolved", rec.unresolved),
        ("site_assembled", False),
        ("release_contract_written", False),
    ))
    write_json(DECISIONS_PATH, decisions)

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8-sig"))
    packet["founder_approvals_written"] = False
    packet["applied_work_order"] = WORK
    packet["note"] = (
        "Only D001 HOLD_PARTIAL_AFFIRMATIVE has been authorized. Other Pass 1 "
        "rows remain undecided. 21c is not published."
    )
    write_json(PACKET_PATH, packet)
    print("D001 HOLD_PARTIAL_AFFIRMATIVE applied. published", rec.published,
          "unresolved", rec.unresolved)


if __name__ == "__main__":
    main()
