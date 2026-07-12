"""BrandEngine behavior: determinism, family resolution, voice, and
artifact-store integration (AES-WEB-001 §5.2 / Part 2 / Part 13 Phase 2).
"""

from __future__ import annotations

import pytest

from engines.website_generation import ArtifactKind, BrandPackage, BusinessSpec
from engines.website_generation.brand import BrandEngine
from engines.website_generation.constants.brand import BANNED_VOICE_PHRASES
from engines.website_generation.contracts.artifacts import artifact_sha256, canonical_artifact_json
from engines.website_generation.contracts.errors import BrandResolutionError
from engines.website_generation.speccompiler.business_spec_compiler import BusinessSpecCompiler
from repositories.artifact_store_repository import ArtifactStoreRepository


def _civic_spec() -> BusinessSpec:
    from engines.website_generation.contracts.artifacts import SpecCompilerInput

    compiler_input = SpecCompilerInput(
        business_name="Summit Legal Advisors",
        niche="professional legal services",
        audience="B2B clients seeking counsel",
        value_proposition="Reliable professional legal services for growing firms",
        directory_taxonomy=("contracts", "compliance"),
        monetization_model="retainer",
        upstream_hashes={},
    )
    return BusinessSpecCompiler().compile(compiler_input)


def _invalid_spec() -> BusinessSpec:
    return BusinessSpec(
        schema_version="1.0.0",
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name="",
        niche="",
        audience="valid audience",
        value_proposition="   ",
    )


class TestDeterminism:
    def test_deterministic_equality(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        engine = BrandEngine()
        first = engine.resolve(spec)
        second = engine.resolve(spec)
        assert canonical_artifact_json(first) == canonical_artifact_json(second)

    def test_identical_artifact_hashes_across_repeated_calls(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        engine = BrandEngine()
        hashes = {artifact_sha256(engine.resolve(spec)) for _ in range(3)}
        assert len(hashes) == 1

    def test_identical_results_across_fresh_engine_instances(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        hashes = {artifact_sha256(BrandEngine().resolve(spec)) for _ in range(3)}
        assert len(hashes) == 1


class TestPetTripFinderGolden:
    def test_resolves_to_field_guide(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        package = BrandEngine().resolve(spec)
        # field_guide's distinguishing focus-ring amber; no other family
        # uses this exact value for focus.ring.
        assert package.palette["color.focus.ring"] == "#b45309"

    def test_palette_includes_spruce_amber_and_wayfinding_blue(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        package = BrandEngine().resolve(spec)
        values = set(package.palette.values())
        assert "#2e5544" in values  # spruce (action.primary)
        assert "#b45309" in values  # trail-marker amber (focus.ring)
        assert "#1a5f8a" in values  # wayfinding blue (text.link / action.secondary)

    def test_display_typography_is_slab_travel_guide_oriented(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        package = BrandEngine().resolve(spec)
        display = package.type_scale["typography.heading.display"]
        assert "Rockwell" in display or "Slab" in display

    def test_price_stack_indicates_tabular_numerals(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        package = BrandEngine().resolve(spec)
        assert "tabular-nums" in package.type_scale["typography.price.default"]

    def test_voice_is_deterministic(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        first = BrandEngine().resolve(spec).voice_profile
        second = BrandEngine().resolve(spec).voice_profile
        assert first == second

    def test_voice_contains_no_banned_phrases(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        voice = BrandEngine().resolve(spec).voice_profile.lower()
        for phrase in BANNED_VOICE_PHRASES:
            assert phrase not in voice

    def test_voice_is_mature_travel_guide_register(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        voice = BrandEngine().resolve(spec).voice_profile.lower()
        assert "travel-guide" in voice
        assert "verification-first" in voice


class TestFamilyDifferentiation:
    def test_civic_shaped_spec_differs_from_field_guide(self, golden_compiler_input):
        field_guide_spec = BusinessSpecCompiler().compile(golden_compiler_input)
        field_guide_package = BrandEngine().resolve(field_guide_spec)
        civic_package = BrandEngine().resolve(_civic_spec())

        assert civic_package.palette != field_guide_package.palette
        assert civic_package.type_scale != field_guide_package.type_scale
        assert civic_package.voice_profile != field_guide_package.voice_profile
        for phrase in BANNED_VOICE_PHRASES:
            assert phrase not in civic_package.voice_profile.lower()


class TestValidation:
    def test_invalid_spec_raises_brand_resolution_error(self):
        with pytest.raises(BrandResolutionError) as excinfo:
            BrandEngine().resolve(_invalid_spec())
        missing = excinfo.value.diagnostics["missing_fields"]
        assert "business_name" in missing
        assert "niche" in missing
        assert "value_proposition" in missing
        assert "audience" not in missing
        assert excinfo.value.stage == "brand_resolution"
        assert excinfo.value.retryable is False


class TestArtifactStoreIntegration:
    def test_brand_package_stores_after_storing_its_business_spec_source(
        self, golden_compiler_input, tmp_path
    ):
        store = ArtifactStoreRepository(tmp_path / "cas")
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        spec_hash = store.put(spec)
        assert spec_hash == artifact_sha256(spec)

        package = BrandEngine().resolve(spec)
        assert package.source_hashes == {"business_spec": spec_hash}

        package_hash = store.put(package)
        assert package_hash == artifact_sha256(package)
        assert store.exists(package_hash)

        loaded = store.get(package_hash, ArtifactKind.BRAND_PACKAGE)
        assert isinstance(loaded, BrandPackage)
        assert loaded.voice_profile == package.voice_profile
        assert loaded.contrast_evidence == package.contrast_evidence
