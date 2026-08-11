"""Version axes and the schema-version registry (AES-SEO-001 §19).

Schema changes are versioned events, never in-place edits: registering a
``(kind, schema_version)`` pair twice with a different model is a loud
:class:`SchemaRegistrationError` (§19.2).

Version axes carried here (§19.1):
* ``CONTRACTS_VERSION`` — the contract package as a whole;
* ``EVIDENCE_MODEL_VERSION`` — observation-type vocabulary + provenance
  semantics (bump when either changes);
* per-kind ``SCHEMA_VERSIONS`` — one entry per contract kind.

Planner, gate-policy, and scoring-policy versions belong to their engines
(Phases D+/G) and are recorded on outputs, not defined here.
"""

from __future__ import annotations

from typing import Dict, Tuple, Type

from pydantic import BaseModel

from engines.demand_mapping.contracts.canonical import SchemaRegistrationError
from engines.demand_mapping.contracts.dimensions import (
    DimensionProfile,
    DimensionProfileSet,
)
from engines.demand_mapping.contracts.evidence import (
    EvidenceObservation,
    EvidenceSnapshot,
)
from engines.demand_mapping.contracts.opportunities import (
    GateResult,
    PageOpportunity,
    PageOpportunitySet,
)
from engines.demand_mapping.contracts.provenance import TaggedValue
from engines.demand_mapping.contracts.records import (
    FieldValue,
    GenericEntityRecord,
    GenericInventorySnapshot,
)

# 1.1.0 — Phase B additive minor: generic inventory record kinds
# (FieldValue, GenericEntityRecord, GenericInventorySnapshot) join the
# registry. No existing schema changed (§19.1: additive = minor).
CONTRACTS_VERSION: str = "1.1.0"
EVIDENCE_MODEL_VERSION: str = "1.0.0"

SCHEMA_VERSIONS: Dict[str, str] = {
    "TaggedValue": "1.0.0",
    "EvidenceObservation": "1.0.0",
    "EvidenceSnapshot": "1.0.0",
    "DimensionProfile": "1.0.0",
    "DimensionProfileSet": "1.0.0",
    "GateResult": "1.0.0",
    "PageOpportunity": "1.0.0",
    "PageOpportunitySet": "1.0.0",
    "FieldValue": "1.0.0",
    "GenericEntityRecord": "1.0.0",
    "GenericInventorySnapshot": "1.0.0",
}

# Engine versions (§4.5): bumped whenever output could differ for
# identical input. Recorded on every output artifact that the engine
# produces (DimensionProfileSet carries it via the producing run).
ENGINE_VERSIONS: Dict[str, str] = {
    "inventory_profiler": "1.0.0",
}

_SCHEMA_REGISTRY: Dict[Tuple[str, str], Type[BaseModel]] = {}


def register_schema(
    kind: str, schema_version: str, model_cls: Type[BaseModel]
) -> None:
    """Register the model class for ``(kind, schema_version)``.

    Re-registering the identical class is idempotent; registering a
    different class for an existing key raises — schema changes are
    versioned events, never in-place edits (§19.2).
    """
    key = (str(kind), str(schema_version))
    existing = _SCHEMA_REGISTRY.get(key)
    if existing is not None and existing is not model_cls:
        raise SchemaRegistrationError(
            "duplicate schema registration for %s %s" % key
        )
    _SCHEMA_REGISTRY[key] = model_cls


def registered_schema(kind: str, schema_version: str) -> Type[BaseModel]:
    """Look up the registered model class for ``(kind, schema_version)``."""
    key = (str(kind), str(schema_version))
    model_cls = _SCHEMA_REGISTRY.get(key)
    if model_cls is None:
        raise SchemaRegistrationError(
            "no registered schema for %s %s" % key
        )
    return model_cls


def registered_schema_versions() -> Dict[str, Tuple[str, ...]]:
    """All registered schema versions per kind, stable-sorted."""
    out: Dict[str, Tuple[str, ...]] = {}
    for kind, version in sorted(_SCHEMA_REGISTRY):
        out.setdefault(kind, ())
        out[kind] = out[kind] + (version,)
    return out


register_schema("TaggedValue", SCHEMA_VERSIONS["TaggedValue"], TaggedValue)
register_schema(
    "EvidenceObservation",
    SCHEMA_VERSIONS["EvidenceObservation"],
    EvidenceObservation,
)
register_schema(
    "EvidenceSnapshot", SCHEMA_VERSIONS["EvidenceSnapshot"], EvidenceSnapshot
)
register_schema(
    "DimensionProfile", SCHEMA_VERSIONS["DimensionProfile"], DimensionProfile
)
register_schema(
    "DimensionProfileSet",
    SCHEMA_VERSIONS["DimensionProfileSet"],
    DimensionProfileSet,
)
register_schema("GateResult", SCHEMA_VERSIONS["GateResult"], GateResult)
register_schema(
    "PageOpportunity", SCHEMA_VERSIONS["PageOpportunity"], PageOpportunity
)
register_schema(
    "PageOpportunitySet",
    SCHEMA_VERSIONS["PageOpportunitySet"],
    PageOpportunitySet,
)
register_schema("FieldValue", SCHEMA_VERSIONS["FieldValue"], FieldValue)
register_schema(
    "GenericEntityRecord",
    SCHEMA_VERSIONS["GenericEntityRecord"],
    GenericEntityRecord,
)
register_schema(
    "GenericInventorySnapshot",
    SCHEMA_VERSIONS["GenericInventorySnapshot"],
    GenericInventorySnapshot,
)
