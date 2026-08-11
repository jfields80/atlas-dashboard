"""Page-opportunity contracts (AES-SEO-001 §8-§11).

A ``PageOpportunity`` is PRE-IA: a reason a page might deserve to exist,
never a page. No contract in this module carries a production URL, a
routing path, or an address slug of any kind — the subsystem cannot mint
one even by defect (§8.1; enforced by test over field names).

``opportunity_id`` is content-derived from the opportunity's *identity*
(intent class, family, target concept) so the id stays stable while
evidence, gate results, and decisions evolve around it (§8.2).

Rejection and deferral are first-class outcomes: a candidate failing hard
gates is emitted as DEFERRED or REJECTED with machine-readable reasons —
it never disappears silently (§11.5).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, Tuple

from pydantic import Field, StrictInt, StrictStr

from engines.demand_mapping.contracts.canonical import (
    ContractValidationError,
    FrozenModel,
    canonical_json,
    sha256_of_text,
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class IntentClass(str, Enum):
    """Closed intent vocabulary (§9.1, Blueprint intent classification)."""

    INFORMATIONAL = "INFORMATIONAL"
    COMMERCIAL = "COMMERCIAL"
    TRANSACTIONAL = "TRANSACTIONAL"
    NAVIGATIONAL = "NAVIGATIONAL"
    LOCAL = "LOCAL"


class OpportunityFamily(str, Enum):
    """Generic page-shape vocabulary (§10.1).

    Deliberately NOT 1:1 with the WGE PageRole enum; the mapping to
    PageRole is a Phase-F handoff concern under AES-WEB authority (§10.3)
    and no such mapping ships as code in this phase.
    """

    GEOGRAPHIC_LANDING = "GEOGRAPHIC_LANDING"
    CATEGORY = "CATEGORY"
    CATEGORY_GEOGRAPHIC = "CATEGORY_GEOGRAPHIC"
    ENTITY_PROFILE = "ENTITY_PROFILE"
    FACET_COLLECTION = "FACET_COLLECTION"
    COMPARISON = "COMPARISON"
    BEST_OF = "BEST_OF"
    COLLECTION = "COLLECTION"
    EDITORIAL_GUIDE = "EDITORIAL_GUIDE"
    FAQ_INFORMATIONAL = "FAQ_INFORMATIONAL"
    REGIONAL_HUB = "REGIONAL_HUB"


class DecisionState(str, Enum):
    """Closed decision vocabulary (§11.4, §13)."""

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    DEFERRED = "DEFERRED"
    REJECTED = "REJECTED"


class GateOutcome(str, Enum):
    """Outcome of one hard gate (§11.2).

    NOT_EVALUABLE records a gate whose required evidence was UNKNOWN or
    stale — it counts as not-passed and is never silently skipped.
    """

    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class RiskFlag(str, Enum):
    """Advisory risk markers (§8.2, §11.3)."""

    THIN_CONTENT = "THIN_CONTENT"
    CANNIBALIZATION_CANDIDATE = "CANNIBALIZATION_CANDIDATE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    OVERLAP = "OVERLAP"


class ClusterRelationKind(str, Enum):
    """Conceptual relation kinds between opportunities (§15.1)."""

    HUB_SPOKE = "HUB_SPOKE"
    TOPIC_CLUSTER = "TOPIC_CLUSTER"
    GEOGRAPHIC_CLUSTER = "GEOGRAPHIC_CLUSTER"
    COMPARISON_RELATION = "COMPARISON_RELATION"
    RELATED_INTENT = "RELATED_INTENT"


class GateResult(FrozenModel):
    """One gate's outcome with a machine-readable reason (§11.2, §11.5)."""

    gate_id: StrictStr = Field(...)
    outcome: GateOutcome = Field(...)
    reason_code: StrictStr = Field(...)
    detail: StrictStr = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.gate_id:
            raise ContractValidationError("gate_id must be non-empty")
        if not _REASON_CODE.match(self.reason_code):
            raise ContractValidationError(
                "reason_code must be SCREAMING_SNAKE_CASE (machine-readable, "
                "§11.5): %r" % self.reason_code
            )


