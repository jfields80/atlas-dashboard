"""Page-opportunity contract tests (AES-SEO-001 §8-§11, §13)."""

from __future__ import annotations

import re

import pytest

import engines.demand_mapping.contracts.dimensions as dimensions_module
import engines.demand_mapping.contracts.evidence as evidence_module
import engines.demand_mapping.contracts.opportunities as opportunities_module
import engines.demand_mapping.contracts.provenance as provenance_module
from engines.demand_mapping.contracts.canonical import (
    ContractValidationError,
    FrozenModel,
    sha256_of_text,
)
from engines.demand_mapping.contracts.opportunities import (
    CandidateQuery,
    ClusterRelation,
    ClusterRelationKind,
    ContentFeasibility,
    DecisionState,
    DimensionValueRef,
    FactRequirement,
    GateOutcome,
    GateResult,
    IntentClass,
    InventorySupport,
    OpportunityFamily,
    PageOpportunity,
    PageOpportunitySet,
    RiskFlag,
    TargetConcept,
    compute_opportunity_id,
)

EVIDENCE_HASH = sha256_of_text("evidence snapshot stand-in")
INVENTORY_HASH = sha256_of_text("inventory snapshot stand-in")


def make_target(**overrides):
    fields = dict(
        dimension_refs=(
            DimensionValueRef(dimension_id="dim.alpha", value_label="a"),
        ),
        geographic_scope="test-market",
    )
    fields.update(overrides)
    return TargetConcept(**fields)


def opportunity_fields(**overrides):
    fields = dict(
        schema_version="1.0.0",
        intent_class=IntentClass.LOCAL,
        opportunity_family=OpportunityFamily.FACET_COLLECTION,
        target_concept=make_target(),
        candidate_queries=(
            CandidateQuery(query_text="example query", evidence_refs=()),
        ),
        demand_evidence_refs=(),
        serp_evidence_refs=(),
        competition_evidence_refs=(),
        inventory_support=InventorySupport(
            entity_count=40, differentiated_count=12, coverage_bp=7500,
        ),
        content_feasibility=ContentFeasibility(required_facts=(
            FactRequirement(dimension_id="dim.alpha", coverage_bp=7500),
        )),
        confidence_bp=5500,
        risk_flags=(),
        cluster_relations=(),
        gate_results=(
            GateResult(
                gate_id="gate.minimum_inventory",
                outcome=GateOutcome.PASSED,
                reason_code="INVENTORY_SUFFICIENT",
                detail="40 entities >= threshold",
            ),
        ),
        decision_state=DecisionState.PROPOSED,
        decision_reasons=(),
        evidence_snapshot_hash=EVIDENCE_HASH,
        inventory_snapshot_hash=INVENTORY_HASH,
        planner_version="1.0.0",
        gate_policy_version="1.0.0",
    )
    fields.update(overrides)
    return fields


def make_opportunity(**overrides):
    return PageOpportunity.build(**opportunity_fields(**overrides))


class TestClosedVocabularies:
    def test_intent_classes(self):
        assert {member.value for member in IntentClass} == {
            "INFORMATIONAL", "COMMERCIAL", "TRANSACTIONAL",
            "NAVIGATIONAL", "LOCAL",
        }

    def test_opportunity_families(self):
        assert len(OpportunityFamily) == 11
        assert {member.value for member in OpportunityFamily} == {
            "GEOGRAPHIC_LANDING", "CATEGORY", "CATEGORY_GEOGRAPHIC",
            "ENTITY_PROFILE", "FACET_COLLECTION", "COMPARISON", "BEST_OF",
            "COLLECTION", "EDITORIAL_GUIDE", "FAQ_INFORMATIONAL",
            "REGIONAL_HUB",
        }

    def test_decision_states(self):
        assert {member.value for member in DecisionState} == {
            "PROPOSED", "APPROVED", "DEFERRED", "REJECTED"
        }

    def test_gate_outcomes(self):
        assert {member.value for member in GateOutcome} == {
            "PASSED", "FAILED", "NOT_EVALUABLE"
        }

    def test_cluster_relation_kinds(self):
        assert {member.value for member in ClusterRelationKind} == {
            "HUB_SPOKE", "TOPIC_CLUSTER", "GEOGRAPHIC_CLUSTER",
            "COMPARISON_RELATION", "RELATED_INTENT",
        }


class TestNoAddressFields:
    """§8.1: no contract may carry a production URL, path, or slug field."""

    FORBIDDEN = re.compile(r"url|route|slug|canonical", re.IGNORECASE)

    def test_no_field_name_is_address_shaped(self):
        for module in (opportunities_module, evidence_module,
                       dimensions_module, provenance_module):
            for obj in vars(module).values():
                if (isinstance(obj, type) and issubclass(obj, FrozenModel)
                        and obj is not FrozenModel):
                    for field_name in obj.__fields__:
                        assert not self.FORBIDDEN.search(field_name), (
                            "%s.%s is address-shaped (§8.1)"
                            % (obj.__name__, field_name)
                        )


class TestOpportunityIdentity:
    def test_build_computes_identity_hash(self):
        opportunity = make_opportunity()
        assert opportunity.opportunity_id == compute_opportunity_id(
            IntentClass.LOCAL,
            OpportunityFamily.FACET_COLLECTION,
            make_target(),
        )

    def test_identity_is_stable_across_decisions_and_evidence(self):
        proposed = make_opportunity()
        rejected = make_opportunity(
            decision_state=DecisionState.REJECTED,
            decision_reasons=("INSUFFICIENT_DIFFERENTIATION",),
            confidence_bp=100,
        )
        assert proposed.opportunity_id == rejected.opportunity_id

    def test_identity_changes_with_target_concept(self):
        other = make_opportunity(target_concept=make_target(
            geographic_scope="other-market"
        ))
        assert other.opportunity_id != make_opportunity().opportunity_id

    def test_tampered_id_rejected(self):
        data = opportunity_fields()
        data["opportunity_id"] = "0" * 64
        with pytest.raises(ContractValidationError):
            PageOpportunity(**data)


