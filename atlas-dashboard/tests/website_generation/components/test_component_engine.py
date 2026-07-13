"""Component Engine tests (AES-WEB-002J.6; AES-WEB-001 §5.5, AES-WEB-002 §14/§26).

Deterministic throughout: no clock/UUID/randomness. Covers the public surface
and version, golden recipe resolution against the real registered catalog,
the embedded §14.3 SelectionTrace (ADR-14), role-derivable prop binding and
the §5.5 unbound-required-prop compile error, selection-pipeline integration
through the engine (lifecycle/compatibility/injected-registry), the
role->recipe map, batch error reporting, and edge cases.

Tests exercise only the public surface (``engines.website_generation`` /
``components``) plus the shared ``make_definition`` fixture, per AES-WEB-001
§3.4 -- never the engine's internal helpers.
"""

from __future__ import annotations

import pytest

from engines.website_generation.components import (
    ComponentEngine,
    ComponentRegistry,
    build_default_registry,
)
from engines.website_generation.components.selection import LifecycleBuildFlags
from engines.website_generation.constants.components import (
    DEFAULT_COMPATIBILITY_VERSIONS,
    RECIPE_SLOTS_BY_PAGE_ROLE,
)
from engines.website_generation.contracts.artifacts import (
    ComponentManifest,
    ContentBlock,
    ContentPackage,
    PagePlan,
    SiteArchitecture,
    artifact_sha256,
    canonical_artifact_json,
)
from engines.website_generation.contracts.components import PropSpec
from engines.website_generation.contracts.enums import (
    ArtifactKind,
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    PropType,
)
from engines.website_generation.contracts.errors import ComponentResolutionError
from engines.website_generation.contracts.interfaces import ComponentEngineInterface
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)

from engines.website_generation.contracts.components import (
    AnalyticsContract,
    RenderingContract,
)

from . import make_definition


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #

def _sa(pages, **overrides) -> SiteArchitecture:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
        pages=tuple(pages),
        nav_routes=(),
        sitemap_routes=tuple(p.route for p in pages),
    )
    fields.update(overrides)
    return SiteArchitecture(**fields)


def _cp(blocks=()) -> ContentPackage:
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )


_HOME_PAGE = PagePlan(route="/", page_type="home", title="Home")
_CATEGORY_PAGE = PagePlan(route="/c/vets", page_type="category", title="Vets")


def _ids(page_components):
    return [inst.component_id for inst in page_components.components]


def _page(manifest, route):
    return next(p for p in manifest.pages if p.route == route)


# --------------------------------------------------------------------------- #
# Public surface + version
# --------------------------------------------------------------------------- #

class TestPublicSurfaceAndVersion:
    def test_is_interface_subclass(self):
        assert issubclass(ComponentEngine, ComponentEngineInterface)

    def test_version_pinned(self):
        assert ComponentEngine.version == ENGINE_VERSIONS["component_engine"]
        assert ComponentEngine.version == "1.0.0"

    def test_compile_returns_component_manifest(self):
        manifest = ComponentEngine().compile(_sa([_HOME_PAGE]), _cp())
        assert isinstance(manifest, ComponentManifest)


# --------------------------------------------------------------------------- #
# Golden output — real registered catalog
# --------------------------------------------------------------------------- #

