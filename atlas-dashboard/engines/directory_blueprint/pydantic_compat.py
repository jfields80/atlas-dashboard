"""Pydantic v1 / v2 compatibility helpers for the Directory Blueprint Engine.

The Atlas contract requires all Pydantic models in this subsystem to run
unmodified under Pydantic v1.x and v2.x. This module centralizes every
version-sensitive operation so the rest of the subsystem never touches a
version-specific API directly.

Rules for the rest of the subsystem:
    * Import ``BaseModel`` and ``Field`` from this module, never from
      ``pydantic`` directly.
    * Never call ``.dict()`` / ``.model_dump()`` on a model directly.
      Use ``model_to_dict`` / ``model_to_json`` / ``model_from_dict``.
    * Do not use ``@validator`` / ``@field_validator``. Validation beyond
      type coercion belongs in factory functions or the service layer.
"""

from __future__ import annotations

from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, Field  # noqa: F401  (re-exported)

try:  # Pydantic v2 exposes VERSION at pydantic.version.VERSION and pydantic.VERSION
    from pydantic import VERSION as _PYDANTIC_VERSION
except ImportError:  # pragma: no cover - extremely old pydantic
    _PYDANTIC_VERSION = "1.0"

PYDANTIC_V2: bool = str(_PYDANTIC_VERSION).startswith("2")

_M = TypeVar("_M", bound=BaseModel)


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """Serialize a model to a plain dict under either Pydantic major version."""
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]
    return model.dict()


def model_to_json(model: BaseModel) -> str:
    """Serialize a model to a JSON string under either Pydantic major version."""
    if hasattr(model, "model_dump_json"):
        return model.model_dump_json()  # type: ignore[attr-defined]
    return model.json()


def model_from_dict(model_cls: Type[_M], data: Dict[str, Any]) -> _M:
    """Construct and validate a model from a dict under either major version."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(data)  # type: ignore[attr-defined]
    return model_cls.parse_obj(data)


def model_from_json(model_cls: Type[_M], raw: str) -> _M:
    """Construct and validate a model from a JSON string."""
    if hasattr(model_cls, "model_validate_json"):
        return model_cls.model_validate_json(raw)  # type: ignore[attr-defined]
    return model_cls.parse_raw(raw)
