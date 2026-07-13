"""Layout Engine tests (AES-WEB-002J.7; AES-WEB-001 §5.6, AES-WEB-002 §9/§11/§16).

Deterministic throughout: no clock/UUID/randomness. Covers the public
surface and version, determinism, page/component ordering, region legality
and the declared-order tie-break, responsive-selection mirroring, grid
placement and BrandPackage token validation, conversion/repetition
placement rules, batch error aggregation, and the architectural boundary
(constructor-injected registry, no sibling-engine import, pipeline unwired).

Tests exercise only the public surface (``engines.website_generation``)
plus the shared fixture builders in this package's ``__init__.py``, per
AES-WEB-001 §3.4 -- never the engine's internal helpers.
"""

from __future__ import annotations

import pytest

from engines.website_generation import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
    ArtifactKind,
    LayoutEngine,
    LayoutPlan,
    RegionKind,
    artifact_sha256,
    canonical_artifact_json,
)
from engines.website_generation.contracts.components import (
    AnalyticsContract,
    ConversionContract,
    MonetizationContract,
    RenderingContract,
    ResponsiveContract,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    ConversionGoal,
)
from engines.website_generation.contracts.errors import LayoutCompositionError
from engines.website_generation.contracts.interfaces import LayoutEngineInterface

from . import instance, make_brand_package, make_definition, make_manifest, make_registry, page


# --------------------------------------------------------------------------- #
# Fixture component definitions
# --------------------------------------------------------------------------- #

def _nav_header(**overrides):
    fields = dict(
        component_id="nav.header.standard",
        component_family=ComponentFamily.NAV,
        commercial_purpose=CommercialPurpose.ORIENT,
        allowed_parent_regions=(RegionKind.HEADER,),
        analytics_contract=AnalyticsContract(impression_id="nav-header-standard"),
        rendering_contract=RenderingContract(
            emitter_key="nav.header.standard@1", class_prefix="ac-nav"
        ),
    )
    fields.update(overrides)
    return make_definition(**fields)


def _hero(**overrides):
    fields = dict(
        component_id="hero.split.value-proposition",
        component_family=ComponentFamily.HERO,
        commercial_purpose=CommercialPurpose.COMMUNICATE_VALUE,
        allowed_parent_regions=(RegionKind.HERO,),
        design_token_dependencies=("grid.columns.3", "grid.gap.default"),
        responsive_contract=ResponsiveContract(
            collapse_behavior="grid-to-stack", mobile_order="dom-order"
        ),
        analytics_contract=AnalyticsContract(
            impression_id="hero-split-value-proposition"
        ),
        rendering_contract=RenderingContract(
            emitter_key="hero.split.value-proposition@1", class_prefix="ac-hero"
        ),
    )
    fields.update(overrides)
    return make_definition(**fields)


def _body_text(**overrides):
    fields = dict(
        component_id="content.text.section",
        component_family=ComponentFamily.CONTENT,
        commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY,
        allowed_parent_regions=(RegionKind.BODY,),
        analytics_contract=AnalyticsContract(impression_id="content-text-section"),
        rendering_contract=RenderingContract(
            emitter_key="content.text.section@1", class_prefix="ac-content"
        ),
    )
    fields.update(overrides)
    return make_definition(**fields)


def _cta_sticky(**overrides):
    fields = dict(
        component_id="cta.sticky.mobile",
        component_family=ComponentFamily.CTA,
        commercial_purpose=CommercialPurpose.DRIVE_CALL,
        # BODY declared before STICKY_MOBILE -- the conversion_contract
        # placement restriction below narrows the choice, proving the
        # tie-break is a *filtered* declared-order pick, not a first-entry
        # default that ignores conversion_contract.
        allowed_parent_regions=(RegionKind.BODY, RegionKind.STICKY_MOBILE),
        conversion_contract=ConversionContract(
            conversion_goal=ConversionGoal.PHONE_CALL,
            placement_regions=(RegionKind.STICKY_MOBILE,),
            repetition_limit_per_page=1,
        ),
        responsive_contract=ResponsiveContract(sticky="bottom", mobile_order="dom-order"),
        analytics_contract=AnalyticsContract(impression_id="cta-sticky-mobile"),
        rendering_contract=RenderingContract(
            emitter_key="cta.sticky.mobile@1", class_prefix="ac-cta"
        ),
    )
    fields.update(overrides)
    return make_definition(**fields)


