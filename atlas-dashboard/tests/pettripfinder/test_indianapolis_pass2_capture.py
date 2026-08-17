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
    assert counts["NEGATIVE"] == 3
    assert counts["IDENTITY_UNCERTAIN"] == 5
    packet = _json(PACKET)
    assert packet["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert packet["authority_changed"] is False
    assert len(packet["positive_candidates"]) == 2
    assert len(packet["negative_candidates"]) == 3
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


def test_strict_identity_gate_before_any_policy():
    results = _json(RESULTS)
    packet = _json(PACKET)
    assert results["founder_decisions_applied"] is False
    assert packet["founder_decisions_applied"] is False
    assert results["identity_gate"]["name"] == "STRICT_TWO_INDEPENDENT_NON_URL_KEYS"
    assert "URL ALONE IS NOT IDENTITY BINDING" in results["identity_gate"]["rule"]
    required = {"address@structured_metadata", "phone@structured_metadata"}
    for row in results["results"]:
        bind = row["identity_binding"]
        assert bind["gate"] == "STRICT_TWO_INDEPENDENT_NON_URL_KEYS"
        assert bind["url_identifier_used_as_bind"] is False
        intended = bind["intended"]
        assert intended["canonical_name"]
        assert intended["first_party_url"]
        assert intended["street"]
        assert intended["city"]
        assert intended["postal_code"]
        if row["outcome"] in ("AFFIRMATIVE_STRUCTURED", "NEGATIVE"):
            assert bind["bound"] is True
            assert bind["clean_bind"] is True
            assert required <= set(bind["independent_non_url_keys"])
            rendered = bind["rendered"]
            assert rendered["street"]
            assert rendered["postal_code"] == intended["postal_code"]
            assert rendered["source"] == "jsonld"
            assert row["proposed_schema_1_2_facts"]
            src = row["policy_source"]
            assert src["first_party"] is True
            assert src["sibling_or_brand_generic"] is False
        else:
            assert bind["bound"] is False
            assert bind.get("clean_bind") is False
            assert row["proposed_schema_1_2_facts"] == []
            assert row["exact_quotes"] == []
            assert row["policy_source"] is None


def test_url_code_is_not_treated_as_a_second_key():
    by = {r["identity_key"]: r for r in _json(RESULTS)["results"]}
    airport = by["courtyard by marriott indianapolis airport"]
    assert airport["outcome"] == "IDENTITY_UNCERTAIN"
    assert airport["identity_binding"]["independent_non_url_keys"] == [
        "phone@structured_metadata"]
    delta = by["delta hotels by marriott indianapolis airport"]
    assert delta["outcome"] == "IDENTITY_UNCERTAIN"
    hi = by["holiday inn indianapolis airport"]
    assert hi["outcome"] == "IDENTITY_UNCERTAIN"
    assert "404 Experience" in hi["notes"][0]
    assert hi["identity_binding"]["rendered"]["page_name"] == "404 Experience"
    jw = by["jw marriott indianapolis"]
    assert jw["outcome"] == "IDENTITY_UNCERTAIN"
    assert jw["recommended_founder_decision"] == "HOLD_RETRY_IDENTITY"
    assert jw["proposed_schema_1_2_facts"] == []
    assert jw["exact_quotes"] == []
    assert jw["identity_binding"]["clean_bind"] is False
    assert "did not bind cleanly" in jw["notes"][0]
    hie = by["holiday inn express plainfield"]
    assert hie["identity_binding"]["rendered"]["page_name"] == (
        "Holiday Inn Express Indianapolis Airport")
    assert hie["identity_binding"]["rendered"]["street"] == "6296 Cambridge Way"
    assert hie["identity_binding"]["rendered"]["phone"] == "1-317-8399000"


def test_retained_policy_is_first_party_property_specific():
    results = _json(RESULTS)
    assert "OTA text" in results["policy_authority"]["rejected"]
    assert "sibling-property policy" in results["policy_authority"]["rejected"]
    crowne = next(r for r in results["results"]
                  if r["identity_key"] == "crowne plaza indianapolis downtown union station")
    assert crowne["policy_source"]["kind"] == "property_specific_first_party_faq"
    assert "Airport" not in crowne["exact_quotes"][0]
    hie = next(r for r in results["results"]
               if r["identity_key"] == "holiday inn express plainfield")
    assert "not Holiday Inn Indianapolis Airport" in hie["identity_binding"]["notes"]
    for row in results["results"]:
        if row["outcome"] in ("AFFIRMATIVE_STRUCTURED", "NEGATIVE"):
            assert row["source_grade"] == "PT1_FIRST_PARTY"
            assert row["artifact_sha256"].startswith("sha256:")


def test_usable_observations_are_publication_grade():
    results = _json(RESULTS)
    required = results["artifact_standard"]["usable_observation_requires"]
    assert "artifact_sha256" in required
    assert "exact contiguous quote" in required
    assert "property identity binding" in required
    for row in results["results"]:
        if row["outcome"] not in ("AFFIRMATIVE_STRUCTURED", "NEGATIVE"):
            continue
        assert row["artifact_sha256"].startswith("sha256:")
        assert row["artifact_kind"] == "rendered_html"
        assert row["captured_at"]
        assert row["capture_method"] == "attended_browser"
        assert row["source_grade"] == "PT1_FIRST_PARTY"
        assert row["exact_quotes"]
        assert row["identity_binding"]["bound"] is True
        assert row["text_sha256"].startswith("sha256:")
        assert row["screenshot_sha256"].startswith("sha256:")
        for fact in row["proposed_schema_1_2_facts"]:
            assert fact["quote"]
            assert fact["quote_contiguous_in_artifact"] is True
            assert fact["quote"] in row["exact_quotes"]


def test_extraction_does_not_infer_species_or_fee_basis():
    results = _json(RESULTS)
    assert results["extraction_doctrine"]["rule"] == "SOURCE SILENCE = ABSENCE"
    by = {r["identity_key"]: r for r in results["results"]}
    mer = by["le meridien indianapolis"]
    mer_fields = {f["field"]: f for f in mer["proposed_schema_1_2_facts"]}
    assert "species" not in mer_fields
    assert any(w["field"] == "species" and w["reason"] == "SOURCE_SILENT"
               for w in mer["withheld_fields"])
    assert mer_fields["pet_fee"]["value"] == {"amount_cents": 0, "currency": "USD"}
    assert "basis" not in mer_fields["pet_fee"]["value"]
    hie = by["holiday inn express plainfield"]
    hie_fee = next(f for f in hie["proposed_schema_1_2_facts"] if f["field"] == "pet_fee")
    assert hie_fee["value"]["basis"] == "per_night"
    assert hie_fee["quote"] == "Pet fee per night: 25 USD"
    hie_species = next(f for f in hie["proposed_schema_1_2_facts"] if f["field"] == "species")
    assert hie_species["value"] == {"dogs": "allowed"}
    assert hie_species["quote"] == "Pets allowed: Only dogs allowed"
    castleton = by["courtyard by marriott indianapolis castleton"]
    assert castleton["service_animal_statements"][0]["treated_as_guest_pet_permission"] is False
    for row in (by["courtyard by marriott indianapolis castleton"],
                by["crowne plaza indianapolis downtown union station"],
                by["fairfield inn and suites indianapolis airport"]):
        fields = {f["field"] for f in row["proposed_schema_1_2_facts"]}
        assert fields == {"pets_allowed"}
