"""WebsiteGenerationPipeline — the single public deterministic entry point.

AES-WEB-001 Phase 1 golden skeleton. The pipeline composes only
Phase 1-available behavior:

* compiles the ``BusinessSpec`` through :class:`BusinessSpecCompiler`;
* applies the pure state machine for the one real transition
  (``INITIALIZED → SPEC_COMPILED``);
* emits a deterministic ``BuildManifest`` skeleton proving version,
  provenance, transition, and hash recording.

It does **not** pretend later engines exist. Unimplemented future stages
are recorded in the manifest as ``NOT_EXECUTED`` with no artifact hash —
never as successful — and the build's final state remains
``SPEC_COMPILED``. No fake BrandPackage, SiteArchitecture,
ContentPackage, or SiteBundle output is fabricated (Sprint 1 directive).

Purity: no I/O, no clock (``generated_at`` enters as an explicit
parameter), no UUIDs (``build_id`` is content-derived per §6.4:
``sha256(BusinessSpec hash + pipeline version + explicit build_salt)``).
Persistence belongs to repositories driven by the future service layer;
the pipeline returns its artifacts to the caller.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from engines.website_generation.constants.build import (
    ACTIVE_STAGE_SEQUENCE,
    PHASE1_EXECUTED_STAGES,
    PIPELINE_VERSION,
    STAGE_SPEC_COMPILATION,
)
from engines.website_generation.contracts.artifacts import (
    BuildManifest,
    BusinessSpec,
    FrozenModel,
    SpecCompilerInput,
    StageRecord,
    TransitionRecord,
    artifact_sha256,
    sha256_of_text,
)
from engines.website_generation.contracts.enums import (
    ArtifactKind,
    BuildState,
    StageExecutionStatus,
    StageOutcome,
)
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)
from engines.website_generation.pipeline.state_machine import transition
from engines.website_generation.speccompiler.business_spec_compiler import (
    BusinessSpecCompiler,
)

# Artifact kind each future stage will produce, recorded in the manifest
# so NOT_EXECUTED records still declare what the stage owes (§4.1).
_STAGE_ARTIFACT_KINDS: Dict[str, Optional[ArtifactKind]] = {
    "spec_compilation": ArtifactKind.BUSINESS_SPEC,
    "brand_resolution": ArtifactKind.BRAND_PACKAGE,
    "ia_planning": ArtifactKind.SITE_ARCHITECTURE,
    "content_drafting": ArtifactKind.CONTENT_CANDIDATE,
    "content_validation": ArtifactKind.CONTENT_PACKAGE,
    "component_resolution": ArtifactKind.COMPONENT_MANIFEST,
    "layout_composition": ArtifactKind.LAYOUT_PLAN,
    "rendering": ArtifactKind.RENDERED_PAGE_SET,
    "seo_compilation": ArtifactKind.SEO_PACKAGE,
    "assembly": ArtifactKind.SITE_BUNDLE,
    "gating": ArtifactKind.QUALITY_REPORT,
    "certification": ArtifactKind.QUALITY_REPORT,
    "packaging": ArtifactKind.BUILD_MANIFEST,
}


class WebsiteGenerationBuildResult(FrozenModel):
    """Frozen return value of a Phase 1 pipeline run.

    Not an artifact (the catalog holds exactly twelve kinds); simply the
    typed hand-off the future service layer will persist through the
    artifact store and build-state repositories.
    """

    business_spec: BusinessSpec
    build_manifest: BuildManifest


class WebsiteGenerationPipeline:
    """Single public deterministic entry point for the WGE (Phase 1)."""

    version = ENGINE_VERSIONS["website_generation_pipeline"]

    def __init__(self) -> None:
        self._compiler = BusinessSpecCompiler()

    def run(
        self,
        compiler_input: SpecCompilerInput,
        build_salt: str = "",
        generated_at: str = "",
    ) -> WebsiteGenerationBuildResult:
        """Run the Phase 1 golden skeleton.

        Identical inputs produce a byte-identical canonical
        ``BuildManifest`` with an identical hash across runs and process
        restarts (replayability contract, §1.1/§4.6).
        """
        # Stage 1 (the only executed Phase 1 stage): spec compilation.
        business_spec = self._compiler.compile(compiler_input)
        spec_hash = artifact_sha256(business_spec)

        # The one real state transition, applied through the pure law.
        state = BuildState.INITIALIZED
        transitions: List[TransitionRecord] = []
        next_state = transition(state, StageOutcome.SUCCESS)
        transitions.append(
            TransitionRecord(
                from_state=state,
                to_state=next_state,
                outcome=StageOutcome.SUCCESS.value,
            )
        )
        state = next_state  # SPEC_COMPILED — and it stays there.

        # Content-derived build identity (§6.4) — no UUIDs, no clock.
        build_id = sha256_of_text(
            spec_hash + PIPELINE_VERSION + str(build_salt)
        )

        stage_records = self._stage_records(spec_hash)

        build_manifest = BuildManifest(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.BUILD_MANIFEST],
            artifact_kind=ArtifactKind.BUILD_MANIFEST,
            source_hashes={"business_spec": spec_hash},
            build_id=build_id,
            pipeline_version=PIPELINE_VERSION,
            engine_versions=dict(ENGINE_VERSIONS),
            final_state=state,
            stage_records=stage_records,
            transitions=tuple(transitions),
            generated_at=str(generated_at),
        )

        return WebsiteGenerationBuildResult(
            business_spec=business_spec,
            build_manifest=build_manifest,
        )

    @staticmethod
    def _stage_records(spec_hash: str) -> Tuple[StageRecord, ...]:
        """Manifest records: one EXECUTED stage, the rest NOT_EXECUTED."""
        records: List[StageRecord] = []
        for stage_name in ACTIVE_STAGE_SEQUENCE:
            if stage_name in PHASE1_EXECUTED_STAGES:
                records.append(
                    StageRecord(
                        stage_name=stage_name,
                        status=StageExecutionStatus.EXECUTED,
                        artifact_kind=_STAGE_ARTIFACT_KINDS[stage_name],
                        artifact_hash=(
                            spec_hash
                            if stage_name == STAGE_SPEC_COMPILATION
                            else None
                        ),
                        engine_version=ENGINE_VERSIONS[
                            "business_spec_compiler"
                        ],
                    )
                )
            else:
                records.append(
                    StageRecord(
                        stage_name=stage_name,
                        status=StageExecutionStatus.NOT_EXECUTED,
                        artifact_kind=_STAGE_ARTIFACT_KINDS[stage_name],
                        artifact_hash=None,
                        engine_version=None,
                    )
                )
        return tuple(records)
