"""PTF-INDIANAPOLIS-HILTON-FRESH-SESSION-001 packet gates."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
RESULTS = PACKAGE / "indianapolis_hilton_fresh_session_results.json"
PACKET = PACKAGE / "indianapolis_hilton_fresh_session_review_packet.json"
QUEUE = PACKAGE / "indianapolis_hilton_fresh_session_001.json"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_hilton_batch_is_exactly_six_hilton_rows():
    results = _json(RESULTS)
    assert results["rows_total"] == 6
    assert results["non_hilton_rows_driven"] == 0
    assert results["fresh_session"] is True
    keys = [r["identity_key"] for r in results["results"]]
    assert keys == [
        "hampton inn and suites indianapolis airport",
        "hampton inn and suites indianapolis keystone",
        "hampton inn and suites indianapolis west speedway",
        "hampton inn indianapolis northeast castleton",
        "hilton garden inn indianapolis airport",
        "home2 suites by hilton indianapolis airport",
    ]
    for row in results["results"]:
        assert row["brand"] == "hilton"
        assert row["identity_key"] == ptf_identity_key(row["hotel"])


def test_outcome_counts_and_home2_is_uncertain():
    counts = _json(RESULTS)["outcome_counts"]
    assert counts["AFFIRMATIVE_STRUCTURED"] == 5
    assert counts["NEGATIVE"] == 0
    assert counts["IDENTITY_UNCERTAIN"] == 1
    assert counts["ACCESS_BLOCKED"] == 0
    home2 = next(r for r in _json(RESULTS)["results"]
                 if r["identity_key"] == "home2 suites by hilton indianapolis airport")
    assert home2["outcome"] == "IDENTITY_UNCERTAIN"
    assert home2["proposed_schema_1_2_facts"] == []
    assert home2["exact_quotes"] == []


def test_bound_rows_have_artifacts_and_no_inferred_species_on_garden_inn():
    by = {r["identity_key"]: r for r in _json(RESULTS)["results"]}
    air = by["hampton inn and suites indianapolis airport"]
    assert air["identity_binding"]["rendered"]["street"] == "9020 Hatfield Drive"
    assert air["artifact_sha256"].startswith("sha256:")
    assert any(f["field"] == "species" for f in air["proposed_schema_1_2_facts"])
    hgi = by["hilton garden inn indianapolis airport"]
    assert hgi["identity_binding"]["rendered"]["street"] == "8910 Hatfield Dr."
    assert not any(f["field"] == "species" for f in hgi["proposed_schema_1_2_facts"])
    assert any(w["field"] == "species" for w in hgi["withheld_fields"])
    for row in by.values():
        if row["outcome"].startswith("AFFIRMATIVE"):
            assert row["source_grade"] == "PT1_FIRST_PARTY"
            assert all(f.get("quote_contiguous_in_artifact")
                       for f in row["proposed_schema_1_2_facts"])


def test_hilton_authority_untouched():
    results = _json(RESULTS)
    packet = _json(PACKET)
    assert results["founder_decisions_applied"] is False
    assert packet["founder_decisions_applied"] is False
    assert packet["authority_changed"] is False
    assert packet["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert results["authority_freeze"]["pass2_decisions_applied"] is False
    assert results["authority_freeze"]["pass3a_decisions_applied"] is False
    assert _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")["published"] is False
    indy = [e for e in _json(PACKAGE / "hotel_exclusions.json")["exclusions"]
            if e.get("market_id") == "indianapolis-in"]
    assert [e["normalized_name"] for e in indy] == [
        "crowne plaza indianapolis airport",
        "courtyard by marriott indianapolis castleton",
        "crowne plaza indianapolis downtown union station",
        "fairfield inn and suites indianapolis airport",
    ]
    assert _json(QUEUE)["executed"] is True
    assert _json(QUEUE)["require_fresh_browser_session"] is True
