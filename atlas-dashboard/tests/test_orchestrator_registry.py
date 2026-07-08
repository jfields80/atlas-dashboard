"""
atlas/tests/test_orchestrator_registry.py

Unit tests for services/orchestrator/pipeline_registry.py — the
AES-006 Atlas Orchestrator's in-process pipeline registration API.
"""

from __future__ import annotations

import pytest

from core.orchestration.pipeline_spec import PipelineSpec, PipelineSpecError
from core.orchestration.stage_spec import StageSpec
from services.orchestrator import pipeline_registry


def _noop(**kwargs):
    return None


@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensures registry state never leaks between tests."""
    pipeline_registry.clear_registry()
    yield
    pipeline_registry.clear_registry()


def _spec(name: str) -> PipelineSpec:
    return PipelineSpec(
        pipeline_name=name,
        pipeline_version="1.0.0",
        stages=(StageSpec(name="only_stage", handler=_noop, output_key="out"),),
    )


def test_register_and_get_pipeline():
    spec = _spec("pipeline_one")
    pipeline_registry.register_pipeline(spec)

    fetched = pipeline_registry.get_pipeline("pipeline_one")
    assert fetched is spec


def test_register_duplicate_name_raises():
    pipeline_registry.register_pipeline(_spec("dup_pipeline"))
    with pytest.raises(pipeline_registry.PipelineAlreadyRegisteredError):
        pipeline_registry.register_pipeline(_spec("dup_pipeline"))


def test_register_invalid_spec_raises_pipeline_spec_error():
    invalid_spec = PipelineSpec(pipeline_name="invalid", pipeline_version="1.0.0", stages=())
    with pytest.raises(PipelineSpecError):
        pipeline_registry.register_pipeline(invalid_spec)

    # A spec that failed validation must not be partially registered.
    with pytest.raises(pipeline_registry.PipelineNotFoundError):
        pipeline_registry.get_pipeline("invalid")


def test_get_unregistered_pipeline_raises_not_found():
    with pytest.raises(pipeline_registry.PipelineNotFoundError):
        pipeline_registry.get_pipeline("never_registered")


def test_list_pipelines_reflects_registered_names():
    pipeline_registry.register_pipeline(_spec("alpha"))
    pipeline_registry.register_pipeline(_spec("beta"))

    names = pipeline_registry.list_pipelines()
    assert set(names) == {"alpha", "beta"}
