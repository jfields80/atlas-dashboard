"""Component Engine tests (AES-WEB-002J.6/J.19; AES-WEB-001 §5.5,
AES-WEB-002 §14/§26; ADR-WEB-CONTENT-BINDING-MAP).

Deterministic throughout: no clock/UUID/randomness. Covers the public
surface and version, golden recipe resolution against the real registered
catalog (now bindability-aware, AES-WEB-002J.19), the embedded §14.3
SelectionTrace (ADR-14), full Phase-B value/content binding and the §5.5
unbound-required-field compile error, selection-pipeline integration
through the engine (lifecycle/compatibility/injected-registry), the
role->recipe map, batch error reporting, and edge cases.

AES-WEB-002J.19 supersedes the AES-WEB-002J.6 "Option A deferred" binding
scope: ``compile()`` now returns a ``ComponentCompilationResult`` (bound
``ComponentManifest`` + companion ``ContentPackage``), and the previously
golden ``home``/``category`` recipe outputs change because bindability-aware
selection now excludes architecturally-unbindable candidates
(``directory.categories.grid``, ``directory.filters.panel``, ...) in favor
of their declared fallbacks -- or, where a required recipe slot has *no*
fallback and its only real candidate is architecturally unbindable
(``category``'s ``pagination``/``zero_results``), the whole compile now
honestly fails rather than silently leaving props/content unbound. Tests
that previously exercised ``category`` are updated to either supply the
bindable ``business-profile`` role instead, or to assert the new honest
failure directly (see ``TestGoldenRealCatalog.
test_category_recipe_honestly_fails_pagination_and_zero_results_unbindable``).

Tests exercise only the public surface (``engines.website_generation`` /
``components``) plus the shared ``make_definition`` fixture, per AES-WEB-001
§3.4 -- never the engine's internal helpers.
"""

from __future__ import annotations

import pytest

from engines.website_generation.brand.brand_engine import BrandEngine
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
    BusinessSpec,
    ComponentCompilationResult,
    ComponentManifest,
    ContentBlock,
    ContentPackage,
    ListingCategory,
    ListingDataset,
    ListingRecord,
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
_BUSINESS_PROFILE_PAGE = PagePlan(
    route="/hotels/lakeview-lodge/", page_type="business-profile", title=""
)


def _ids(page_components):
    return [inst.component_id for inst in page_components.components]


def _page(manifest, route):
    return next(p for p in manifest.pages if p.route == route)


def _brand():
    """A real, deterministic BrandPackage (AES-WEB-002J.19 Phase-B input) --
    the pure Brand Engine over a fixed inline spec, mirroring the
    established local-demo-fixture precedent."""
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name="Test Directory",
        niche="test niche",
        audience="test audience",
        value_proposition="test value proposition",
    )
    return BrandEngine().resolve(spec)


def _home_blocks():
    """Every editorial block a bindability-aware home-recipe compile needs
    (hero.search.directory's h1/subhead, nav.utility.bar's message; "intro"
    is unused by the components home currently selects but included for
    parity with the IA vocabulary)."""
    return [
        ContentBlock(page_route="/", slot_id="hero_h1", text="Find pet-friendly places to stay"),
        ContentBlock(page_route="/", slot_id="intro", text="Browse trusted, pet-welcoming businesses."),
        ContentBlock(page_route="/", slot_id="subhead", text="Verified hotels, parks, and restaurants."),
        ContentBlock(page_route="/", slot_id="message", text="Some listings are sponsored and labeled."),
    ]


def _listing_dataset():
    """One real, fully-populated listing (AES-WEB-002J.19 Phase-B input) --
    enough to satisfy every currently-bindable business-profile field
    (name, description, contact, hours, rating, credentials)."""
    from engines.website_generation.contracts.artifacts import (
        ListingAddress,
        ListingContact,
        ListingHoursEntry,
        ListingRating,
    )
    from engines.website_generation.contracts.enums import Weekday

    category = ListingCategory(category_id="cat-hotels", label="Hotels", slug="hotels")
    listing = ListingRecord(
        listing_id="lakeview-lodge",
        business_name="Lakeview Lodge",
        slug="lakeview-lodge",
        category_id="cat-hotels",
        description="A lakeside lodge that welcomes pets.",
        contact=ListingContact(phone="555-0100", email="stay@lakeview.example"),
        address=ListingAddress(city="Austin", state="TX"),
        hours=(ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),),
        rating=ListingRating(rating_hundredths=450, review_count=27),
        credentials=("Licensed pet boarding operator",),
    )
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET,
        source_hashes={},
        listings=(listing,),
        categories=(category,),
        locations=(),
    )


