"""PTF-INDIANAPOLIS-PASS2-FOUNDER-DECISION-001 — recorded, not applied."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
DECISION = PACKAGE / "indianapolis_pass2_founder_decision_001.json"
QUEUE3 = PACKAGE / "indianapolis_capture_ready_queue_003.json"
QUEUE2 = PACKAGE / "indianapolis_capture_ready_queue_002.json"
RESULTS = PACKAGE / "indianapolis_pass2_capture_results.json"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_decisions_are_recorded_and_not_applied():
    rec = _json(DECISION)
    assert rec["status"] == "RECORDED_NOT_APPLIED"
    assert rec["founder_decisions_applied"] is False
    assert rec["authority_changed"] is False
    assert rec["counts"]["policy_decisions_recorded"] == 5
    assert rec["counts"]["positive_approved"] == 2
    assert rec["counts"]["verified_no_pets_approved"] == 3
    assert rec["counts"]["identity_holds"] == 5
    assert rec["counts"]["decisions_applied"] == 0
    assert all(d["applied"] is False for d in rec["positive_decisions"])
    assert all(d["applied"] is False for d in rec["negative_decisions"])
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


def test_approved_fields_match_founder_limits():
    rec = _json(DECISION)
    hie = next(d for d in rec["positive_decisions"]
               if d["decision_id"] == "INDY-P2-007")
    assert hie["decision"] == "APPROVE_PUBLISH_STRUCTURED"
    assert "pet_count_scope" in hie["do_not_invent"]
    assert hie["accepted_identity"]["street"] == "6296 Cambridge Way"
    mer = next(d for d in rec["positive_decisions"]
               if d["decision_id"] == "INDY-P2-010")
    assert "species" in mer["do_not_invent"]
    downtown = next(d for d in rec["negative_decisions"]
                    if d["decision_id"] == "INDY-P2-004")
    assert downtown["do_not_inherit_from"] == "crowne plaza indianapolis airport"
    assert "Airport" not in downtown["evidence_quote"]
    holds = {h["identity_key"]: h for h in rec["identity_holds"]}
    assert set(holds) == {
        "comfort inn indianapolis airport plainfield",
        "courtyard by marriott indianapolis airport",
        "delta hotels by marriott indianapolis airport",
        "holiday inn indianapolis airport",
        "jw marriott indianapolis",
    }
    for hold in holds.values():
        assert hold["decision"] == "HOLD_IDENTITY_UNCERTAIN"
        assert hold["lane"] == "identity-repair"
        assert hold["next_action"]


def test_remaining_eight_queue_is_prepared_not_executed():
    q3 = _json(QUEUE3)
    q2 = {h["hotel_id"] for h in _json(QUEUE2)["hotels"]}
    driven = {r["identity_key"] for r in _json(RESULTS)["results"]}
    remaining = {h["hotel_id"] for h in q3["hotels"]}
    assert q3["executed"] is False
    assert len(q3["hotels"]) == 8
    assert remaining == q2 - driven
    assert q3["split"] == {"hilton_family": 6, "marriott_or_other_non_hilton": 2}
    hilton = [h for h in q3["hotels"] if h["family"] == "hilton"]
    other = [h for h in q3["hotels"] if h["family"] != "hilton"]
    assert len(hilton) == 6
    assert {h["brand"] for h in other} == {"marriott", "ihg"}
    assert q3["recommendation"]["hilton_own_session"] is True
    for hotel in q3["hotels"]:
        assert hotel["hotel_id"] == ptf_identity_key(hotel["hotel_name"])
        assert "Do not execute" in hotel["notes"]
