"""Evidence observation and snapshot contracts (AES-SEO-001 §6).

An ``EvidenceObservation`` is the atomic unit of external knowledge; an
``EvidenceSnapshot`` is an immutable, content-addressed set of observations
frozen at a point in time. Raw external response bodies never live inside
these contracts — they are referenced by content hash (``raw_ref``) into the
content-addressed store (§6.2, §18).

Identity is content-derived: ``observation_id`` and ``snapshot_id`` are the
SHA-256 of the canonical form of the record's own fields, so identical
content always carries identical identity (§4.2). Use the ``build``
classmethods to compute identities; direct construction re-validates them.

Numeric payloads are integer-only, carried as sorted ``(name, value)`` pairs
rather than open dictionaries (no unrestricted mappings in canonical
contracts). Textual payloads (e.g. suggested queries returned by a
provider) are carried as a sorted tuple of strings.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from pydantic import Field, StrictInt, StrictStr

from engines.demand_mapping.contracts.canonical import (
    ContractValidationError,
    FrozenModel,
    canonical_json,
    sha256_of_text,
)
from engines.demand_mapping.contracts.provenance import (
    Provenance,
    validate_confidence_bp,
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ObservationType(str, Enum):
    """Closed, versioned observation vocabulary (§6.1).

    Adding a member is an evidence-model minor version bump (§19.1);
    removing or re-defining one is a major version bump.
    """

    DEMAND_VOLUME = "DEMAND_VOLUME"
    QUERY_SUGGESTION = "QUERY_SUGGESTION"
    SERP_COMPOSITION = "SERP_COMPOSITION"
    COMPETITOR_PRESENCE = "COMPETITOR_PRESENCE"
    QUESTION_DEMAND = "QUESTION_DEMAND"
    PAGE_PERFORMANCE = "PAGE_PERFORMANCE"


class EvidenceObservation(FrozenModel):
    """One provenance-tagged observation from one provider (§6.1)."""

    schema_version: StrictStr = Field(...)
    observation_id: StrictStr = Field(...)
    observation_type: ObservationType = Field(...)
    provider_id: StrictStr = Field(...)
    provider_version: StrictStr = Field(...)
    query: StrictStr = Field(...)
    query_params: Tuple[Tuple[StrictStr, StrictStr], ...] = Field(...)
    market_scope: StrictStr = Field(...)
    observed_at: StrictStr = Field(...)
    provenance: Provenance = Field(...)
    confidence_bp: Optional[StrictInt] = Field(None)
    metrics: Tuple[Tuple[StrictStr, StrictInt], ...] = Field(...)
    texts: Tuple[StrictStr, ...] = Field(...)
    raw_ref: Optional[StrictStr] = Field(None)
    derived_from: Tuple[StrictStr, ...] = Field(())

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_observation(self)

    @classmethod
    def build(cls, **fields: Any) -> "EvidenceObservation":
        """Construct with the content-derived ``observation_id`` computed."""
        fields.pop("observation_id", None)
        candidate = dict(fields)
        candidate["observation_id"] = compute_observation_id(fields)
        return cls(**candidate)


def _observation_identity_payload(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a field dict for hashing: drop the id, fill defaults.

    Filling defaults here guarantees a partial caller dict and a fully
    populated instance always produce the same content hash (§4.2).
    """
    payload = dict(fields)
    payload.pop("observation_id", None)
    payload.setdefault("confidence_bp", None)
    payload.setdefault("raw_ref", None)
    payload.setdefault("derived_from", ())
    return payload


def compute_observation_id(fields: Dict[str, Any]) -> str:
    """SHA-256 of the canonical form of every field except the id itself."""
    return sha256_of_text(canonical_json(_observation_identity_payload(fields)))


def _validate_sorted_unique_pairs(
    pairs: Tuple[Tuple[str, Any], ...], label: str
) -> None:
    keys = [key for key, _ in pairs]
    if keys != sorted(keys):
        raise ContractValidationError(
            "%s must be sorted by name for deterministic ordering (§4.3)"
            % label
        )
    if len(keys) != len(set(keys)):
        raise ContractValidationError("%s must have unique names" % label)