# --------------------------------------------------------------------------- #
# Public surface + version
# --------------------------------------------------------------------------- #

class TestPublicSurfaceAndVersion:
    def test_is_interface_subclass(self):
        assert issubclass(ComponentEngine, ComponentEngineInterface)

    def test_version_pinned(self):
        # AES-WEB-002J.19: 1.0.0 -> 1.1.0 (Phase-B binding is a §5.5
        # behavior change; see contracts/versions.py).
        assert ComponentEngine.version == ENGINE_VERSIONS["component_engine"]
        assert ComponentEngine.version == "1.1.0"

    def test_compile_returns_component_compilation_result(self):
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        assert isinstance(result, ComponentCompilationResult)
        assert isinstance(result.component_manifest, ComponentManifest)
        assert isinstance(result.content_package, ContentPackage)


# --------------------------------------------------------------------------- #
# Golden output — real registered catalog
# --------------------------------------------------------------------------- #

class TestGoldenRealCatalog:
    def test_home_recipe_resolves_expected_components(self):
        # AES-WEB-002J.19: directory.categories.grid declares a required
        # STRUCTURED_DEFERRED field (category_source_ref/category_tiles --
        # tile label+href is not representable by flat ContentBlock text,
        # ADR-WEB-CONTENT-BINDING-MAP) so bindability-aware selection now
        # excludes it in favor of its declared fallback, layout.grid.standard.
        # directory.locations.grid is likewise excluded, and -- because its
        # recipe slot is optional with no fallback -- silently dropped
        # (unchanged §26 doctrine for a slot with no bindable winner).
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        assert _ids(_page(result.component_manifest, "/")) == [
            "nav.utility.bar",
            "hero.search.directory",
            "layout.grid.standard",
        ]

    def test_category_recipe_honestly_fails_pagination_unbindable(self):
        # AES-WEB-002J.19 finding (J.19 architectural preflight §17/§28): the
        # category recipe's "pagination" and "zero_results" slots are both
        # required with NO declared fallback, and their only real candidates
        # (nav.pagination.standard: page_context is SOURCE_UNAVAILABLE;
        # status.results.zero: recovery_links is STRUCTURED_DEFERRED) are
        # both categorically unbindable. No amount of supplied content,
        # listing data, or brand data changes this -- it is an architectural
        # gap, not a data gap -- so the category recipe cannot fully bind
        # until a future sprint adds a source for one of those two fields.
        #
        # The selector's pre-J.19 fail-fast-per-page behavior (unchanged by
        # J.19: a required slot with no survivor raises immediately, See
        # ComponentSelector._select_slot's step 9) means only the *first*
        # unfillable required slot in the recipe's declared order actually
        # surfaces per attempt -- "pagination" precedes "zero_results" in
        # CATEGORY_RECIPE_SLOTS, so it is the one observed here. Because the
        # whole page's selection fails before Phase B ever runs, none of the
        # page's other components (including hero.local.standard) are
        # attempted -- this is a selection-level failure, reported under
        # "unresolved_required_slots", not a Phase-B binding failure.
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([_CATEGORY_PAGE]),
                _cp([
                    ContentBlock(page_route="/c/vets", slot_id="hero_h1", text="Pet-friendly vets"),
                    ContentBlock(page_route="/c/vets", slot_id="intro", text="Vets that welcome your pets warmly."),
                ]),
                listing_dataset=_listing_dataset(),
                brand_package=_brand(),
            )
        diagnostics = exc.value.diagnostics
        assert "unresolved_required_slots" in diagnostics
        entry = diagnostics["unresolved_required_slots"][0]
        assert entry["route"] == "/c/vets"
        assert entry["diagnostics"]["slot_id"] == "/c/vets#pagination"
        # Every candidate that reached the pool was eliminated -- naming
        # nav.pagination.standard (the real, categorically-unbindable
        # candidate) among them proves this is the expected architectural
        # gap, not an unrelated selection bug.
        eliminated_ids = {c["component_id"] for c in entry["diagnostics"]["candidates"]}
        assert "nav.pagination.standard" in eliminated_ids

    def test_manifest_header_and_provenance(self):
        sa, cp, brand = _sa([_HOME_PAGE]), _cp(_home_blocks()), _brand()
        result = ComponentEngine().compile(sa, cp, brand_package=brand)
        manifest = result.component_manifest
        assert manifest.artifact_kind is ArtifactKind.COMPONENT_MANIFEST
        assert manifest.schema_version == SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST]
        assert manifest.schema_version == "1.1.0"
        assert manifest.source_hashes == {
            "site_architecture": artifact_sha256(sa),
            "content_package": artifact_sha256(cp),
            "brand_package": artifact_sha256(brand),
            "binding_map_version": "1.0.0",
        }

    def test_content_refs_populated_when_bindable(self):
        # AES-WEB-002J.19 supersedes the AES-WEB-002J.6 "Option A deferred"
        # scope this test used to pin (content_refs always empty). Every
        # selected instance's required content slots are now bound to real
        # ContentBlocks -- content_refs is non-empty exactly where a
        # component declares required content slots.
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        page = _page(result.component_manifest, "/")
        with_slots = {
            inst.component_id: inst.content_refs
            for inst in page.components
            if inst.content_refs
        }
        assert with_slots == {
            "nav.utility.bar": ("message",),
            "hero.search.directory": ("h1", "subhead"),
        }

    def test_all_eighteen_roles_with_no_binding_inputs_honestly_fails(self):
        # AES-WEB-002J.19 supersedes the AES-WEB-002J.6 "every role at least
        # partially resolves" premise: Phase B now requires real data for
        # every selected required field. With no ContentPackage blocks, no
        # ListingDataset, and no BrandPackage, essentially every role's
        # selected components have some required field with no source --
        # proving Phase B is honestly enforced (no placeholder fallback),
        # never a silent partial success.
        pages = tuple(
            PagePlan(route="/r/%d" % i, page_type=role.value, title=role.value)
            for i, role in enumerate(PageRole)
        )
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa(pages), _cp())
        assert exc.value.diagnostics  # at least one failure bucket populated

    def test_page_order_preserved(self):
        pages = [_BUSINESS_PROFILE_PAGE, _HOME_PAGE]  # deliberately not sorted
        result = ComponentEngine().compile(
            _sa(pages), _cp(_home_blocks()),
            listing_dataset=_listing_dataset(), brand_package=_brand(),
        )
        assert [p.route for p in result.component_manifest.pages] == [
            "/hotels/lakeview-lodge/", "/",
        ]


