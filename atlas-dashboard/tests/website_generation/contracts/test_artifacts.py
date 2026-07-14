"""Artifact contract tests (AES-WEB-001 Phase 1).

Covers: all thirteen kinds registered at v1.0.0 (the original twelve, §4.1,
plus the AES-WEB-002J.17 additive ``LISTING_DATASET`` --
ADR-WEB-LISTING-DATASET), frozen behavior, canonical serialization
stability, hash identity/change, unsupported schema rejection, and
mandatory header enforcement.
"""

from __future__ import annotations

import json

import pytest

from engines.website_generation import (
    SCHEMA_VERSIONS,
    ArtifactKind,
    BrandPackage,
    BuildManifest,
    BuildState,
    BusinessSpec,
    ComponentManifest,
    ComponentPlacement,
    ContentCandidate,
    ContentPackage,
    ContrastEvidence,
    GridPlacement,
    InternalLinkIntent,
    LayoutPlan,
    LayoutRegion,
    ListingDataset,
    PageHierarchyEntry,
    PageLayout,
    QualityReport,
    RegionLayoutDetail,
    RenderedPage,
    RenderedPageDetail,
    RenderedPageSet,
    ResponsiveSelection,
    SEOPackage,
    SchemaRegistrationError,
    SelectionCandidate,
    SelectionScoreComponent,
    SelectionTrace,
    SiteArchitecture,
    SiteBundle,
    SlotSelectionTrace,
    UnsupportedSchemaVersionError,
    artifact_sha256,
    canonical_artifact_json,
    canonical_json,
    registered_artifact_model,
    registered_schema_versions,
)
from engines.website_generation.contracts.artifacts import (
    ArtifactCanonicalizationError,
    BrandPackageV1,
    BundleFile,
    ComponentManifestV1,
    GateResult,
    LayoutPlanV1,
    QualityReportV1,
    RenderedPageSetV1,
    SiteArchitectureV1,
    SiteBundleV1,
    model_to_dict,
)
from engines.website_generation.contracts.enums import GateSeverity
from engines.website_generation.contracts.enums import RegionKind
from engines.website_generation.contracts.versions import (
    register_artifact_model,
)

ALL_KINDS = list(ArtifactKind)


def _make_spec(**overrides) -> BusinessSpec:
    fields = dict(
        schema_version="1.0.0",
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={"external:project": "a" * 64},
        business_name="Pet Trip Finder",
        niche="pet travel",
        audience="pet owners",
        value_proposition="verified pet-friendly stays",
        directory_taxonomy=("hotels", "parks"),
    )
    fields.update(overrides)
    return BusinessSpec(**fields)


