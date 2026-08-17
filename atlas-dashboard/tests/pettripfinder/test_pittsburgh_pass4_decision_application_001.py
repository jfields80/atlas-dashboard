"""PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001 final authority gates."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.policy_migration import evidence_hash, record_hash


ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_final_partition_derives_the_ten_decision_transitions():
    partition = load(LP / "pittsburgh_final_partition_001.json")
    assert partition["count"] == 96
    assert partition["final_state_counts"] == {
        "AWAITING_IDENTITY_RESOLUTION": 38, "AWAITING_CENSUS_REVIEW": 3,
        "AWAITING_OFFICIAL_URL": 3, "AWAITING_PROPERTY_LEVEL_URL": 1,
        "AWAITING_POLICY_OBSERVATION": 3, "PUBLISHED_PET_FRIENDLY": 37,
        "VERIFIED_NO_PETS": 8, "OUT_OF_CURRENT_CATEGORY": 3}
    states = {row["identity_key"]: row for row in partition["items"]}
    assert states["courtyard by marriott pittsburgh airport"]["final_state"] == "VERIFIED_NO_PETS"
    assert states["courtyard by marriott pittsburgh airport settlers ridge"]["final_state"] == "VERIFIED_NO_PETS"
    assert all(not states[key]["resolved"] for key in (
        "hyatt regency pittsburgh international airport", "mansions on fifth",
        "sunnyledge boutique hotel"))


def test_final_records_preserve_the_special_founder_semantics_and_governance():
    facts = {row["identity_key"]: row for row in load(LP / "hotel_policy_facts_pittsburgh-pa.json")["hotels"]}
    assert len(facts) == 37
    sonesta = facts["sonesta simply suites pittsburgh airport"]
    assert sonesta["facts"]["weight_limit_stated_none"] is True
    assert sonesta["facts"]["breed_restrictions_stated_none"] is True
    assert "species" not in sonesta["facts"]
    assert "basis" not in sonesta["facts"]["fee_tiers"][0]
    airport = facts["hyatt place pittsburgh airport"]
    assert "pet_fee" not in airport["facts"]
    assert airport["withheld_fields"]["pet_fee"]["reason_code"] == "SOURCE_AMBIGUOUS"
    north = facts["hyatt place pittsburgh north shore"]
    assert north["facts"]["other_charges"] == [{
        "kind": "cleaning_fee", "amount_cents": 10000, "currency": "USD",
        "conditional": True, "trigger": "7 - 30 nights"}]
    assert "refundable" not in north["facts"]["other_charges"][0]
    joinery = facts["joinery hotel pittsburgh"]
    assert "pet_fee" not in joinery["facts"]
    assert joinery["withheld_fields"]["pet_fee"]["reason_code"] == "SOURCE_CONTRADICTORY"
    for key in ("motel 6 pittsburgh", "sonesta simply suites pittsburgh airport",
                "springhill suites pittsburgh airport", "towneplace suites pittsburgh airport robinson township",
                "hyatt house pittsburgh bloomfield shadyside", "hyatt place pittsburgh airport",
                "hyatt place pittsburgh north shore", "joinery hotel pittsburgh"):
        approval = facts[key]["approval"]
        assert approval["operator"] == "jfields80"
        assert approval["decision"] == "APPROVED_AFTER_CURRENT_REVIEW"
        assert approval["record_hash"] == record_hash(facts[key])
        assert approval["evidence_hash"] == evidence_hash(facts[key]["evidence"])


def test_application_report_and_packet_bind_exactly_ten_decisions():
    report = load(REPORTS / "pittsburgh_pass4_application_001_report.json")
    packet = load(REPORTS / "pittsburgh_pass4_claude_founder_review_packet.json")
    assert report["authority_before"] == {
        "published": 29, "verified_no_pets": 6, "out_of_category": 3, "unresolved": 58}
    assert report["authority_after"] == {
        "published": 37, "verified_no_pets": 8, "out_of_category": 3, "unresolved": 48}
    assert len(report["published_decisions"]) == 8
    assert len(report["exclusion_decisions"]) == 2
    assert packet["decisions_recorded"] == packet["decisions_applied"] == 10
    assert all(row["authority_application_status"] == "APPLIED" for row in packet["entries"])
