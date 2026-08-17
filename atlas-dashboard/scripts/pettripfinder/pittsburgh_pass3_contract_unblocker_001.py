"""Validate the Pass 3 compatibility unblocker and prepare application 001A.

This work order is deliberately non-authoritative: it validates existing
capture artifacts and writes a preparation report only.  It never writes
facts, exclusions, seeds, the partition, or approvals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.pettripfinder.contracts import evidence, policy_schema


ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"
PACKET_PATH = REPORTS / "pittsburgh_pass3_founder_review_packet.json"
PLAN_PATH = REPORTS / "pittsburgh_pass3_decision_application_plan.json"
OUT_PATH = REPORTS / "pittsburgh_pass3_decision_application_001a_plan.json"
FACTS_PATH = LP / "hotel_policy_facts_pittsburgh-pa.json"
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
PARTITION_PATH = LP / "pittsburgh_final_partition_001.json"
WORK_ORDER = "PTF-PITTSBURGH-PASS3-DECISION-APPLICATION-001A"

APPLIED_DECISIONS = {
    "PGH-P3-D001": "APPROVE_PUBLISH_STRUCTURED",
    "PGH-P3-D002": "APPROVE_PUBLISH_STRUCTURED",
    "PGH-P3-D003": "APPROVE_VERIFIED_NO_PETS",
    "PGH-P3-D004": "APPROVE_VERIFIED_NO_PETS",
    "PGH-P3-D006": "APPROVE_WITH_CHANGE",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def repair_lf_encoded_artifacts(packet: dict) -> int:
    """Restore LF bytes only when they reproduce the already-recorded hash."""
    repaired = 0
    for entry in packet["entries"]:
        for artifact in entry.get("artifacts", []):
            path = ROOT / artifact["artifact_file"]
            raw = path.read_bytes()
            lf = raw.replace(b"\r\n", b"\n")
            if raw != lf and "sha256:" + hashlib.sha256(lf).hexdigest() == artifact["artifact_sha256"]:
                path.write_bytes(lf)
                repaired += 1
    return repaired


def assert_current_authority(plan: dict) -> dict:
    current = plan["preconditions"]["current_authority"]
    paths = {
        "hotel_policy_facts_pittsburgh_pa": FACTS_PATH,
        "hotel_exclusions": EXCLUSIONS_PATH,
        "pittsburgh_final_partition": PARTITION_PATH,
    }
    for key, path in paths.items():
        assert sha(path) == current["authority_sha256"][key], key
    assert (current["published"], current["verified_no_pets"], current["unresolved"]) == (26, 4, 63)
    return current


def validate_entry(entry: dict) -> dict:
    assert entry["decision_id"] in APPLIED_DECISIONS
    assert entry["founder_decision"] == APPLIED_DECISIONS[entry["decision_id"]]
    assert entry["authority_application_status"] == "NOT_APPLIED"
    artifact = entry["artifacts"][0]
    artifact_path = ROOT / artifact["artifact_file"]
    assert sha(artifact_path) == artifact["artifact_sha256"]
    transcript = artifact_path.read_text(encoding="utf-8")
    quotes = [item["quote"] for item in entry["quotes"]]
    assert all(evidence.quote_is_contiguous(quote, transcript) for quote in quotes)
    probe = {
        "evidence_ref": "ev:pass3-probe-" + entry["decision_id"].lower(),
        "field": "policy_observation",
        "quote": quotes[0],
        "source_url": entry["final_url"],
        "value": "VALIDATED_ONLY",
        "artifact_class": entry["artifact_class"],
        **artifact,
    }
    issues = evidence.validate({"evidence": [probe]})
    assert not issues, issues
    return {
        "decision_id": entry["decision_id"],
        "hotel": entry["hotel"],
        "result": "CONTRACT_VALID_WITH_ALIAS",
        "artifact_sha256": artifact["artifact_sha256"],
        "raw_artifact_kind": artifact["artifact_kind"],
        "canonical_artifact_kind": evidence.canonical_artifact_kind(artifact["artifact_kind"]),
        "raw_source_grade": artifact["source_grade"],
        "canonical_source_grade": evidence.canonical_source_grade(artifact["source_grade"]),
    }


def validate_residence_shape(entry: dict) -> None:
    facts = dict(entry["proposed_schema_1_2_facts"])
    facts["other_charges"] = [{
        "kind": "cleaning_fee",
        "amount_cents": 25000,
        "currency": "USD",
        "conditional": True,
        "trigger": "Must sign waiver stating cats are neutered or a $250.00 cleaning fee may apply.",
    }]
    issues = policy_schema.validate_facts(facts)
    assert not issues, issues
    assert "refundable" not in facts["other_charges"][0]


def build() -> dict:
    packet = load(PACKET_PATH)
    plan = load(PLAN_PATH)
    assert packet["status"] == "FOUNDER_DECISIONS_RECORDED_NOT_APPLIED"
    authority = assert_current_authority(plan)
    entries = {entry["decision_id"]: entry for entry in packet["entries"]}
    assert set(entries) == set(APPLIED_DECISIONS) | {"PGH-P3-D005"}
    sunnyledge = entries["PGH-P3-D005"]
    assert sunnyledge["founder_decision"] == "NO_FOUNDER_POLICY_DECISION"
    assert sunnyledge["next_action"] == "RECAPTURE_REQUIRED"
    assert not sunnyledge["artifacts"]
    validate_residence_shape(entries["PGH-P3-D001"])
    artifacts = [validate_entry(entries[did]) for did in APPLIED_DECISIONS]
    assert len(artifacts) == 5
    return {
        "schema": "ptf-pittsburgh-pass3-decision-application-001a-plan/1.0",
        "work_order": WORK_ORDER,
        "market_id": "pittsburgh-pa",
        "status": "PREPARED_NOT_EXECUTED",
        "authority_changed": False,
        "authority_before_application": authority,
        "other_charges_refundability_rule": "OPTIONAL_IF_UNSTATED; absence means unknown and is never inferred. Conditional charges require their source-stated trigger.",
        "evidence_alias_rules": {
            "official_page_rendered_text": "rendered_html",
            "OFFICIAL_PROPERTY": "PT1_FIRST_PARTY",
        },
        "pass3_artifacts": artifacts,
        "recapture_required": ["Sunnyledge Boutique Hotel"],
        "oaklander_fee_state": "SOURCE_CONTRADICTORY",
        "application_direction_only": {
            "published_delta": 3,
            "verified_no_pets_delta": 2,
            "final_unresolved_count": "DERIVE_FROM_REBUILT_PARTITION_AT_APPLICATION",
        },
        "required_application_order": [
            "Construct final records and exclusions from the five recorded founder decisions only.",
            "Create approvals only after final record and evidence hashes are computed.",
            "Keep Sunnyledge unresolved with RECAPTURE_REQUIRED.",
            "Rebuild the partition and downstream outputs mechanically.",
        ],
        "non_actions": ["No authority applied.", "No merge.", "No deployment."],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write only the 001A preparation report.")
    parser.add_argument("--repair-artifact-encoding", action="store_true", help="Restore LF artifact bytes only when they match the recorded SHA-256.")
    args = parser.parse_args()
    if args.repair_artifact_encoding:
        repaired = repair_lf_encoded_artifacts(load(PACKET_PATH))
        print("PASS3 artifact LF encoding repaired: %d" % repaired)
    report = build()
    if args.apply:
        OUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS3 contract unblocker valid: 5/5 artifacts via aliases; authority unchanged 26/4/63; application 001A prepared only")


if __name__ == "__main__":
    main()