class TestCatalogRegistration:
    def test_exactly_thirteen_artifact_kinds(self):
        # Twelve from AES-WEB-001 §4.1, plus the AES-WEB-002J.17 additive
        # LISTING_DATASET (ADR-WEB-LISTING-DATASET) -- the first artifact
        # kind added to the catalog since Phase 1.
        assert len(ALL_KINDS) == 13

    def test_all_thirteen_kinds_registered_at_v1(self):
        for kind in ALL_KINDS:
            model_cls = registered_artifact_model(kind, "1.0.0")
            assert model_cls is not None

    def test_schema_versions_map_covers_every_kind(self):
        # Amendment A1: ComponentManifest current schema is 1.1.0.
        # AES-WEB-002J.2 (AES-WEB-001 §5.2/Part 2): BrandPackage current
        # schema is likewise 1.1.0 (additive radius_scale/extended_tokens/
        # contrast_evidence). AES-WEB-002J.3 (AES-WEB-001 §5.3/Part 2):
        # SiteArchitecture current schema is likewise 1.1.0 (additive
        # page_ids/page_hierarchy/internal_link_topology). AES-WEB-002J.7
        # (AES-WEB-001 §5.6/Part 2): LayoutPlan current schema is likewise
        # 1.1.0 (additive region_details). AES-WEB-002J.8 (AES-WEB-001
        # §5.7/Part 2): RenderedPageSet current schema is likewise 1.1.0
        # (additive page_details/shared_css). Every other kind remains 1.0.0.
        assert set(SCHEMA_VERSIONS) == set(ALL_KINDS)
        assert SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST] == "1.1.0"
        assert SCHEMA_VERSIONS[ArtifactKind.BRAND_PACKAGE] == "1.1.0"
        assert SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE] == "1.1.0"
        assert SCHEMA_VERSIONS[ArtifactKind.LAYOUT_PLAN] == "1.1.0"
        assert SCHEMA_VERSIONS[ArtifactKind.RENDERED_PAGE_SET] == "1.1.0"
        assert SCHEMA_VERSIONS[ArtifactKind.SITE_BUNDLE] == "1.1.0"
        assert SCHEMA_VERSIONS[ArtifactKind.QUALITY_REPORT] == "1.1.0"
        _minor_bumped = (
            ArtifactKind.COMPONENT_MANIFEST,
            ArtifactKind.BRAND_PACKAGE,
            ArtifactKind.SITE_ARCHITECTURE,
            ArtifactKind.LAYOUT_PLAN,
            ArtifactKind.RENDERED_PAGE_SET,
            ArtifactKind.SITE_BUNDLE,
            ArtifactKind.QUALITY_REPORT,
        )
        for kind in ALL_KINDS:
            if kind in _minor_bumped:
                continue
            assert SCHEMA_VERSIONS[kind] == "1.0.0"

    def test_registered_schema_versions_projection(self):
        versions = registered_schema_versions()
        assert set(versions) == set(ALL_KINDS)
        _minor_bumped = (
            ArtifactKind.COMPONENT_MANIFEST,
            ArtifactKind.BRAND_PACKAGE,
            ArtifactKind.SITE_ARCHITECTURE,
            ArtifactKind.LAYOUT_PLAN,
            ArtifactKind.RENDERED_PAGE_SET,
            ArtifactKind.SITE_BUNDLE,
            ArtifactKind.QUALITY_REPORT,
        )
        for kind in ALL_KINDS:
            if kind in _minor_bumped:
                # A1 / AES-WEB-002J.2 / AES-WEB-002J.3 / AES-WEB-002J.7 /
                # AES-WEB-002J.8 / AES-WEB-002J.10 / AES-WEB-002J.11: both
                # 1.0.0 (field-less) and 1.1.0 stay registered.
                assert versions[kind] == ("1.0.0", "1.1.0")
            else:
                assert versions[kind] == ("1.0.0",)

    def test_unsupported_schema_version_rejected(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.BUSINESS_SPEC, "9.9.9")

    def test_duplicate_registration_rejected(self):
        with pytest.raises(SchemaRegistrationError):
            register_artifact_model(
                ArtifactKind.BUSINESS_SPEC, "1.0.0", SiteBundle
            )

    def test_no_selection_trace_artifact_kind(self):
        # A1 embeds the trace in ComponentManifest — no independent
        # SelectionTrace artifact was ever created (AES-WEB-002 §14.3). This
        # invariant is independent of the AES-WEB-002J.17 LISTING_DATASET
        # addition (a real thirteenth kind now exists, for an unrelated
        # reason -- see test_exactly_thirteen_artifact_kinds).
        assert not any(
            "SELECTION" in kind.name or "TRACE" in kind.name
            for kind in ALL_KINDS
        )


def _make_selection_trace(**overrides) -> SelectionTrace:
    slot = SlotSelectionTrace(
        slot_id=overrides.get("slot_id", "hero"),
        candidates=(
            SelectionCandidate(
                component_id="hero.split.value-proposition",
                component_version="1.0.0",
                score=overrides.get("score", 150),
                score_components=(
                    SelectionScoreComponent(factor="preferred", points=100),
                    SelectionScoreComponent(factor="exact_intent", points=50),
                ),
            ),
            SelectionCandidate(
                component_id="hero.centered.standard",
                eliminated_by=overrides.get("eliminated_by", "commercial_purpose"),
            ),
        ),
        elimination_counts=overrides.get("elimination_counts", {"lifecycle": 3}),
        tie_break_basis=overrides.get("tie_break_basis", "score"),
        chosen_component_id="hero.split.value-proposition",
        chosen_component_version="1.0.0",
        chosen_variant=overrides.get("chosen_variant", "image-right"),
    )
    return SelectionTrace(slots=(slot,))


def _make_manifest(schema_version="1.1.0", selection_trace=None) -> ComponentManifest:
    return ComponentManifest(
        schema_version=schema_version,
        artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
        source_hashes={},
        selection_trace=selection_trace,
    )


