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
    # Information Architecture Engine (AES-WEB-001 §5.3 / Part 2 / Part 13
    # Phase 2; AES-WEB-002J.3). Not wired into pipeline execution.
    "InformationArchitectureEngine",
    # Content Engine (AES-WEB-001 §5.4 / Part 2; AES-WEB-002J.4). Not wired
    # into pipeline execution.
    "ContentEngine",
    # SEO Engine (AES-WEB-001 §5.8 / Part 2; AES-WEB-002J.5). Not wired into
    # pipeline execution.
    "SEOEngine",
    # Component Engine (AES-WEB-001 §5.5 / Part 2; AES-WEB-002J.6). Not wired
    # into pipeline execution.
    "ComponentEngine",
    # Layout Engine (AES-WEB-001 §5.6 / Part 2; AES-WEB-002J.7). Not wired
    # into pipeline execution.
    "LayoutEngine",
    # Renderer (AES-WEB-001 §5.7 / Part 2; AES-WEB-002J.8). Not wired into
    # pipeline execution.
    "Renderer",
    # Assembly Engine (AES-WEB-001 §5.9 / Part 2; AES-WEB-002J.10). Not wired
    # into pipeline execution.
    "AssemblyEngine",
    # artifact models
    "ArtifactHeader",
    "BrandPackage",
    "BuildManifest",
    "BusinessSpec",
    "ComponentInstance",
    "ComponentManifest",
    "ComponentPlacement",
    "ContentBlock",
    "ContentCandidate",
    "ContentPackage",
    "ContrastEvidence",
    "GateResult",
    "GridPlacement",
    "InternalLinkIntent",
    "LaunchCertificateBody",
    "LayoutPlan",
    "LayoutRegion",
    "PageComponents",
    "PageHierarchyEntry",
    "PageLayout",
    "PagePlan",
    "QualityReport",
    "BundleFile",
    "RegionLayoutDetail",
    "RenderedPage",
    "RenderedPageDetail",
    "RenderedPageSet",
    "ResponsiveSelection",
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
    "ArchitecturePlanningError",
    "ArtifactIntegrityError",
    "ArtifactNotFoundError",
    "ArtifactValidationError",
    "ContentValidationError",
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
            # AES-WEB-002J.3: same pattern — registered at schema 1.0.0 for
            # replay, but deliberately internal — the public SiteArchitecture
            # is the current (1.1.0) shape.
            "SiteArchitectureV1",
            # AES-WEB-002J.7: same pattern — registered at schema 1.0.0 for
            # replay, but deliberately internal — the public LayoutPlan is
            # the current (1.1.0) shape.
            "LayoutPlanV1",
            # LayoutEngineInterface follows the established pattern of every
            # other engine interface (BrandEngineInterface,
            # ComponentEngineInterface, ...): declared in contracts/
            # interfaces.py, never exported at the top level. Only the
            # concrete engine class is public.
            "LayoutEngineInterface",
            # LayoutCompositionError follows the AES-WEB-002J.5/J.6 precedent
            # (SEOCompilationError, ComponentResolutionError): declared in
            # contracts/errors.py, imported directly from there by tests,
            # never exported at the top level.
            "LayoutCompositionError",
            # AES-WEB-002J.8: same pattern as LayoutPlanV1 above -- registered
            # at schema 1.0.0 for replay, but deliberately internal -- the
            # public RenderedPageSet is the current (1.1.0) shape.
            "RenderedPageSetV1",
            # RendererInterface follows the established engine-interface
            # pattern (LayoutEngineInterface, ...): declared in contracts/
            # interfaces.py, never exported at the top level. Only the
            # concrete Renderer class is public.
            "RendererInterface",
            # RenderError follows the LayoutCompositionError precedent:
            # declared in contracts/errors.py, imported directly from there
            # by tests, never exported at the top level.
            "RenderError",
            # AES-WEB-002J.10: same pattern as RenderedPageSetV1 -- the 1.0.0
            # hash-only SiteBundle shape, registered for replay but
            # deliberately internal; the public SiteBundle is the 1.1.0 shape.
            "SiteBundleV1",
            # AssemblyEngineInterface / AssemblyError follow the
            # RendererInterface / RenderError precedent: declared in
            # contracts/, never exported at the top level. Only the concrete
            # AssemblyEngine class is public.
            "AssemblyEngineInterface",
            "AssemblyError",
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
            "constants/ia.py",
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

    # AES-WEB-002J.3 (AES-WEB-001 §5.3/Part 2/Part 13 Phase 2): the
    # Information Architecture Engine package, authorized by this delivery
    # only — an operator decision, not a mechanical consequence of an
    # earlier amendment.
    J3_AUTHORIZED_PACKAGES = {
        "ia",
    }

    # AES-WEB-002J.4 (AES-WEB-001 §5.4/Part 2): the Content Engine package,
    # authorized by this delivery only — an operator decision, not a
    # mechanical consequence of an earlier amendment.
    J4_AUTHORIZED_PACKAGES = {
        "content",
    }

    # AES-WEB-002J.5 (AES-WEB-001 §5.8/Part 2): the SEO Engine package,
    # authorized by this delivery only — an operator decision, not a
    # mechanical consequence of an earlier amendment.
    J5_AUTHORIZED_PACKAGES = {
        "seo",
    }

    # AES-WEB-002J.7 (AES-WEB-001 §5.6/Part 2/Part 13 Phase 2): the Layout
    # Engine package, authorized by this delivery only — an operator
    # decision, not a mechanical consequence of an earlier amendment.
    J7_AUTHORIZED_PACKAGES = {
        "layouts",
    }

    # AES-WEB-002J.8 (AES-WEB-001 §5.7/Part 2/Part 13 Phase 2): the Renderer
    # package, authorized by this delivery only — an operator decision, not
    # a mechanical consequence of an earlier amendment.
    J8_AUTHORIZED_PACKAGES = {
        "rendering",
    }

    # AES-WEB-002J.10 (AES-WEB-001 §5.9/Part 2/Part 13 Phase 2): the Assembly
    # Engine package, authorized by this delivery only — an operator
    # decision, not a mechanical consequence of an earlier amendment.
    J10_AUTHORIZED_PACKAGES = {
        "assembly",
    }

    AUTHORIZED_PACKAGES = (
        PHASE1_PACKAGES
        | A3_AUTHORIZED_PACKAGES
        | J2_AUTHORIZED_PACKAGES
        | J3_AUTHORIZED_PACKAGES
        | J4_AUTHORIZED_PACKAGES
        | J5_AUTHORIZED_PACKAGES
        | J7_AUTHORIZED_PACKAGES
        | J8_AUTHORIZED_PACKAGES
        | J10_AUTHORIZED_PACKAGES
    )

    def test_phase1_packages_present(self):
        base = REPO_ROOT / "engines" / "website_generation"
        present = {p.name for p in base.iterdir() if p.is_dir()}
        present.discard("__pycache__")
        assert self.PHASE1_PACKAGES <= present

    def test_no_unauthorized_later_phase_packages(self):
        # Every top-level package present must be authorized. The A3 future
        # tree is permitted; every other later-phase engine package (brand,
        # ia, content, layouts, seo) remains rejected until its own phase
        # authorizes it. "rendering" is authorized as of AES-WEB-002J.8 and
        # "assembly" as of AES-WEB-002J.10 (J8/J10_AUTHORIZED_PACKAGES above).
        base = REPO_ROOT / "engines" / "website_generation"
        present = {p.name for p in base.iterdir() if p.is_dir()}
        present.discard("__pycache__")
        unauthorized = present - self.AUTHORIZED_PACKAGES
        assert not unauthorized, (
            "unauthorized later-phase packages present: %s" % sorted(unauthorized)
        )

    def test_unauthorized_engine_packages_still_rejected(self):
        # Every AES-WEB-001 Part 2 engine package now exists and is authorized
        # (brand J.2, ia J.3, content J.4, seo J.5, layouts J.7, rendering
        # J.8, assembly J.10; components/gates via A3). What remains rejected
        # is anything that is NOT a WGE engine and must never appear under
        # engines/website_generation/: "deployment" is a service/adapter and
        # repository concern (AES-WEB-001 §5, §12, §3.5 DeploymentAdapter),
        # never a deterministic engine package here.
        base = REPO_ROOT / "engines" / "website_generation"
        present = {p.name for p in base.iterdir() if p.is_dir()}
        for forbidden in (
            "deployment",
        ):
            assert forbidden not in present, forbidden

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

    def test_aes_web_002j3_ia_tree_exists(self):
        # AES-WEB-002J.3 (AES-WEB-001 §5.3/Part 2/Part 13 Phase 2) creates
        # exactly the two authorized ia-package files -- no helper module
        # (unlike brand/'s token_resolver.py; AES-WEB-001 Part 2 authorizes
        # only one implementation file for ia/) and no layouts/, rendering/,
        # assembly/, content/, seo/, or gates/ additions (see
        # test_import_audit.py's ia-only import matrix and this module's
        # J3_AUTHORIZED_PACKAGES comment above).
        base = REPO_ROOT / "engines" / "website_generation"
        for relative in (
            "ia/__init__.py",
            "ia/information_architecture_engine.py",
        ):
            assert (base / relative).is_file(), relative

    def test_aes_web_002j4_content_tree_exists(self):
        # AES-WEB-002J.4 (AES-WEB-001 §5.4/Part 2) creates exactly the three
        # authorized content-package files -- no content_resolver.py, no
        # phrase-library or template module, and no layouts/, rendering/,
        # assembly/, seo/, or gates/ additions (see test_import_audit.py's
        # content-only import matrix and this module's
        # J4_AUTHORIZED_PACKAGES comment above).
        base = REPO_ROOT / "engines" / "website_generation"
        for relative in (
            "content/__init__.py",
            "content/content_engine.py",
            "content/content_validators.py",
        ):
            assert (base / relative).is_file(), relative
        assert not (base / "content" / "content_resolver.py").exists()

    def test_aes_web_002j5_seo_tree_exists(self):
        # AES-WEB-002J.5 (AES-WEB-001 §5.8/Part 2) creates exactly the three
        # authorized SEO Engine files -- no seo_checks.py, no
        # structured-data module, and no layouts/, rendering/, or assembly/
        # additions (see test_import_audit.py's seo-only import matrix and
        # this module's J5_AUTHORIZED_PACKAGES comment above). Pins the
        # exact seo/ file list: nothing more, nothing less.
        base = REPO_ROOT / "engines" / "website_generation"
        expected = {
            "seo/__init__.py",
            "seo/seo_engine.py",
            "seo/seo_validators.py",
        }
        for relative in expected:
            assert (base / relative).is_file(), relative
        seo_dir = base / "seo"
        present = {"seo/" + p.name for p in seo_dir.iterdir() if p.is_file()}
        assert present == expected

    def test_aes_web_002j7_layouts_tree_exists(self):
        # AES-WEB-002J.7 (AES-WEB-001 §5.6/Part 2) creates exactly the two
        # authorized layouts-package files -- no separate composition.py
        # helper (this delivery's algorithm fits in layout_engine.py), and
        # no rendering/ or assembly/ additions (see test_import_audit.py's
        # layouts-only import matrix and this module's
        # J7_AUTHORIZED_PACKAGES comment above). Pins the exact layouts/
        # file list: nothing more, nothing less.
        base = REPO_ROOT / "engines" / "website_generation"
        expected = {
            "layouts/__init__.py",
            "layouts/layout_engine.py",
        }
        for relative in expected:
            assert (base / relative).is_file(), relative
        layouts_dir = base / "layouts"
        present = {"layouts/" + p.name for p in layouts_dir.iterdir() if p.is_file()}
        assert present == expected

    def test_aes_web_002j8_rendering_tree_exists(self):
        # AES-WEB-002J.8 (AES-WEB-001 §5.7/Part 2) created the rendering
        # package foundation -- one orchestrator (renderer.py), one
        # HTML-primitives/emitter-table module (html_emitter.py), one
        # CSS-primitives module (css_emitter.py), and three per-family
        # emitter modules for the three J.8-authorized catalog waves
        # (layout_atoms, navigation, discovery). AES-WEB-002J.9 (AES-WEB-001
        # §5.7/Part 2) adds exactly four more per-family emitter modules for
        # the four remaining catalog waves (listings_profiles,
        # trust_conversion, seo_editorial, monetization_status), closing the
        # 72-component emitter table -- and no other rendering/ file, and no
        # assembly/ addition (see test_import_audit.py's rendering-only
        # import matrix and this module's J8_AUTHORIZED_PACKAGES comment
        # above). Pins the exact rendering/ file list: nothing more,
        # nothing less.
        base = REPO_ROOT / "engines" / "website_generation"
        expected = {
            # J.8 foundation
            "rendering/__init__.py",
            "rendering/renderer.py",
            "rendering/html_emitter.py",
            "rendering/css_emitter.py",
            "rendering/emitters_layout_atoms.py",
            "rendering/emitters_navigation.py",
            "rendering/emitters_discovery.py",
            # AES-WEB-002J.9 remaining family emitters
            "rendering/emitters_listings_profiles.py",
            "rendering/emitters_trust_conversion.py",
            "rendering/emitters_seo_editorial.py",
            "rendering/emitters_monetization_status.py",
        }
        for relative in expected:
            assert (base / relative).is_file(), relative
        rendering_dir = base / "rendering"
        present = {
            "rendering/" + p.name for p in rendering_dir.iterdir() if p.is_file()
        }
        assert present == expected

    def test_aes_web_002j10_assembly_tree_exists(self):
        # AES-WEB-002J.10 (AES-WEB-001 §5.9/Part 2) creates exactly the three
        # authorized assembly-package files -- one engine class
        # (assembly_engine.py) and one pure-builders module
        # (assembly_builders.py: route mapping, head injection, sitemap/
        # robots serialization) plus __init__.py -- and no deployment/ or
        # filesystem writer (see test_import_audit.py's assembly-only import
        # matrix + no-filesystem guard and this module's
        # J10_AUTHORIZED_PACKAGES comment above). Pins the exact assembly/
        # file list: nothing more, nothing less.
        base = REPO_ROOT / "engines" / "website_generation"
        expected = {
            "assembly/__init__.py",
            "assembly/assembly_engine.py",
            "assembly/assembly_builders.py",
        }
        for relative in expected:
            assert (base / relative).is_file(), relative
        assembly_dir = base / "assembly"
        present = {
            "assembly/" + p.name for p in assembly_dir.iterdir() if p.is_file()
        }
        assert present == expected

    def test_aes_web_002j6_component_engine_present(self):
        # AES-WEB-002J.6 (AES-WEB-001 §5.5/Part 2; AES-WEB-002 §14/§26/§29)
        # adds exactly one file to the already-authorized components/ tree:
        # component_engine.py, directly under components/ (the §29 file layout
        # and test_import_audit.py's group-"" whitelist both place it there).
        # No new top-level package, no flat catalog/filters/scoring/selector
        # modules -- selection stays in components/selection/, definitions in
        # components/catalog/ (authority > the implementation prompt's package
        # sketch, per the CLAUDE.md precedence rule).
        base = REPO_ROOT / "engines" / "website_generation"
        assert (base / "components" / "component_engine.py").is_file()

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
