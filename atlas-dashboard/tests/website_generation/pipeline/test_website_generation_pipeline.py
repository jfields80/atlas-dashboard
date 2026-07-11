"""Golden skeleton pipeline tests (AES-WEB-001 Phase 1, §11.5).

Deliverable proof for Phase 1: a golden ``BuildManifest`` hash
reproduced twice — byte-identical canonical output across repeated runs
and fresh pipeline instances — with complete source hashes and version
maps for executed stages and no fake later-stage completion.
"""

from __future__ import annotations

import pytest

from engines.website_generation import (
    ENGINE_VERSIONS,
    ArtifactKind,
    BuildState,
    SpecCompilationError,
    SpecCompilerInput,
    StageExecutionStatus,
    WebsiteGenerationBuildResult,
    WebsiteGenerationPipeline,
    artifact_sha256,
    canonical_artifact_json,
    sha256_of_text,
)
from engines.website_generation.constants.build import (
    ACTIVE_STAGE_SEQUENCE,
    PHASE1_EXECUTED_STAGES,
    PIPELINE_VERSION,
)
from ..conftest import (
    FIXED_BUILD_SALT,
    FIXED_GENERATED_AT,
)


def _run(golden_compiler_input) -> WebsiteGenerationBuildResult:
    return WebsiteGenerationPipeline().run(
        golden_compiler_input,
        build_salt=FIXED_BUILD_SALT,
        generated_at=FIXED_GENERATED_AT,
    )


class TestGoldenSkeletonDeterminism:
    def test_same_input_twice_byte_identical_manifest(
        self, golden_compiler_input
    ):
        first = _run(golden_compiler_input)
        second = _run(golden_compiler_input)
        assert canonical_artifact_json(
            first.build_manifest
        ) == canonical_artifact_json(second.build_manifest)

    def test_manifest_hash_identical_across_repeated_runs(
        self, golden_compiler_input
    ):
        hashes = {
            artifact_sha256(_run(golden_compiler_input).build_manifest)
            for _ in range(3)
        }
        assert len(hashes) == 1

    def test_build_id_is_content_derived(self, golden_compiler_input):
        result = _run(golden_compiler_input)
        spec_hash = artifact_sha256(result.business_spec)
        expected = sha256_of_text(
            spec_hash + PIPELINE_VERSION + FIXED_BUILD_SALT
        )
        assert result.build_manifest.build_id == expected

    def test_different_salt_changes_build_id_only_not_spec(
        self, golden_compiler_input
    ):
        a = WebsiteGenerationPipeline().run(
            golden_compiler_input, build_salt="salt-a", generated_at=""
        )
        b = WebsiteGenerationPipeline().run(
            golden_compiler_input, build_salt="salt-b", generated_at=""
        )
        assert a.build_manifest.build_id != b.build_manifest.build_id
        assert artifact_sha256(a.business_spec) == artifact_sha256(
            b.business_spec
        )


class TestManifestProvenanceAndVersions:
    def test_source_hashes_reference_business_spec(
        self, golden_compiler_input
    ):
        result = _run(golden_compiler_input)
        assert result.build_manifest.source_hashes == {
            "business_spec": artifact_sha256(result.business_spec)
        }

    def test_engine_version_map_complete(self, golden_compiler_input):
        manifest = _run(golden_compiler_input).build_manifest
        assert manifest.engine_versions == dict(ENGINE_VERSIONS)
        assert manifest.pipeline_version == PIPELINE_VERSION

    def test_transition_recorded_through_pure_law(
        self, golden_compiler_input
    ):
        manifest = _run(golden_compiler_input).build_manifest
        assert len(manifest.transitions) == 1
        record = manifest.transitions[0]
        assert record.from_state == BuildState.INITIALIZED
        assert record.to_state == BuildState.SPEC_COMPILED
        assert record.outcome == "SUCCESS"

    def test_manifest_header_is_enforced(self, golden_compiler_input):
        manifest = _run(golden_compiler_input).build_manifest
        assert manifest.artifact_kind == ArtifactKind.BUILD_MANIFEST
        assert manifest.schema_version == "1.0.0"


class TestNoFakeLaterStageCompletion:
    def test_final_state_is_spec_compiled(self, golden_compiler_input):
        # Phase 1 does not advance past the one real stage.
        manifest = _run(golden_compiler_input).build_manifest
        assert manifest.final_state == BuildState.SPEC_COMPILED

    def test_only_spec_compilation_is_executed(self, golden_compiler_input):
        manifest = _run(golden_compiler_input).build_manifest
        executed = [
            r.stage_name
            for r in manifest.stage_records
            if r.status == StageExecutionStatus.EXECUTED
        ]
        assert tuple(executed) == PHASE1_EXECUTED_STAGES

    def test_future_stages_marked_not_executed_without_hashes(
        self, golden_compiler_input
    ):
        manifest = _run(golden_compiler_input).build_manifest
        for record in manifest.stage_records:
            if record.stage_name in PHASE1_EXECUTED_STAGES:
                assert record.artifact_hash is not None
                assert record.engine_version is not None
            else:
                assert record.status == StageExecutionStatus.NOT_EXECUTED
                assert record.artifact_hash is None
                assert record.engine_version is None

    def test_stage_records_cover_full_sequence_in_order(
        self, golden_compiler_input
    ):
        manifest = _run(golden_compiler_input).build_manifest
        assert tuple(
            r.stage_name for r in manifest.stage_records
        ) == ACTIVE_STAGE_SEQUENCE

    def test_no_fake_artifacts_returned(self, golden_compiler_input):
        result = _run(golden_compiler_input)
        # The Phase 1 result carries exactly the spec and the manifest —
        # no fabricated BrandPackage / SiteArchitecture / SiteBundle.
        fields = getattr(type(result), "model_fields", None) or type(
            result
        ).__fields__
        assert set(fields) == {
            "business_spec",
            "build_manifest",
        }


class TestPipelineFailurePropagation:
    def test_spec_compilation_error_propagates(self):
        with pytest.raises(SpecCompilationError):
            WebsiteGenerationPipeline().run(SpecCompilerInput())