class TestComponentManifestSelectionTrace:
    """Amendment A1 — schema-versioned selection_trace (AES-WEB-002 §14.3)."""

    def test_schema_1_0_0_still_supported_and_field_less(self):
        model_cls = registered_artifact_model(
            ArtifactKind.COMPONENT_MANIFEST, "1.0.0"
        )
        assert model_cls is ComponentManifestV1
        legacy = ComponentManifestV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
            source_hashes={},
        )
        # 1.0.0 serialization is byte-identical to the pre-amendment shape:
        # no selection_trace key at all (the canonical serializer emits None
        # as null, so a field-less 1.0.0 model is required for replay).
        assert "selection_trace" not in canonical_artifact_json(legacy)

    def test_schema_1_1_0_is_registered(self):
        model_cls = registered_artifact_model(
            ArtifactKind.COMPONENT_MANIFEST, "1.1.0"
        )
        assert model_cls is ComponentManifest

    def test_selection_trace_is_optional(self):
        manifest = _make_manifest(selection_trace=None)
        assert manifest.selection_trace is None
        # Optional but explicit: absence serializes as null, never dropped.
        assert '"selection_trace":null' in canonical_artifact_json(manifest)

    def test_valid_typed_trace_serializes_deterministically(self):
        a = _make_manifest(selection_trace=_make_selection_trace())
        b = _make_manifest(selection_trace=_make_selection_trace())
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert '"selection_trace"' in canonical_artifact_json(a)

    def test_same_trace_same_hash(self):
        a = _make_manifest(selection_trace=_make_selection_trace())
        b = _make_manifest(selection_trace=_make_selection_trace())
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_changed_filtering_changes_hash(self):
        base = artifact_sha256(_make_manifest(selection_trace=_make_selection_trace()))
        changed = artifact_sha256(
            _make_manifest(
                selection_trace=_make_selection_trace(
                    elimination_counts={"lifecycle": 4}
                )
            )
        )
        assert base != changed

    def test_changed_scoring_changes_hash(self):
        base = artifact_sha256(_make_manifest(selection_trace=_make_selection_trace()))
        changed = artifact_sha256(
            _make_manifest(selection_trace=_make_selection_trace(score=140))
        )
        assert base != changed

    def test_changed_tiebreak_changes_hash(self):
        base = artifact_sha256(_make_manifest(selection_trace=_make_selection_trace()))
        changed = artifact_sha256(
            _make_manifest(
                selection_trace=_make_selection_trace(tie_break_basis="component_id")
            )
        )
        assert base != changed

    def test_unsupported_manifest_version_fails(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(
                ArtifactKind.COMPONENT_MANIFEST, "2.0.0"
            )

    def test_trace_rejects_arbitrary_fields(self):
        # extra="forbid" on every frozen model — no untyped fields (A1 #12).
        with pytest.raises(Exception):
            SelectionTrace(slots=(), bogus=1)
        with pytest.raises(Exception):
            SlotSelectionTrace(slot_id="x", bogus="nope")
        with pytest.raises(Exception):
            _make_manifest(selection_trace={"bogus": 1})

    def test_trace_models_are_frozen(self):
        trace = _make_selection_trace()
        with pytest.raises(Exception):
            trace.schema_version = "9.9.9"
        with pytest.raises(Exception):
            trace.slots[0].slot_id = "changed"

    def test_no_floats_in_scores(self):
        # Integer scoring only (§14.2 step 6); floats are rejected by the
        # canonical serializer.
        component = SelectionScoreComponent(factor="preferred", points=100)
        assert isinstance(component.points, int)


def _make_brand_package(schema_version="1.1.0", **overrides) -> BrandPackage:
    fields = dict(
        schema_version=schema_version,
        artifact_kind=ArtifactKind.BRAND_PACKAGE,
        source_hashes={},
        palette={"color.text.default": "#23312a"},
        type_scale={"typography.body.default": "400 16px/1.5 sans-serif"},
        spacing_scale={"spacing.stack.default": "16px"},
        voice_profile="deterministic voice",
        asset_hashes={},
        radius_scale={"radius.card": "10px"},
        extended_tokens={"breakpoint.sm": "640px"},
        contrast_evidence=(
            ContrastEvidence(
                foreground_token="color.text.default",
                background_token="color.surface.page",
                contrast_ratio_hundredths=1271,
                required_hundredths=450,
                passed=True,
            ),
        ),
    )
    fields.update(overrides)
    return BrandPackage(**fields)


class TestBrandPackageSchema:
    """AES-WEB-002J.2 — additive-minor BrandPackage schema (AES-WEB-001 §5.2)."""

    def test_schema_1_0_0_still_supported_and_field_less(self):
        model_cls = registered_artifact_model(ArtifactKind.BRAND_PACKAGE, "1.0.0")
        assert model_cls is BrandPackageV1
        legacy = BrandPackageV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.BRAND_PACKAGE,
            source_hashes={},
        )
        # 1.0.0 serialization is byte-identical to the pre-Phase-2 shape:
        # none of the Phase 2 keys exist at all (the canonical serializer
        # emits None as null, so a field-less 1.0.0 model is required for
        # replay — same reasoning as ComponentManifestV1).
        text = canonical_artifact_json(legacy)
        assert "radius_scale" not in text
        assert "extended_tokens" not in text
        assert "contrast_evidence" not in text

    def test_schema_1_1_0_is_registered(self):
        model_cls = registered_artifact_model(ArtifactKind.BRAND_PACKAGE, "1.1.0")
        assert model_cls is BrandPackage

    def test_new_fields_default_empty(self):
        package = BrandPackage(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.BRAND_PACKAGE,
            source_hashes={},
        )
        assert package.radius_scale == {}
        assert package.extended_tokens == {}
        assert package.contrast_evidence == ()

    def test_canonical_round_trip_is_stable(self):
        a = _make_brand_package()
        b = _make_brand_package()
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_changed_contrast_evidence_changes_hash(self):
        base = artifact_sha256(_make_brand_package())
        changed = artifact_sha256(
            _make_brand_package(
                contrast_evidence=(
                    ContrastEvidence(
                        foreground_token="color.text.default",
                        background_token="color.surface.page",
                        contrast_ratio_hundredths=999,
                        required_hundredths=450,
                        passed=True,
                    ),
                )
            )
        )
        assert base != changed

    def test_unsupported_brand_package_version_fails(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.BRAND_PACKAGE, "2.0.0")

    def test_brand_package_is_frozen(self):
        package = _make_brand_package()
        with pytest.raises(Exception):
            package.voice_profile = "changed"
        with pytest.raises(Exception):
            package.contrast_evidence[0].passed = False

    def test_contrast_evidence_rejects_arbitrary_fields(self):
        # extra="forbid" on every frozen model (§4.4).
        with pytest.raises(Exception):
            ContrastEvidence(
                foreground_token="color.text.default",
                background_token="color.surface.page",
                contrast_ratio_hundredths=1271,
                required_hundredths=450,
                passed=True,
                bogus=1,
            )

    def test_no_floats_reach_canonical_brand_artifact(self):
        # The shared canonicalizer (contracts/artifacts.py) actively rejects
        # floats anywhere in the payload, including the new Phase 2 fields —
        # not merely "happens not to contain one" (mirrors
        # TestComponentContracts.test_no_floats_present's injection style).
        payload = model_to_dict(_make_brand_package())
        payload["extended_tokens"]["breakpoint.sm"] = 640.0
        with pytest.raises(ArtifactCanonicalizationError):
            canonical_json(payload)