class TestGoldenRealCatalog:
    def test_home_recipe_resolves_expected_components(self):
        manifest = ComponentEngine().compile(_sa([_HOME_PAGE]), _cp())
        assert _ids(_page(manifest, "/")) == [
            "nav.utility.bar",
            "hero.search.directory",
            "directory.categories.grid",
            "directory.locations.grid",
        ]

    def test_category_recipe_resolves_expected_components(self):
        manifest = ComponentEngine().compile(_sa([_CATEGORY_PAGE]), _cp())
        assert _ids(_page(manifest, "/c/vets")) == [
            "hero.local.standard",
            "directory.filters.panel",
            "directory.sort.control",
            "directory.results.summary",
            "listing.card.standard",
            "nav.pagination.standard",
            "status.results.zero",
        ]

    def test_manifest_header_and_provenance(self):
        sa, cp = _sa([_HOME_PAGE]), _cp()
        manifest = ComponentEngine().compile(sa, cp)
        assert manifest.artifact_kind is ArtifactKind.COMPONENT_MANIFEST
        assert manifest.schema_version == SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST]
        assert manifest.schema_version == "1.1.0"
        assert manifest.source_hashes == {
            "site_architecture": artifact_sha256(sa),
            "content_package": artifact_sha256(cp),
        }

    def test_content_refs_deferred_empty(self):
        # Option A: content-value binding is deferred; content_refs stays ().
        manifest = ComponentEngine().compile(
            _sa([_HOME_PAGE, _CATEGORY_PAGE]), _cp()
        )
        for page in manifest.pages:
            for inst in page.components:
                assert inst.content_refs == ()

    def test_all_eighteen_roles_compile(self):
        pages = tuple(
            PagePlan(route="/r/%d" % i, page_type=role.value, title=role.value)
            for i, role in enumerate(PageRole)
        )
        manifest = ComponentEngine().compile(_sa(pages), _cp())
        assert len(manifest.pages) == len(PageRole) == 18
        # Every page resolves at least its required slots into instances.
        assert all(page.components for page in manifest.pages)

    def test_page_order_preserved(self):
        pages = [_CATEGORY_PAGE, _HOME_PAGE]  # deliberately not sorted
        manifest = ComponentEngine().compile(_sa(pages), _cp())
        assert [p.route for p in manifest.pages] == ["/c/vets", "/"]


# --------------------------------------------------------------------------- #
# SelectionTrace (§14.3, ADR-14)
# --------------------------------------------------------------------------- #

class TestSelectionTrace:
    def test_trace_embedded(self):
        manifest = ComponentEngine().compile(_sa([_HOME_PAGE]), _cp())
        assert manifest.selection_trace is not None
        assert manifest.selection_trace.slots  # non-empty

    def test_trace_slot_ids_route_qualified(self):
        manifest = ComponentEngine().compile(
            _sa([_HOME_PAGE, _CATEGORY_PAGE]), _cp()
        )
        slot_ids = [s.slot_id for s in manifest.selection_trace.slots]
        # Every slot id carries its page route, so same-named slots across
        # pages ("hero") are disambiguated -- "why this component on this page".
        assert "/#hero" in slot_ids
        assert "/c/vets#hero" in slot_ids
        assert all("#" in sid for sid in slot_ids)

    def test_trace_chosen_matches_instances(self):
        manifest = ComponentEngine().compile(_sa([_CATEGORY_PAGE]), _cp())
        page = _page(manifest, "/c/vets")
        chosen = [
            s.chosen_component_id
            for s in manifest.selection_trace.slots
            if s.slot_id.startswith("/c/vets#") and s.chosen_component_id
        ]
        assert chosen == _ids(page)

    def test_trace_records_score_and_tiebreak(self):
        manifest = ComponentEngine().compile(_sa([_CATEGORY_PAGE]), _cp())
        hero = next(
            s for s in manifest.selection_trace.slots
            if s.slot_id == "/c/vets#hero"
        )
        assert hero.chosen_component_id == "hero.local.standard"
        assert hero.tie_break_basis  # a survivor ranked => basis recorded
        winner = next(
            c for c in hero.candidates
            if c.component_id == "hero.local.standard"
        )
        assert winner.score is not None

    def test_trace_hashes_with_manifest(self):
        # §14.3: the embedded trace "hashes with the manifest". Dropping it
        # must change the artifact hash.
        manifest = ComponentEngine().compile(_sa([_HOME_PAGE]), _cp())
        without_trace = ComponentManifest(
            schema_version=manifest.schema_version,
            artifact_kind=manifest.artifact_kind,
            source_hashes=manifest.source_hashes,
            pages=manifest.pages,
        )
        assert manifest.selection_trace is not None
        assert without_trace.selection_trace is None
        assert artifact_sha256(manifest) != artifact_sha256(without_trace)
        assert "selection_trace" in canonical_artifact_json(manifest)


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_identical_inputs_identical_output(self):
        sa, cp = _sa([_HOME_PAGE, _CATEGORY_PAGE]), _cp()
        a = ComponentEngine().compile(sa, cp)
        b = ComponentEngine().compile(sa, cp)  # fresh engine instance
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_content_block_order_independence(self):
        sa = _sa([_HOME_PAGE])
        blocks = [
            ContentBlock(page_route="/", slot_id="hero_h1", text="A"),
            ContentBlock(page_route="/", slot_id="intro", text="B"),
        ]
        forward = ComponentEngine().compile(sa, _cp(blocks))
        reverse = ComponentEngine().compile(sa, _cp(list(reversed(blocks))))
        # ContentPackage input order must not affect the manifest (it is only
        # hashed for provenance) — but the two ContentPackages differ, so the
        # content_package source hash differs; compare the pages + trace only.
        assert forward.pages == reverse.pages
        assert forward.selection_trace == reverse.selection_trace


