"""
atlas/services/orchestrator/pipelines/directory_launch.py

Registers the "directory_launch_v1" pipeline (AES-006 Phase 2) with
the orchestrator framework built in Phase 1.

Chain: Investment Committee Decision -> Blueprint -> Ingestion ->
Launch Kit -> Directory Builder -> Preview (optional).

This module contains no business logic — it only declares stage
order and wiring. All computation happens in the adapters
(``services/orchestrator/adapters/directory_launch_adapters.py``) and
the real services they call.

Registration is explicit, not automatic: callers must import and
invoke ``register_directory_launch_pipeline()`` before running this
pipeline via ``services.orchestrator.orchestrator_runner.run_pipeline``.
This keeps the framework's registration testable in isolation and
avoids forcing pipeline registration into the global app boot
sequence (consistent with the Phase 1 design).
"""

from __future__ import annotations

from core.orchestration.pipeline_spec import PipelineSpec
from core.orchestration.stage_spec import StageSpec
from services.orchestrator import pipeline_registry
from services.orchestrator.adapters.directory_launch_adapters import (
    blueprint_stage,
    build_stage,
    ingestion_stage,
    launch_kit_stage,
    preview_stage,
)

PIPELINE_NAME = "directory_launch_v1"
PIPELINE_VERSION = "1.0.0"


def build_directory_launch_spec() -> PipelineSpec:
    """Constructs (but does not register) the Directory Launch PipelineSpec."""
    return PipelineSpec(
        pipeline_name=PIPELINE_NAME,
        pipeline_version=PIPELINE_VERSION,
        seed_keys=(
            "conn",
            "committee_decision",
            "opportunity_extra",
            "raw_listings",
            "project_slug",
            "launch_kit_output_root",
            "projects_root",
            "preview_root",
        ),
        stages=(
            StageSpec(
                name="blueprint",
                handler=blueprint_stage,
                input_keys=("conn", "committee_decision", "opportunity_extra"),
                output_key="blueprint",
            ),
            StageSpec(
                name="ingestion",
                handler=ingestion_stage,
                input_keys=("conn", "blueprint", "raw_listings"),
                output_key="ingestion_result",
            ),
            StageSpec(
                name="launch_kit",
                handler=launch_kit_stage,
                input_keys=("blueprint", "ingestion_result", "project_slug", "launch_kit_output_root"),
                output_key="launch_kit_result",
            ),
            StageSpec(
                name="build",
                handler=build_stage,
                input_keys=("launch_kit_result", "projects_root"),
                output_key="build_result",
            ),
            StageSpec(
                name="preview",
                handler=preview_stage,
                input_keys=("build_result", "preview_root"),
                output_key="preview_result",
                optional=True,
            ),
        ),
    )


def register_directory_launch_pipeline() -> PipelineSpec:
    """
    Registers the Directory Launch pipeline with the orchestrator's
    pipeline registry. Safe to call once per process; calling it
    again after a prior successful registration raises
    ``pipeline_registry.PipelineAlreadyRegisteredError``.
    """
    spec = build_directory_launch_spec()
    pipeline_registry.register_pipeline(spec)
    return spec
