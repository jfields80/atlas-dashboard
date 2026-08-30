"""Prepare, but never execute, Pittsburgh Pass 4 founder-decision application.

This verifier creates the immutable input plan for
PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001.  It deliberately does not
write market authority, approvals, seeds, exclusions, or partitions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"
PACKET = REPORTS / "pittsburgh_pass4_claude_founder_review_packet.json"
RESULTS = REPORTS / "pittsburgh_pass4_claude_capture_results.json"
PLAN = REPORTS / "pittsburgh_pass4_decision_application_001_plan.json"
PARTITION = LP / "pittsburgh_final_partition_001.json"
FACTS = LP / "hotel_policy_facts_pittsburgh-pa.json"
EXCLUSIONS = LP / "markets" / "authority" / "pittsburgh-pa" / "hotel_exclusions.json"

EXPECTED_DECISIONS = OrderedDict([
    ("PGH-P4-C001", "APPROVE_VERIFIED_NO_PETS"),
    ("PGH-P4-C002", "APPROVE_VERIFIED_NO_PETS"),
    ("PGH-P4-C003", "APPROVE_PARTIAL_PUBLICATION"),
    ("PGH-P4-C004", "APPROVE_WITH_CHANGE"),
    ("PGH-P4-C005", "APPROVE_PUBLISH_STRUCTURED"),
    ("PGH-P4-C006", "APPROVE_PUBLISH_STRUCTURED"),
    ("PGH-P4-C007", "APPROVE_WITH_CHANGE"),
    ("PGH-P4-C008", "APPROVE_WITH_CHANGE"),
    ("PGH-P4-C009", "APPROVE_WITH_CHANGE"),
    ("PGH-P4-C011", "APPROVE_WITH_CHANGE"),
])
EXCLUSION_IDS = {"PGH-P4-C001", "PGH-P4-C002"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def authority_counts() -> dict:
    facts = load(FACTS)
    exclusions = load(EXCLUSIONS)
    partition = load(PARTITION)
    states = Counter(item["final_state"] for item in partition["items"])
    return OrderedDict([
        ("census", len(partition["items"])),
        ("published", len(facts["hotels"])),
        ("verified_no_pets", sum(row["exclusion_state"] == "VERIFIED_NO_PETS" for row in exclusions["exclusions"])),
        ("out_of_category", sum(row["exclusion_state"] == "OUT_OF_CURRENT_CATEGORY" for row in exclusions["exclusions"])),
        ("unresolved", sum(count for state, count in states.items() if state.startswith("AWAITING_"))),
        ("policy_facts_sha256", sha256(FACTS)),
        ("exclusions_sha256", sha256(EXCLUSIONS)),
        ("partition_sha256", sha256(PARTITION)),
    ])


def validate_and_build() -> dict:
    packet = load(PACKET)
    results = load(RESULTS)
    assert packet["status"] == "ALL_FOUNDER_DECISIONS_RECORDED_APPLICATION_PREP_PENDING"
    assert packet["decisions_recorded"] == 10 and packet["decisions_applied"] == 0
    entries = {entry["capture_id"]: entry for entry in packet["entries"]}
    assert list(entries) == list(EXPECTED_DECISIONS)
    assert {key: entries[key]["founder_decision"] for key in EXPECTED_DECISIONS} == EXPECTED_DECISIONS
    assert all(entry["authority_application_status"] == "NOT_APPLIED" for entry in entries.values())
    assert all(entry["founder_review_required"] is False for entry in entries.values())

    captured = {item["capture_id"]: item for item in results["items"]}
    assert set(entries) <= set(captured)
    bindings = []
    for capture_id, entry in entries.items():
        source = captured[capture_id]
        assert entry["identity_key"] == source["identity_key"]
        artifact = entry["artifacts"][0]
        artifact_path = ROOT / artifact["artifact_file"]
        assert artifact_path.is_file(), f"missing durable evidence: {artifact_path}"
        assert sha256(artifact_path) == artifact["artifact_sha256"], capture_id
        artifact_text = artifact_path.read_text(encoding="utf-8")
        quotes = [quote["quote"] for quote in entry["quotes"]]
        assert all(quote in artifact_text for quote in quotes), capture_id
        bindings.append(OrderedDict([
            ("capture_id", capture_id),
            ("identity_key", entry["identity_key"]),
            ("artifact_sha256", artifact["artifact_sha256"]),
            ("identity_binding", entry["identity_binding"]),
            ("quotes_contiguous_in_artifact", True),
        ]))

    current = authority_counts()
    assert {key: current[key] for key in ("census", "published", "verified_no_pets", "out_of_category", "unresolved")} == {
        "census": 96, "published": 29, "verified_no_pets": 6, "out_of_category": 3, "unresolved": 58}
    partition = {item["identity_key"]: item for item in load(PARTITION)["items"]}
    assert all(not partition[entry["identity_key"]]["resolved"] for entry in entries.values())
    published_delta = len(entries) - len(EXCLUSION_IDS)
    no_pets_delta = len(EXCLUSION_IDS)
    expected = OrderedDict([
        ("census", current["census"]),
        ("published", current["published"] + published_delta),
        ("verified_no_pets", current["verified_no_pets"] + no_pets_delta),
        ("out_of_category", current["out_of_category"]),
    ])
    expected["unresolved"] = expected["census"] - expected["published"] - expected["verified_no_pets"] - expected["out_of_category"]
    assert expected == {"census": 96, "published": 37, "verified_no_pets": 8, "out_of_category": 3, "unresolved": 48}

    exclusions = []
    publications = []
    for capture_id, entry in entries.items():
        target = "verified_no_pets" if capture_id in EXCLUSION_IDS else "published_pet_friendly"
        target_list = exclusions if capture_id in EXCLUSION_IDS else publications
        target_list.append(OrderedDict([
            ("capture_id", capture_id),
            ("hotel", entry["hotel"]),
            ("identity_key", entry["identity_key"]),
            ("founder_decision", entry["founder_decision"]),
            ("target", target),
            ("approved_facts", entry["application_instruction"]["approved_facts"]),
            ("withheld_fields", entry["withheld_fields"]),
            ("other_charges", entry["proposed_schema_1_2_facts"].get("other_charges", [])),
            ("artifact_binding", next(binding for binding in bindings if binding["capture_id"] == capture_id)),
            ("application_status", "NOT_EXECUTED"),
        ]))
    return OrderedDict([
        ("schema", "ptf-pittsburgh-pass4-decision-application-plan/1.0"),
        ("work_order", "PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001"),
        ("market_id", "pittsburgh-pa"),
        ("status", "PREPARED_NOT_EXECUTED"),
        ("authority_before", current),
        ("expected_authority_after", expected),
        ("publication_decisions", publications),
        ("verified_no_pets_decisions", exclusions),
        ("excluded_from_application", [
            OrderedDict([("hotel", "Hyatt Regency Pittsburgh International Airport"), ("state", "IDENTITY_UNCERTAIN")]),
            OrderedDict([("hotel", "Mansions on Fifth"), ("state", "POLICY_NOT_FOUND")]),
            OrderedDict([("hotel", "Sunnyledge Boutique Hotel"), ("state", "SOURCE_AMBIGUOUS")]),
        ]),
        ("semantic_constraints", OrderedDict([
            ("sonesta", "Weight and breed restrictions are explicitly stated none; species and suite-to-room scope remain absent; duration tiers have no inferred fee basis."),
            ("hyatt_house", "Duration-tier amounts remain basis-absent; the included cleaning fee is not split into a synthetic charge."),
            ("hyatt_place_airport", "Pet fee remains SOURCE_AMBIGUOUS; advance-notice wording may be applied only if the canonical contract directly represents it."),
            ("hyatt_place_north_shore", "Both duration tier amounts remain basis-absent; $100 cleaning fee is conditional with its exact 7–30-night trigger and refundability absent."),
            ("joinery", "Pet fee remains SOURCE_CONTRADICTORY; no fee structure is selected."),
        ])),
        ("approval_requirements", [
            "Construct each final authority record before any founder approval binding.",
            "Bind final record_hash and evidence_hash after construction; require operator jfields80 and APPROVED_AFTER_CURRENT_REVIEW.",
            "Bind final evidence and founder-decision hashes for verified-no-pets exclusions.",
            "Reject stale approvals, agent-attributed human approvals, and post-signature mutation.",
        ]),
        ("authority_changes_executed", False),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write the plan only; authority is never written")
    args = parser.parse_args()
    plan = validate_and_build()
    if args.write:
        PLAN.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Prepared Pittsburgh Pass 4 application plan; authority unchanged")
    else:
        print(json.dumps({"status": plan["status"], "expected_authority_after": plan["expected_authority_after"]}, indent=1))


if __name__ == "__main__":
    main()