def _make_site_architecture(schema_version="1.1.0", **overrides) -> SiteArchitecture:
    fields = dict(
        schema_version=schema_version,
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
        pages=(),
        nav_routes=(),
        sitemap_routes=(),
        page_ids={"/": "pg_0000000000000000"},
        page_hierarchy=(PageHierarchyEntry(route="/", parent_route=""),),
        internal_link_topology=(
            InternalLinkIntent(from_route="/", to_routes=("/parks/",)),
        ),
    )
    fields.update(overrides)
    return SiteArchitecture(**fields)


class TestSiteArchitectureSchema:
    """AES-WEB-002J.3 — additive-minor SiteArchitecture schema (AES-WEB-001 §5.3)."""

    def test_schema_1_0_0_still_supported_and_field_less(self):
        model_cls = registered_artifact_model(ArtifactKind.SITE_ARCHITECTURE, "1.0.0")
        assert model_cls is SiteArchitectureV1
        legacy = SiteArchitectureV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
            source_hashes={},
        )
        # 1.0.0 serialization is byte-identical to the pre-J.3 shape: none
        # of the new keys exist at all (the canonical serializer emits None
        # as null, so a field-less 1.0.0 model is required for replay --
        # same reasoning as ComponentManifestV1/BrandPackageV1).
        text = canonical_artifact_json(legacy)
        assert "page_ids" not in text
        assert "page_hierarchy" not in text
        assert "internal_link_topology" not in text

    def test_schema_1_1_0_is_registered(self):
        model_cls = registered_artifact_model(ArtifactKind.SITE_ARCHITECTURE, "1.1.0")
        assert model_cls is SiteArchitecture

    def test_new_fields_default_empty(self):
        site = SiteArchitecture(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
            source_hashes={},
        )
        assert site.page_ids == {}
        assert site.page_hierarchy == ()
        assert site.internal_link_topology == ()

    def test_canonical_round_trip_is_stable(self):
        a = _make_site_architecture()
        b = _make_site_architecture()
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_changed_hierarchy_changes_hash(self):
        base = artifact_sha256(_make_site_architecture())
        changed = artifact_sha256(
            _make_site_architecture(
                page_hierarchy=(
                    PageHierarchyEntry(route="/", parent_route=""),
                    PageHierarchyEntry(route="/parks/", parent_route="/"),
                )
            )
        )
        assert base != changed

    def test_changed_link_topology_changes_hash(self):
        base = artifact_sha256(_make_site_architecture())
        changed = artifact_sha256(
            _make_site_architecture(
                internal_link_topology=(
                    InternalLinkIntent(from_route="/", to_routes=("/hotels/",)),
                )
            )
        )
        assert base != changed

    def test_changed_page_ids_changes_hash(self):
        base = artifact_sha256(_make_site_architecture())
        changed = artifact_sha256(
            _make_site_architecture(page_ids={"/": "pg_ffffffffffffffff"})
        )
        assert base != changed

    def test_unsupported_site_architecture_version_fails(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.SITE_ARCHITECTURE, "2.0.0")

    def test_site_architecture_is_frozen(self):
        site = _make_site_architecture()
        with pytest.raises(Exception):
            site.pages = ()
        with pytest.raises(Exception):
            site.page_hierarchy[0].parent_route = "/changed/"

    def test_page_hierarchy_entry_rejects_arbitrary_fields(self):
        # extra="forbid" on every frozen model (§4.4).
        with pytest.raises(Exception):
            PageHierarchyEntry(route="/", parent_route="", bogus=1)
        with pytest.raises(Exception):
            InternalLinkIntent(from_route="/", to_routes=(), bogus=1)


