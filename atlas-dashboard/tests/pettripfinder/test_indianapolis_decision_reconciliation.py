"""Recorded Indianapolis founder decisions: Hilton batch + full reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
HILTON = PACKAGE / "indianapolis_hilton_fresh_session_founder_decision_001.json"
RECON = PACKAGE / "indianapolis_decision_reconciliation_001.json"
APPLY = PACKAGE / "indianapolis_decision_application_001.json"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_hilton_decisions_recorded_not_applied():
    rec = _json(HILTON)
    assert rec["status"] == "RECORDED_NOT_APPLIED"
    assert rec["founder_decisions_applied"] is False
    assert rec["counts"]["positive_approved"] == 5
    assert rec["counts"]["identity_holds"] == 1
    assert rec["counts"]["decisions_applied"] == 0
    assert rec["counts"]["access_blocked"] == 0
    ids = [d["decision_id"] for d in rec["positive_decisions"]]
    assert ids == [
        "INDY-HFS-001", "INDY-HFS-002", "INDY-HFS-003",
        "INDY-HFS-004", "INDY-HFS-005",
    ]
    hgi = next(d for d in rec["positive_decisions"] if d["decision_id"] == "INDY-HFS-005")
    assert hgi["species"] == "ABSENT"
    assert hgi["accepted_identity"]["street"] == "8910 Hatfield Drive"
    cas = next(d for d in rec["positive_decisions"] if d["decision_id"] == "INDY-HFS-004")
    assert "weight_limit_stated_none" in cas["do_not_invent"]
    west = next(d for d in rec["positive_decisions"] if d["decision_id"] == "INDY-HFS-003")
    assert "$93.20" in west["approved_fields"][-1]
    hold = rec["identity_holds"][0]
    assert hold["decision"] == "HOLD_IDENTITY_UNCERTAIN"
    assert "9025 Hatfield" in hold["next_action"]
    assert _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")["published"] is True


def test_reconciliation_totals_and_application_live_published():
    recon = _json(RECON)
    tot = recon["totals"]
    assert tot["approved_positive_publications"] == 8
    assert tot["approved_verified_no_pets"] == 4
    assert tot["identity_holds"] == 7
    assert tot["decisions_applied"] == 12
    assert tot["remaining_unresolved_capture_ready_rows"] == 0
    assert tot["remaining_identity_repair_rows"] == 7
    assert recon["authority_live"]["published_pet_friendly"] == 8
    assert recon["authority_live"]["verified_no_pets"] == 4
    assert recon["approved_positive_publications"]["applied"] == 8
    assert recon["authority_live"]["unresolved"] == 141
    assert recon["approved_positive_publications"]["published"] is True
    assert recon["approved_verified_no_pets"]["applied"] == 4
    assert recon["approved_verified_no_pets"]["already_applied_before_this_order"] == [
        "INDY-P1-007"]
    assert recon["approved_verified_no_pets"]["applied_by_this_order"] == [
        "INDY-P2-003", "INDY-P2-004", "INDY-P2-006"]
    applied = [r["decision_id"] for r in recon["approved_verified_no_pets"]["rows"]
               if r["status"] == "APPLIED"]
    assert applied == [
        "INDY-P1-007", "INDY-P2-003", "INDY-P2-004", "INDY-P2-006"]
    app = _json(APPLY)
    assert app["work_order"] == "PTF-INDIANAPOLIS-DECISION-APPLICATION-001"
    assert app["executed"] is True
    assert app["status"] == "LIVE_PUBLISHED"
    assert app["published"] is True
    assert len(app["would_apply_positives"]) == 8
    assert len(app["would_apply_verified_no_pets"]) == 3
    assert app["already_applied"] == ["INDY-P1-007"]
    assert "INDY-HFS-006" in app["would_not_apply"]
    indy = [e for e in _json(PACKAGE / "hotel_exclusions.json")["exclusions"]
            if e.get("market_id") == "indianapolis-in"]
    # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004 promoted the founder-signed authority: 24 verified-no-pets exclusions.
    assert [e["normalized_name"] for e in indy] == [
        "comfort inn indianapolis airport plainfield",
        "courtyard by marriott indianapolis airport",
        "courtyard by marriott indianapolis at the capitol",
        "courtyard by marriott indianapolis downtown",
        "courtyard by marriott indianapolis fishers",
        "courtyard indianapolis noblesville",
        "courtyard indianapolis plainfield",
        "courtyard indianapolis west speedway",
        "crowne plaza indianapolis airport",
        "crowne plaza indianapolis downtown union station",
        "fairfield inn and suites indianapolis carmel",
        "fairfield inn and suites indianapolis downtown",
        "fairfield inn and suites indianapolis east",
        "holiday inn express and suites greenwood",
        "holiday inn express and suites indianapolis north carmel",
        "holiday inn express and suites indianapolis w airport area",
        "holiday inn express indianapolis downtown",
        "holiday inn express indianapolis fishers an ihg hotel",
        "holiday inn indianapolis downtown",
        "jw marriott indianapolis",
        "springhill suites by marriott indianapolis carmel",
        "springhill suites by marriott indianapolis westfield",
        "springhill suites indianapolis airport plainfield",
        "springhill suites indianapolis downtown",
    ]
