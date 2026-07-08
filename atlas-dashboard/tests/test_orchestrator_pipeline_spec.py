"""
atlas/tests/test_orchestrator_pipeline_spec.py

Unit tests for core/orchestration/{stage_spec,pipeline_spec}.py —
the AES-006 Atlas Orchestrator's pure declarative data structures.

No I/O, no persistence, no subsystem coupling.
"""

from __future__ import annotations

import pytest

from core.orchestration.pipeline_spec import PipelineSpec, PipelineSpecError, validate
from core.orchestration.stage_spec import StageSpec


def _noop(**kwargs):
    return None


def test_validate_accepts_well_formed_pipeline():
    spec = PipelineSpec(
        pipeline_name="sample",
        pipeline_version="1.0.0",
        seed_keys=("raw_input",),
        stages=(
            StageSpec(name="stage_a", handler=_noop, input_keys=("raw_input",), output_key="a_out"),
            StageSpec(name="stage_b", handler=_noop, input_keys=("a_out",), output_key="b_out"),
        ),
    )
    validate(spec)  # should not raise


def test_validate_rejects_empty_stages():
    spec = PipelineSpec(pipeline_name="empty", pipeline_version="1.0.0", stages=())
    with pytest.raises(PipelineSpecError, match="at least one stage"):
        validate(spec)


def test_validate_rejects_duplicate_stage_names():
    spec = PipelineSpec(
        pipeline_name="dupes",
        pipeline_version="1.0.0",
        stages=(
            StageSpec(name="stage_a", handler=_noop, output_key="out_a"),
            StageSpec(name="stage_a", handler=_noop, output_key="out_b"),
        ),
    )
    with pytest.raises(PipelineSpecError, match="duplicate stage name"):
        validate(spec)


def test_validate_rejects_unresolvable_input_keys():
    spec = PipelineSpec(
        pipeline_name="unresolvable",
        pipeline_version="1.0.0",
        stages=(
            StageSpec(name="stage_a", handler=_noop, input_keys=("never_produced",), output_key="out_a"),
        ),
    )
    with pytest.raises(PipelineSpecError, match="never_produced"):
        validate(spec)


def test_validate_allows_input_keys_satisfied_by_seed_keys():
    spec = PipelineSpec(
        pipeline_name="seeded",
        pipeline_version="1.0.0",
        seed_keys=("seed_value",),
        stages=(
            StageSpec(name="stage_a", handler=_noop, input_keys=("seed_value",), output_key="out_a"),
        ),
    )
    validate(spec)  # should not raise


def test_validate_allows_input_keys_satisfied_by_earlier_stage_output():
    spec = PipelineSpec(
        pipeline_name="chained",
        pipeline_version="1.0.0",
        stages=(
            StageSpec(name="stage_a", handler=_noop, output_key="out_a"),
            StageSpec(name="stage_b", handler=_noop, input_keys=("out_a",), output_key="out_b"),
        ),
    )
    validate(spec)  # should not raise


def test_stage_spec_and_pipeline_spec_are_frozen():
    stage = StageSpec(name="stage_a", handler=_noop, output_key="out_a")
    with pytest.raises(Exception):
        stage.name = "renamed"  # type: ignore[misc]

    spec = PipelineSpec(pipeline_name="frozen", pipeline_version="1.0.0", stages=(stage,))
    with pytest.raises(Exception):
        spec.pipeline_name = "renamed"  # type: ignore[misc]