def validate_observation(observation: EvidenceObservation) -> None:
    """All semantic rules for an EvidenceObservation (§5, §6)."""
    for name in ("schema_version", "provider_id", "provider_version",
                 "market_scope", "observed_at"):
        if not getattr(observation, name):
            raise ContractValidationError("%s must be non-empty" % name)
    _validate_sorted_unique_pairs(observation.query_params, "query_params")
    _validate_sorted_unique_pairs(observation.metrics, "metrics")
    if tuple(observation.texts) != tuple(sorted(observation.texts)):
        raise ContractValidationError(
            "texts must be sorted for deterministic ordering (§4.3)"
        )
    validate_confidence_bp(observation.provenance, observation.confidence_bp)

    if observation.provenance is Provenance.DERIVED:
        if not observation.derived_from:
            raise ContractValidationError(
                "DERIVED observations must reference their source "
                "observations (§5.2b)"
            )
    elif observation.derived_from:
        raise ContractValidationError(
            "derived_from is forbidden unless provenance is DERIVED (§6.1)"
        )
    if list(observation.derived_from) != sorted(set(observation.derived_from)):
        raise ContractValidationError(
            "derived_from must be sorted and unique (§4.3)"
        )

    if observation.provenance in (Provenance.VERIFIED, Provenance.OPERATOR):
        if not observation.raw_ref:
            raise ContractValidationError(
                "%s observations must carry a content-addressed raw_ref "
                "(§6.2, §20)" % observation.provenance.value
            )
    if observation.raw_ref is not None and not _HEX64.match(observation.raw_ref):
        raise ContractValidationError(
            "raw_ref must be a 64-hex SHA-256 content reference (§6.2)"
        )

    expected = compute_observation_id(
        {name: getattr(observation, name) for name in observation.__fields__}
    )
    if observation.observation_id != expected:
        raise ContractValidationError(
            "observation_id does not match content hash — identity is "
            "content-derived (§4.2); use EvidenceObservation.build()"
        )


class EvidenceSnapshot(FrozenModel):
    """An immutable, content-addressed set of observations (§6.3).

    Observations are stored sorted by ``observation_id``; the snapshot's
    identity is the SHA-256 of the canonical form of its own fields. An
    empty snapshot is legal (§6.4) — absent evidence evaluates as UNKNOWN.
    """

    schema_version: StrictStr = Field(...)
    snapshot_id: StrictStr = Field(...)
    evidence_model_version: StrictStr = Field(...)
    market_scope: StrictStr = Field(...)
    label: StrictStr = Field("")
    observations: Tuple[EvidenceObservation, ...] = Field(...)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        validate_snapshot(self)

    @classmethod
    def build(cls, **fields: Any) -> "EvidenceSnapshot":
        """Construct with sorted observations and a computed ``snapshot_id``."""
        fields.pop("snapshot_id", None)
        observations = tuple(
            sorted(fields.get("observations", ()),
                   key=lambda item: item.observation_id)
        )
        fields["observations"] = observations
        candidate = dict(fields)
        candidate["snapshot_id"] = compute_snapshot_id(fields)
        return cls(**candidate)


def compute_snapshot_id(fields: Dict[str, Any]) -> str:
    """SHA-256 of the canonical form of every field except the id itself.

    Defaults are filled before hashing so partial caller dicts and full
    instances always agree (§4.2).
    """
    payload = dict(fields)
    payload.pop("snapshot_id", None)
    payload.setdefault("label", "")
    return sha256_of_text(canonical_json(payload))


def validate_snapshot(snapshot: EvidenceSnapshot) -> None:
    """All semantic rules for an EvidenceSnapshot (§6.3)."""
    for name in ("schema_version", "evidence_model_version", "market_scope"):
        if not getattr(snapshot, name):
            raise ContractValidationError("%s must be non-empty" % name)
    ids = [obs.observation_id for obs in snapshot.observations]
    if ids != sorted(ids):
        raise ContractValidationError(
            "observations must be sorted by observation_id (§4.3)"
        )
    if len(ids) != len(set(ids)):
        raise ContractValidationError(
            "observations must have unique observation_ids"
        )
    expected = compute_snapshot_id(
        {name: getattr(snapshot, name) for name in snapshot.__fields__}
    )
    if snapshot.snapshot_id != expected:
        raise ContractValidationError(
            "snapshot_id does not match content hash — identity is "
            "content-derived (§6.3); use EvidenceSnapshot.build()"
        )