def _make_layout_plan(schema_version="1.1.0", **overrides) -> LayoutPlan:
    fields = dict(
        schema_version=schema_version,
        artifact_kind=ArtifactKind.LAYOUT_PLAN,
        source_hashes={},
        pages=(
            PageLayout(
                route="/",
                regions=(LayoutRegion(region_id="HERO", component_indexes=(0,)),),
            ),
        ),
        region_details=(
            RegionLayoutDetail(
                route="/",
                region_id="HERO",
                region_kind=RegionKind.HERO,
                placements=(
                    ComponentPlacement(
                        component_index=0,
                        grid=GridPlacement(
                            columns_token="grid.columns.3", column_span=1
                        ),
                        responsive=ResponsiveSelection(
                            collapse_behavior="grid-to-stack"
                        ),
                    ),
                ),
            ),
        ),
    )
    fields.update(overrides)
    return LayoutPlan(**fields)


def _make_rendered_page_set(schema_version="1.1.0", **overrides) -> RenderedPageSet:
    fields = dict(
        schema_version=schema_version,
        artifact_kind=ArtifactKind.RENDERED_PAGE_SET,
        source_hashes={},
        pages=(RenderedPage(route="/", html_hash="a" * 64, css_hash=""),),
        shared_css_hash="b" * 64,
        page_details=(RenderedPageDetail(route="/", html="<p>hi</p>"),),
        shared_css=":root{}",
    )
    fields.update(overrides)
    return RenderedPageSet(**fields)


class TestLayoutPlanSchema:
    """AES-WEB-002J.7 — additive-minor LayoutPlan schema (AES-WEB-001 §5.6)."""

    def test_schema_1_0_0_still_supported_and_field_less(self):
        model_cls = registered_artifact_model(ArtifactKind.LAYOUT_PLAN, "1.0.0")
        assert model_cls is LayoutPlanV1
        legacy = LayoutPlanV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.LAYOUT_PLAN,
            source_hashes={},
        )
        # 1.0.0 serialization is byte-identical to the pre-J.7 shape: the
        # new key does not exist at all (the canonical serializer emits None
        # as null, so a field-less 1.0.0 model is required for replay --
        # same reasoning as ComponentManifestV1/BrandPackageV1/
        # SiteArchitectureV1).
        text = canonical_artifact_json(legacy)
        assert "region_details" not in text

    def test_schema_1_1_0_is_registered(self):
        model_cls = registered_artifact_model(ArtifactKind.LAYOUT_PLAN, "1.1.0")
        assert model_cls is LayoutPlan

    def test_new_field_defaults_empty(self):
        plan = LayoutPlan(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.LAYOUT_PLAN,
            source_hashes={},
        )
        assert plan.region_details == ()

    def test_canonical_round_trip_is_stable(self):
        a = _make_layout_plan()
        b = _make_layout_plan()
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_changed_region_details_changes_hash(self):
        base = artifact_sha256(_make_layout_plan())
        changed = artifact_sha256(
            _make_layout_plan(
                region_details=(
                    RegionLayoutDetail(
                        route="/",
                        region_id="HERO",
                        region_kind=RegionKind.HERO,
                        placements=(
                            ComponentPlacement(
                                component_index=0,
                                grid=GridPlacement(
                                    columns_token="grid.columns.4", column_span=1
                                ),
                            ),
                        ),
                    ),
                )
            )
        )
        assert base != changed

    def test_pages_and_regions_unchanged_shape(self):
        # LayoutRegion/PageLayout are shared byte-for-byte by LayoutPlanV1
        # and LayoutPlan -- new capability lives only in region_details
        # (the established J.2/J.3 idiom: never restructure an existing
        # field's type).
        plan = _make_layout_plan()
        assert plan.pages[0].regions[0].component_indexes == (0,)

    def test_unsupported_layout_plan_version_fails(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.LAYOUT_PLAN, "2.0.0")

    def test_layout_plan_is_frozen(self):
        plan = _make_layout_plan()
        with pytest.raises(Exception):
            plan.pages = ()
        with pytest.raises(Exception):
            plan.region_details[0].region_id = "changed"

    def test_region_layout_detail_rejects_arbitrary_fields(self):
        # extra="forbid" on every frozen model (§4.4).
        with pytest.raises(Exception):
            RegionLayoutDetail(
                route="/", region_id="HERO", region_kind=RegionKind.HERO, bogus=1
            )
        with pytest.raises(Exception):
            ComponentPlacement(component_index=0, bogus=1)
        with pytest.raises(Exception):
            GridPlacement(columns_token="grid.columns.3", bogus=1)
        with pytest.raises(Exception):
            ResponsiveSelection(collapse_behavior="grid-to-stack", bogus=1)


