"""PTF-INDIANAPOLIS-ATTENDED-CAPTURE-001 -- Pass 1 packet gates."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
RESULTS = PACKAGE / "indianapolis_pass1_capture_results.json"
PACKET = PACKAGE / "indianapolis_pass1_founder_review_packet.json"
MARKET = "indianapolis-in"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_packets_exist_and_cover_exactly_ten():
    results = _json(RESULTS)
    packet = _json(PACKET)
    assert results["rows_total"] == 10
    assert len(results["results"]) == 10
    assert results["market_id"] == MARKET
    assert packet["status"] == "FOUNDER_DECIDED_NEGATIVE_APPLIED"
    assert packet["authority_changed"] is False


def test_outcome_counts_sum_to_ten():
    counts = _json(RESULTS)["outcome_counts"]
    assert sum(counts.values()) == 10
    assert counts["AFFIRMATIVE_STRUCTURED"] == 0
    assert counts["AFFIRMATIVE_PARTIAL"] == 0
    assert counts["NEGATIVE"] == 1
    assert counts["POLICY_NOT_FOUND"] == 0
    assert counts["IDENTITY_UNCERTAIN"] == 8
    assert counts["ROUTING_PROBLEM"] == 0
    assert counts["ACCESS_BLOCKED"] == 1
    assert counts["CAPTURE_FAILED"] == 0


def test_no_indianapolis_authority_was_written():
    assert _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")["published"] is True
    routing = _json(PACKAGE / "identity_routing.json")
    assert not [r for r in routing["routes"] if r.get("market_id") == MARKET]
    exclusions = _json(PACKAGE / "hotel_exclusions.json")
    records = exclusions["exclusions"] if isinstance(exclusions, dict) else exclusions
    indy = [e for e in records if e.get("market_id") == MARKET]
    # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: the promoted shard carries 24 exclusions under the generic ids.
    assert "ii-crowne-plaza-indianapolis-airport" in {
        e["exclusion_id"] for e in indy}
    assert len(indy) == 24


def test_negative_candidate_is_crowne_airport_with_contiguous_quote():
    results = _json(RESULTS)
    packet = _json(PACKET)
    negative = [r for r in results["results"] if r["outcome"] == "NEGATIVE"]
    assert len(negative) == 1
    row = negative[0]
    assert row["identity_key"] == ptf_identity_key(row["hotel"])
    assert row["identity_key"] == "crowne plaza indianapolis airport"
    assert row["artifact_kind"] == "rendered_html"
    assert row["artifact_sha256"].startswith("sha256:")
    quote = "No, pets are not allowed at Crowne Plaza Indianapolis-Airport."
    assert quote in row["exact_quotes"]
    facts = row["proposed_schema_1_2_facts"]
    assert facts == [{
        "field": "pets_allowed",
        "value": False,
        "quote": quote,
        "quote_contiguous_in_artifact": True,
    }]
    assert packet["positive_candidates"] == []
    assert packet["negative_candidates"][0]["decision_id"] == "INDY-P1-007"
    assert packet["negative_candidates"][0]["recommended_founder_decision"] == (
        "APPROVE_VERIFIED_NO_PETS")
    assert packet["negative_candidates"][0]["founder_decision"] == (
        "APPROVE_VERIFIED_NO_PETS")
    assert packet["negative_candidates"][0]["outcome"] == "APPLIED_VERIFIED_NO_PETS"


def test_every_row_has_a_founder_recommendation_and_no_approval():
    packet = _json(PACKET)
    results = _json(RESULTS)
    for row in results["results"]:
        assert row["recommended_founder_decision"]
        assert "founder_decision" not in row
        assert row["identity_key"] == ptf_identity_key(row["hotel"])
    assert packet.get("founder_decision") is None
    negative = packet["negative_candidates"][0]
    assert negative["founder_decision"] == "APPROVE_VERIFIED_NO_PETS"