# --------------------------------------------------------------------------- #
# Role-derivable prop binding (§5.5)
# --------------------------------------------------------------------------- #

class TestRolePropBinding:
    def test_context_role_bound_to_page_role(self):
        manifest = ComponentEngine().compile(_sa([_CATEGORY_PAGE]), _cp())
        hero = _page(manifest, "/c/vets").components[0]
        assert hero.component_id == "hero.local.standard"
        assert hero.props == {"context_role": "category"}

    def test_value_layer_props_left_unbound(self):
        # directory.categories.grid declares category_source_ref
        # (CONTENT_BLOCK_REF) and columns (INT_BOUNDED) -- both value-layer,
        # not role-derivable, so they are deferred (props stays empty).
        manifest = ComponentEngine().compile(_sa([_HOME_PAGE]), _cp())
        grid = next(
            inst for inst in _page(manifest, "/").components
            if inst.component_id == "directory.categories.grid"
        )
        assert grid.props == {}

    def test_unbindable_required_role_prop_is_compile_error(self):
        # §5.5: an unbound required prop is a compile error *here*. Craft a
        # layout.section.container-shaped fallback that carries a role-typed
        # required prop whose enum excludes "submission"; both required
        # submission slots fall back to it, so binding runs and must raise.
        bad = make_definition(
            component_id="layout.section.container",
            component_family=ComponentFamily.LAYOUT,
            lifecycle_status=LifecycleStatus.ACTIVE,
            rendering_contract=RenderingContract(
                emitter_key="layout.section.container@1", class_prefix="ac-layout"
            ),
            analytics_contract=AnalyticsContract(
                impression_id="layout-section-container"
            ),
            required_props={
                "ctx": PropSpec(
                    prop_type=PropType.STR_ENUM,
                    enum_values=("home",),  # excludes "submission"
                    description="role-typed prop whose enum omits the host role",
                ),
            },
        )
        registry = ComponentRegistry([bad])
        page = PagePlan(route="/submit", page_type="submission", title="Submit")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa([page]), _cp(), registry=registry)
        diagnostics = exc.value.diagnostics
        assert "unbindable_required_props" in diagnostics
        offenders = diagnostics["unbindable_required_props"]
        assert any(
            o["component_id"] == "layout.section.container" and o["prop"] == "ctx"
            for o in offenders
        )


# --------------------------------------------------------------------------- #
# Selection-pipeline integration through the engine
# --------------------------------------------------------------------------- #

