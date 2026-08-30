"""PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001 preparation gates."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports" / "pittsburgh_pass4_decision_application_001_plan.json"


def test_plan_is_prepared_not_executed_with_mechanical_expected_partition():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["status"] == "PREPARED_NOT_EXECUTED"
    assert plan["authority_changes_executed"] is False
    assert plan["authority_before"]["published"] == 29
    assert plan["authority_before"]["verified_no_pets"] == 6
    assert plan["authority_before"]["unresolved"] == 58
    assert plan["expected_authority_after"] == {
        "census": 96, "published": 37, "verified_no_pets": 8,
        "out_of_category": 3, "unresolved": 48}


def test_plan_has_all_decisions_with_bound_evidence_and_preserved_holds():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    decisions = plan["verified_no_pets_decisions"] + plan["publication_decisions"]
    assert len(decisions) == 10
    assert all(row["application_status"] == "NOT_EXECUTED" for row in decisions)
    assert all(row["artifact_binding"]["artifact_sha256"].startswith("sha256:") for row in decisions)
    by_id = {row["capture_id"]: row for row in decisions}
    assert by_id["PGH-P4-C009"]["other_charges"] == [{
        "kind": "cleaning_fee", "amount_cents": 10000, "currency": "USD",
        "conditional": True, "trigger": "7 - 30 nights"}]
    assert {row["hotel"]: row["state"] for row in plan["excluded_from_application"]} == {
        "Hyatt Regency Pittsburgh International Airport": "IDENTITY_UNCERTAIN",
        "Mansions on Fifth": "POLICY_NOT_FOUND",
        "Sunnyledge Boutique Hotel": "SOURCE_AMBIGUOUS"}
