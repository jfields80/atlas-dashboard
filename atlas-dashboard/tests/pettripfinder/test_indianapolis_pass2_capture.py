"""PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS2-001 packet gates."""

from __future__ import annotations

import json
from pathlib import Path

from pettripfinder.indianapolis_promoted_state import assert_exclusion_cohort_preserved

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
    OUTCOMES = {
        "AFFIRMATIVE_STRUCTURED", "AFFIRMATIVE_PARTIAL", "NEGATIVE",
        "POLICY_NOT_FOUND", "IDENTITY_UNCERTAIN", "ROUTING_PROBLEM",
        "ACCESS_BLOCKED", "CAPTURE_FAILED",
    }
    for row in results["results"]:
        assert row["identity_key"] == ptf_identity_key(row["hotel"])
        assert row["brand"] != "hilton"
        assert row["outcome"] in OUTCOMES
        assert row["official_url"]
        assert row["final_url"]
        assert "identity_signals" in row
        assert "recommended_founder_decision" in row


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
    assert _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")["published"] is True


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
    assert "fee scope" in results["extraction_doctrine"]["never_infer"]
    assert "refundability" in results["extraction_doctrine"]["never_infer"]
    by = {r["identity_key"]: r for r in results["results"]}
    mer = by["le meridien indianapolis"]
    mer_fields = {f["field"]: f for f in mer["proposed_schema_1_2_facts"]}
    assert "species" not in mer_fields
    assert any(w["field"] == "species" and w["reason"] == "SOURCE_SILENT"
               for w in mer["withheld_fields"])
    assert mer_fields["pet_fee"]["value"] == {"amount_cents": 0, "currency": "USD"}
    assert "basis" not in mer_fields["pet_fee"]["value"]
    assert "scope" not in mer_fields["pet_fee"]["value"]
    assert "refundable" not in mer_fields["pet_fee"]["value"]
    hie = by["holiday inn express plainfield"]
    hie_fee = next(f for f in hie["proposed_schema_1_2_facts"] if f["field"] == "pet_fee")
    assert hie_fee["value"]["basis"] == "per_night"
    assert "scope" not in hie_fee["value"]
    assert hie_fee["value"]["refundable"] is False
    assert hie_fee["quote"] == "Pet fee per night: 25 USD"
    assert hie_fee["refundability_quote"] == (
        "Dogs permitted with a nominal nonrefundable fee each night.")
    assert any(w["field"] == "pet_fee.scope" and w["reason"] == "SOURCE_SILENT"
               for w in hie["withheld_fields"])
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


def test_weight_fee_and_reservation_are_not_inferred():
    results = _json(RESULTS)
    never = results["extraction_doctrine"]["never_infer"]
    assert "combined weight as per-pet" in never
    assert "reservation requirement from payment timing" in never
    assert "exact price from up to or not to exceed" in never
    assert "other_charges" in results["extraction_doctrine"]["conditional_money"]
    assert "never general_restrictions" in results["extraction_doctrine"]["conditional_money"]
    by = {r["identity_key"]: r for r in results["results"]}
    mer_weight = next(f for f in by["le meridien indianapolis"]["proposed_schema_1_2_facts"]
                      if f["field"] == "weight_limit")
    assert "scope" not in mer_weight["value"]
    hie = by["holiday inn express plainfield"]
    assert not any(f["field"] == "reservation_requirement"
                   for f in hie["proposed_schema_1_2_facts"])
    fairfield = by["fairfield inn and suites indianapolis airport"]
    assert not any(f["field"] == "reservation_requirement"
                   for f in fairfield["proposed_schema_1_2_facts"])
    assert not any(f["field"] == "general_restrictions"
                   for f in fairfield["proposed_schema_1_2_facts"])
    assert any(w["field"] == "other_charges.cleaning_fee"
               and w["reason"] == "SOURCE_AMBIGUOUS"
               for w in fairfield["withheld_fields"])
    for row in results["results"]:
        for fact in row["proposed_schema_1_2_facts"]:
            quote = (fact.get("quote") or "").lower()
            if fact["field"] in ("pet_fee", "other_charges"):
                assert "up to" not in quote
                assert "not to exceed" not in quote
            assert fact["field"] != "general_restrictions"


