"""PTF-POLICY-P0-001 -- ptf-policy-observation/1.0 contract tests."""

from __future__ import annotations

import pytest

from scripts.pettripfinder.identity_evidence import POLICY_FIELD_NAMES
from scripts.pettripfinder.policy.policy_observation import (
    ADDITIVE_EXTRACTION_FIELDS,
    AUTHORITY_TIERS,
    CONTRACT_VERSION,
    EXTRACTION_FIELDS,
    SOURCE_TYPE_MAX_TIER,
    PolicyObservationError,
    asserted_fields,
    assert_not_identity_evidence,
    establishing_fields,
    quoted_fields,
    validate_emission_batch,
    validate_observation,
)


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


def test_valid_observation_round_trips():
    assert validate_observation(observation())["obs_id"] == "obs-1"


def test_strict_keys_reject_unknown_field():
    with pytest.raises(PolicyObservationError, match="additionalProperties"):
        validate_observation(observation(surprise="nope"))


def test_missing_required_field_fails():
    doc = observation()
    del doc["evidence"]
    with pytest.raises(PolicyObservationError, match="missing required"):
        validate_observation(doc)


def test_contract_version_is_pinned():
    with pytest.raises(PolicyObservationError, match="contract_version"):
        validate_observation(observation(contract_version="2.0.0"))


@pytest.mark.parametrize("tier", AUTHORITY_TIERS)
def test_all_declared_tiers_are_accepted(tier):
    # Structural validation accepts any declared tier; whether the tier may
    # ESTABLISH anything is the membrane's question, not the contract's.
    doc = observation(authority_tier=tier)
    assert validate_observation(doc)["authority_tier"] == tier


def test_unknown_tier_rejected():
    with pytest.raises(PolicyObservationError, match="authority_tier"):
        validate_observation(observation(authority_tier="PT9"))


def test_unknown_source_type_rejected():
    with pytest.raises(PolicyObservationError, match="source_type"):
        validate_observation(observation(source_type="a_friend_told_me"))


def test_every_source_type_declares_a_max_tier():
    assert set(SOURCE_TYPE_MAX_TIER.values()) <= set(AUTHORITY_TIERS)


def test_quote_is_required_on_evidence_items():
    with pytest.raises(PolicyObservationError, match="quote"):
        validate_observation(observation(
            evidence=[{"quote": "  ", "location": "x", "field_refs": []}]))


def test_evidence_location_is_required():
    with pytest.raises(PolicyObservationError, match="location"):
        validate_observation(observation(
            evidence=[{"quote": "q", "location": "", "field_refs": []}]))


def test_field_refs_must_name_known_fields():
    with pytest.raises(PolicyObservationError, match="unknown field"):
        validate_observation(observation(
            evidence=[{"quote": "q", "location": "l", "field_refs": ["vibes"]}]))


def test_extraction_vocabulary_is_closed():
    with pytest.raises(PolicyObservationError, match="unknown extraction field"):
        validate_observation(observation(extraction={"pet_vibes": "good"}))


def test_money_must_be_integer_minor_units():
    with pytest.raises(PolicyObservationError, match="integer in minor units"):
        validate_observation(observation(
            extraction={"pets_allowed": True, "pet_fee": 50.0},
            evidence=[{"quote": "q", "location": "l",
                       "field_refs": ["pets_allowed", "pet_fee"]}]))


def test_money_check_is_recursive_through_tiers():
    with pytest.raises(PolicyObservationError, match="integer in minor units"):
        validate_observation(observation(
            extraction={"pets_allowed": True,
                        "fee_tiers": [{"length_min_nights": 1, "amount_minor": 75.5}]},
            evidence=[{"quote": "q", "location": "l",
                       "field_refs": ["pets_allowed", "fee_tiers"]}]))


def test_identity_check_requires_name_on_page():
    with pytest.raises(PolicyObservationError, match="name_on_page"):
        validate_observation(observation(identity_check={}))


def test_hotel_ref_may_not_be_extended():
    with pytest.raises(PolicyObservationError, match="never extends it"):
        validate_observation(observation(hotel_ref={
            "market_id": "columbus-oh", "canonical_name": "X",
            "normalized_name": "x", "atlas_hotel_id": "HOTEL-0001"}))


def test_hotel_ref_requires_the_join_key():
    with pytest.raises(PolicyObservationError, match="normalized_name"):
        validate_observation(observation(hotel_ref={
            "market_id": "columbus-oh", "canonical_name": "X",
            "normalized_name": ""}))


def test_unknown_flag_code_rejected():
    with pytest.raises(PolicyObservationError, match="unknown flag code"):
        validate_observation(observation(
            flags=[{"code": "FLAG_LOOKS_FINE", "detail": "d"}]))


def test_flag_without_detail_rejected():
    with pytest.raises(PolicyObservationError, match="non-empty detail"):
        validate_observation(observation(
            flags=[{"code": "FLAG_AMBIGUOUS_BASIS", "detail": ""}]))


def test_observed_at_must_be_iso_date():
    with pytest.raises(PolicyObservationError, match="ISO date"):
        validate_observation(observation(observed_at="August 1 2026"))


def test_batch_requires_unique_obs_ids():
    with pytest.raises(PolicyObservationError, match="unique"):
        validate_emission_batch([observation(), observation()])


def test_batch_must_be_an_array():
    with pytest.raises(PolicyObservationError, match="array"):
        validate_emission_batch(observation())


def test_not_stated_asserts_nothing():
    extraction = {"pets_allowed": True, "weight_limit": "not_stated",
                  "breed_restrictions": ""}
    assert asserted_fields(extraction) == {"pets_allowed"}


def test_service_animal_text_never_establishes():
    extraction = {"service_animal_exception": "Service animals are welcome."}
    assert asserted_fields(extraction) == {"service_animal_exception"}
    assert establishing_fields(extraction) == frozenset()


def test_quoted_fields_collects_every_field_ref():
    evidence = [{"quote": "a", "location": "l", "field_refs": ["pets_allowed"]},
                {"quote": "b", "location": "l", "field_refs": ["pet_fee"]}]
    assert quoted_fields(evidence) == {"pets_allowed", "pet_fee"}


def test_vocabulary_aligns_with_production_policy_fields():
    """The contract must not silently invent a field production cannot store.

    Additions are allowed but must be DECLARED, so the translator gap is
    visible rather than discovered later.
    """
    undeclared = (EXTRACTION_FIELDS - POLICY_FIELD_NAMES) - ADDITIVE_EXTRACTION_FIELDS
    assert undeclared == frozenset(), (
        "extraction fields absent from production POLICY_FIELD_NAMES and not "
        "declared additive: %s" % sorted(undeclared))


def test_policy_observation_may_not_be_used_as_identity_evidence():
    with pytest.raises(PolicyObservationError, match="identity evidence"):
        assert_not_identity_evidence(observation())
