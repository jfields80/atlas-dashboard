"""Frozen base model, canonical serialization, and content identity.

AES-SEO-001 §4.4: canonical form is UTF-8 JSON with sorted keys and compact
separators; artifact identity is sha256(canonical_json); canonicalization
rejects ``float`` values outright (integer-only numeric policy, AMB-4).

The pydantic v1/v2 isolation mirrors the established repository pattern in
``engines/website_generation/contracts/artifacts.py`` so the contracts pass
under the pinned v1 baseline (``docs/development/environment.md``) and under
a future v2 migration alike.

Semantic validation pattern: models needing cross-field rules override
``__init__`` and call an explicit module-level validator after construction.
This works identically under both pydantic majors and keeps every rule
readable in one named function (no hidden decorator machinery).
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Dict, Type, TypeVar

import pydantic
from pydantic import BaseModel

PYDANTIC_V2: bool = str(getattr(pydantic, "VERSION", "1.0")).startswith("2")

_M = TypeVar("_M", bound=BaseModel)


class DemandMappingContractError(ValueError):
    """Base error for every Demand Mapping contract violation."""


class ContractCanonicalizationError(DemandMappingContractError):
    """A value cannot be represented in canonical contract JSON."""


class ContractValidationError(DemandMappingContractError):
    """A contract instance violates an AES-SEO-001 semantic rule."""


class SchemaRegistrationError(DemandMappingContractError):
    """A schema version was registered twice (§19.2)."""


if PYDANTIC_V2:
    from pydantic import ConfigDict

    class FrozenModel(BaseModel):
        """Immutable base model (pydantic v2)."""

        model_config = ConfigDict(frozen=True, extra="forbid")

else:

    class FrozenModel(BaseModel):
        """Immutable base model (pydantic v1)."""

        class Config:
            frozen = True
            allow_mutation = False
            extra = "forbid"


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """Serialize a model to a plain dict under either pydantic major."""
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]
    return model.dict()


def model_from_dict(model_cls: Type[_M], data: Dict[str, Any]) -> _M:
    """Construct and validate a model from a dict under either major."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(data)  # type: ignore[attr-defined]
    return model_cls.parse_obj(data)


def _canonicalize(value: Any) -> Any:
    """Reduce a value to canonical JSON-serializable primitives.

    ``None`` is preserved (fields are never silently dropped), enums
    collapse to their string values, tuples emit as JSON arrays, and
    mapping keys must be strings so sorted-key output is total.
    """
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        raise ContractCanonicalizationError(
            "float values are not permitted in canonical Demand Mapping "
            "contracts (AES-SEO-001 §4.4, AMB-4)"
        )
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, BaseModel):
        return _canonicalize(model_to_dict(value))
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key in value:
            if not isinstance(key, str):
                raise ContractCanonicalizationError(
                    "canonical mappings require string keys, got %r"
                    % type(key).__name__
                )
            out[key] = _canonicalize(value[key])
        return out
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ContractCanonicalizationError(
        "unsupported canonical value type: %r" % type(value).__name__
    )


def canonical_json(payload: Any) -> str:
    """Canonical JSON: UTF-8, sorted keys, no insignificant whitespace."""
    return json.dumps(
        _canonicalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_contract_json(model: BaseModel) -> str:
    """Canonical JSON text of a frozen contract model."""
    return canonical_json(model_to_dict(model))


def sha256_of_text(text: str) -> str:
    """SHA-256 hex digest of UTF-8 encoded text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def contract_sha256(model: BaseModel) -> str:
    """Content identity of a contract: sha256(canonical_json) (§4.4)."""
    return sha256_of_text(canonical_contract_json(model))