def test_negatives_require_explicit_first_party_refusal():
    results = _json(RESULTS)
    assert "explicit first-party refusal" in results["negative_standard"]["rule"]
    negatives = [r for r in results["results"] if r["outcome"] == "NEGATIVE"]
    assert len(negatives) == 3
    for row in negatives:
        refusal = next(f for f in row["proposed_schema_1_2_facts"]
                       if f["field"] == "pets_allowed")
        assert refusal["value"] is False
        assert "not allowed" in refusal["quote"].lower()
        assert row["policy_source"]["first_party"] is True
        assert refusal["quote"] in row["exact_quotes"]
    castleton = next(r for r in negatives
                     if r["identity_key"] == "courtyard by marriott indianapolis castleton")
    assert castleton["proposed_schema_1_2_facts"][0]["quote"] == "Pets Not Allowed"
    assert "Service animals only" not in {
        f["quote"] for f in castleton["proposed_schema_1_2_facts"]}
    assert "Silence is not negative" in results["negative_standard"]["silence"]
    assert "do not convert" in results["negative_standard"]["service_animals"]


def test_crowne_downtown_is_not_airport_inheritance():
    results = _json(RESULTS)
    warn = results["crowne_downtown_warning"]
    assert "Crowne Plaza Indianapolis Airport" in warn["rule"]
    assert warn["downtown_identity_key"] == "crowne plaza indianapolis downtown union station"
    downtown = next(r for r in results["results"]
                    if r["identity_key"] == warn["downtown_identity_key"])
    assert downtown["outcome"] == "NEGATIVE"
    assert "Airport" not in downtown["exact_quotes"][0]
    assert "Dwtn-Union Stn" in downtown["exact_quotes"][0]


def test_authority_freeze_and_benchmark():
    results = _json(RESULTS)
    packet = _json(PACKET)
    freeze = results["authority_freeze"]
    assert freeze["capture_only"] is True
    assert freeze["published_pet_friendly"] == 0
    assert freeze["verified_no_pets"] == 1
    assert freeze["verified_no_pets_identity_key"] == "crowne plaza indianapolis airport"
    assert freeze["indianapolis_policy_facts_written"] is False
    assert freeze["exclusion_authority_altered"] is False
    assert packet["founder_decisions_applied"] is False
    assert packet["authority_changed"] is False
    assert packet["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")["published"] is True
    exclusions = _json(PACKAGE / "hotel_exclusions.json")
    indy = [e for e in exclusions["exclusions"]
            if e.get("market_id") == "indianapolis-in"]
    # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004 promoted the founder-signed authority: 24 verified-no-pets exclusions.
    assert_exclusion_cohort_preserved(indy)
    bench = results["speed_benchmark"]
    assert bench["total_elapsed_seconds"] == 1179.09
    assert bench["rows_attempted"] == 10
    assert bench["usable_artifacts"] == 5
    assert bench["positive_candidates"] == 2
    assert bench["negative_candidates"] == 3
    assert bench["identity_failures"] == 5
    assert bench["policy_not_found"] == 0
    assert bench["access_blocked"] == 0
    assert bench["captures_per_hour"] == 30.5
    assert bench["useful_artifact_yield"] == 0.5
    cmp_ = results["pass1_comparison"]
    assert cmp_["primary_metric"] == "USEFUL_ARTIFACT_YIELD"
    assert cmp_["pass1"]["useful_artifact_yield"] == 0.1
    assert cmp_["pass2"]["useful_artifact_yield"] == 0.5
    assert cmp_["pass2"]["usable_artifacts"] == 5
    assert cmp_["pass1"]["usable_artifacts"] == 1
    assert cmp_["pass2"]["captures_per_hour"] < cmp_["pass1"]["captures_per_hour"]
    assert cmp_["delta"]["usable_artifacts"] == 4
    assert results["brand_care"]["marriott"]["hotels"]
    assert results["brand_care"]["ihg"]["hotels"]
    assert results["brand_care"]["choice"]["hotels"] == [
        "Comfort Inn Airport Plainfield"]