class DimensionValueRef(FrozenModel):
    """A reference into a DimensionProfile: one dimension, one value."""

    dimension_id: StrictStr = Field(...)
    value_label: StrictStr = Field(...)


class TargetConcept(FrozenModel):
    """What the proposed page would be about — concept, never an address.

    ``geographic_scope`` is a concept descriptor (market/area label); it is
    never a routing path (§8.1). Empty string means no geographic scoping.
    """

    dimension_refs: Tuple[DimensionValueRef, ...] = Field(...)
    geographic_scope: StrictStr = Field("")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        refs = [(ref.dimension_id, ref.value_label)
                for ref in self.dimension_refs]
        if refs != sorted(refs):
            raise ContractValidationError(
                "dimension_refs must be sorted (§4.3)"
            )
        if len(refs) != len(set(refs)):
            raise ContractValidationError("dimension_refs must be unique")


class CandidateQuery(FrozenModel):
    """A query/topic the page would compete for, with its evidence."""

    query_text: StrictStr = Field(...)
    evidence_refs: Tuple[StrictStr, ...] = Field(())

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.query_text:
            raise ContractValidationError("query_text must be non-empty")
        if list(self.evidence_refs) != sorted(set(self.evidence_refs)):
            raise ContractValidationError(
                "evidence_refs must be sorted and unique (§4.3)"
            )


class InventorySupport(FrozenModel):
    """How much real inventory backs the opportunity (§8.2)."""

    entity_count: StrictInt = Field(...)
    differentiated_count: StrictInt = Field(...)
    coverage_bp: StrictInt = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.entity_count < 0 or self.differentiated_count < 0:
            raise ContractValidationError("inventory counts must be >= 0")
        if self.differentiated_count > self.entity_count:
            raise ContractValidationError(
                "differentiated_count cannot exceed entity_count"
            )
        if not (0 <= self.coverage_bp <= 10000):
            raise ContractValidationError(
                "coverage_bp must be within [0, 10000]"
            )


class FactRequirement(FrozenModel):
    """One fact the page needs, and its present coverage (§8.2)."""

    dimension_id: StrictStr = Field(...)
    coverage_bp: StrictInt = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.dimension_id:
            raise ContractValidationError("dimension_id must be non-empty")
        if not (0 <= self.coverage_bp <= 10000):
            raise ContractValidationError(
                "coverage_bp must be within [0, 10000]"
            )


class ContentFeasibility(FrozenModel):
    """Whether the facts the page needs actually exist (§8.2)."""

    required_facts: Tuple[FactRequirement, ...] = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        ids = [fact.dimension_id for fact in self.required_facts]
        if ids != sorted(ids):
            raise ContractValidationError(
                "required_facts must be sorted by dimension_id (§4.3)"
            )
        if len(ids) != len(set(ids)):
            raise ContractValidationError("required_facts must be unique")


class ClusterRelation(FrozenModel):
    """A conceptual edge to another opportunity (§15.1) — never a link."""

    relation_kind: ClusterRelationKind = Field(...)
    other_opportunity_id: StrictStr = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.other_opportunity_id:
            raise ContractValidationError(
                "other_opportunity_id must be non-empty"
            )


class PageOpportunity(FrozenModel):
    """An evidence-bearing page proposal — PRE-IA, address-free (§8)."""

    schema_version: StrictStr = Field(...)
    opportunity_id: StrictStr = Field(...)
    intent_class: IntentClass = Field(...)
    opportunity_family: OpportunityFamily = Field(...)
    target_concept: TargetConcept = Field(...)
    candidate_queries: Tuple[CandidateQuery, ...] = Field(...)
    demand_evidence_refs: Tuple[StrictStr, ...] = Field(())
    serp_evidence_refs: Tuple[StrictStr, ...] = Field(())
    competition_evidence_refs: Tuple[StrictStr, ...] = Field(())
    inventory_support: InventorySupport = Field(...)
    content_feasibility: ContentFeasibility = Field(...)
    confidence_bp: StrictInt = Field(...)
    risk_flags: Tuple[RiskFlag, ...] = Field(())
    cluster_relations: Tuple[ClusterRelation, ...] = Field(())
    gate_results: Tuple[GateResult, ...] = Field(...)
    decision_state: DecisionState = Field(...)
    decision_reasons: Tuple[StrictStr, ...] = Field(())
    evidence_snapshot_hash: StrictStr = Field(...)
    inventory_snapshot_hash: StrictStr = Field(...)
    planner_version: StrictStr = Field(...)
    gate_policy_version: StrictStr = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_page_opportunity(self)

    @classmethod
    def build(cls, **fields: Any) -> "PageOpportunity":
        """Construct with the content-derived ``opportunity_id`` computed."""
        fields.pop("opportunity_id", None)
        candidate = dict(fields)
        candidate["opportunity_id"] = compute_opportunity_id(
            fields["intent_class"],
            fields["opportunity_family"],
            fields["target_concept"],
        )
        return cls(**candidate)


