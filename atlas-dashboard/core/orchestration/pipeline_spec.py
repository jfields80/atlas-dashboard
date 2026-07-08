"""
atlas/core/orchestration/pipeline_spec.py

Declarative description of an ordered pipeline: a name, a version, and
an ordered tuple of ``StageSpec`` entries.

A ``PipelineSpec`` is pure data — it does not know how to execute
itself (that is ``services/orchestrator/orchestrator_runner.py``'s
job) and does not import any concrete subsystem/engine/service code.
Subsystems register their own ``PipelineSpec`` with the pipeline
registry; the spec and the runner never hardcode subsystem knowledge.

Rules:
  - Frozen (immutable) — a spec must not change after construction.
  - ``validate`` never mutates the spec; it only raises on defects.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.orchestration.stage_spec import StageSpec


@dataclass(frozen=True)
class PipelineSpec:
    """
    Declarative definition of a full pipeline.

    Attributes:
        pipeline_name: Unique identifier used for registration,
            idempotency hashing, and persisted run records.
        pipeline_version: Semver-style string. Bump whenever the
            stage composition or a stage's handler behavior changes
            in a way that should invalidate prior idempotency caches.
        stages: Ordered stages executed in tuple order.
        seed_keys: Context keys the caller is expected to supply as
            the pipeline's initial seed payload (available to any
            stage from the start, without having been produced by an
            earlier stage).
    """

    pipeline_name: str
    pipeline_version: str
    stages: tuple[StageSpec, ...]
    seed_keys: tuple[str, ...] = ()


class PipelineSpecError(ValueError):
    """Raised when a PipelineSpec fails structural validation."""


def validate(spec: PipelineSpec) -> None:
    """
    Validates structural correctness of a ``PipelineSpec``.

    Checks:
      - At least one stage is declared.
      - Stage names are unique within the pipeline.
      - Every stage's ``input_keys`` are satisfiable — each key must
        be present in ``seed_keys`` or be an earlier stage's
        ``output_key``.

    Raises ``PipelineSpecError`` on the first violation found. Does
    not mutate ``spec``.
    """
    if not spec.stages:
        raise PipelineSpecError(
            f"Pipeline {spec.pipeline_name!r} must declare at least one stage"
        )

    seen_names: set[str] = set()
    available_keys: set[str] = set(spec.seed_keys)

    for stage in spec.stages:
        if stage.name in seen_names:
            raise PipelineSpecError(
                f"Pipeline {spec.pipeline_name!r} has duplicate stage name: "
                f"{stage.name!r}"
            )
        seen_names.add(stage.name)

        missing = [key for key in stage.input_keys if key not in available_keys]
        if missing:
            raise PipelineSpecError(
                f"Pipeline {spec.pipeline_name!r} stage {stage.name!r} requires "
                f"input keys {missing} that are not available from seed_keys "
                f"or any earlier stage's output_key"
            )

        if stage.output_key:
            available_keys.add(stage.output_key)