class TestSelectionIntegration:
    def test_injected_registry_is_used(self):
        # An empty registry cannot fill the home required slots -> failure,
        # proving the injected registry (not the default catalog) is consulted.
        with pytest.raises(ComponentResolutionError):
            ComponentEngine().compile(
                _sa([_HOME_PAGE]), _cp(), registry=ComponentRegistry([])
            )

    def test_strict_lifecycle_flags_reject_proposed_catalog(self):
        # Every registered component is PROPOSED; strict flags (no PROPOSED)
        # eliminate all candidates and fallbacks -> required slots unresolved.
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([_HOME_PAGE]), _cp(),
                lifecycle_flags=LifecycleBuildFlags(),
            )
        assert "unresolved_required_slots" in exc.value.diagnostics

    def test_incompatible_versions_reject_catalog(self):
        # Definitions pin renderer <2.0.0; a 2.x renderer fails compatibility.
        bad_versions = dict(DEFAULT_COMPATIBILITY_VERSIONS, renderer="2.0.0")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([_HOME_PAGE]), _cp(),
                compatibility_versions=bad_versions,
            )
        assert "unresolved_required_slots" in exc.value.diagnostics

    def test_default_flags_allow_proposed(self):
        # The default lifecycle flags allow PROPOSED, so the all-PROPOSED
        # catalog resolves without explicit flags.
        manifest = ComponentEngine().compile(_sa([_HOME_PAGE]), _cp())
        assert _page(manifest, "/").components


# --------------------------------------------------------------------------- #
# Role -> recipe map + unsupported roles
# --------------------------------------------------------------------------- #

class TestRecipeRoleMapping:
    def test_map_covers_every_page_role(self):
        assert set(RECIPE_SLOTS_BY_PAGE_ROLE) == {r.value for r in PageRole}

    def test_unknown_page_type_reported(self):
        page = PagePlan(route="/x", page_type="not-a-role", title="X")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa([page]), _cp())
        diagnostics = exc.value.diagnostics
        assert "unsupported_page_roles" in diagnostics
        assert diagnostics["unsupported_page_roles"] == [
            {"route": "/x", "page_type": "not-a-role"}
        ]


# --------------------------------------------------------------------------- #
# Batch error reporting
# --------------------------------------------------------------------------- #

class TestBatchErrorReporting:
    def test_multiple_unsupported_pages_batched_and_sorted(self):
        pages = [
            PagePlan(route="/z", page_type="bogus", title="Z"),
            PagePlan(route="/a", page_type="bogus", title="A"),
        ]
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa(pages), _cp())
        reported = exc.value.diagnostics["unsupported_page_roles"]
        assert [r["route"] for r in reported] == ["/a", "/z"]  # sorted by route

    def test_diagnostics_stage_label(self):
        page = PagePlan(route="/x", page_type="bogus", title="X")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa([page]), _cp())
        assert exc.value.stage == "component_resolution"


# --------------------------------------------------------------------------- #
# Edge cases
# --------------------------------------------------------------------------- #

class TestEdgeCases:
    def test_empty_site_architecture(self):
        manifest = ComponentEngine().compile(_sa([]), _cp())
        assert manifest.pages == ()
        assert manifest.selection_trace is not None
        assert manifest.selection_trace.slots == ()

    def test_optional_unbuilt_slots_dropped_but_traced(self):
        # home's featured_zone is optional and points at an unbuilt family;
        # it must not become an instance, but it is still traced (with no
        # chosen component) per §26 / §14.2 step 9.
        manifest = ComponentEngine().compile(_sa([_HOME_PAGE]), _cp())
        assert "monetization.sponsor.featured" not in _ids(_page(manifest, "/"))
        featured = next(
            s for s in manifest.selection_trace.slots
            if s.slot_id == "/#featured_zone"
        )
        assert featured.chosen_component_id == ""

    def test_empty_page_source_hashes_still_present(self):
        manifest = ComponentEngine().compile(_sa([]), _cp())
        assert set(manifest.source_hashes) == {"site_architecture", "content_package"}
