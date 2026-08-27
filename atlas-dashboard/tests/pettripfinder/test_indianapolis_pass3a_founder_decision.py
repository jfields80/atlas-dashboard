"""PTF-INDIANAPOLIS-PASS3A-FOUNDER-DECISION-001 — recorded, not applied."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
DECISION = PACKAGE / "indianapolis_pass3a_founder_decision_001.json"
HILTON = PACKAGE / "indianapolis_hilton_fresh_session_001.json"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_residence_inn_decision_recorded_not_applied():
    rec = _json(DECISION)
    assert rec["status"] == "RECORDED_NOT_APPLIED"
    assert rec["founder_decisions_applied"] is False
    assert rec["authority_changed"] is False
    assert rec["counts"]["policy_decisions_recorded"] == 2
    assert rec["counts"]["positive_approved"] == 1
    assert rec["counts"]["identity_holds"] == 1
    assert rec["counts"]["undecided"] == 0
    assert rec["counts"]["decisions_applied"] == 0
    row = rec["positive_decisions"][0]
    assert row["decision_id"] == "INDY-P3A-001"
    assert row["decision"] == "APPROVE_PUBLISH_STRUCTURED"
    assert row["applied"] is False
    assert row["accepted_identity"]["street"] == "5224 West Southern Avenue"
    assert row["accepted_identity"]["phone"] == "317-244-1500"
    assert "pets_allowed" in row["approved_fields"]
    assert "pet_fee=$100 per_stay" in row["approved_fields"]
    assert "refundable=false" in row["approved_fields"]
    assert "weight_limit=75 lb" in row["approved_fields"]
    assert "pet_count_limit=2" in row["approved_fields"]
    assert "fee scope" in row["do_not_invent"]
    assert "weight scope" in row["do_not_invent"]
    assert "species" in row["do_not_invent"]
    assert "service-animal statement" in row["do_not_invent"]
    assert row["payment_timing"]["not"] == "reservation_requirement"
    assert "Fairfield at 5220" in row["note"]
    hold = rec["identity_holds"][0]
    assert hold["decision_id"] == "INDY-P3A-002"
    assert hold["decision"] == "HOLD_IDENTITY_UNCERTAIN"
    assert hold["lane"] == "identity-repair"
    assert hold["applied"] is False
    assert "street" in hold["next_action"].lower()
    assert rec["undecided"] == []
    assert _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")["published"] is True
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
    assert _json(PACKAGE / "indianapolis_pass2_founder_decision_001.json")[
        "status"] == "RECORDED_NOT_APPLIED"
    assert _json(HILTON)["executed"] is True