# --------------------------------------------------------------------------- #
# SelectionTrace (§14.3, ADR-14)
# --------------------------------------------------------------------------- #

class TestSelectionTrace:
    def test_trace_embedded(self):
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        manifest = result.component_manifest
        assert manifest.selection_trace is not None
        assert manifest.selection_trace.slots  # non-empty

    def test_trace_slot_ids_route_qualified(self):
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE, _BUSINESS_PROFILE_PAGE]), _cp(_home_blocks()),
            listing_dataset=_listing_dataset(), brand_package=_brand(),
        )
        slot_ids = [s.slot_id for s in result.component_manifest.selection_trace.slots]
        # Every slot id carries its page route, so same-named slots across
        # pages ("hero") are disambiguated -- "why this component on this page".
        assert "/#hero" in slot_ids
        assert "/hotels/lakeview-lodge/#profile_header" in slot_ids
        assert all("#" in sid for sid in slot_ids)

    def test_trace_chosen_matches_instances(self):
        result = ComponentEngine().compile(
            _sa([_BUSINESS_PROFILE_PAGE]), _cp(),
            listing_dataset=_listing_dataset(), brand_package=_brand(),
        )
        manifest = result.component_manifest
        page = _page(manifest, "/hotels/lakeview-lodge/")
        chosen = [
            s.chosen_component_id
            for s in manifest.selection_trace.slots
            if s.slot_id.startswith("/hotels/lakeview-lodge/#") and s.chosen_component_id
        ]
        assert chosen == _ids(page)

    def test_trace_records_score_and_tiebreak(self):
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        hero = next(
            s for s in result.component_manifest.selection_trace.slots
            if s.slot_id == "/#hero"
        )
        assert hero.chosen_component_id == "hero.search.directory"
        assert hero.tie_break_basis  # a survivor ranked => basis recorded
        winner = next(
            c for c in hero.candidates
            if c.component_id == "hero.search.directory"
        )
        assert winner.score is not None

    def test_trace_hashes_with_manifest(self):
        # §14.3: the embedded trace "hashes with the manifest". Dropping it
        # must change the artifact hash.
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        manifest = result.component_manifest
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
        sa = _sa([_HOME_PAGE, _BUSINESS_PROFILE_PAGE])
        cp = _cp(_home_blocks())
        ld, brand = _listing_dataset(), _brand()
        a = ComponentEngine().compile(sa, cp, listing_dataset=ld, brand_package=brand)
        b = ComponentEngine().compile(sa, cp, listing_dataset=ld, brand_package=brand)  # fresh engine instance
        assert artifact_sha256(a.component_manifest) == artifact_sha256(b.component_manifest)
        assert artifact_sha256(a.content_package) == artifact_sha256(b.content_package)

    def test_content_block_order_independence(self):
        sa = _sa([_HOME_PAGE])
        reorderable = [
            ContentBlock(page_route="/", slot_id="hero_h1", text="A"),
            ContentBlock(page_route="/", slot_id="intro", text="B"),
        ]
        fixed = [
            ContentBlock(page_route="/", slot_id="subhead", text="C"),
            ContentBlock(page_route="/", slot_id="message", text="D"),
        ]
        brand = _brand()
        forward = ComponentEngine().compile(
            sa, _cp(reorderable + fixed), brand_package=brand
        )
        reverse = ComponentEngine().compile(
            sa, _cp(list(reversed(reorderable)) + fixed), brand_package=brand
        )
        # ContentPackage input order must not affect the manifest (it is only
        # hashed for provenance) — but the two ContentPackages differ, so the
        # content_package source hash differs; compare the pages + trace only.
        assert forward.component_manifest.pages == reverse.component_manifest.pages
        assert forward.component_manifest.selection_trace == reverse.component_manifest.selection_trace