class TestOpportunityRules:
    def test_rejected_requires_reasons(self):
        with pytest.raises(ContractValidationError):
            make_opportunity(decision_state=DecisionState.REJECTED)

    def test_deferred_requires_reasons(self):
        with pytest.raises(ContractValidationError):
            make_opportunity(decision_state=DecisionState.DEFERRED)

    def test_rejected_with_reasons_is_first_class(self):
        opportunity = make_opportunity(
            decision_state=DecisionState.REJECTED,
            decision_reasons=("DUPLICATE_INTENT",),
        )
        assert opportunity.decision_state is DecisionState.REJECTED

    def test_confidence_bounds(self):
        with pytest.raises(ContractValidationError):
            make_opportunity(confidence_bp=10001)

    def test_snapshot_hashes_must_be_sha256(self):
        with pytest.raises(ContractValidationError):
            make_opportunity(evidence_snapshot_hash="short")
        with pytest.raises(ContractValidationError):
            make_opportunity(inventory_snapshot_hash="short")

    def test_evidence_refs_sorted_unique(self):
        with pytest.raises(ContractValidationError):
            make_opportunity(demand_evidence_refs=("b", "a"))
        with pytest.raises(ContractValidationError):
            make_opportunity(serp_evidence_refs=("a", "a"))

    def test_self_cluster_rejected(self):
        identity = compute_opportunity_id(
            IntentClass.LOCAL,
            OpportunityFamily.FACET_COLLECTION,
            make_target(),
        )
        with pytest.raises(ContractValidationError):
            make_opportunity(cluster_relations=(
                ClusterRelation(
                    relation_kind=ClusterRelationKind.TOPIC_CLUSTER,
                    other_opportunity_id=identity,
                ),
            ))

    def test_duplicate_gate_ids_rejected(self):
        gate = GateResult(
            gate_id="gate.minimum_inventory",
            outcome=GateOutcome.PASSED,
            reason_code="INVENTORY_SUFFICIENT",
            detail="",
        )
        with pytest.raises(ContractValidationError):
            make_opportunity(gate_results=(gate, gate))

    def test_reason_code_must_be_machine_readable(self):
        with pytest.raises(ContractValidationError):
            GateResult(
                gate_id="gate.x",
                outcome=GateOutcome.FAILED,
                reason_code="not machine readable",
                detail="",
            )

    def test_inventory_support_arithmetic(self):
        with pytest.raises(ContractValidationError):
            InventorySupport(
                entity_count=5, differentiated_count=6, coverage_bp=100,
            )


class TestOpportunitySet:
    def build_set(self, opportunities):
        return PageOpportunitySet.build(
            schema_version="1.0.0",
            opportunities=opportunities,
            evidence_snapshot_hashes=(EVIDENCE_HASH,),
            inventory_snapshot_hash=INVENTORY_HASH,
            contracts_version="1.0.0",
            evidence_model_version="1.0.0",
            planner_version="1.0.0",
            gate_policy_version="1.0.0",
        )

    def test_build_sorts_and_hashes(self):
        first = make_opportunity()
        second = make_opportunity(intent_class=IntentClass.COMMERCIAL)
        built = self.build_set((second, first))
        ids = [item.opportunity_id for item in built.opportunities]
        assert ids == sorted(ids)
        assert len(built.set_id) == 64

    def test_identical_content_identical_set_id(self):
        assert (
            self.build_set((make_opportunity(),)).set_id
            == self.build_set((make_opportunity(),)).set_id
        )

    def test_duplicate_opportunities_rejected(self):
        opportunity = make_opportunity()
        with pytest.raises(ContractValidationError):
            self.build_set((opportunity, opportunity))

    def test_opportunity_evidence_hash_must_be_registered_in_set(self):
        stray = make_opportunity(
            evidence_snapshot_hash=sha256_of_text("some other snapshot")
        )
        with pytest.raises(ContractValidationError):
            self.build_set((stray,))

    def test_opportunity_inventory_hash_must_match_set(self):
        stray = make_opportunity(
            inventory_snapshot_hash=sha256_of_text("other inventory")
        )
        with pytest.raises(ContractValidationError):
            self.build_set((stray,))

    def test_tampered_set_id_rejected(self):
        built = self.build_set(())
        data = {name: getattr(built, name) for name in built.__fields__}
        data["set_id"] = "0" * 64
        with pytest.raises(ContractValidationError):
            PageOpportunitySet(**data)

    def test_rejected_opportunities_are_carried_not_dropped(self):
        rejected = make_opportunity(
            decision_state=DecisionState.REJECTED,
            decision_reasons=("INSUFFICIENT_INVENTORY",),
        )
        built = self.build_set((rejected,))
        assert built.opportunities[0].decision_state is DecisionState.REJECTED


class TestRiskFlags:
    def test_flags_sorted_unique(self):
        with pytest.raises(ContractValidationError):
            make_opportunity(risk_flags=(
                RiskFlag.THIN_CONTENT, RiskFlag.CANNIBALIZATION_CANDIDATE,
            ))
        opportunity = make_opportunity(risk_flags=(
            RiskFlag.CANNIBALIZATION_CANDIDATE, RiskFlag.THIN_CONTENT,
        ))
        assert len(opportunity.risk_flags) == 2
