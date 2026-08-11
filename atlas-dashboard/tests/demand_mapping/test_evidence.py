"""Evidence observation/snapshot tests (AES-SEO-001 §6)."""

from __future__ import annotations

import pytest

from engines.demand_mapping.contracts.canonical import (
    ContractValidationError,
    sha256_of_text,
)
from engines.demand_mapping.contracts.evidence import (
    EvidenceObservation,
    EvidenceSnapshot,
    ObservationType,
    compute_observation_id,
)
from engines.demand_mapping.contracts.provenance import Provenance

RAW_REF = sha256_of_text("raw payload stand-in")


def observation_fields(**overrides):
    fields = dict(
        schema_version="1.0.0",
        observation_type=ObservationType.DEMAND_VOLUME,
        provider_id="manual-provider",
        provider_version="1.0.0",
        query="example query",
        query_params=(("locale", "en-US"), ("region", "us")),
        market_scope="test-market",
        observed_at="2026-08-09T00:00:00Z",
        provenance=Provenance.OPERATOR,
        confidence_bp=9000,
        metrics=(("monthly_volume", 1400),),
        texts=(),
        raw_ref=RAW_REF,
    )
    fields.update(overrides)
    return fields


def make_observation(**overrides):
    return EvidenceObservation.build(**observation_fields(**overrides))


class TestObservationIdentity:
    def test_build_computes_content_derived_id(self):
        observation = make_observation()
        assert observation.observation_id == compute_observation_id(
            observation_fields()
        )

    def test_identical_content_identical_id(self):
        assert (
            make_observation().observation_id
            == make_observation().observation_id
        )

    def test_tampered_id_rejected(self):
        observation = make_observation()
        data = dict(observation_fields())
        data["observation_id"] = "0" * 64
        with pytest.raises(ContractValidationError):
            EvidenceObservation(**data)
        assert observation.observation_id != "0" * 64

    def test_defaults_do_not_change_identity(self):
        explicit = EvidenceObservation.build(
            **observation_fields(derived_from=())
        )
        fields = observation_fields()
        fields.pop("derived_from", None)
        implicit = EvidenceObservation.build(**fields)
        assert explicit.observation_id == implicit.observation_id


class TestObservationRules:
    def test_derived_requires_sources(self):
        with pytest.raises(ContractValidationError):
            make_observation(
                provenance=Provenance.DERIVED, raw_ref=None, derived_from=()
            )

    def test_derived_with_sources_is_legal(self):
        source = make_observation()
        derived = make_observation(
            provenance=Provenance.DERIVED,
            raw_ref=None,
            derived_from=(source.observation_id,),
        )
        assert derived.derived_from == (source.observation_id,)

    def test_derived_from_forbidden_for_other_states(self):
        with pytest.raises(ContractValidationError):
            make_observation(derived_from=("a" * 64,))

    def test_verified_and_operator_require_raw_ref(self):
        with pytest.raises(ContractValidationError):
            make_observation(provenance=Provenance.VERIFIED, raw_ref=None)
        with pytest.raises(ContractValidationError):
            make_observation(provenance=Provenance.OPERATOR, raw_ref=None)

    def test_estimated_may_omit_raw_ref(self):
        observation = make_observation(
            provenance=Provenance.ESTIMATED, confidence_bp=4000, raw_ref=None
        )
        assert observation.raw_ref is None

    def test_raw_ref_must_be_sha256_hex(self):
        with pytest.raises(ContractValidationError):
            make_observation(raw_ref="not-a-hash")

    def test_query_params_must_be_sorted_unique(self):
        with pytest.raises(ContractValidationError):
            make_observation(query_params=(("z", "1"), ("a", "2")))
        with pytest.raises(ContractValidationError):
            make_observation(query_params=(("a", "1"), ("a", "2")))

    def test_metrics_must_be_sorted_unique(self):
        with pytest.raises(ContractValidationError):
            make_observation(metrics=(("b", 1), ("a", 2)))
        with pytest.raises(ContractValidationError):
            make_observation(metrics=(("a", 1), ("a", 2)))

    def test_texts_must_be_sorted(self):
        with pytest.raises(ContractValidationError):
            make_observation(
                observation_type=ObservationType.QUERY_SUGGESTION,
                texts=("zeta", "alpha"),
            )

    def test_no_raw_body_fields_exist(self):
        forbidden = {"body", "raw_body", "response", "response_body",
                     "payload", "content", "html"}
        for model in (EvidenceObservation, EvidenceSnapshot):
            assert not forbidden & set(model.__fields__), model.__name__


class TestSnapshot:
    def test_build_sorts_observations_and_hashes_identity(self):
        first = make_observation()
        second = make_observation(query="second query")
        ordered = sorted(
            (first, second), key=lambda item: item.observation_id
        )
        snapshot = EvidenceSnapshot.build(
            schema_version="1.0.0",
            evidence_model_version="1.0.0",
            market_scope="test-market",
            observations=(second, first),
        )
        assert snapshot.observations == tuple(ordered)
        assert len(snapshot.snapshot_id) == 64

    def test_identical_content_identical_snapshot_id(self):
        def build():
            return EvidenceSnapshot.build(
                schema_version="1.0.0",
                evidence_model_version="1.0.0",
                market_scope="test-market",
                observations=(make_observation(),),
            )

        assert build().snapshot_id == build().snapshot_id

    def test_empty_snapshot_is_legal(self):
        snapshot = EvidenceSnapshot.build(
            schema_version="1.0.0",
            evidence_model_version="1.0.0",
            market_scope="test-market",
            observations=(),
        )
        assert snapshot.observations == ()

    def test_duplicate_observations_rejected(self):
        observation = make_observation()
        with pytest.raises(ContractValidationError):
            EvidenceSnapshot.build(
                schema_version="1.0.0",
                evidence_model_version="1.0.0",
                market_scope="test-market",
                observations=(observation, observation),
            )

    def test_tampered_snapshot_id_rejected(self):
        snapshot = EvidenceSnapshot.build(
            schema_version="1.0.0",
            evidence_model_version="1.0.0",
            market_scope="test-market",
            observations=(),
        )
        with pytest.raises(ContractValidationError):
            EvidenceSnapshot(
                schema_version=snapshot.schema_version,
                snapshot_id="0" * 64,
                evidence_model_version=snapshot.evidence_model_version,
                market_scope=snapshot.market_scope,
                label=snapshot.label,
                observations=snapshot.observations,
            )
