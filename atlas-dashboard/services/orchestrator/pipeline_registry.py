"""
atlas/services/orchestrator/pipeline_registry.py

In-process registry of ``PipelineSpec`` declarations for the AES-006
Atlas Orchestrator.

Subsystems (current and future — AES-007+) register a
``PipelineSpec`` here to make it runnable via
``services/orchestrator/orchestrator_runner.py``. The registry itself
knows nothing about any specific subsystem: it only stores and
validates specs.

Rules:
  - Zero business logic — validation only, delegated to
    ``core.orchestration.pipeline_spec.validate``.
  - Zero I/O, zero persistence — this is an in-process, in-memory
    registry, not a database table.
"""

from __future__ import annotations

from core.orchestration.pipeline_spec import PipelineSpec, validate

_REGISTRY: dict[str, PipelineSpec] = {}


class PipelineAlreadyRegisteredError(ValueError):
    """Raised when registering a pipeline_name that is already registered."""


class PipelineNotFoundError(KeyError):
    """Raised when looking up a pipeline_name that has not been registered."""


def register_pipeline(spec: PipelineSpec) -> None:
    """
    Validates and registers a ``PipelineSpec``.

    Raises ``PipelineAlreadyRegisteredError`` if ``spec.pipeline_name``
    is already registered. Raises ``core.orchestration.pipeline_spec.
    PipelineSpecError`` if the spec fails structural validation.
    """
    if spec.pipeline_name in _REGISTRY:
        raise PipelineAlreadyRegisteredError(
            f"Pipeline already registered: {spec.pipeline_name!r}"
        )

    validate(spec)
    _REGISTRY[spec.pipeline_name] = spec


def get_pipeline(pipeline_name: str) -> PipelineSpec:
    """Returns the registered ``PipelineSpec`` for ``pipeline_name``."""
    try:
        return _REGISTRY[pipeline_name]
    except KeyError:
        raise PipelineNotFoundError(
            f"No pipeline registered with name: {pipeline_name!r}"
        ) from None


def list_pipelines() -> list[str]:
    """Returns the names of all currently registered pipelines."""
    return list(_REGISTRY.keys())


def clear_registry() -> None:
    """
    Removes all registered pipelines.

    Intended for test isolation only — production code should never
    need to clear the registry.
    """
    _REGISTRY.clear()
