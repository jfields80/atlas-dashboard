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
    # Brand Engine (AES-WEB-001 §5.2 / Part 2 / Part 13 Phase 2;
    # AES-WEB-002J.2). Not wired into pipeline execution.
    "BrandEngine",
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
    "ContrastEvidence",
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
            # AES-WEB-002J.2: same pattern — registered at schema 1.0.0 for
            # replay, but deliberately internal — the public BrandPackage is
            # the current (1.1.0) shape.
            "BrandPackageV1",
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

    # AES-WEB-002J.2 (AES-WEB-001 §5.2/Part 2/Part 13 Phase 2): the Brand
    # Engine package, authorized by this delivery only — an operator
    # decision, not a mechanical consequence of an earlier amendment.
    J2_AUTHORIZED_PACKAGES = {
        "brand",
    }

    AUTHORIZED_PACKAGES = (
        PHASE1_PACKAGES | A3_AUTHORIZED_PACKAGES | J2_AUTHORIZED_PACKAGES
    )

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
        # "brand" is authorized as of AES-WEB-002J.2 (see
        # J2_AUTHORIZED_PACKAGES above) and is intentionally no longer in
        # this list.
        base = REPO_ROOT / "engines" / "website_generation"
        present = {p.name for p in base.iterdir() if p.is_dir()}
        for later_phase in (
            "ia", "content", "layouts", "rendering", "seo", "assembly",
        ):
            assert later_phase not in present, later_phase

    def test_aes_web_002a_component_tree_exists(self):
        # AES-WEB-002A creates the §31 "New files" package areas: the
        # registry foundation plus the selection/validation/compatibility
        # skeleton packages.
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

    def test_aes_web_002i_gates_tree_exists(self):
        # AES-WEB-002I creates the §31/§29.1 "New files" gate-check package
        # area: exactly the five authorized check modules (component,
        # composition, rendering, commercial, responsive — see
        # test_import_audit.py's _AUTHORIZED_GATE_CHECK_MODULES and this
        # module's own A3_AUTHORIZED_PACKAGES["gates"] comment above). No
        # quality_gate_engine.py and no accessibility_checks.py/seo_checks.py
        # — see engines/website_generation/gates/__init__.py and
        # constants/gates.py's module docstrings for why.
        base = REPO_ROOT / "engines" / "website_generation"
        for relative in (
            "gates/__init__.py",
            "gates/checks/__init__.py",
            "gates/checks/component_checks.py",
            "gates/checks/composition_checks.py",
            "gates/checks/rendering_checks.py",
            "gates/checks/commercial_checks.py",
            "gates/checks/responsive_checks.py",
        ):
            assert (base / relative).is_file(), relative
        assert not (base / "gates" / "quality_gate_engine.py").exists()
        assert not (base / "gates" / "checks" / "accessibility_checks.py").exists()
        assert not (base / "gates" / "checks" / "seo_checks.py").exists()

    def test_aes_web_002j2_brand_tree_exists(self):
        # AES-WEB-002J.2 (AES-WEB-001 §5.2/Part 2/Part 13 Phase 2) creates
        # exactly the three authorized brand-package files — no layouts/,
        # rendering/, assembly/, ia/, content/, seo/, or gates/ additions
        # (see test_import_audit.py's brand-only import matrix and this
        # module's J2_AUTHORIZED_PACKAGES comment above).
        base = REPO_ROOT / "engines" / "website_generation"
        for relative in (
            "brand/__init__.py",
            "brand/brand_engine.py",
            "brand/token_resolver.py",
        ):
            assert (base / relative).is_file(), relative

    def test_catalog_wave_modules_exist(self):
        # §29.1 catalog module map: layout_atoms.py (Wave 1, 002B),
        # navigation.py (Wave 2, 002C), discovery.py (Wave 3, 002D),
        # listings_profiles.py (Wave 4, 002E), trust_conversion.py
        # (Wave 5, 002F), seo_editorial.py (Wave 6, 002G),
        # monetization_status.py (Wave 7, 002H — the eighth and final
        # catalog wave, closing the 72-component MVP catalog).
        # listings_profiles.py first existed early, per amendment A4
        # (§34.3-A4), carrying only the provisional listing.card.standard;
        # AES-WEB-002E completed it into the full §27.5 twelve-component
        # Wave 4 inventory — see its module docstring and
        # test_catalog_listing_provisional.py's (renamed)
        # TestAmendmentA4Provenance class.
        base = REPO_ROOT / "engines" / "website_generation" / "components" / "catalog"
        for relative in (
            "layout_atoms.py", "navigation.py", "discovery.py",
            "listings_profiles.py", "trust_conversion.py", "seo_editorial.py",
            "monetization_status.py",
        ):
            assert (base / relative).is_file(), relative


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
