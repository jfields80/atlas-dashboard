"""
atlas/core/orchestration/stage_spec.py

Declarative description of a single pipeline stage.

A ``StageSpec`` carries no execution state and imports no subsystem
code — it is pure data. The orchestrator runner reads ``input_keys``
and ``output_key`` to wire stages together via a shared context dict,
and calls ``handler`` to do the actual work.

Rules:
  - Frozen (immutable) — a spec must not change after construction.
  - No I/O, no persistence, no side effects live here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class StageSpec:
    """
    Declarative definition of one stage in a pipeline.

    Attributes:
        name: Unique stage name within its pipeline. Used for
            checkpointing (stored as ``stage_name`` in persistence).
        handler: Callable invoked with the stage's resolved inputs as
            keyword arguments (one per entry in ``input_keys``,
            resolved from the running pipeline context). Returns the
            stage's output value.
        input_keys: Context keys this stage reads. Each key must be
            satisfied either by the pipeline's declared seed keys or
            by an earlier stage's ``output_key``.
        output_key: Context key this stage's return value is stored
            under for later stages to consume.
        optional: If True, a failure in this stage does not fail the
            whole pipeline run (reserved for future use by the
            runner; carried here so specs can declare intent now).
    """

    name: str
    handler: Callable[..., Any]
    input_keys: tuple[str, ...] = ()
    output_key: str = ""
    optional: bool = False
