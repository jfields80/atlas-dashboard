"""PTF-PITTSBURGH-PASS3-DECISION-APPLICATION-001A final authority gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.pettripfinder.policy_migration import evidence_hash, record_hash


ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_pass3_report_reconciles_the_derived_partition_counts():
    report = load(REPORTS / "pittsburgh_pass3_application_001a_report.json")
    assert report["authority_before"] == {"published": 26, "verified_no_pets": 4, "unresolved": 63,
                                           "authority_sha256": report["authority_before"]["authority_sha256"]}
    assert report["authority_after"] == {"published": 29, "verified_no_pets": 6, "unresolved": 58}
    assert report["published_decisions"] == ["PGH-P3-D001", "PGH-P3-D002", "PGH-P3-D006"]
    assert report["exclusion_decisions"] == ["PGH-P3-D003", "PGH-P3-D004"]
    assert report["not_applied"] == ["PGH-P3-D005"]


def test_final_records_preserve_each_founder_ruling_and_governance():
    facts = {r["identity_key"]: r for r in load(LP / "hotel_policy_facts_pittsburgh-pa.json")["hotels"]}
    residence = facts["residence inn pittsburgh north shore"]
    charge = residence["facts"]["other_charges"][0]
    assert charge == {"kind": "cleaning_fee", "amount_cents": 25000, "currency": "USD", "conditional": True,
                      "trigger": "Must sign waiver stating cats are neutered or a $250.00 cleaning fee may apply."}
    assert residence["facts"]["pet_fee"] == {"amount_cents": 10000, "currency": "USD", "basis": "per_stay", "refundable": False}
    sheraton = facts["sheraton pittsburgh hotel at station square"]
    assert sheraton["facts"]["species"] == {"dogs": "accepted"}
    oaklander = facts["the oaklander hotel autograph collection"]
    assert "pet_fee" not in oaklander["facts"]
    assert oaklander["withheld_fields"]["pet_fee"]["reason_code"] == "SOURCE_CONTRADICTORY"
    for record in (residence, sheraton, oaklander):
        approval = record["approval"]
        assert approval["operator"] == "jfields80"
        assert approval["decision"] == "APPROVED_AFTER_CURRENT_REVIEW"
        assert approval["record_hash"] == record_hash(record)
        assert approval["evidence_hash"] == evidence_hash(record["evidence"])


def test_refusals_and_sunnyledge_keep_their_distinct_states():
    exclusions = [r for r in load(LP / "hotel_exclusions.json")["exclusions"] if r.get("market_id") == "pittsburgh-pa"]
    by_name = {r["normalized_name"]: r for r in exclusions}
    for name, did in {"springhill suites pittsburgh bakery square": "PGH-P3-D003", "springhill suites pittsburgh north shore": "PGH-P3-D004"}.items():
        record = by_name[name]
        assert record["exclusion_state"] == "VERIFIED_NO_PETS"
        assert record["founder_decision_id"] == did
        binding = {"record_hash": record["record_hash"], "approval_hash": record["approval_hash"],
                   "source_hash": record["source_hash"], "founder_decision_id": did,
                   "founder_decision_hash": record["founder_decision_hash"]}
        assert record["founder_evidence_binding_hash"] == "sha256:" + hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
    partition = {r["identity_key"]: r for r in load(LP / "pittsburgh_final_partition_001.json")["items"]}
    assert partition["sunnyledge boutique hotel"]["final_state"] == "AWAITING_POLICY_OBSERVATION"
    packet = load(REPORTS / "pittsburgh_pass3_founder_review_packet.json")
    sunnyledge = next(r for r in packet["entries"] if r["decision_id"] == "PGH-P3-D005")
    assert sunnyledge["outcome"] == "RECAPTURE_REQUIRED"
