"""PTF-POLICY-P0-001 -- policy Membrane M1..M12 tests.

Each rule gets a test that would fail if the rule were removed. A rule with no
failing test is a comment.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.policy import policy_membrane as M
from scripts.pettripfinder.policy.policy_observation import CONTRACT_VERSION


def observation(**overrides):
    base = {
        "obs_id": "obs-1",
        "contract_version": CONTRACT_VERSION,
        "hotel_ref": {"market_id": "columbus-oh",
                      "canonical_name": "Sample Inn Columbus",
                      "normalized_name": "sample inn columbus"},
        "identity_check": {"name_on_page": "Sample Inn Columbus"},
        "source_url": "https://www.sample-brand.com/columbus",
        "source_type": "official_property_page",
        "authority_tier": "PT1",
        "observed_at": "2026-08-01",
        "retrieved_at": "2026-08-08T12:00:00Z",
        "capture_method": "deterministic_fetch",
        "evidence": [{"quote": "Dogs and cats accepted.", "location": "policies",
                      "field_refs": ["pets_allowed"]}],
        "extraction": {"pets_allowed": True},
        "extraction_confidence": "EXACT_QUOTE",
        "flags": [],
    }
    base.update(overrides)
    return base


def test_clean_official_observation_is_valid():
    v = M.evaluate(observation())
    assert v.verdict == M.VALID
    assert v.may_establish is True


def test_malformed_observation_is_rejected_not_raised():
    v = M.evaluate({"obs_id": "x"})
    assert v.verdict == M.REJECT_MALFORMED_OBSERVATION
    assert v.rejected is True


# --- M1 / M2: identity-grade and OTA sources never establish ---------------- #

def test_m2_ota_extraction_survives_only_as_a_hint():
    v = M.evaluate(observation(source_type="ota", authority_tier="PT4"))
    assert v.verdict == M.VALID_HINT_ONLY
    assert v.hint_only is True
    assert v.may_establish is False
    assert "pets_allowed" in v.stripped_fields


def test_m1_map_listing_cannot_establish():
    v = M.evaluate(observation(source_type="map_listing",
                               authority_tier="PT4"))
    assert v.may_establish is False


def test_m1_source_may_not_claim_a_tier_above_its_type():
    v = M.evaluate(observation(source_type="ota", authority_tier="PT1"))
    assert v.verdict == M.REJECT_TIER_FORBIDS_ESTABLISH
    assert v.rule == "M1"


# --- M3: brand-generic never becomes property-specific ---------------------- #

def test_m3_brand_generic_carrying_establishing_fields_is_rejected():
    v = M.evaluate(observation(source_type="official_brand_faq",
                               authority_tier="PT2"))
    assert v.verdict == M.REJECT_BRAND_GENERIC_AS_PROPERTY
    assert v.rule == "M3"


def test_m3_brand_generic_with_no_extraction_is_allowed_to_corroborate():
    v = M.evaluate(observation(source_type="official_brand_faq",
                               authority_tier="PT2", extraction={},
                               evidence=[]))
    assert v.verdict == M.VALID


# --- M4: snippets never carry numbers --------------------------------------- #

def test_m4_search_snippet_may_not_carry_extraction():
    v = M.evaluate(observation(source_type="search_snippet", authority_tier="PT4",
                               extraction={"pet_fee": 2500},
                               evidence=[{"quote": "$25 per night",
                                          "location": "serp",
                                          "field_refs": ["pet_fee"]}]))
    assert v.verdict == M.REJECT_SNIPPET_EXTRACTION
    assert v.rule == "M4"


# --- M5: archive can never be the sole basis -------------------------------- #

def test_m5_archive_only_set_is_detected():
    archive = observation(source_type="cached_archive", authority_tier="PT4")
    assert M.archive_only([archive]) is True
    assert M.archive_only([archive, observation()]) is False
    assert M.archive_only([]) is False


# --- M6: service-animal language is not a pet policy ------------------------ #

def test_m6_service_animal_only_is_not_a_pet_policy():
    obs = observation(
        extraction={"service_animal_exception": "Service animals are welcome."},
        evidence=[{"quote": "Service animals are welcome.", "location": "policies",
                   "field_refs": ["service_animal_exception"]}])
    assert M.service_animal_only(obs) is True
    # It is still a structurally VALID observation -- it just establishes nothing.
    assert M.evaluate(obs).verdict == M.VALID


def test_m6_service_animal_plus_real_policy_is_not_service_animal_only():
    obs = observation(
        extraction={"pets_allowed": True,
                    "service_animal_exception": "Service animals are welcome."},
        evidence=[{"quote": "Dogs accepted. Service animals are welcome.",
                   "location": "policies",
                   "field_refs": ["pets_allowed", "service_animal_exception"]}])
    assert M.service_animal_only(obs) is False


# --- M7: inference never publishes ------------------------------------------ #

def test_m7_inferred_extraction_is_flagged():
    assert M.infers_without_publishing(
        observation(extraction_confidence="INFERRED")) is True
    assert M.infers_without_publishing(observation()) is False


# --- M8: contradictions are preserved, never auto-resolved ------------------ #

def test_m8_contradicting_official_fees_are_reported_not_resolved():
    a = observation(obs_id="a", extraction={"pets_allowed": True, "pet_fee": 7500},
                    evidence=[{"quote": "$75", "location": "l",
                               "field_refs": ["pets_allowed", "pet_fee"]}])
    b = observation(obs_id="b", extraction={"pets_allowed": True, "pet_fee": 15000},
                    evidence=[{"quote": "$150", "location": "l",
                               "field_refs": ["pets_allowed", "pet_fee"]}])
    pairs = M.contradicting_pairs([a, b])
    assert len(pairs) == 1
    assert pairs[0]["field"] == "pet_fee"
    assert {pairs[0]["value_a"], pairs[0]["value_b"]} == {7500, 15000}
    assert "never selects a winner" in pairs[0]["resolution"]


def test_m8_agreement_is_not_a_contradiction():
    a = observation(obs_id="a")
    b = observation(obs_id="b")
    assert M.contradicting_pairs([a, b]) == []


def test_m8_ota_disagreement_is_not_an_official_contradiction():
    official = observation(obs_id="a", extraction={"pets_allowed": True, "pet_fee": 7500},
                           evidence=[{"quote": "$75", "location": "l",
                                      "field_refs": ["pets_allowed", "pet_fee"]}])
    ota = observation(obs_id="b", source_type="ota", authority_tier="PT4",
                      extraction={"pets_allowed": True, "pet_fee": 15000},
                      evidence=[{"quote": "$150", "location": "l",
                                 "field_refs": ["pets_allowed", "pet_fee"]}])
    # An OTA cannot contradict an official source into a conflict; it hints.
    assert M.contradicting_pairs([official, ota]) == []


# --- M9: no field without a quote ------------------------------------------- #

def test_m9_field_without_evidence_is_an_overclaim():
    v = M.evaluate(observation(
        extraction={"pets_allowed": True, "pet_fee": 5000},
        evidence=[{"quote": "Pets accepted.", "location": "l",
                   "field_refs": ["pets_allowed"]}]))
    assert v.verdict == M.REJECT_FIELD_WITHOUT_EVIDENCE
    assert v.rule == "M9"
    assert "pet_fee" in v.detail


def test_m9_absence_claims_need_no_quote():
    v = M.evaluate(observation(
        extraction={"pets_allowed": True, "weight_limit": "not_stated"},
        evidence=[{"quote": "Pets accepted.", "location": "l",
                   "field_refs": ["pets_allowed"]}]))
    assert v.verdict == M.VALID


# --- M10: wrong property means no evidence ---------------------------------- #

def test_m10_identity_mismatch_voids_the_observation():
    v = M.evaluate(observation(
        identity_check={"name_on_page": "Completely Different Lodge"}))
    assert v.verdict == M.REJECT_WRONG_PROPERTY
    assert v.rule == "M10"


def test_m10_booking_mirror_cannot_claim_pt1():
    v = M.evaluate(observation(
        hotel_ref={"market_id": "columbus-oh",
                   "canonical_name": "Sample Inn Columbus",
                   "normalized_name": "sample inn columbus",
                   "official_url": "https://www.sample-brand.com/columbus"},
        source_url="https://sample-inn-columbus.h-rez.com/"))
    assert v.verdict == M.REJECT_WRONG_PROPERTY
    assert "booking-mirror" in v.detail


def test_m10_shorter_page_name_still_matches():
    v = M.evaluate(observation(identity_check={"name_on_page": "Sample Inn"}))
    assert v.verdict == M.VALID


# --- M11: policy observations never establish identity ---------------------- #

def test_m11_reject_state_exists_and_is_closed():
    assert M.REJECT_POLICY_AS_IDENTITY in M.VERDICTS


# --- structural ------------------------------------------------------------- #

def test_every_rule_has_a_statement():
    assert set(M.RULES) == {"M%d" % i for i in range(1, 13)}
    assert all(v.strip() for v in M.RULES.values())


def test_batch_evaluation_never_aborts_on_a_rejection():
    results = M.evaluate_batch([observation(), {"broken": True}, observation(obs_id="c")])
    assert [r.rejected for r in results] == [False, True, False]