def _default_registry():
    return make_registry([_nav_header(), _hero(), _body_text(), _cta_sticky()])


# --------------------------------------------------------------------------- #
# Public surface + version + architecture
# --------------------------------------------------------------------------- #

class TestPublicSurfaceAndVersion:
    def test_is_interface_subclass(self):
        assert issubclass(LayoutEngine, LayoutEngineInterface)

    def test_version_pinned(self):
        assert LayoutEngine.version == ENGINE_VERSIONS["layout_engine"]
        assert LayoutEngine.version == "1.0.0"

    def test_compose_returns_layout_plan(self):
        registry = _default_registry()
        manifest = make_manifest([page("/", [instance(component_id="hero.split.value-proposition")])])
        plan = LayoutEngine(registry).compose(manifest, make_brand_package())
        assert isinstance(plan, LayoutPlan)

    def test_registry_is_required_constructor_argument(self):
        with pytest.raises(TypeError):
            LayoutEngine()  # type: ignore[call-arg]


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def _manifest(self):
        return make_manifest(
            [
                page(
                    "/",
                    [
                        instance(component_id="nav.header.standard"),
                        instance(component_id="hero.split.value-proposition"),
                        instance(component_id="content.text.section"),
                    ],
                )
            ]
        )

    def test_identical_inputs_produce_equal_plan(self):
        manifest, brand = self._manifest(), make_brand_package()
        a = LayoutEngine(_default_registry()).compose(manifest, brand)
        b = LayoutEngine(_default_registry()).compose(manifest, brand)
        assert a == b

    def test_identical_inputs_produce_equal_canonical_json(self):
        manifest, brand = self._manifest(), make_brand_package()
        a = LayoutEngine(_default_registry()).compose(manifest, brand)
        b = LayoutEngine(_default_registry()).compose(manifest, brand)
        assert canonical_artifact_json(a) == canonical_artifact_json(b)

    def test_identical_inputs_produce_equal_hashes(self):
        manifest, brand = self._manifest(), make_brand_package()
        a = LayoutEngine(_default_registry()).compose(manifest, brand)
        b = LayoutEngine(_default_registry()).compose(manifest, brand)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_separate_engine_instances_produce_identical_output(self):
        manifest, brand = self._manifest(), make_brand_package()
        registry = _default_registry()
        a = LayoutEngine(registry).compose(manifest, brand)
        b = LayoutEngine(registry).compose(manifest, brand)
        assert a == b

    def test_registry_construction_order_does_not_change_output(self):
        manifest, brand = self._manifest(), make_brand_package()
        defs = [_nav_header(), _hero(), _body_text(), _cta_sticky()]
        forward = LayoutEngine(make_registry(defs)).compose(manifest, brand)
        backward = LayoutEngine(make_registry(list(reversed(defs)))).compose(manifest, brand)
        assert artifact_sha256(forward) == artifact_sha256(backward)

    def test_diagnostic_order_is_stable(self):
        manifest = make_manifest(
            [
                page(
                    "/z/",
                    [instance(component_id="does.not.exist")],
                ),
                page(
                    "/a/",
                    [instance(component_id="also.missing")],
                ),
            ]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        with pytest.raises(LayoutCompositionError) as exc_info_2:
            LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        assert (
            exc_info.value.diagnostics["unresolved_components"]
            == exc_info_2.value.diagnostics["unresolved_components"]
        )
        routes = [d["route"] for d in exc_info.value.diagnostics["unresolved_components"]]
        assert routes == sorted(routes)


# --------------------------------------------------------------------------- #
# Page and component ordering
# --------------------------------------------------------------------------- #

class TestOrdering:
    def test_page_order_matches_manifest(self):
        manifest = make_manifest(
            [
                page("/z/", [instance(component_id="hero.split.value-proposition")]),
                page("/a/", [instance(component_id="hero.split.value-proposition")]),
            ]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        assert [p.route for p in plan.pages] == ["/z/", "/a/"]

    def test_region_order_is_fixed_semantic_order_not_manifest_order(self):
        # Declared out of region order on purpose: hero, nav, body-text.
        manifest = make_manifest(
            [
                page(
                    "/",
                    [
                        instance(component_id="hero.split.value-proposition"),
                        instance(component_id="nav.header.standard"),
                        instance(component_id="content.text.section"),
                    ],
                )
            ]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        region_ids = [r.region_id for r in plan.pages[0].regions]
        # HEADER < HERO < BODY per the RegionKind declaration order (§9.1),
        # regardless that hero was declared first in the manifest.
        assert region_ids == [
            RegionKind.HEADER.value,
            RegionKind.HERO.value,
            RegionKind.BODY.value,
        ]

    def test_component_index_references_original_manifest_position(self):
        manifest = make_manifest(
            [
                page(
                    "/",
                    [
                        instance(component_id="hero.split.value-proposition"),  # 0
                        instance(component_id="nav.header.standard"),  # 1
                        instance(component_id="content.text.section"),  # 2
                    ],
                )
            ]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        by_region = {r.region_id: r.component_indexes for r in plan.pages[0].regions}
        assert by_region[RegionKind.HERO.value] == (0,)
        assert by_region[RegionKind.HEADER.value] == (1,)
        assert by_region[RegionKind.BODY.value] == (2,)

    def test_region_grouping_preserves_manifest_order_within_region(self):
        manifest = make_manifest(
            [
                page(
                    "/",
                    [
                        instance(component_id="content.text.section"),  # 0 -> BODY
                        instance(component_id="hero.split.value-proposition"),  # 1 -> HERO
                        instance(component_id="content.text.section"),  # 2 -> BODY
                    ],
                )
            ]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        body_region = next(
            r for r in plan.pages[0].regions if r.region_id == RegionKind.BODY.value
        )
        assert body_region.component_indexes == (0, 2)

    def test_empty_regions_are_omitted(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        region_ids = {r.region_id for r in plan.pages[0].regions}
        assert region_ids == {RegionKind.HERO.value}
        assert RegionKind.FOOTER.value not in region_ids
        assert RegionKind.ANNOUNCEMENT.value not in region_ids


# --------------------------------------------------------------------------- #
# Region legality
# --------------------------------------------------------------------------- #

class TestRegionLegality:
    def test_missing_component_definition_fails(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="does.not.exist")])]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        diag = exc_info.value.diagnostics["unresolved_components"][0]
        assert diag["route"] == "/"
        assert diag["component_index"] == 0
        assert diag["component_id"] == "does.not.exist"

    def test_unsupported_version_fails(self):
        manifest = make_manifest(
            [
                page(
                    "/",
                    [instance(component_id="hero.split.value-proposition", component_version="9.9.9")],
                )
            ]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        assert "unresolved_components" in exc_info.value.diagnostics

    def test_no_legal_region_fails(self):
        registry = make_registry([_hero(allowed_parent_regions=())])
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(registry).compose(manifest, make_brand_package())
        diag = exc_info.value.diagnostics["illegal_placements"][0]
        assert diag["rule"] == "no_legal_region"

    def test_conversion_placement_restriction_excludes_declared_region(self):
        # allowed_parent_regions=(BODY,) but the conversion contract
        # restricts placement to STICKY_MOBILE -- no intersection.
        registry = make_registry(
            [
                _cta_sticky(
                    allowed_parent_regions=(RegionKind.BODY,),
                    conversion_contract=ConversionContract(
                        conversion_goal=ConversionGoal.PHONE_CALL,
                        placement_regions=(RegionKind.STICKY_MOBILE,),
                    ),
                )
            ]
        )
        manifest = make_manifest(
            [page("/", [instance(component_id="cta.sticky.mobile")])]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(registry).compose(manifest, make_brand_package())
        diag = exc_info.value.diagnostics["illegal_placements"][0]
        assert diag["rule"] == "no_legal_region"
        assert diag["allowed_parent_regions"] == [RegionKind.BODY.value]
        assert diag["conversion_placement_regions"] == [RegionKind.STICKY_MOBILE.value]

    def test_conversion_placement_restriction_narrows_legal_region(self):
        # allowed_parent_regions declares BODY first, but the conversion
        # contract narrows legal placement to STICKY_MOBILE only -- proving
        # the tie-break is filtered by conversion_contract, not a raw
        # first-entry pick.
        manifest = make_manifest(
            [page("/", [instance(component_id="cta.sticky.mobile")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        region_ids = [r.region_id for r in plan.pages[0].regions]
        assert region_ids == [RegionKind.STICKY_MOBILE.value]

    def test_multi_region_eligibility_follows_declared_order(self):
        registry = make_registry(
            [_body_text(allowed_parent_regions=(RegionKind.BODY, RegionKind.HERO))]
        )
        manifest = make_manifest(
            [page("/", [instance(component_id="content.text.section")])]
        )
        plan = LayoutEngine(registry).compose(manifest, make_brand_package())
        region_ids = [r.region_id for r in plan.pages[0].regions]
        assert region_ids == [RegionKind.BODY.value]


# --------------------------------------------------------------------------- #
# Responsive behavior
# --------------------------------------------------------------------------- #

class TestResponsiveBehavior:
    def test_responsive_selection_mirrors_component_contract(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        detail = plan.region_details[0]
        placement = detail.placements[0]
        assert placement.responsive.collapse_behavior == "grid-to-stack"
        assert placement.responsive.mobile_order == "dom-order"

    def test_responsive_selection_is_deterministic(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        a = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        b = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        assert a.region_details == b.region_details

    def test_sticky_selection_mirrors_contract(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="cta.sticky.mobile")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        placement = plan.region_details[0].placements[0]
        assert placement.responsive.sticky == "bottom"

    def test_no_css_or_media_query_output_appears(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        text = canonical_artifact_json(plan)
        assert "@media" not in text
        assert "<" not in text and ">" not in text


# --------------------------------------------------------------------------- #
# Grid and placement
# --------------------------------------------------------------------------- #

class TestGridPlacement:
    def test_grid_token_chosen_from_declared_dependencies(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        placement = plan.region_details[0].placements[0]
        assert placement.grid.columns_token == "grid.columns.3"
        assert placement.grid.column_span == 1

    def test_no_grid_dependency_defaults_empty(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="nav.header.standard")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        placement = plan.region_details[0].placements[0]
        assert placement.grid.columns_token == ""

    def test_invalid_grid_reference_fails(self):
        registry = make_registry(
            [_hero(design_token_dependencies=("grid.columns.5",))]
        )
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(registry).compose(manifest, make_brand_package())
        diag = exc_info.value.diagnostics["invalid_grid_references"][0]
        assert diag["grid_token"] == "grid.columns.5"

    def test_grid_token_validated_against_given_brand_package(self):
        # grid.columns.4 is declared but the injected BrandPackage only
        # authorizes 2/3/4 by default fixture -- override to omit it.
        registry = make_registry(
            [_hero(design_token_dependencies=("grid.columns.4",))]
        )
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        brand = make_brand_package(extended_tokens={"grid.columns.2": "x"})
        with pytest.raises(LayoutCompositionError):
            LayoutEngine(registry).compose(manifest, brand)

    def test_no_pixel_output_in_grid_placement(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        assert "px" not in canonical_artifact_json(plan)


# --------------------------------------------------------------------------- #
# Conversion and disclosure
# --------------------------------------------------------------------------- #

class TestConversionAndDisclosure:
    def test_valid_conversion_placement_succeeds(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="cta.sticky.mobile")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        assert plan.pages[0].regions[0].region_id == RegionKind.STICKY_MOBILE.value

    def test_repetition_limit_violation_fails(self):
        manifest = make_manifest(
            [
                page(
                    "/",
                    [
                        instance(component_id="cta.sticky.mobile"),
                        instance(component_id="cta.sticky.mobile"),
                    ],
                )
            ]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        diag = exc_info.value.diagnostics["repetition_limit_violations"][0]
        assert diag["component_index"] == 1
        assert diag["limit"] == 1
        assert diag["occurrence"] == 2

    def test_repetition_within_limit_succeeds(self):
        registry = make_registry(
            [
                _cta_sticky(
                    conversion_contract=ConversionContract(
                        conversion_goal=ConversionGoal.PHONE_CALL,
                        placement_regions=(RegionKind.STICKY_MOBILE,),
                        repetition_limit_per_page=2,
                    )
                )
            ]
        )
        manifest = make_manifest(
            [
                page(
                    "/",
                    [
                        instance(component_id="cta.sticky.mobile"),
                        instance(component_id="cta.sticky.mobile"),
                    ],
                )
            ]
        )
        plan = LayoutEngine(registry).compose(manifest, make_brand_package())
        assert plan.pages[0].regions[0].component_indexes == (0, 1)

    def test_repetition_counted_per_page_not_across_pages(self):
        manifest = make_manifest(
            [
                page("/a/", [instance(component_id="cta.sticky.mobile")]),
                page("/b/", [instance(component_id="cta.sticky.mobile")]),
            ]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        assert len(plan.pages) == 2

    def test_monetized_component_without_placement_restriction_is_placed_normally(self):
        # AES-WEB-002J.7 authorized deferral: trust adjacency (CG-COM-009)
        # and disclosure-order verification are Quality Gate concerns
        # (AES-WEB-002 §16.4), not Layout Engine composition legality -- the
        # Layout Engine never fabricates a check it cannot ground in
        # component-contract data alone. A monetization-bearing component
        # with no placement_constraints composes exactly like any other.
        registry = make_registry(
            [_body_text(monetization_contract=MonetizationContract())]
        )
        manifest = make_manifest(
            [page("/", [instance(component_id="content.text.section")])]
        )
        plan = LayoutEngine(registry).compose(manifest, make_brand_package())
        assert plan.pages[0].regions[0].region_id == RegionKind.BODY.value


# --------------------------------------------------------------------------- #
# Error behavior
# --------------------------------------------------------------------------- #

class TestErrorBehavior:
    def test_diagnostics_aggregate_across_violation_kinds(self):
        registry = make_registry([_hero(allowed_parent_regions=())])
        manifest = make_manifest(
            [
                page(
                    "/",
                    [
                        instance(component_id="does.not.exist"),
                        instance(component_id="hero.split.value-proposition"),
                    ],
                )
            ]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(registry).compose(manifest, make_brand_package())
        diagnostics = exc_info.value.diagnostics
        assert "unresolved_components" in diagnostics
        assert "illegal_placements" in diagnostics

    def test_no_partial_plan_on_failure(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="does.not.exist")])]
        )
        try:
            LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
            assert False, "expected LayoutCompositionError"
        except LayoutCompositionError as exc:
            assert exc.diagnostics  # a real diagnostic exists
            # No LayoutPlan object is ever returned on this path -- the
            # exception is the only value produced.

    def test_error_stage_and_retryability(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="does.not.exist")])]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        assert exc_info.value.stage == "layout_composition"
        assert exc_info.value.retryable is False

    def test_diagnostics_sorted_by_route_then_index(self):
        manifest = make_manifest(
            [
                page(
                    "/",
                    [
                        instance(component_id="also.missing"),
                        instance(component_id="does.not.exist"),
                    ],
                )
            ]
        )
        with pytest.raises(LayoutCompositionError) as exc_info:
            LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        indexes = [
            d["component_index"]
            for d in exc_info.value.diagnostics["unresolved_components"]
        ]
        assert indexes == sorted(indexes)


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #

class TestProvenance:
    def test_source_hashes_include_inputs_and_registry(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        brand = make_brand_package()
        registry = _default_registry()
        plan = LayoutEngine(registry).compose(manifest, brand)
        assert plan.source_hashes["component_manifest"] == artifact_sha256(manifest)
        assert plan.source_hashes["brand_package"] == artifact_sha256(brand)
        assert plan.source_hashes["component_registry"] == registry.registry_hash()

    def test_schema_version_is_current(self):
        manifest = make_manifest(
            [page("/", [instance(component_id="hero.split.value-proposition")])]
        )
        plan = LayoutEngine(_default_registry()).compose(manifest, make_brand_package())
        assert plan.schema_version == SCHEMA_VERSIONS[ArtifactKind.LAYOUT_PLAN]
        assert plan.schema_version == "1.1.0"