class TestRenderedPageSetSchema:
    """AES-WEB-002J.8 — additive-minor RenderedPageSet schema (AES-WEB-001
    §5.7)."""

    def test_schema_1_0_0_still_supported_and_field_less(self):
        model_cls = registered_artifact_model(ArtifactKind.RENDERED_PAGE_SET, "1.0.0")
        assert model_cls is RenderedPageSetV1
        legacy = RenderedPageSetV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.RENDERED_PAGE_SET,
            source_hashes={},
        )
        # 1.0.0 serialization is byte-identical to the pre-J.8 hash-only
        # shape: the new keys do not exist at all (same reasoning as
        # ComponentManifestV1/BrandPackageV1/SiteArchitectureV1/LayoutPlanV1).
        text = canonical_artifact_json(legacy)
        assert '"page_details"' not in text
        assert '"shared_css"' not in text
        assert '"shared_css_hash"' in text

    def test_schema_1_1_0_is_registered(self):
        model_cls = registered_artifact_model(ArtifactKind.RENDERED_PAGE_SET, "1.1.0")
        assert model_cls is RenderedPageSet

    def test_new_fields_default_empty(self):
        page_set = RenderedPageSet(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.RENDERED_PAGE_SET,
            source_hashes={},
        )
        assert page_set.page_details == ()
        assert page_set.shared_css == ""

    def test_v1_payload_still_parses_via_v1_model(self):
        # A 1.0.0 payload produced before J.8 (hash-only, no page_details/
        # shared_css keys) still parses through the registered 1.0.0 model.
        legacy_json = canonical_artifact_json(
            RenderedPageSetV1(
                schema_version="1.0.0",
                artifact_kind=ArtifactKind.RENDERED_PAGE_SET,
                source_hashes={},
                pages=(),
                shared_css_hash="deadbeef",
            )
        )
        replayed = RenderedPageSetV1(**json.loads(legacy_json))
        assert replayed.shared_css_hash == "deadbeef"

    def test_canonical_round_trip_is_stable(self):
        a = _make_rendered_page_set()
        b = _make_rendered_page_set()
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_changed_page_details_changes_hash(self):
        base = artifact_sha256(_make_rendered_page_set())
        changed = artifact_sha256(
            _make_rendered_page_set(
                page_details=(RenderedPageDetail(route="/", html="<p>changed</p>"),)
            )
        )
        assert base != changed

    def test_rendered_page_unchanged_shape(self):
        # RenderedPage is shared byte-for-byte by RenderedPageSetV1 and
        # RenderedPageSet -- new capability lives only in page_details/
        # shared_css (the established J.2/J.3/J.7 idiom: never restructure
        # an existing field's type).
        page_set = _make_rendered_page_set()
        assert page_set.pages[0].route == "/"
        assert page_set.pages[0].css_hash == ""

    def test_unsupported_rendered_page_set_version_fails(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.RENDERED_PAGE_SET, "2.0.0")

    def test_rendered_page_set_is_frozen(self):
        page_set = _make_rendered_page_set()
        with pytest.raises(Exception):
            page_set.pages = ()
        with pytest.raises(Exception):
            page_set.page_details[0].html = "changed"

    def test_rendered_page_detail_rejects_arbitrary_fields(self):
        with pytest.raises(Exception):
            RenderedPageDetail(route="/", html="<p></p>", bogus=1)

    def test_no_binary_embedding_text_only(self):
        # §4.3: artifacts never embed binary data -- html/shared_css are
        # plain str fields (UTF-8 text), never bytes.
        page_set = _make_rendered_page_set()
        assert isinstance(page_set.page_details[0].html, str)
        assert isinstance(page_set.shared_css, str)


def _make_site_bundle(schema_version="1.1.0", **overrides) -> SiteBundle:
    fields = dict(
        schema_version=schema_version,
        artifact_kind=ArtifactKind.SITE_BUNDLE,
        source_hashes={},
        file_map={"index.html": "a" * 64, "styles.css": "b" * 64},
        bundle_hash="c" * 64,
        files=(
            BundleFile(path="index.html", content="<!doctype html><html></html>"),
            BundleFile(path="styles.css", content=":root{}"),
        ),
    )
    fields.update(overrides)
    return SiteBundle(**fields)