def compute_opportunity_id(
    intent_class: IntentClass,
    opportunity_family: OpportunityFamily,
    target_concept: TargetConcept,
) -> str:
    """Stable identity: hash of (intent, family, target concept) only (§8.2).

    Evidence, gates, and decisions may change; the opportunity's identity
    does not.
    """
    payload = {
        "intent_class": intent_class,
        "opportunity_family": opportunity_family,
        "target_concept": target_concept,
    }
    return sha256_of_text(canonical_json(payload))


def _validate_sorted_unique_refs(refs: Tuple[str, ...], label: str) -> None:
    if list(refs) != sorted(set(refs)):
        raise ContractValidationError(
            "%s must be sorted and unique (§4.3)" % label
        )


def validate_page_opportunity(opportunity: PageOpportunity) -> None:
    """All semantic rules for a PageOpportunity (§8, §11, §13)."""
    for name in ("schema_version", "planner_version", "gate_policy_version"):
        if not getattr(opportunity, name):
            raise ContractValidationError("%s must be non-empty" % name)
    for name in ("evidence_snapshot_hash", "inventory_snapshot_hash"):
        if not _HEX64.match(getattr(opportunity, name)):
            raise ContractValidationError(
                "%s must be a 64-hex SHA-256 content hash (§8.2)" % name
            )
    if not (0 <= opportunity.confidence_bp <= 10000):
        raise ContractValidationError(
            "confidence_bp must be within [0, 10000] (§5.3)"
        )

    queries = [item.query_text for item in opportunity.candidate_queries]
    if queries != sorted(queries):
        raise ContractValidationError(
            "candidate_queries must be sorted by query_text (§4.3)"
        )
    if len(queries) != len(set(queries)):
        raise ContractValidationError("candidate_queries must be unique")

    _validate_sorted_unique_refs(
        opportunity.demand_evidence_refs, "demand_evidence_refs"
    )
    _validate_sorted_unique_refs(
        opportunity.serp_evidence_refs, "serp_evidence_refs"
    )
    _validate_sorted_unique_refs(
        opportunity.competition_evidence_refs, "competition_evidence_refs"
    )

    flags = [flag.value for flag in opportunity.risk_flags]
    if flags != sorted(set(flags)):
        raise ContractValidationError(
            "risk_flags must be sorted and unique (§4.3)"
        )

    relations = [
        (relation.relation_kind.value, relation.other_opportunity_id)
        for relation in opportunity.cluster_relations
    ]
    if relations != sorted(relations):
        raise ContractValidationError(
            "cluster_relations must be sorted (§4.3)"
        )
    if len(relations) != len(set(relations)):
        raise ContractValidationError("cluster_relations must be unique")
    for relation in opportunity.cluster_relations:
        if relation.other_opportunity_id == opportunity.opportunity_id:
            raise ContractValidationError(
                "an opportunity cannot cluster with itself"
            )

    gate_ids = [gate.gate_id for gate in opportunity.gate_results]
    if gate_ids != sorted(gate_ids):
        raise ContractValidationError(
            "gate_results must be sorted by gate_id (§4.3)"
        )
    if len(gate_ids) != len(set(gate_ids)):
        raise ContractValidationError("gate_results must have unique gate_ids")

    if opportunity.decision_state in (
        DecisionState.DEFERRED, DecisionState.REJECTED
    ) and not opportunity.decision_reasons:
        raise ContractValidationError(
            "DEFERRED and REJECTED opportunities must carry decision "
            "reasons — nothing fails silently (§11.5)"
        )

    expected = compute_opportunity_id(
        opportunity.intent_class,
        opportunity.opportunity_family,
        opportunity.target_concept,
    )
    if opportunity.opportunity_id != expected:
        raise ContractValidationError(
            "opportunity_id does not match its identity hash (§8.2); use "
            "PageOpportunity.build()"
        )