# --------------------------------------------------------------------------- #
# Prop binding (§5.5) -- literal, reference, and the compile-time
# role-typed-enum contradiction
# --------------------------------------------------------------------------- #

class TestPropBinding:
    def test_value_layer_props_bound_when_data_supplied(self):
        # AES-WEB-002J.19 supersedes the AES-WEB-002J.6 "left unbound" scope
        # this test used to pin. listing.card.standard's listing_ref
        # (LISTING_REF) and density (STR_ENUM) are now both bound.
        result = ComponentEngine().compile(
            _sa([_BUSINESS_PROFILE_PAGE]), _cp(),
            listing_dataset=_listing_dataset(), brand_package=_brand(),
        )
        card = next(
            inst for inst in _page(result.component_manifest, "/hotels/lakeview-lodge/").components
            if inst.component_id == "listing.card.standard"
        )
        assert card.props["density"] in ("comfortable", "compact")
        assert card.props["listing_ref"].startswith("bind.listing_name.")
        block = next(
            b for b in result.content_package.blocks if b.slot_id == card.props["listing_ref"]
        )
        assert block.text == "Lakeview Lodge"

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
        # catalog resolves (selection succeeds) without explicit flags --
        # Phase B then honestly fails for lack of content/brand data, which
        # is a distinct, expected concern from lifecycle filtering.
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa([_HOME_PAGE]), _cp())
        # Proves selection (not lifecycle filtering) reached Phase B:
        # the failure is a binding gap, not "unresolved_required_slots".
        assert "unresolved_required_slots" not in exc.value.diagnostics


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
        result = ComponentEngine().compile(_sa([]), _cp())
        manifest = result.component_manifest
        assert manifest.pages == ()
        assert manifest.selection_trace is not None
        assert manifest.selection_trace.slots == ()

    def test_optional_unbuilt_slots_dropped_but_traced(self):
        # home's featured_zone is optional and points at an unbuilt family;
        # it must not become an instance, but it is still traced (with no
        # chosen component) per §26 / §14.2 step 9.
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        manifest = result.component_manifest
        assert "monetization.sponsor.featured" not in _ids(_page(manifest, "/"))
        featured = next(
            s for s in manifest.selection_trace.slots
            if s.slot_id == "/#featured_zone"
        )
        assert featured.chosen_component_id == ""

    def test_optional_architecturally_unbindable_slot_dropped_but_traced(self):
        # AES-WEB-002J.19: home's locations_grid slot is optional with no
        # fallback; directory.locations.grid is categorically unbindable
        # (location_source_ref/location_tiles are STRUCTURED_DEFERRED), so
        # bindability-aware selection drops it exactly like an unbuilt-family
        # slot -- no instance, but still traced with no chosen component.
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        manifest = result.component_manifest
        assert "directory.locations.grid" not in _ids(_page(manifest, "/"))
        locations = next(
            s for s in manifest.selection_trace.slots
            if s.slot_id == "/#locations_grid"
        )
        assert locations.chosen_component_id == ""

    def test_empty_page_source_hashes_still_present(self):
        result = ComponentEngine().compile(_sa([]), _cp())
        assert set(result.component_manifest.source_hashes) == {
            "site_architecture", "content_package", "binding_map_version",
        }