class TestSiteBundleSchema:
    """AES-WEB-002J.10 — additive-minor SiteBundle schema (AES-WEB-001 §5.9)."""

    def test_schema_1_0_0_still_supported_and_field_less(self):
        model_cls = registered_artifact_model(ArtifactKind.SITE_BUNDLE, "1.0.0")
        assert model_cls is SiteBundleV1
        legacy = SiteBundleV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.SITE_BUNDLE,
            source_hashes={},
        )
        # 1.0.0 serialization is byte-identical to the pre-J.10 hash-only
        # shape: the new key does not exist at all (same reasoning as
        # RenderedPageSetV1 et al.).
        text = canonical_artifact_json(legacy)
        assert '"files"' not in text
        assert '"file_map"' in text
        assert '"bundle_hash"' in text

    def test_schema_1_1_0_is_registered(self):
        model_cls = registered_artifact_model(ArtifactKind.SITE_BUNDLE, "1.1.0")
        assert model_cls is SiteBundle

    def test_new_field_defaults_empty(self):
        bundle = SiteBundle(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.SITE_BUNDLE,
            source_hashes={},
        )
        assert bundle.files == ()

    def test_v1_payload_still_parses_via_v1_model(self):
        legacy_json = canonical_artifact_json(
            SiteBundleV1(
                schema_version="1.0.0",
                artifact_kind=ArtifactKind.SITE_BUNDLE,
                source_hashes={},
                file_map={"index.html": "deadbeef"},
                bundle_hash="feedface",
            )
        )
        replayed = SiteBundleV1(**json.loads(legacy_json))
        assert replayed.bundle_hash == "feedface"

    def test_canonical_round_trip_is_stable(self):
        a = _make_site_bundle()
        b = _make_site_bundle()
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_changed_files_changes_hash(self):
        base = artifact_sha256(_make_site_bundle())
        changed = artifact_sha256(
            _make_site_bundle(
                files=(BundleFile(path="index.html", content="<p>changed</p>"),)
            )
        )
        assert base != changed

    def test_file_map_unchanged_shape(self):
        # file_map/bundle_hash are shared byte-for-byte by SiteBundleV1 and
        # SiteBundle -- new capability lives only in files (the established
        # additive idiom).
        bundle = _make_site_bundle()
        assert bundle.file_map["index.html"] == "a" * 64
        assert bundle.bundle_hash == "c" * 64

    def test_unsupported_site_bundle_version_fails(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.SITE_BUNDLE, "2.0.0")

    def test_site_bundle_is_frozen(self):
        bundle = _make_site_bundle()
        with pytest.raises(Exception):
            bundle.file_map = {}
        with pytest.raises(Exception):
            bundle.files[0].content = "changed"

    def test_bundle_file_rejects_arbitrary_fields(self):
        with pytest.raises(Exception):
            BundleFile(path="x", content="y", bogus=1)

    def test_no_binary_embedding_text_only(self):
        bundle = _make_site_bundle()
        assert isinstance(bundle.files[0].content, str)


def _make_quality_report(schema_version="1.1.0", **overrides) -> QualityReport:
    fields = dict(
        schema_version=schema_version,
        artifact_kind=ArtifactKind.QUALITY_REPORT,
        source_hashes={},
        gate_results=(
            GateResult(
                gate_id="CG-RND-009",
                severity=GateSeverity.BLOCKING,
                passed=True,
                details="route='/index.html': no unsafe URLs",
            ),
        ),
        certified=False,
        deferred_gate_ids=("CG-A11Y-001", "CG-SEO-001"),
    )
    fields.update(overrides)
    return QualityReport(**fields)


class TestQualityReportSchema:
    """AES-WEB-002J.11 — additive-minor QualityReport schema (AES-WEB-001
    §5.10)."""

    def test_schema_1_0_0_still_supported_and_field_less(self):
        model_cls = registered_artifact_model(ArtifactKind.QUALITY_REPORT, "1.0.0")
        assert model_cls is QualityReportV1
        legacy = QualityReportV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.QUALITY_REPORT,
            source_hashes={},
        )
        text = canonical_artifact_json(legacy)
        assert '"deferred_gate_ids"' not in text
        assert '"gate_results"' in text
        assert '"certified"' in text

    def test_schema_1_1_0_is_registered(self):
        model_cls = registered_artifact_model(ArtifactKind.QUALITY_REPORT, "1.1.0")
        assert model_cls is QualityReport

    def test_new_field_defaults_empty(self):
        report = QualityReport(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.QUALITY_REPORT,
            source_hashes={},
        )
        assert report.deferred_gate_ids == ()

    def test_v1_payload_still_parses_via_v1_model(self):
        legacy_json = canonical_artifact_json(
            QualityReportV1(
                schema_version="1.0.0",
                artifact_kind=ArtifactKind.QUALITY_REPORT,
                source_hashes={},
                certified=True,
            )
        )
        replayed = QualityReportV1(**json.loads(legacy_json))
        assert replayed.certified is True

    def test_canonical_round_trip_is_stable(self):
        a = _make_quality_report()
        b = _make_quality_report()
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_changed_deferred_gate_ids_changes_hash(self):
        base = artifact_sha256(_make_quality_report())
        changed = artifact_sha256(_make_quality_report(deferred_gate_ids=("CG-A11Y-001",)))
        assert base != changed

    def test_gate_results_unchanged_shape(self):
        # GateResult is shared byte-for-byte by QualityReportV1 and
        # QualityReport -- new capability lives only in deferred_gate_ids.
        report = _make_quality_report()
        assert report.gate_results[0].gate_id == "CG-RND-009"
        assert report.gate_results[0].passed is True

    def test_unsupported_quality_report_version_fails(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.QUALITY_REPORT, "2.0.0")

    def test_quality_report_is_frozen(self):
        report = _make_quality_report()
        with pytest.raises(Exception):
            report.certified = True
        with pytest.raises(Exception):
            report.gate_results[0].passed = False

    def test_rejects_arbitrary_fields(self):
        with pytest.raises(Exception):
            QualityReport(
                schema_version="1.1.0",
                artifact_kind=ArtifactKind.QUALITY_REPORT,
                source_hashes={},
                bogus=1,
            )


