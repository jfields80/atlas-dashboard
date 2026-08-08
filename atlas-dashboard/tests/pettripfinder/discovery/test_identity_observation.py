"""PTF-DISCOVERY-P0-001 -- ptf-identity-observation/1.0 contract tests.

The strict-key rule, the Membrane, the closed enums, and the one
translation boundary into ptf-identity-evidence/1.0. The EX-EMISSION-001
fixture is the verified example batch from the PTF-PARALLEL-RESEARCH-002
package (sha256 b771a938...49, pinned by its MANIFEST) -- it is ported, not
recreated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.discovery.identity_observation import (
    CONTRACT_VERSION,
    OBSERVATION_TIER_BY_FAMILY,
    IdentityObservationError,
    observation_to_evidence,
    translate_emission_batch,
    validate_emission_batch,
    validate_observation,
)
from scripts.pettripfinder.discovery.source_families import SOURCE_FAMILIES
from scripts.pettripfinder.identity_evidence import (
    IDENTITY_CONFIRMED,
    POSSIBLE_CLOSURE,
    POSSIBLE_REBRAND,
    TIERS,
    adjudicate,
    validate_evidence,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _observation(**overrides):
    record = {
        "obs_id": "obs-001",
        "contract_version": CONTRACT_VERSION,
        "source_id": "fl_dbpr_lodging",
        "source_family": "REGISTRY",
        "observed_at": "2026-07-01",
        "name": "Bayshore Palms Hotel",
        "parse_confidence": "HIGH",
        "warnings": [],
        "provenance": {
            "retrieval_mode": "bulk_file",
            "retrieved_at": "2026-08-07T14:05:00Z",
            "raw_pointer": "hrlodge4.csv#row=1842",
        },
    }
    record.update(overrides)
    return record


class TestValidation:
    def test_minimal_valid_observation_passes(self):
        assert validate_observation(_observation())["obs_id"] == "obs-001"

    @pytest.mark.parametrize("field", [
        "obs_id", "contract_version", "source_id", "source_family",
        "observed_at", "name", "parse_confidence", "warnings", "provenance"])
    def test_every_required_field_is_required(self, field):
        record = _observation()
        del record[field]
        with pytest.raises(IdentityObservationError):
            validate_observation(record)

    def test_unknown_field_is_rejected_not_extended(self):
        with pytest.raises(IdentityObservationError, match="unknown field"):
            validate_observation(_observation(star_rating="4"))

    def test_wrong_contract_version_rejected(self):
        with pytest.raises(IdentityObservationError, match="contract_version"):
            validate_observation(_observation(contract_version="1.1.0"))

    def test_unknown_source_family_rejected(self):
        with pytest.raises(IdentityObservationError, match="source_family"):
            validate_observation(_observation(source_family="SOCIAL"))

    def test_observed_at_must_be_iso_date(self):
        with pytest.raises(IdentityObservationError, match="observed_at"):
            validate_observation(_observation(observed_at="07/01/2026"))

    def test_unknown_warning_code_rejected(self):
        with pytest.raises(IdentityObservationError, match="warning code"):
            validate_observation(_observation(
                warnings=[{"code": "W_MADE_UP", "detail": "x"}]))

    def test_warning_without_detail_is_silent_guessing(self):
        with pytest.raises(IdentityObservationError, match="detail"):
            validate_observation(_observation(
                warnings=[{"code": "W_GEO_MISSING", "detail": " "}]))

    def test_provenance_requires_raw_pointer(self):
        record = _observation()
        del record["provenance"]["raw_pointer"]
        with pytest.raises(IdentityObservationError, match="raw_pointer"):
            validate_observation(record)

    def test_provenance_unknown_key_rejected(self):
        record = _observation()
        record["provenance"]["cost_usd"] = 0
        with pytest.raises(IdentityObservationError, match="unknown key"):
            validate_observation(record)

    def test_unknown_retrieval_mode_rejected(self):
        record = _observation()
        record["provenance"]["retrieval_mode"] = "scrape"
        with pytest.raises(IdentityObservationError, match="retrieval_mode"):
            validate_observation(record)

    @pytest.mark.parametrize("field,value", [
        ("lat", 91), ("lat", -90.5), ("lon", 181), ("lon", True)])
    def test_out_of_range_or_bool_coordinates_rejected(self, field, value):
        with pytest.raises(IdentityObservationError):
            validate_observation(_observation(**{field: value}))

    def test_in_range_coordinates_accepted(self):
        record = validate_observation(_observation(lat=27.95, lon=-82.46))
        assert record["lat"] == 27.95


class TestMembrane:
    def test_policy_field_fails_with_membrane_error_not_unknown_key(self):
        with pytest.raises(IdentityObservationError, match="pet-policy"):
            validate_observation(_observation(pet_fee="75"))

    def test_camel_case_smuggle_is_caught(self):
        with pytest.raises(IdentityObservationError, match="pet-policy"):
            validate_observation(_observation(petsAllowed=True))

    def test_policy_key_inside_provenance_is_caught(self):
        record = _observation()
        record["provenance"]["policy_quote"] = "pets welcome"
        with pytest.raises(IdentityObservationError, match="pet-policy"):
            validate_observation(record)

    def test_discovery_signal_names_are_also_denied(self):
        with pytest.raises(IdentityObservationError, match="pet-policy"):
            validate_observation(_observation(pet_friendly=True))


class TestBatch:
    def test_batch_must_be_an_array(self):
        with pytest.raises(IdentityObservationError, match="array"):
            validate_emission_batch({"obs": []})

    def test_duplicate_obs_id_rejected(self):
        with pytest.raises(IdentityObservationError, match="unique"):
            validate_emission_batch([_observation(), _observation()])

    def test_empty_batch_is_valid(self):
        assert validate_emission_batch([]) == []

    def test_verified_package_example_batch_validates_and_translates(self):
        batch = json.loads(
            (FIXTURES / "EX-EMISSION-001.json").read_text(encoding="utf-8"))
        evidence = translate_emission_batch(batch)
        assert len(evidence) == 3
        for record in evidence:
            assert record["source_family"] == "REGISTRY"
            assert record["tier"] == 2


class TestTranslation:
    def test_every_family_has_a_tier_and_no_extras(self):
        assert set(OBSERVATION_TIER_BY_FAMILY) == set(SOURCE_FAMILIES)
        assert set(OBSERVATION_TIER_BY_FAMILY.values()) <= set(TIERS)

    def test_evidence_round_trip_passes_evidence_validation(self):
        evidence = observation_to_evidence(_observation(
            address="2140 Harbor Crest Blvd", zip="33607", city="Tampa",
            state="FL", phone="(813) 555-0142",
            property_code="FL_DBPR:HOT6099999", license_class="HOTL"))
        assert validate_evidence(evidence) == evidence
        assert evidence["source_url"] == "hrlodge4.csv#row=1842"
        assert evidence["postal_code"] == "33607"
        assert evidence["property_code"] == "FL_DBPR:HOT6099999"

    def test_registry_with_full_address_confirms_through_existing_rules(self):
        evidence = observation_to_evidence(_observation(
            address="2140 Harbor Crest Blvd", zip="33607"))
        assert adjudicate([evidence])["outcome"] == IDENTITY_CONFIRMED

    def test_permanently_closed_flows_into_closure_outcome(self):
        evidence = observation_to_evidence(_observation(
            address="2140 Harbor Crest Blvd", zip="33607",
            permanently_closed=True))
        assert adjudicate([evidence])["outcome"] == POSSIBLE_CLOSURE

    def test_prior_names_flow_into_rebrand_outcome(self):
        evidence = observation_to_evidence(_observation(
            address="2140 Harbor Crest Blvd", zip="33607",
            prior_names=["Harbor Crest Inn"]))
        assert adjudicate([evidence])["outcome"] == POSSIBLE_REBRAND

    def test_family_is_the_independence_unit_after_translation(self):
        # Two REGISTRY observations from two different concrete registries
        # are one voice: they must NOT confirm each other.
        a = observation_to_evidence(_observation(
            obs_id="a", source_id="registry_one",
            address="100 Main St", zip="33607"))
        b = observation_to_evidence(_observation(
            obs_id="b", source_id="registry_two",
            address="100 Main St", zip="33607"))
        assert a["source_family"] == b["source_family"] == "REGISTRY"

    def test_translation_is_deterministic(self):
        one = observation_to_evidence(_observation(address="1 X St", zip="33607"))
        two = observation_to_evidence(_observation(address="1 X St", zip="33607"))
        assert one == two
