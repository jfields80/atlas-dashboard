"""Public-surface audit and legacy-package protection (Sprint 1).

Asserts the package exports exactly the approved Phase 1 surface (§3.4),
that internal helpers stay internal, and that the legacy
``engines/website_generator`` and ``engines/website_intelligence``
packages remain present, importable, and independent of the new package.
"""

from __future__ import annotations

from pathlib import Path

import engines.website_generation as wge

REPO_ROOT = Path(__file__).resolve().parents[3]

EXPECTED_PUBLIC_SURFACE = {
    # pipeline + engines
    "WebsiteGenerationPipeline",
    "WebsiteGenerationBuildResult",
    "BusinessSpecCompiler",
    # artifact models
    "ArtifactHeader",
    "BrandPackage",
    "BuildManifest",
    "BusinessSpec",
    "ComponentInstance",
    "ComponentManifest",
    "ContentBlock",
    "ContentCandidate",
    "ContentPackage",
    "GateResult",
    "LaunchCertificateBody",
    "LayoutPlan",
    "LayoutRegion",
    "PageComponents",
    "PageLayout",
    "PagePlan",
    "QualityReport",
    "RenderedPage",
    "RenderedPageSet",
    "SEOEntry",
    "SEOPackage",
    "SiteArchitecture",
    "SiteBundle",
    "SpecCompilerInput",
    "StageRecord",
    "TransitionRecord",
    # serialization / identity helpers
    "artifact_sha256",
    "canonical_artifact_json",
    "canonical_json",
    "sha256_of_text",
    # enums
    "ArtifactKind",
    "ArtifactLifecycleState",
    "BuildState",
    "GateSeverity",
    "StageExecutionStatus",
    "StageOutcome",
    # errors
    "ArtifactIntegrityError",
    "ArtifactNotFoundError",
    "ArtifactValidationError",
    "IllegalTransitionError",
    "RepositoryCorruptionError",
    "SchemaRegistrationError",
    "SpecCompilationError",
    "UnsupportedSchemaVersionError",
    "WebsiteGenerationError",
    # registries
    "ENGINE_VERSIONS",
    "SCHEMA_VERSIONS",
    "registered_artifact_model",
    "registered_schema_versions",
}


class TestPublicSurface:
    def test_all_matches_approved_surface_exactly(self):
        assert set(wge.__all__) == EXPECTED_PUBLIC_SURFACE

    def test_every_export_resolves(self):
        for name in wge.__all__:
            assert getattr(wge, name, None) is not None, name

    def test_internal_helpers_not_exported(self):
        for internal in (
            "FrozenModel",  # contract base — internal at the top level
            "model_to_dict",
            "model_from_dict",
            "transition",
            "ALLOWED_TRANSITIONS",
            "register_artifact_model",
        ):
            assert internal not in wge.__all__


class TestAuthorizedPackageTree:
    def test_phase1_tree_exists(self):
        base = REPO_ROOT / "engines" / "website_generation"
        for relative in (
            "__init__.py",
            "contracts/__init__.py",
            "contracts/artifacts.py",
            "contracts/interfaces.py",
            "contracts/enums.py",
            "contracts/errors.py",
            "contracts/versions.py",
            "constants/__init__.py",
            "constants/build.py",
            "constants/brand.py",
            "constants/seo.py",
            "constants/gates.py",
            "speccompiler/__init__.py",
            "speccompiler/business_spec_compiler.py",
            "pipeline/__init__.py",
            "pipeline/website_generation_pipeline.py",
            "pipeline/state_machine.py",
        ):
            assert (base / relative).is_file(), relative

    def test_no_unauthorized_later_phase_packages(self):
        base = REPO_ROOT / "engines" / "website_generation"
        present = {p.name for p in base.iterdir() if p.is_dir()}
        present.discard("__pycache__")
        assert present == {
            "contracts",
            "constants",
            "speccompiler",
            "pipeline",
        }


class TestLegacyPackageProtection:
    def test_legacy_packages_remain_present(self):
        for package in ("website_generator", "website_intelligence"):
            path = REPO_ROOT / "engines" / package / "__init__.py"
            assert path.is_file(), package

    def test_legacy_packages_still_import(self):
        import engines.website_generator  # noqa: F401
        import engines.website_intelligence  # noqa: F401

    def test_legacy_packages_do_not_reference_new_namespace(self):
        for package in ("website_generator", "website_intelligence"):
            for path in (REPO_ROOT / "engines" / package).rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                assert "engines.website_generation" not in text, str(path)