class PageOpportunitySet(FrozenModel):
    """One planner run's full output, including every DEFERRED and
    REJECTED opportunity (§8.4, §11.5). ``set_id`` is content-derived."""

    schema_version: StrictStr = Field(...)
    set_id: StrictStr = Field(...)
    opportunities: Tuple[PageOpportunity, ...] = Field(...)
    evidence_snapshot_hashes: Tuple[StrictStr, ...] = Field(...)
    inventory_snapshot_hash: StrictStr = Field(...)
    contracts_version: StrictStr = Field(...)
    evidence_model_version: StrictStr = Field(...)
    planner_version: StrictStr = Field(...)
    gate_policy_version: StrictStr = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_page_opportunity_set(self)

    @classmethod
    def build(cls, **fields: Any) -> "PageOpportunitySet":
        """Construct with sorted opportunities and a computed ``set_id``."""
        fields.pop("set_id", None)
        fields["evidence_snapshot_hashes"] = tuple(
            sorted(set(fields.get("evidence_snapshot_hashes", ())))
        )
        fields["opportunities"] = tuple(
            sorted(fields.get("opportunities", ()),
                   key=lambda item: item.opportunity_id)
        )
        candidate = dict(fields)
        candidate["set_id"] = compute_opportunity_set_id(fields)
        return cls(**candidate)


def compute_opportunity_set_id(fields: Dict[str, Any]) -> str:
    """SHA-256 of the canonical form of every field except the id itself."""
    payload = dict(fields)
    payload.pop("set_id", None)
    return sha256_of_text(canonical_json(payload))


def validate_page_opportunity_set(
    opportunity_set: PageOpportunitySet,
) -> None:
    """All semantic rules for a PageOpportunitySet (§8.4, §19.3)."""
    for name in ("schema_version", "contracts_version",
                 "evidence_model_version", "planner_version",
                 "gate_policy_version"):
        if not getattr(opportunity_set, name):
            raise ContractValidationError("%s must be non-empty" % name)
    if not _HEX64.match(opportunity_set.inventory_snapshot_hash):
        raise ContractValidationError(
            "inventory_snapshot_hash must be a 64-hex SHA-256 hash"
        )
    hashes = opportunity_set.evidence_snapshot_hashes
    if list(hashes) != sorted(set(hashes)):
        raise ContractValidationError(
            "evidence_snapshot_hashes must be sorted and unique (§4.3)"
        )
    for value in hashes:
        if not _HEX64.match(value):
            raise ContractValidationError(
                "evidence_snapshot_hashes entries must be 64-hex hashes"
            )

    ids = [item.opportunity_id for item in opportunity_set.opportunities]
    if ids != sorted(ids):
        raise ContractValidationError(
            "opportunities must be sorted by opportunity_id (§4.3)"
        )
    if len(ids) != len(set(ids)):
        raise ContractValidationError(
            "opportunities must have unique opportunity_ids — duplicate "
            "intent collapses before decisioning (§11.2)"
        )
    allowed = set(hashes)
    for item in opportunity_set.opportunities:
        if item.evidence_snapshot_hash not in allowed:
            raise ContractValidationError(
                "every opportunity's evidence_snapshot_hash must appear in "
                "the set's evidence_snapshot_hashes (§19.3)"
            )
        if (item.inventory_snapshot_hash
                != opportunity_set.inventory_snapshot_hash):
            raise ContractValidationError(
                "every opportunity must share the set's "
                "inventory_snapshot_hash (§19.3)"
            )

    expected = compute_opportunity_set_id(
        {name: getattr(opportunity_set, name)
         for name in opportunity_set.__fields__}
    )
    if opportunity_set.set_id != expected:
        raise ContractValidationError(
            "set_id does not match content hash (§4.2); use "
            "PageOpportunitySet.build()"
        )
