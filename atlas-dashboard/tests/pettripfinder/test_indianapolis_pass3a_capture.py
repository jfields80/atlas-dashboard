"""PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS3A-001 packet gates."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
RESULTS = PACKAGE / "indianapolis_pass3a_capture_results.json"
PACKET = PACKAGE / "indianapolis_pass3a_founder_review_packet.json"
QUEUE3 = PACKAGE / "indianapolis_capture_ready_queue_003.json"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_pass3a_covers_exactly_two_non_hilton_rows():
    results = _json(RESULTS)
    assert results["rows_total"] == 2
    assert results["hilton_rows_driven"] == 0
    keys = [r["identity_key"] for r in results["results"]]
    assert keys == [
        "residence inn by marriott indianapolis airport",
        "staybridge suites indianapolis airport plainfield",
    ]
    ready = {h["hotel_id"] for h in _json(QUEUE3)["hotels"]}
    assert set(keys) <= ready
    for row in results["results"]:
        assert row["identity_key"] == ptf_identity_key(row["hotel"])
        assert row["brand"] != "hilton"


def test_residence_inn_is_bound_and_not_a_sibling():
    row = next(r for r in _json(RESULTS)["results"]
               if r["identity_key"] == "residence inn by marriott indianapolis airport")
    assert row["outcome"] == "AFFIRMATIVE_STRUCTURED"
    bind = row["identity_binding"]
    assert bind["bound"] is True
    assert bind["rendered"]["street"] == "5224 West Southern Avenue"
    assert bind["rendered"]["phone"] == "+13172441500"
    assert "address@structured_metadata" in bind["independent_non_url_keys"]
    assert "phone@structured_metadata" in bind["independent_non_url_keys"]
    assert bind["url_identifier_used_as_bind"] is False
    facts = {f["field"]: f for f in row["proposed_schema_1_2_facts"]}
    assert facts["pets_allowed"]["value"] is True
    assert facts["pet_fee"]["value"]["amount_cents"] == 10000
    assert facts["pet_fee"]["value"]["basis"] == "per_stay"
    assert facts["pet_fee"]["value"]["refundable"] is False
    assert "scope" not in facts["pet_fee"]["value"]
    assert facts["weight_limit"]["value"]["value"] == 75.0
    assert "scope" not in facts["weight_limit"]["value"]
    assert facts["pet_count_limit"]["value"] == 2
    assert facts["pet_count_scope"]["value"] == "per_room"
    assert "species" not in facts
    assert row["artifact_sha256"].startswith("sha256:")
    assert "5220" not in row["identity_binding"]["rendered"]["street"]


def test_staybridge_identity_failed_has_no_policy():
    row = next(r for r in _json(RESULTS)["results"]
               if r["identity_key"] == "staybridge suites indianapolis airport plainfield")
    assert row["outcome"] == "IDENTITY_UNCERTAIN"
    assert row["proposed_schema_1_2_facts"] == []
    assert row["exact_quotes"] == []
    assert row["identity_binding"]["bound"] is False


def test_pass3a_authority_untouched():
    results = _json(RESULTS)
    packet = _json(PACKET)
    assert results["founder_decisions_applied"] is False
    assert packet["founder_decisions_applied"] is False
    assert packet["authority_changed"] is False
    assert packet["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert packet["hilton_remaining"] == 6
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
        "founder_decisions_applied"] is False
    assert _json(PACKAGE / "indianapolis_pass2_founder_decision_001.json")[
        "status"] == "RECORDED_NOT_APPLIED"


def test_residence_inn_quotes_are_contiguous_and_artifact_complete():
    row = next(r for r in _json(RESULTS)["results"]
               if r["identity_key"] == "residence inn by marriott indianapolis airport")
    for field in ("artifact_sha256", "artifact_kind", "captured_at",
                  "capture_method", "source_grade"):
        assert row[field]
    assert row["identity_binding"]["bound"] is True
    for quote in row["exact_quotes"]:
        assert quote
    for fact in row["proposed_schema_1_2_facts"]:
        assert fact["quote_contiguous_in_artifact"] is True
        assert fact["quote"] in row["exact_quotes"]
    assert "CEILING != PRICE" in _json(RESULTS)["extraction_doctrine"]["rule"]


def test_hilton_fresh_session_queue_is_hilton_only():
    hilton = _json(PACKAGE / "indianapolis_hilton_fresh_session_001.json")
    assert hilton["work_order"] == "PTF-INDIANAPOLIS-HILTON-FRESH-SESSION-001"
    assert hilton["require_fresh_browser_session"] is True
    assert hilton["no_prior_hilton_page_load"] is True
    assert len(hilton["hotels"]) == 6
    assert all(h["brand"] == "hilton" for h in hilton["hotels"])
    assert _json(PACKET)["hilton_next_batch"] == (
        "indianapolis_hilton_fresh_session_001.json")
    driven = {r["identity_key"] for r in _json(RESULTS)["results"]}
    assert driven.isdisjoint({h["hotel_id"] for h in hilton["hotels"]})