class TestFrozenBehavior:
    def test_artifacts_are_frozen(self):
        spec = _make_spec()
        with pytest.raises(Exception):
            spec.business_name = "Changed"

    def test_header_fields_are_mandatory(self):
        with pytest.raises(Exception):
            BusinessSpec(  # no header fields supplied
                business_name="x",
                niche="y",
                audience="z",
                value_proposition="w",
            )

    def test_extra_fields_are_forbidden(self):
        with pytest.raises(Exception):
            _make_spec(unexpected_field="nope")

    def test_every_kind_constructs_with_minimal_payload(self):
        constructors = {
            ArtifactKind.BUSINESS_SPEC: lambda h: _make_spec(),
            ArtifactKind.BRAND_PACKAGE: lambda h: BrandPackage(**h),
            ArtifactKind.SITE_ARCHITECTURE: lambda h: SiteArchitecture(**h),
            ArtifactKind.CONTENT_CANDIDATE: lambda h: ContentCandidate(
                page_route="/", slot_id="hero", body="text", **h
            ),
            ArtifactKind.CONTENT_PACKAGE: lambda h: ContentPackage(**h),
            ArtifactKind.COMPONENT_MANIFEST: lambda h: ComponentManifest(**h),
            ArtifactKind.LAYOUT_PLAN: lambda h: LayoutPlan(**h),
            ArtifactKind.RENDERED_PAGE_SET: lambda h: RenderedPageSet(**h),
            ArtifactKind.SEO_PACKAGE: lambda h: SEOPackage(**h),
            ArtifactKind.SITE_BUNDLE: lambda h: SiteBundle(**h),
            ArtifactKind.QUALITY_REPORT: lambda h: QualityReport(**h),
            ArtifactKind.BUILD_MANIFEST: lambda h: BuildManifest(
                build_id="b" * 64,
                pipeline_version="1.0.0",
                final_state=BuildState.SPEC_COMPILED,
                **h,
            ),
            ArtifactKind.LISTING_DATASET: lambda h: ListingDataset(**h),
        }
        for kind in ALL_KINDS:
            header = dict(
                schema_version="1.0.0",
                artifact_kind=kind,
                source_hashes={},
            )
            artifact = constructors[kind](header)
            assert artifact.artifact_kind == kind
            assert artifact.schema_version == "1.0.0"
            assert isinstance(artifact.source_hashes, dict)


class TestCanonicalSerialization:
    def test_sorted_keys_no_insignificant_whitespace(self):
        text = canonical_json({"b": 1, "a": {"z": None, "y": 2}})
        assert text == '{"a":{"y":2,"z":null},"b":1}'

    def test_null_handling_is_explicit(self):
        record = json.loads(canonical_artifact_json(
            QualityReport(
                schema_version="1.0.0",
                artifact_kind=ArtifactKind.QUALITY_REPORT,
                source_hashes={},
            )
        ))
        assert record["certificate"] is None  # never silently dropped

    def test_serialization_stable_across_construction_order(self):
        spec_a = _make_spec()
        spec_b = BusinessSpec(
            value_proposition="verified pet-friendly stays",
            business_name="Pet Trip Finder",
            source_hashes={"external:project": "a" * 64},
            artifact_kind=ArtifactKind.BUSINESS_SPEC,
            schema_version="1.0.0",
            niche="pet travel",
            audience="pet owners",
            directory_taxonomy=("hotels", "parks"),
        )
        assert canonical_artifact_json(spec_a) == canonical_artifact_json(
            spec_b
        )

    def test_enum_values_serialize_as_strings(self):
        payload = json.loads(canonical_artifact_json(_make_spec()))
        assert payload["artifact_kind"] == "BUSINESS_SPEC"


class TestContentIdentity:
    def test_identical_artifacts_yield_identical_hashes(self):
        assert artifact_sha256(_make_spec()) == artifact_sha256(_make_spec())

    def test_changed_payload_yields_changed_hash(self):
        base = artifact_sha256(_make_spec())
        changed = artifact_sha256(_make_spec(niche="dog travel"))
        assert base != changed

    def test_hash_is_sha256_hex(self):
        digest = artifact_sha256(_make_spec())
        assert len(digest) == 64
        int(digest, 16)  # parses as hex
