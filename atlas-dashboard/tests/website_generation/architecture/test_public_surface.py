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
    # selection-trace models (amendment A1; AES-WEB-002 §14.3)
    "SelectionCandidate",
    "SelectionScoreComponent",
    "SelectionTrace",
    "SiteArchitecture",
    "SiteBundle",
    "SlotSelectionTrace",
    "SpecCompilerInput",
    "StageRecord",
    "TransitionRecord",
    # component contracts (AES-WEB-002A)
    "AccessibilityContract",
    "AnalyticsContract",
    "ComponentDefinition",
    "ConversionContract",
    "DeprecationInfo",
    "DirectoryContract",
    "MonetizationContract",
    "PropSpec",
    "RenderingContract",
    "ResponsiveContract",
    "SEOContract",
    "SlotSpec",
    "VariantSpec",
    # component registry (AES-WEB-002A)
    "ComponentRegistry",
    "ComponentRegistryView",
    "RegistryInventoryEntry",
    "REGISTERED_COMPONENTS",
    "build_default_registry",
    "definition_fingerprint",
    "validate_definition",
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
    # component enums (AES-WEB-002A)
    "AssetRole",
    "CommercialPurpose",
    "ComponentFamily",
    "ConversionGoal",
    "LifecycleStatus",
    "ListingKind",
    "PageRole",
    "PropType",
    "RegionKind",
    "SemanticElement",
    "SlotCardinality",
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
    # component errors (AES-WEB-002A)
    "ComponentNotFoundError",
    "ComponentSystemError",
    "ConflictingComponentError",
    "DuplicateComponentError",
    "InvalidCompatibilityDeclarationError",
    "InvalidComponentDefinitionError",
    "UnsupportedComponentVersionError",
    # registries
    "ENGINE_VERSIONS",
    "SCHEMA_VERSIONS",
    "registered_artifact_model",
    "registered_schema_versions",
    # component-system versions (AES-WEB-002A)
    "COMPONENT_CONTRACT_SCHEMA_VERSION",
    "COMPONENT_SYSTEM_VERSIONS",
    "REGISTRY_FINGERPRINT_VERSION",
    "REGISTRY_VERSION",
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
            # A1 legacy compatibility model: registered at schema 1.0.0 for
            # replay, but deliberately internal — the public ComponentManifest
            # is the current (1.1.0) shape.
            "ComponentManifestV1",
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

    # Phase 1 packages physically present after Phase 1 delivery.
    PHASE1_PACKAGES = {
        "contracts",
        "constants",
        "speccompiler",
        "pipeline",
    }

    # Component-system packages authorized by amendment A3 (AES-WEB-002 §29.1,
    # §34.3-A3). Authorization only: these directories are physically created
    # by AES-WEB-002A, not by this amendment delivery, so they may be present
    # once 002A lands without violating the Phase 1 lock.
    A3_AUTHORIZED_PACKAGES = {
        "components",  # + catalog/ selection/ validation/ compatibility/
        "gates",       # + checks/ (component/composition/rendering/commercial/responsive)
    }

    AUTHORIZED_PACKAGES = PHASE1_PACKAGES | A3_AUTHORIZED_PACKAGES

    def test_phase1_packages_present(self):
        base = REPO_ROOT / "engines" / "website_generation"
        present = {p.name for p in base.iterdir() if p.is_dir()}
        present.discard("__pycache__")
        assert self.PHASE1_PACKAGES <= present

    def test_no_unauthorized_later_phase_packages(self):
        # Every top-level package present must be authorized. The A3 future
        # tree is permitted; every other later-phase engine package (brand,
        # ia, content, layouts, rendering, seo, assembly) remains rejected
        # until its own phase authorizes it.
        base = REPO_ROOT / "engines" / "website_generation"
        present = {p.name for p in base.iterdir() if p.is_dir()}
        present.discard("__pycache__")
        unauthorized = present - self.AUTHORIZED_PACKAGES
        assert not unauthorized, (
            "unauthorized later-phase packages present: %s" % sorted(unauthorized)
        )

    def test_unauthorized_engine_packages_still_rejected(self):
        # These AES-WEB-001 Part 2 engine packages belong to later WGE phases
        # and are NOT authorized by this amendment; they must not exist yet.
        base = REPO_ROOT / "engines" / "website_generation"
        present = {p.name for p in base.iterdir() if p.is_dir()}
        for later_phase in (
            "brand", "ia", "content", "layouts", "rendering", "seo", "assembly",
        ):
            assert later_phase not in present, later_phase

    def test_aes_web_002a_component_tree_exists(self):
        # AES-WEB-002A creates the §31 "New files" package areas: the
        # registry foundation plus the selection/validation/compatibility
        # skeleton packages. Gate-check modules remain a later wave (002I).
        base = REPO_ROOT / "engines" / "website_generation"
        for relative in (
            "components/__init__.py",
            "components/registry.py",
            "components/catalog/__init__.py",
            "components/selection/__init__.py",
            "components/selection/selector.py",
            "components/validation/__init__.py",
            "components/compatibility/__init__.py",
            "constants/components.py",
            "constants/analytics.py",
        ):
            assert (base / relative).is_file(), relative
        assert not (base / "gates").exists(), "gates/ is a later wave (002I)"

    def test_catalog_wave_modules_exist(self):
        # §29.1 catalog module map: layout_atoms.py (Wave 1, 002B),
        # navigation.py (Wave 2, 002C), discovery.py (Wave 3, 002D),
        # listings_profiles.py (Wave 4, 002E), trust_conversion.py
        # (Wave 5, 002F), seo_editorial.py (Wave 6, 002G).
        # listings_profiles.py first existed early, per amendment A4
        # (§34.3-A4), carrying only the provisional listing.card.standard;
        # AES-WEB-002E completed it into the full §27.5 twelve-component
        # Wave 4 inventory — see its module docstring and
        # test_catalog_listing_provisional.py's (renamed)
        # TestAmendmentA4Provenance class. monetization_status.py remains
        # unauthorized until its own wave (002H).
        base = REPO_ROOT / "engines" / "website_generation" / "components" / "catalog"
        for relative in (
            "layout_atoms.py", "navigation.py", "discovery.py",
            "listings_profiles.py", "trust_conversion.py", "seo_editorial.py",
        ):
            assert (base / relative).is_file(), relative
        for later_wave in (
            "monetization_status.py",
        ):
            assert not (base / later_wave).exists(), later_wave


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
