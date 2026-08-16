"""PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS2-001 packet gates."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
RESULTS = PACKAGE / "indianapolis_pass2_capture_results.json"
PACKET = PACKAGE / "indianapolis_pass2_founder_review_packet.json"
QUEUE = PACKAGE / "indianapolis_capture_ready_queue_002.json"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_pass2_covers_exactly_the_ten_non_hilton_ready_rows():
    results = _json(RESULTS)
    assert results["rows_total"] == 10
    assert results["hilton_rows_driven"] == 0
    hotels = [r["identity_key"] for r in results["results"]]
    assert len(hotels) == 10
    assert "embassy suites by hilton indianapolis downtown" not in hotels
    ready = {h["hotel_id"] for h in _json(QUEUE)["hotels"]}
    assert set(hotels) <= ready
    for row in results["results"]:
        assert row["identity_key"] == ptf_identity_key(row["hotel"])
        assert row["brand"] != "hilton"


def test_outcome_counts_sum_to_ten_and_authority_untouched():
    counts = _json(RESULTS)["outcome_counts"]
    assert sum(counts.values()) == 10
    assert counts["AFFIRMATIVE_STRUCTURED"] == 2
    assert counts["NEGATIVE"] == 4
    assert counts["IDENTITY_UNCERTAIN"] == 4
    packet = _json(PACKET)
    assert packet["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert packet["authority_changed"] is False
    assert len(packet["positive_candidates"]) == 2
    assert len(packet["negative_candidates"]) == 4
    assert not (PACKAGE / "hotel_policy_facts_indianapolis-in.json").exists()


def test_crowne_downtown_refusal_is_independent_of_airport():
    row = next(r for r in _json(RESULTS)["results"]
               if r["identity_key"] == "crowne plaza indianapolis downtown union station")
    assert row["outcome"] == "NEGATIVE"
    quote = "No, pets are not allowed at Crowne Plaza Indianapolis-Dwtn-Union Stn."
    assert quote in row["exact_quotes"]
    assert "Airport" not in quote
    assert row["artifact_sha256"].startswith("sha256:")


def test_holiday_inn_express_and_le_meridien_are_the_positives():
    positives = {r["identity_key"]: r for r in _json(PACKET)["positive_candidates"]}
    assert set(positives) == {
        "holiday inn express plainfield",
        "le meridien indianapolis",
    }
    hie = positives["holiday inn express plainfield"]
    fields = {f["field"] for f in hie["proposed_schema_1_2_facts"]}
    assert "pets_allowed" in fields
    assert "species" in fields
    withheld = {w["field"] for w in hie["withheld_fields"]}
    assert "pet_fee.scope" in withheld
    mer = positives["le meridien indianapolis"]
    assert any(f["field"] == "pets_allowed" and f["value"] is True
               for f in mer["proposed_schema_1_2_facts"])
    assert any(w["field"] == "weight_limit.scope" for w in mer["withheld_fields"])
    assert any(w["field"] == "species" for w in mer["withheld_fields"])
